#!/usr/bin/env bash
# Publish the website (this folder) to GitHub Pages in one command.
#   ./site/deploy-github-pages.sh
# It pushes the site files to a branch called gh-pages (your main branch is not touched) and turns on Pages.
# Needs: git, the GitHub CLI (`gh auth status` must say you are logged in), and a public repository.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
remote="$(git -C "$root" remote get-url origin)"
slug="$(echo "$remote" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
owner="${slug%%/*}"; repo="${slug##*/}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
rsync -a --exclude 'README.md' --exclude 'deploy-github-pages.sh' --exclude '*.zip' "$root/site/" "$tmp/"
touch "$tmp/.nojekyll"

cd "$tmp"
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C "$root" config user.name)" -c user.email="$(git -C "$root" config user.email)" \
    commit -q -m "Publish website"
git remote add origin "$remote"
git push -q -f origin gh-pages

# turn Pages on (or update it if it already exists)
if ! gh api -X POST "repos/$owner/$repo/pages" -f 'source[branch]=gh-pages' -f 'source[path]=/' >/dev/null 2>&1; then
  gh api -X PUT "repos/$owner/$repo/pages" -f 'source[branch]=gh-pages' -f 'source[path]=/' >/dev/null 2>&1 || true
fi
url="https://$owner.github.io/$repo/"
gh repo edit "$owner/$repo" --homepage "$url" >/dev/null 2>&1 || true
echo "Published. It can take 1-2 minutes to go live: $url"
