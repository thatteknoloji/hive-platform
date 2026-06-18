#!/bin/bash
# Reddirect MCP sunucusunu derle (bir kez)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$DIR/reddirect-src" ]; then
  git clone --depth 1 https://github.com/jeebus87/reddirect.git "$DIR/reddirect-src"
fi
cd "$DIR/reddirect-src"
npm install
npm run build
echo "OK: reddirect hazır — $DIR/reddirect-src/dist/index.js"
