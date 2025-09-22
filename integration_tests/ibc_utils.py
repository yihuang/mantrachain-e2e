import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

from pystarport import cluster, ports

from .network import Hermes, Mantra, setup_custom_mantra
from .utils import (
    CHAIN_ID,
    DEFAULT_DENOM,
    escrow_address,
    wait_for_new_blocks,
    wait_for_port,
)


class IBCNetwork(NamedTuple):
    ibc1: Mantra
    ibc2: Mantra
    hermes: Hermes | None


def call_hermes_cmd(hermes, incentivized, version):
    subprocess.check_call(
        [
            "hermes",
            "--config",
            hermes.configpath,
            "create",
            "channel",
            "--a-port",
            "transfer",
            "--b-port",
            "transfer",
            "--a-chain",
            CHAIN_ID,
            "--b-chain",
            "mantra-1",
            "--new-client-connection",
            "--yes",
        ]
        + (
            [
                "--channel-version",
                json.dumps(version),
            ]
            if incentivized
            else []
        )
    )


def prepare_network(tmp_path, name, chain):
    name = f"configs/{name}.jsonnet"
    with contextmanager(setup_custom_mantra)(
        tmp_path,
        27000,
        Path(__file__).parent / name,
        relayer=cluster.Relayer.HERMES.value,
        chain=chain,
    ) as ibc1:
        cli = ibc1.cosmos_cli()
        ibc2 = Mantra(ibc1.base_dir.parent / "mantra-1")
        # wait for grpc ready
        wait_for_port(ports.grpc_port(ibc2.base_port(0)))
        wait_for_port(ports.grpc_port(ibc1.base_port(0)))
        wait_for_new_blocks(ibc2.cosmos_cli(), 1)
        wait_for_new_blocks(cli, 1)
        version = {"fee_version": "ics29-1", "app_version": "ics20-1"}
        path = ibc1.base_dir.parent / "relayer"
        hermes = Hermes(path.with_suffix(".toml"))
        call_hermes_cmd(hermes, False, version)
        ibc1.supervisorctl("start", "relayer-demo")
        yield IBCNetwork(ibc1, ibc2, hermes)
        wait_for_port(hermes.port)


def hermes_transfer(
    ibc, src_chain, dst_chain, src_amount, dst_addr, denom=DEFAULT_DENOM, memo=None
):
    port = "transfer"
    channel = "channel-0"
    # wait for hermes
    output = subprocess.getoutput(
        f"curl -s -X GET 'http://127.0.0.1:{ibc.hermes.port}/state' | jq"
    )
    assert json.loads(output)["status"] == "success"
    cmd = (
        f"hermes --config {ibc.hermes.configpath} tx ft-transfer "
        f"--dst-chain {dst_chain} --src-chain {src_chain} --src-port {port} "
        f"--src-channel {channel} --amount {src_amount} "
        f"--timeout-height-offset 1000 --number-msgs 1 "
        f"--denom {denom} --receiver {dst_addr} --key-name relayer"
    )
    if memo:
        cmd += f" --memo '{memo}'"
    subprocess.run(cmd, check=True, shell=True)
    return f"{port}/{channel}/{denom}", escrow_address(port, channel)
