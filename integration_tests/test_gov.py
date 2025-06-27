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
    cli = mantra.cosmos_cli()
    sender = "community"
    addr_a = cli.address(sender)
    addr_b = cli.address("reserve")
    subdenom = "test"
    transfer_amt = 1
    gas = 300000
    # check create tokenfactory denom
    rsp = cli.create_tokenfactory_denom(subdenom, _from=sender)
    assert rsp["code"] == 0, rsp["raw_log"]
    rsp = cli.query_tokenfactory_denoms(addr_a)
    denom = f"factory/{addr_a}/{subdenom}"
    assert denom in rsp.get("denoms"), rsp
    balance = cli.balance(addr_a, denom)
    amt = 10**6
    coin = f"{amt}{denom}"
    # check mint tokenfactory denom
    rsp = cli.mint_tokenfactory_denom(coin, _from=sender, gas=gas)
    assert rsp["code"] == 0, rsp["raw_log"]
    current = cli.balance(addr_a, denom)
    assert current == balance + amt
    balance = current
    # check transfer tokenfactory denom
    rsp = cli.transfer(addr_a, addr_b, f"{transfer_amt}{denom}")
    assert rsp["code"] == 0, rsp["raw_log"]
    current = cli.balance(addr_a, denom)
    assert current == balance - transfer_amt
    balance = current
    # check burn tokenfactory denom
    burn_amt = 10**3
    coin = f"{burn_amt}{denom}"
    rsp = cli.burn_tokenfactory_denom(coin, _from=sender, gas=gas)
    assert rsp["code"] == 0, rsp["raw_log"]
    current = cli.balance(addr_a, denom)
    assert current == balance - burn_amt
    balance = current
    # check disable send for denom
    denoms = [DEFAULT_DENOM, denom]
    assert len(cli.query_bank_send(*denoms)) == 0, "should be empty"
    send_enable = [
        {"denom": DEFAULT_DENOM, "enabled": True},
        {"denom": denom},
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
    rsp = cli.transfer(addr_a, addr_b, f"1{denom}")
    assert rsp["code"] != 0
    assert "send transactions are disabled" in rsp["raw_log"]
    # check mint and burn again
    coin = f"{amt}{denom}"
    rsp = cli.mint_tokenfactory_denom(coin, _from=sender, gas=gas)
    assert rsp["code"] == 0, rsp["raw_log"]
    current = cli.balance(addr_a, denom)
    assert current == balance + amt
    balance = current

    coin = f"{burn_amt}{denom}"
    rsp = cli.burn_tokenfactory_denom(coin, _from=sender, gas=gas)
    assert rsp["code"] == 0, rsp["raw_log"]
    current = cli.balance(addr_a, denom)
    assert current == balance - burn_amt
    balance = current
