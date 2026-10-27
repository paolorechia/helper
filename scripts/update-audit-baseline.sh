#!/usr/bin/env bash
# Regenerate qc/audit-baseline.txt from the current uv.lock.
#
# Run this after a dependency bump, then review the diff. Every newly added
# ID is an advisory that CI will now accept silently, so check each one for
# reachability from this project's code before committing the result.
set -euo pipefail

cd "$(dirname "$0")/.."

baseline="qc/audit-baseline.txt"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The text output lists exactly the advisory IDs uv reports, but it can list
# the same advisory twice under two ID schemes (a GHSA id and a PYSEC id).
# uv only matches one of them, so the candidate list is verified against uv
# itself below and any id uv rejects is dropped.
uv audit --preview-features audit-command >"$tmp/raw.txt" || true

# grep exits 1 when it matches nothing, and under 'set -e' that would abort
# the script before it wrote anything. "No advisories at all" is exactly the
# case where the baseline should be emptied, so treat "no match" as "no
# candidates" rather than as a failure.
{ grep -oE '^- (GHSA|PYSEC)-[0-9A-Za-z-]+:' "$tmp/raw.txt" || true; } \
  | sed -e 's/^- //' -e 's/:$//' \
  | sort -u >"$tmp/candidates.txt"

args=()
while read -r id; do
  if [ -n "$id" ]; then
    args+=(--ignore "$id")
  fi
done <"$tmp/candidates.txt"

# uv reports every id it could not match; drop those so CI stays quiet.
# The ${args[@]+...} form expands to nothing when the array is empty, which
# plain "${args[@]}" does not do under 'set -u' on bash 3.2 (still the
# default on macOS).
uv audit --preview-features audit-command ${args[@]+"${args[@]}"} \
  >"$tmp/verify.txt" 2>&1 || true
{ grep -oE 'Ignored vulnerability `[A-Z]+-[0-9A-Za-z-]+` does not match' "$tmp/verify.txt" || true; } \
  | sed -e 's/Ignored vulnerability `//' -e 's/` does not match//' \
  | sort -u >"$tmp/unmatched.txt"

# grep -f with an empty pattern file selects no lines at all, so filtering by
# an empty "unmatched" list would silently empty the baseline. Only filter
# when uv actually rejected something.
if [ -s "$tmp/unmatched.txt" ]; then
  grep -vxF -f "$tmp/unmatched.txt" "$tmp/candidates.txt" >"$tmp/final.txt" || true
else
  cp "$tmp/candidates.txt" "$tmp/final.txt"
fi

# The header is every leading comment line, so editing it above does not
# need the line count kept in sync here.
if [ -f "$baseline" ]; then
  awk '/^#/{print; next} {exit}' "$baseline" >"$tmp/header.txt"
else
  : >"$tmp/header.txt"
fi

{
  cat "$tmp/header.txt"
  cat "$tmp/final.txt"
} >"$baseline.new"

mv "$baseline.new" "$baseline"

echo "Wrote $(grep -vc '^#' "$baseline" || true) advisory IDs to $baseline"
if [ -s "$tmp/unmatched.txt" ]; then
  echo "Dropped $(wc -l <"$tmp/unmatched.txt" | tr -d ' ') id(s) uv does not match"
fi
