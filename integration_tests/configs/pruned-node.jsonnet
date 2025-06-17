local config = import 'default.jsonnet';

config {
  'mantra_5887-1'+: {
    'app-config'+: {
      pruning: 'everything',
      'state-sync'+: {
        'snapshot-interval': 0,
      },
    },
    validators: [super.validators[0] {
      // don't enable versiondb, since it don't do pruning right now
      'app-config':: super['app-config'],
    }] + super.validators[1:],
  },
}
