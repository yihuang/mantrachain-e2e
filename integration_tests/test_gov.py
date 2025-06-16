from .utils import (
    DEFAULT_DENOM,
    eth_to_bech32,
    module_address,
    submit_any_proposal,
    submit_gov_proposal,
)


def test_submit_any_proposal(mantra, tmp_path):
    submit_any_proposal(mantra, tmp_path)


def test_submit_send_enabled(mantra, tmp_path):
    # check bank send enable
    cli = mantra.cosmos_cli()
    denoms = [DEFAULT_DENOM, "stake"]
    assert len(cli.query_bank_send(*denoms)) == 0, "should be empty"
    send_enable = [
        {"denom": DEFAULT_DENOM},
        {"denom": "stake", "enabled": True},
    ]
    submit_gov_proposal(
        mantra,
        tmp_path,
        messages=[
            {
                "@type": "/cosmos.bank.v1beta1.MsgSetSendEnabled",
                "authority": eth_to_bech32(module_address("gov")),
                "sendEnabled": send_enable,
            }
        ],
    )
    assert cli.query_bank_send(*denoms) == send_enable
