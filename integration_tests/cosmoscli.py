import json
import subprocess
import tempfile

from pystarport.utils import build_cli_args_safe, interact

from .utils import DEFAULT_GAS, DEFAULT_GAS_PRICE, get_sync_info


class ChainCommand:
    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, cmd, *args, stdin=None, stderr=subprocess.STDOUT, **kwargs):
        "execute mantrachaind"
        args = " ".join(build_cli_args_safe(cmd, *args, **kwargs))
        return interact(f"{self.cmd} {args}", input=stdin, stderr=stderr)


class CosmosCLI:
    "the apis to interact with wallet and blockchain"

    def __init__(
        self,
        data_dir,
        node_rpc,
        cmd,
        chain_id=None,
    ):
        self.data_dir = data_dir
        genesis_path = self.data_dir / "config" / "genesis.json"
        if genesis_path.exists():
            self._genesis = json.loads(genesis_path.read_text())
            self.chain_id = self._genesis["chain_id"]
        else:
            self._genesis = {}
            self.chain_id = chain_id
        self.node_rpc = node_rpc
        self.raw = ChainCommand(cmd)
        self.output = None
        self.error = None

    @classmethod
    def init(cls, moniker, data_dir, node_rpc, cmd, chain_id):
        "the node's config is already added"
        ChainCommand(cmd)(
            "init",
            moniker,
            chain_id=chain_id,
            home=data_dir,
        )
        return cls(data_dir, node_rpc, cmd)

    def validators(self):
        return json.loads(
            self.raw(
                "query", "staking", "validators", output="json", node=self.node_rpc
            )
        )["validators"]

    def status(self):
        return json.loads(self.raw("status", node=self.node_rpc))

    def block_height(self):
        return int(get_sync_info(self.status())["latest_block_height"])

    def balances(self, addr, height=0):
        return json.loads(
            self.raw(
                "query",
                "bank",
                "balances",
                addr,
                height=height,
                output="json",
                home=self.data_dir,
                node=self.node_rpc,
            )
        )["balances"]

    def balance(self, addr, denom="uom", height=0):
        denoms = {
            coin["denom"]: int(coin["amount"])
            for coin in self.balances(addr, height=height)
        }
        return denoms.get(denom, 0)

    def address(self, name, bech="acc", field="address"):
        output = self.raw(
            "keys",
            "show",
            name,
            f"--{field}",
            home=self.data_dir,
            keyring_backend="test",
            bech=bech,
        )
        return output.strip().decode()

    def account(self, addr):
        return json.loads(
            self.raw(
                "query", "auth", "account", addr, output="json", node=self.node_rpc
            )
        )

    def transfer(
        self,
        from_,
        to,
        coins,
        generate_only=False,
        event_query_tx=True,
        fees=None,
        **kwargs,
    ):
        kwargs.setdefault("gas_prices", DEFAULT_GAS_PRICE)
        kwargs.setdefault("gas", DEFAULT_GAS)
        rsp = json.loads(
            self.raw(
                "tx",
                "bank",
                "send",
                from_,
                to,
                coins,
                "-y",
                "--generate-only" if generate_only else None,
                home=self.data_dir,
                fees=fees,
                **kwargs,
            )
        )
        if rsp.get("code") == 0 and event_query_tx:
            rsp = self.event_query_tx_for(rsp["txhash"])
        return rsp

    def event_query_tx_for(self, hash, **kwargs):
        default_kwargs = {
            "node": self.node_rpc,
            "output": "json",
        }
        return json.loads(
            self.raw(
                "query",
                "event-query-tx-for",
                hash,
                **(default_kwargs | kwargs),
            )
        )

    def query_all_txs(self, addr):
        txs = self.raw(
            "query",
            "txs-all",
            addr,
            home=self.data_dir,
            keyring_backend="test",
            node=self.node_rpc,
        )
        return json.loads(txs)

    def broadcast_tx(self, tx_file, **kwargs):
        kwargs.setdefault("broadcast_mode", "sync")
        kwargs.setdefault("output", "json")
        rsp = json.loads(
            self.raw("tx", "broadcast", tx_file, node=self.node_rpc, **kwargs)
        )
        if rsp["code"] == 0:
            rsp = self.event_query_tx_for(rsp["txhash"], **kwargs)
        return rsp

    def broadcast_tx_json(self, tx, **kwargs):
        with tempfile.NamedTemporaryFile("w") as fp:
            json.dump(tx, fp)
            fp.flush()
            return self.broadcast_tx(fp.name)

    def sign_tx(self, tx_file, signer, **kwargs):
        default_kwargs = {
            "home": self.data_dir,
            "keyring_backend": "test",
            "chain_id": self.chain_id,
            "node": self.node_rpc,
            "output": "json",
        }
        return json.loads(
            self.raw(
                "tx",
                "sign",
                tx_file,
                from_=signer,
                **(default_kwargs | kwargs),
            )
        )

    def sign_tx_json(self, tx, signer, max_priority_price=None, **kwargs):
        if max_priority_price is not None:
            tx["body"]["extension_options"].append(
                {
                    "@type": "/cosmos.evm.types.v1.ExtensionOptionDynamicFeeTx",
                    "max_priority_price": str(max_priority_price),
                }
            )
        with tempfile.NamedTemporaryFile("w") as fp:
            json.dump(tx, fp)
            fp.flush()
            return self.sign_tx(fp.name, signer, **kwargs)

    def create_account(self, name, mnemonic=None, **kwargs):
        "create new keypair in node's keyring"
        default_kwargs = {
            "home": self.data_dir,
            "output": "json",
            "keyring_backend": "test",
        }
        if mnemonic is None:
            output = self.raw(
                "keys",
                "add",
                name,
                **(default_kwargs | kwargs),
            )
        else:
            output = self.raw(
                "keys",
                "add",
                name,
                "--recover",
                stdin=mnemonic.encode() + b"\n",
                **(default_kwargs | kwargs),
            )
        return json.loads(output)

    def build_evm_tx(self, raw_tx: str, **kwargs):
        return json.loads(
            self.raw(
                "tx",
                "evm",
                "raw",
                raw_tx,
                "-y",
                "--generate-only",
                home=self.data_dir,
                **kwargs,
            )
        )

    def get_default_kwargs(self):
        return {
            "gas_prices": DEFAULT_GAS_PRICE,
            "gas": "auto",
            "gas_adjustment": "1.5",
        }

    def submit_gov_proposal(self, proposal, **kwargs):
        default_kwargs = self.get_default_kwargs()
        kwargs.setdefault("broadcast_mode", "sync")
        rsp = json.loads(
            self.raw(
                "tx",
                "gov",
                "submit-proposal",
                proposal,
                "-y",
                home=self.data_dir,
                node=self.node_rpc,
                stderr=subprocess.DEVNULL,
                **(default_kwargs | kwargs),
            )
        )
        if rsp["code"] == 0:
            rsp = self.event_query_tx_for(rsp["txhash"])
        return rsp

    def query_grant(self, granter, grantee):
        "query grant details by granter and grantee addresses"
        res = json.loads(
            self.raw(
                "query",
                "feegrant",
                "grant",
                granter,
                grantee,
                home=self.data_dir,
                node=self.node_rpc,
                output="json",
            )
        )
        res = res.get("allowance") or res
        return res

    def query_proposal(self, proposal_id):
        res = json.loads(
            self.raw(
                "query",
                "gov",
                "proposal",
                proposal_id,
                output="json",
                node=self.node_rpc,
            )
        )
        return res.get("proposal") or res

    def staking_pool(self, bonded=True):
        res = self.raw("query", "staking", "pool", output="json", node=self.node_rpc)
        res = json.loads(res)
        res = res.get("pool") or res
        return int(res["bonded_tokens" if bonded else "not_bonded_tokens"])

    def query_tally(self, proposal_id):
        res = json.loads(
            self.raw(
                "query",
                "gov",
                "tally",
                proposal_id,
                output="json",
                node=self.node_rpc,
            )
        )
        return res.get("tally") or res

    def gov_vote(self, voter, proposal_id, option, event_query_tx=True, **kwargs):
        default_kwargs = self.get_kwargs()
        rsp = json.loads(
            self.raw(
                "tx",
                "gov",
                "vote",
                proposal_id,
                option,
                "-y",
                from_=voter,
                **(default_kwargs | kwargs),
            )
        )
        if rsp["code"] == 0 and event_query_tx:
            rsp = self.event_query_tx_for(rsp["txhash"])
        return rsp

    def query_bank_send(self, *denoms):
        return json.loads(
            self.raw(
                "q",
                "bank",
                "send-enabled",
                *denoms,
                home=self.data_dir,
                output="json",
            )
        ).get("send_enabled", [])

    def make_multisig(self, name, signer1, signer2):
        self.raw(
            "keys",
            "add",
            name,
            multisig=f"{signer1},{signer2}",
            multisig_threshold="2",
            home=self.data_dir,
            keyring_backend="test",
        )

    def sign_multisig_tx(self, tx_file, multi_addr, signer_name):
        return json.loads(
            self.raw(
                "tx",
                "sign",
                tx_file,
                from_=signer_name,
                multisig=multi_addr,
                home=self.data_dir,
                keyring_backend="test",
                chain_id=self.chain_id,
                node=self.node_rpc,
            )
        )

    def combine_multisig_tx(self, tx_file, multi_name, signer1_file, signer2_file):
        return json.loads(
            self.raw(
                "tx",
                "multisign",
                tx_file,
                multi_name,
                signer1_file,
                signer2_file,
                home=self.data_dir,
                keyring_backend="test",
                chain_id=self.chain_id,
                node=self.node_rpc,
            )
        )

    def account_by_num(self, num):
        return json.loads(
            self.raw(
                "q",
                "auth",
                "address-by-acc-num",
                num,
                output="json",
                node=self.node_rpc,
            )
        )

    # TODO: remove after fix client ctx in v4
    def get_kwargs(self):
        return {
            "home": self.data_dir,
            "keyring_backend": "test",
            "chain_id": self.chain_id,
            "node": self.node_rpc,
            "output": "json",
        }

    def software_upgrade(self, proposer, proposal, **kwargs):
        default_kwargs = self.get_kwargs()
        rsp = json.loads(
            self.raw(
                "tx",
                "upgrade",
                "software-upgrade",
                proposal["name"],
                "-y",
                "--no-validate",
                from_=proposer,
                # content
                title=proposal.get("title"),
                note=proposal.get("note"),
                upgrade_height=proposal.get("upgrade-height"),
                upgrade_time=proposal.get("upgrade-time"),
                upgrade_info=proposal.get("upgrade-info"),
                summary=proposal.get("summary"),
                deposit=proposal.get("deposit"),
                # basic
                **(default_kwargs | kwargs),
            )
        )
        if rsp["code"] == 0:
            rsp = self.event_query_tx_for(rsp["txhash"])
        return rsp

    def get_params(self, module, **kwargs):
        kwargs.setdefault("node", self.node_rpc)
        kwargs.setdefault("output", "json")
        return json.loads(self.raw("q", module, "params", **kwargs))

    def query_base_fee(self, **kwargs):
        default_kwargs = {"home": self.data_dir}
        return json.loads(
            self.raw(
                "q",
                "feemarket",
                "base-fee",
                **(default_kwargs | kwargs),
            )
        )["base_fee"]
