#!/usr/bin/env bash
# Run a single prepared eval task through the claude backend at a chosen model.
# Env: REPO_ROOT (checkout of the evaluated source, e.g. f032eeb).
# Usage: REPO_ROOT=... ./run_model.sh <model-id> <runs-dir> /abs/path/to/task-NNN.jsonl
set -u
MODEL="$1"; RUNS="$2"; tf="$3"
: "${REPO_ROOT:?set REPO_ROOT to the evaluated checkout}"
rd=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['run_dir'])" "$tf")
if [ -f "$RUNS/$rd/output.md" ]; then echo "SKIP $rd"; exit 0; fi
cd "$REPO_ROOT" || { echo "FAIL $rd cd"; exit 1; }
out=$(timeout 300 skill-benchmark run-agent --agent claude --model "$MODEL" --tasks "$tf" --runs "$RUNS" 2>&1)
rc=$?
if [ -f "$RUNS/$rd/output.md" ]; then echo "DONE $rd"; else echo "FAIL $rd rc=$rc :: $(echo "$out" | tail -1)"; fi
