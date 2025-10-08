import json
import os
import signal
import subprocess
from pathlib import Path

import _jsonnet
import tomlkit
import web3
from pystarport import cluster, ports
from pystarport.expansion import expand
from requests.exceptions import (
    HTTPError,
    Timeout,
    TooManyRedirects,
)
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider, WebSocketProvider
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc.utils import ExceptionRetryConfiguration

from .cosmoscli import CosmosCLI
from .utils import (
    CHAIN_ID,
    CMD,
    supervisorctl,
    wait_for_block,
    wait_for_port,
    wait_for_url,
)

RETRY_CONFIG = ExceptionRetryConfiguration(
    errors=(ConnectionError, HTTPError, Timeout, TooManyRedirects),
    retries=10,
)


class Mantra:
    def __init__(self, base_dir, chain_binary=CMD):
        self._w3 = None
        self._async_w3 = None
        self.base_dir = base_dir
        self.config = json.loads((base_dir / "config.json").read_text())
        self.chain_binary = chain_binary
        self._use_websockets = False

    def copy(self):
        return Mantra(self.base_dir)

    def w3_http_endpoint(self, i=0):
        port = ports.evmrpc_port(self.base_port(i))
        return f"http://localhost:{port}"

    def w3_ws_endpoint(self, i=0):
        port = ports.evmrpc_ws_port(self.base_port(i))
        return f"ws://localhost:{port}"

    @property
    def w3(self):
        if self._w3 is None:
            self._w3 = self.node_w3(0)
        return self._w3

    @property
    def async_w3(self, i=0):
        if self._async_w3 is None:
            self._async_w3 = self.async_node_w3(0)
        return self._async_w3

    def node_w3(self, i=0):
        if self._use_websockets:
            return web3.Web3(
                WebSocketProvider(
                    self.w3_ws_endpoint(i), exception_retry_configuration=RETRY_CONFIG
                )
            )
        else:
            return web3.Web3(
                HTTPProvider(
                    self.w3_http_endpoint(i), exception_retry_configuration=RETRY_CONFIG
                )
            )

    def async_node_w3(self, i=0):
        return AsyncWeb3(
            AsyncHTTPProvider(
                self.w3_http_endpoint(i),
                cache_allowed_requests=True,
                exception_retry_configuration=RETRY_CONFIG,
            ),
        )

    def base_port(self, i):
        return self.config["validators"][i]["base_port"]

    def node_rpc(self, i):
        return "tcp://127.0.0.1:%d" % ports.rpc_port(self.base_port(i))

    def cosmos_cli(self, i=0) -> CosmosCLI:
        return CosmosCLI(self.node_home(i), self.node_rpc(i), self.chain_binary)

    def node_home(self, i=0):
        return self.base_dir / f"node{i}"

    def use_websocket(self, use=True):
        self._w3 = None
        self._use_websockets = use

    def supervisorctl(self, *args):
        return supervisorctl(self.base_dir / "../tasks.ini", *args)


class Hermes:
    def __init__(self, config: Path):
        self.configpath = config
        self.config = tomlkit.loads(config.read_text())
        self.port = 3000


class ConnectMantra:
    def __init__(self, rpc, evm_rpc, evm_rpc_ws, chain_id, chain_binary="mantrachaind"):
        self._w3 = None
        self._async_w3 = None
        self.rpc = rpc
        self.evm_rpc = evm_rpc
        self.evm_rpc_ws = evm_rpc_ws
        self.chain_id = chain_id
        self.chain_binary = chain_binary
        self._use_websockets = False

    @property
    def w3(self):
        if self._w3 is None:
            self._w3 = self.node_w3()
        return self._w3

    @property
    def async_w3(self):
        if self._async_w3 is None:
            self._async_w3 = self.async_node_w3()
        return self._async_w3

    def node_w3(self):
        if self._use_websockets:
            return web3.Web3(
                WebSocketProvider(
                    self.evm_rpc_ws, exception_retry_configuration=RETRY_CONFIG
                )
            )
        else:
            return web3.Web3(
                HTTPProvider(self.evm_rpc, exception_retry_configuration=RETRY_CONFIG)
            )

    def async_node_w3(self):
        return AsyncWeb3(
            AsyncHTTPProvider(
                self.evm_rpc,
                cache_allowed_requests=True,
                exception_retry_configuration=RETRY_CONFIG,
            )
        )

    def cosmos_cli(self, home) -> CosmosCLI:
        return CosmosCLI(home, self.rpc, self.chain_binary, self.chain_id)

    def use_websocket(self, use=True):
        self._w3 = None
        self._use_websockets = use


def setup_mantra(path, base_port, chain):
    cfg = Path(__file__).parent / ("configs/enable-indexer.jsonnet")
    yield from setup_custom_mantra(path, base_port, cfg, chain=chain)


def setup_custom_mantra(
    path,
    base_port,
    config,
    post_init=None,
    chain_binary=None,
    wait_port=True,
    relayer=cluster.Relayer.HERMES.value,
    genesis=None,
    chain=None,
):
    assert config.suffix == ".jsonnet"

    # expand jsonnet with ext vars
    data = json.loads(
        _jsonnet.evaluate_file(str(config), ext_vars={"CHAIN_CONFIG": chain})
    )
    data = expand(data, None, config)
    config = path / "expanded_config.json"
    config.write_text(json.dumps(data, indent=2))

    cmd = [
        "pystarport",
        "init",
        "--config",
        config,
        "--data",
        path,
        "--base_port",
        str(base_port),
        "--no_remove",
    ]
    if relayer == cluster.Relayer.RLY.value:
        cmd = cmd + ["--relayer", str(relayer)]
    if chain_binary is not None:
        cmd = cmd[:1] + ["--cmd", chain_binary] + cmd[1:]
    print(*cmd)
    subprocess.run(cmd, check=True)
    if post_init is not None:
        post_init(path, base_port, config, genesis)
    proc = subprocess.Popen(
        ["pystarport", "start", "--data", path, "--quiet"],
        preexec_fn=os.setsid,
    )
    try:
        if wait_port:
            wait_for_port(ports.rpc_port(base_port))
        c = Mantra(path / CHAIN_ID, chain_binary=chain_binary or chain)
        wait_for_block(c.cosmos_cli(), 1)
        yield c
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        # proc.terminate()
        proc.wait()


def connect_custom_mantra():
    rpc = os.getenv("RPC", "http://127.0.0.1:26657")
    evm_rpc = os.getenv("EVM_RPC", "http://127.0.0.1:26651")
    evm_rpc_ws = os.getenv("EVM_RPC_WS", "ws://127.0.0.1:26652")
    wait_for_url(rpc)
    wait_for_url(evm_rpc)
    yield ConnectMantra(rpc, evm_rpc, evm_rpc_ws, CHAIN_ID, chain_binary=CMD)


class Geth:
    def __init__(self, w3, async_w3):
        self.w3 = w3
        self.async_w3 = async_w3


def setup_geth(path, base_port):
    with (path / "geth.log").open("w") as logfile:
        cmd = [
            "start-geth",
            path,
            "--http.port",
            str(base_port),
            "--port",
            str(base_port + 1),
            "--miner.etherbase",
            "0x57f96e6B86CdeFdB3d412547816a82E3E0EbF9D2",
            "--http.api",
            "eth,net,web3,debug",
        ]
        print(*cmd)
        proc = subprocess.Popen(
            cmd,
            preexec_fn=os.setsid,
            stdout=logfile,
            stderr=subprocess.STDOUT,
        )
        try:
            wait_for_port(base_port)
            url = f"http://127.0.0.1:{base_port}"
            w3 = web3.Web3(HTTPProvider(url))
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            async_w3 = AsyncWeb3(AsyncHTTPProvider(url, cache_allowed_requests=True))
            async_w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            yield Geth(w3, async_w3)
        finally:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            # proc.terminate()
            proc.wait()
