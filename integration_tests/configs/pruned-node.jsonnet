local config = import 'default.jsonnet';

config {
  'mantra-canary-net-1'+: {
    'app-config'+: {
      pruning: 'everything',
      'state-sync'+: {
        'snapshot-interval': 0,
      },
    },
  },
}
