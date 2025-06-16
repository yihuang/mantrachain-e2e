local config = import 'default.jsonnet';

config {
  'mantra_5887-1'+: {
    validators: [validator {
      gas_prices: '10000000000000uom',
    } for validator in super.validators],
    genesis+: {
      app_state+: {
        feemarket+: {
          params+: {
            base_fee_change_denominator: '3',
            elasticity_multiplier: '4',
            base_fee: '10000000000000',
            min_gas_price: '10000000000000',
          },
        },
      },
    },
  },
}
