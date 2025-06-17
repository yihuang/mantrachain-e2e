local default = import 'default.jsonnet';

default {
  'mantra-canary-net-1'+: {
    config+: {
      consensus+: {
        timeout_commit: '15s',
      },
    },
  },
}
