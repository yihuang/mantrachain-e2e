local config = import 'default.jsonnet';

config {
  'mantra-canary-net-1'+: {
    validators: super.validators[:std.length(super.validators) - 1] + [super.validators[std.length(super.validators) - 1] {
      'app-config'+: {
        mempool: {
          'max-txs': -1,
        },
      },
    }],
    genesis+: {
      consensus_params: {
        block: {
          max_bytes: '3000000',
          max_gas: '300000000',
        },
      },
      app_state+: {
        evm:: super.evm,
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
            fee_denom: 'uom',
            enabled: true,
            distribute_fees: false,
          },
        },
      },
    },
  },
}
