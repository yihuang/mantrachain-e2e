local config = import 'default.jsonnet';

config {
  'mantra-canary-net-1'+: {
    validators: [{
      'coin-type': 60,
      coins: '1stake,100000000000uom,115792089237316195423570985008687907853269984665640564039457584007913129639935utesttest',
      staked: '1stake',
      mnemonic: '${VALIDATOR1_MNEMONIC}',
      commission_rate: '0.000000000000000000',
      commission_max_rate: '0.000000000000000000',
      commission_max_change_rate: '0.000000000000000000',
    }, {
      'coin-type': 60,
      coins: '1stake,100000000000uom',
      staked: '1stake',
      mnemonic: '${VALIDATOR2_MNEMONIC}',
    }, {
      'coin-type': 60,
      coins: '1stake,100000000000uom',
      staked: '1stake',
      mnemonic: '${VALIDATOR3_MNEMONIC}',
    }, {
      'coin-type': 60,
      coins: '1stake,100000000000uom',
      staked: '1stake',
    }],
    genesis+: {
      consensus_params: {
        block: {
          max_bytes: '3000000',
          max_gas: '300000000',
        },
      },
      app_state+: {
        slashing: {
          params: {
            signed_blocks_window: 3,
            min_signed_per_window: '1',
            downtime_jail_duration: '3s',
            slash_fraction_double_sign: '0.01',
            slash_fraction_downtime: '1',
          },
        },
      },
    },
  },
}
