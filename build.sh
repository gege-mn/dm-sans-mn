#!/bin/sh
# Rebuild DM Sans MN from the upstream DM Sans sources.
#   ./build.sh          sources + variable and static fonts
#   ./build.sh quick    sources + variable fonts only
set -e
cd "$(dirname "$0")"
UPSTREAM_COMMIT=4412393b7d2de9fe7a92064c2dce9b5af5d7fd26

if [ ! -d .venv ]; then
  uv venv -q --python 3.12 .venv
  uv pip install -q --python .venv/bin/python -r requirements.txt
fi
export PATH="$PWD/.venv/bin:$PATH"

if [ ! -d upstream ]; then
  git clone -q https://github.com/googlefonts/dm-fonts.git upstream
  git -C upstream checkout -q "$UPSTREAM_COMMIT"
fi

python build/gen.py
[ "$1" = quick ] && printf 'buildStatic: false\n' >> sources/config.yaml
rm -rf fonts
gftools builder sources/config.yaml
for f in fonts/variable/*.ttf; do
  fonttools ttLib.woff2 compress -q -o "fonts/webfonts/$(basename "${f%.ttf}").woff2" "$f" 2>/dev/null || {
    mkdir -p fonts/webfonts
    fonttools ttLib.woff2 compress -q -o "fonts/webfonts/$(basename "${f%.ttf}").woff2" "$f"
  }
done
python build/gen.py >/dev/null   # restore the full config if this was a quick build
ls fonts/*
