#!/bin/sh
# 把本机的作品集原图同步到服务器。
#
# 图片不进 git（见 .gitignore），所以服务器上那份只能靠这个脚本送，CI 不管图。
# 缩略图也不用传：后端容器会按需生成并缓存在 server/images/thumb/。
#
# 用法：
#   SERVER_USER=root SERVER_HOST=1.2.3.4 sh tools/upload-images.sh
#
# 刻意不带 --delete：服务器上多出来的文件（比如你临时放的）不该被本机状态抹掉。
# 想删某张图，直接在服务器上删，同时把 content/gallery.json 里对应那条去掉。
set -eu

: "${SERVER_USER:?请先设置 SERVER_USER，例如 SERVER_USER=root}"
: "${SERVER_HOST:?请先设置 SERVER_HOST，例如 SERVER_HOST=1.2.3.4}"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/server/images/full"
DST="/app/xiaoou-portfolio/server/images/full"

if [ ! -d "$SRC" ]; then
  echo "找不到 $SRC" >&2
  exit 1
fi

COUNT=$(ls "$SRC"/*.jpg 2>/dev/null | wc -l | tr -d ' ')
echo "本地 $SRC 下有 $COUNT 张图，同步到 $SERVER_HOST:$DST"

# 首次部署时远端目录还不存在（CI 只 mkdir 项目根目录）
ssh -o ServerAliveInterval=30 "$SERVER_USER@$SERVER_HOST" "mkdir -p '$DST'"

rsync -avz --exclude='*.tmp' \
  -e 'ssh -o ServerAliveInterval=30' \
  "$SRC/" "$SERVER_USER@$SERVER_HOST:$DST/"

echo "完成。接口用的路径是 /portfolio-images/full/<文件名>"
