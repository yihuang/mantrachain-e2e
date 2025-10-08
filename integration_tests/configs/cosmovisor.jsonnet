local config = import 'default.jsonnet';
local chain = (import 'chains.jsonnet')[std.extVar('CHAIN_CONFIG')];

config {
  'mantra-canary-net-1'+: {
    'app-config'+: {
      evm+: {
        'evm-chain-id': 5887,
      },
    },
    validators: [validator {
      'coin-type':: validator['coin-type'],
      'app-config'+: {
        mempool: {
          'max-txs': -1,  // TODO: wait fix sender release
        },
      },
    } for validator in super.validators],
    accounts: [account {
      'coin-type':: account['coin-type'],
    } for account in super.accounts],
    genesis+: {
      consensus_params: {
        block: {
          max_bytes: '3000000',
          max_gas: '300000000',
        },
      },
      app_state+: {
        evm:: super.evm,
        erc20:: super.erc20,
        feemarket: {
          params: {
            alpha: '0.000000000000000000',
            beta: '1.000000000000000000',
            gamma: '0.000000000000000000',
            delta: '0.000000000000000000',
            min_base_gas_price: '0.010000000000000000',
            min_learning_rate: '0.125000000000000000',
            max_learning_rate: '0.125000000000000000',
            max_block_utilization: '75000000',
            window: '1',
            fee_denom: chain.evm_denom,
            enabled: true,
            distribute_fees: false,
          },
        },
      },
    },
  },
}
