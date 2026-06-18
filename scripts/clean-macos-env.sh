#!/usr/bin/env bash
# macOS — Python/node malloc stack logging terminal gürültüsünü susturur.
unset MallocStackLogging MallocStackLoggingNoCompact 2>/dev/null || true
if [[ $# -gt 0 ]]; then
  exec "$@"
fi
