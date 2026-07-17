#!/usr/bin/env bash
# Human-readable CHIPS harvest status for one repo's dedicated database.
# A demo/ops surface: shows what CHIPS has ingested and is tracking for a repo,
# with no dependency on Ollama or the chips Python env (pure read-only psql).
#
# Usage (from anywhere; talks to the chips-prod-postgres container):
#   wsl -d Ubuntu-24.04 -- bash scripts/ops/chips-harvest-status.sh <db-name>
# e.g. chips_backend | chips_chat | chips_staec | chips_bproxy
set -euo pipefail

DB="${1:?usage: chips-harvest-status.sh <db-name>}"
CONTAINER="${CHIPS_PROD_PG_CONTAINER:-chips-prod-postgres}"

q() { docker exec "$CONTAINER" psql -U postgres -d "$DB" -t -A -c "$1" 2>/dev/null; }

echo "=============================================================="
echo " CHIPS harvest status — database: $DB"
echo "=============================================================="
echo
echo "Commits ingested  : $(q 'SELECT count(*) FROM cortex_git_commits;')"
echo "Memories compiled : $(q 'SELECT count(*) FROM cortex_memories;')"
echo "History span      : $(q "SELECT COALESCE(to_char(min(committed_at),'YYYY-MM-DD') || ' -> ' || to_char(max(committed_at),'YYYY-MM-DD'), '(none)') FROM cortex_git_commits;")"
echo
echo "-- Top contributors ------------------------------------------"
q "SELECT '  ' || rpad(author, 34) || lpad(count(*)::text, 5) || ' commits'
   FROM cortex_git_commits GROUP BY author ORDER BY count(*) DESC LIMIT 5;"
echo
echo "-- Most recent activity --------------------------------------"
q "SELECT '  ' || to_char(committed_at,'YYYY-MM-DD') || '  ' || left(COALESCE(summary, message, ''), 70)
   FROM cortex_git_commits ORDER BY committed_at DESC LIMIT 8;"
echo
