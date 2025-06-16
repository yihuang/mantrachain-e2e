local default = import 'default.jsonnet';

default {
  'mantra_5887-1'+: {
    config+: {
      consensus+: {
        timeout_commit: '15s',
      },
    },
  },
}
