#!/usr/bin/env bash
# Build the site and publish dist/ to the gh-pages branch.
# Refuses to publish anything that is not a web file.
set -euo pipefail
cd "$(dirname "$0")/.."

npm run build

python3 - <<'PY'
from pathlib import Path
root = Path("dist")
allowed = {
    ".html", ".css", ".js", ".svg", ".webp", ".jpg", ".jpeg", ".png", ".gif",
    ".ico", ".json", ".csv", ".md", ".txt", ".xml", ".mid", ".zip", ".woff", ".woff2",
    ".m4a", ".mp4", ".vtt",
}
bad = []
count = 0
for path in root.rglob("*"):
    if not path.is_file():
        continue
    count += 1
    if path.name == ".nojekyll":
        continue
    if path.suffix.lower() not in allowed:
        bad.append(str(path))
if bad:
    raise SystemExit("refusing to publish:\n" + "\n".join(bad))
if not (root / ".nojekyll").is_file():
    raise SystemExit("refusing to publish without .nojekyll")
if not (root / "index.html").is_file() or not (root / "article.html").is_file():
    raise SystemExit("refusing to publish without index.html and article.html")
print(f"guard ok: {count} files")
PY

remote="${GH_PAGES_REMOTE:-https://github.com/mizcausevic-dev/nostalgia-breakbeat-kit-studio.git}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cp -R dist/. "$work/"
git -C "$work" init -b gh-pages >/dev/null
git -C "$work" add -A
git -C "$work" -c user.name="Cursor Agent" -c user.email="cursoragent@cursor.com" commit -m "Publish the Nostalgia kit lab" >/dev/null
if [ -z "${crsragent:-}" ]; then
  echo "crsragent is not set; cannot push gh-pages" >&2
  exit 1
fi
ask="$(mktemp)"
cat >"$ask" <<'EOF'
#!/bin/sh
case "$1" in
  *sername*) printf '%s\n' 'x-access-token' ;;
  *) printf '%s\n' "$crsragent" ;;
esac
EOF
chmod 700 "$ask"
GIT_ASKPASS="$ask" GIT_TERMINAL_PROMPT=0 git -C "$work" push --force "$remote" gh-pages
rm -f "$ask"
echo "published gh-pages"
