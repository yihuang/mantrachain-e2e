local config = import 'default.jsonnet';
local chain = (import 'chains.jsonnet')[std.extVar('CHAIN_CONFIG')];

config {
  'mantra-canary-net-1'+: {
    validators: [validator {
      gas_prices: '100' + chain.evm_denom,
    } for validator in super.validators],
    genesis+: {
      consensus+: {
        params+: {
          block+: {
            max_gas+: '81500000',
          },
        },
      },
      app_state+: {
        feemarket+: {
          params+: {
            base_fee_change_denominator: '3',
            elasticity_multiplier: '4',
            base_fee: '100',
            min_gas_price: '100',
          },
        },
      },
    },
  },
}
