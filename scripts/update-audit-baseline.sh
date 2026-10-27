#!/usr/bin/env bash
# Regenerate qc/audit-baseline.txt from the current uv.lock.
#
# Run this after a dependency bump, then review the diff. Every newly added
# ID is an advisory that CI will now accept silently, so check each one for
# reachability from this project's code before committing the result.
set -euo pipefail

cd "$(dirname "$0")/.."

baseline="qc/audit-baseline.txt"
header_lines=13

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The text output lists exactly the advisory IDs uv reports, but it can list
# the same advisory twice under two ID schemes (a GHSA id and a PYSEC id).
# uv only matches one of them, so the candidate list is verified against uv
# itself below and any id uv rejects is dropped.
uv audit --preview-features audit-command >"$tmp/raw.txt" || true

grep -oE '^- (GHSA|PYSEC)-[0-9A-Za-z-]+:' "$tmp/raw.txt" \
  | sed -e 's/^- //' -e 's/:$//' \
  | sort -u >"$tmp/candidates.txt"

args=()
while read -r id; do
  [ -n "$id" ] && args+=(--ignore "$id")
done <"$tmp/candidates.txt"

# uv reports every id it could not match; drop those so CI stays quiet.
uv audit --preview-features audit-command "${args[@]}" >"$tmp/verify.txt" 2>&1 || true
grep -oE 'Ignored vulnerability `[A-Z]+-[0-9A-Za-z-]+` does not match' "$tmp/verify.txt" \
  | sed -e 's/Ignored vulnerability `//' -e 's/` does not match//' \
  | sort -u >"$tmp/unmatched.txt"

grep -vxF -f "$tmp/unmatched.txt" "$tmp/candidates.txt" >"$tmp/final.txt" || true

{
  head -"$header_lines" "$baseline"
  cat "$tmp/final.txt"
} >"$baseline.new"

mv "$baseline.new" "$baseline"

echo "Wrote $(grep -vc '^#' "$baseline") advisory IDs to $baseline"
if [ -s "$tmp/unmatched.txt" ]; then
  echo "Dropped $(wc -l <"$tmp/unmatched.txt" | tr -d ' ') id(s) uv does not match"
fi
