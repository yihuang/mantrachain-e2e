local config = import 'min_gas_price_lte.jsonnet';

config {
  'mantra_5887-1'+: {
    genesis+: {
      consensus+: {
        params+: {
          block+: {
            max_gas: '84000000',
          },
        },
      },
    },
  },
}
