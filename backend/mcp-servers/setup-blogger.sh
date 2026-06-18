#!/usr/bin/env bash
# Blogger MCP kurulum — Desktop/mcp-blogger-server
set -e
TARGET="$HOME/Desktop/mcp-blogger-server"
REPO="https://github.com/aleck31/mcp-blogger.git"

if [ ! -d "$TARGET" ]; then
  git clone "$REPO" "$TARGET"
fi

cd "$TARGET"
npm install
chmod +x start-mcp.sh scripts/get-token.mjs 2>/dev/null || true

echo ""
echo "✅ Kurulum tamam. Sıradaki adım:"
echo "   cd $TARGET && npm run get-token"
echo ""
echo "Cursor MCP: HIVE/.cursor/mcp.json zaten yapılandırıldı."
echo "Token aldıktan sonra Cursor'ı yeniden başlat."
