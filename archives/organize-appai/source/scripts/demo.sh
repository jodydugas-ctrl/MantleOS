#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PRODUCT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
ISOLATED_ROOT=$(CDPATH= cd -- "$PRODUCT_ROOT/../.." && pwd -P)
if [ -f "$ISOLATED_ROOT/WORKSPACE.txt" ]; then
  WORKSPACE=$ISOLATED_ROOT
  RECORDED=$(tr -d '\r\n' < "$WORKSPACE/WORKSPACE.txt")
  case "$RECORDED" in
    [A-Za-z]:\\*)
      if command -v cygpath >/dev/null 2>&1; then
        RECORDED=$(cygpath -u "$RECORDED")
      elif command -v wslpath >/dev/null 2>&1; then
        RECORDED=$(wslpath -u "$RECORDED")
      fi
      ;;
  esac
  RECORDED=$(CDPATH= cd -- "$RECORDED" && pwd -P)
  if [ "$WORKSPACE" != "$RECORDED" ]; then
    echo "Refusing: WORKSPACE.txt does not match the resolved workspace." >&2
    exit 2
  fi
  FIXTURE_SOURCE="$WORKSPACE/fixtures/inbox"
else
  WORKSPACE="$PRODUCT_ROOT/.organize-appai/demo-workspace"
  mkdir -p "$WORKSPACE"
  FIXTURE_SOURCE="$PRODUCT_ROOT/demo-fixtures/inbox"
fi

if [ -x "$WORKSPACE/.venvs/organize/bin/python" ]; then
  PY_ORGANIZE="$WORKSPACE/.venvs/organize/bin/python"
  PY_MANTLE="$WORKSPACE/.venvs/mantle/bin/python"
elif [ -x "$WORKSPACE/.venvs/organize/Scripts/python.exe" ]; then
  PY_ORGANIZE="$WORKSPACE/.venvs/organize/Scripts/python.exe"
  PY_MANTLE="$WORKSPACE/.venvs/mantle/Scripts/python.exe"
else
  PY_ORGANIZE=python
  PY_MANTLE=python
fi

FIXTURE_BEFORE=$("$PY_ORGANIZE" -c \
  'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); h=hashlib.sha256(); [(h.update(str(f.relative_to(p)).encode()),h.update(f.read_bytes())) for f in sorted(p.rglob("*")) if f.is_file()]; print(h.hexdigest())' \
  "$FIXTURE_SOURCE")

DEMO_ROOT="$WORKSPACE/artifacts/demo"
WORKING="$DEMO_ROOT/working"
DEMO_CONFIG="$DEMO_ROOT/demo.yaml"
PROPOSALS="$DEMO_ROOT/proposals"

PATH_GUARD="$WORKSPACE/scripts/path_guard.py"
if [ ! -f "$PATH_GUARD" ]; then
  PATH_GUARD="$PRODUCT_ROOT/scripts/path_guard.py"
fi
"$PY_MANTLE" "$PATH_GUARD" --workspace "$WORKSPACE" \
  "$DEMO_ROOT" "$WORKING" "$DEMO_CONFIG" "$PROPOSALS"

if [ -d "$DEMO_ROOT" ]; then
  rm -rf -- "$DEMO_ROOT"
fi
mkdir -p "$WORKING" "$PROPOSALS"
cp -R "$FIXTURE_SOURCE" "$WORKING/inbox"
sed 's#fixtures/inbox#artifacts/demo/working/inbox#g' \
  "$PRODUCT_ROOT/examples/appai-demo.yaml" > "$DEMO_CONFIG"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
cd "$WORKSPACE"

echo "=== Selected configuration ==="
sed -n '1,160p' "$DEMO_CONFIG"

echo "=== Deterministic explanation ==="
"$PY_ORGANIZE" -m organize explain "$DEMO_CONFIG" --working-dir "$WORKSPACE"

echo "=== Traced simulation ==="
"$PY_ORGANIZE" -m organize sim "$DEMO_CONFIG" --working-dir "$WORKSPACE" \
  --tags demo --format JSONL --trace "$DEMO_ROOT/run-trace.jsonl" \
  > "$DEMO_ROOT/simulation.jsonl"
sed -n '1,12p' "$DEMO_ROOT/simulation.jsonl"

echo "=== Why invoice-001.txt matched ==="
"$PY_ORGANIZE" -m organize why "$WORKING/inbox/invoice-001.txt" \
  --trace-file "$DEMO_ROOT/run-trace.jsonl" --safe-root "$WORKSPACE"

echo "=== Why receipt-2025.txt did not match ==="
"$PY_ORGANIZE" -m organize why "$WORKING/inbox/receipt-2025.txt" \
  --trace-file "$DEMO_ROOT/run-trace.jsonl" --safe-root "$WORKSPACE"

echo "=== Offline proposal ==="
"$PY_ORGANIZE" -m organize assist --safe-root "$WORKSPACE" \
  --location "$WORKING/inbox" --proposal-dir "$PROPOSALS" --format json \
  "Find duplicate files but do not delete anything" > "$DEMO_ROOT/assist.json"
sed -n '1,80p' "$DEMO_ROOT/assist.json"
PROPOSAL=$("$PY_ORGANIZE" -c \
  'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["proposal_path"])' \
  "$DEMO_ROOT/assist.json")

echo "=== Validate and simulate proposal ==="
"$PY_ORGANIZE" -m organize check "$PROPOSAL"
"$PY_ORGANIZE" -m organize sim "$PROPOSAL" --working-dir "$WORKSPACE" \
  --format JSONL > "$DEMO_ROOT/proposal-simulation.jsonl"
sed -n '1,12p' "$DEMO_ROOT/proposal-simulation.jsonl"

echo "=== Mantle resident status ==="
"$PY_ORGANIZE" -m organize mantle-status --product-root "$PRODUCT_ROOT"

if [ -d "$WORKSPACE/sources/mantle-os/.git" ]; then
  test -z "$(git -C "$WORKSPACE/sources/mantle-os" status --porcelain)"
fi
if [ -d "$WORKSPACE/sources/organize-upstream/.git" ]; then
  test -z "$(git -C "$WORKSPACE/sources/organize-upstream" status --porcelain)"
fi
FIXTURE_AFTER=$("$PY_ORGANIZE" -c \
  'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); h=hashlib.sha256(); [(h.update(str(f.relative_to(p)).encode()),h.update(f.read_bytes())) for f in sorted(p.rglob("*")) if f.is_file()]; print(h.hexdigest())' \
  "$FIXTURE_SOURCE")
test "$FIXTURE_BEFORE" = "$FIXTURE_AFTER"
echo "Demo complete. Artifacts: $DEMO_ROOT"
