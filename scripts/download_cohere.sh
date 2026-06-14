#!/usr/bin/env bash
#
# Download Cohere Wikipedia embeddings dataset.
#
# Source: NVIDIA RAFT wiki_all_1M subset (1M vectors × 768-dim, ~2.9GB).
# This dataset combines English Wikipedia (Kaggle 2023) with Cohere Wikipedia
# (2022) embeddings using paraphrase-multilingual-mpnet-base-v2.
#
# Data format: fbin (RAFT binary) → converted to fvecs/ivecs.
#
# Usage: ./download_cohere.sh [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_DIR="$SCRIPT_DIR/../cohere/raw"

# --- Configuration ---
# Set COHERE_URL environment variable to override the default URL.
# Example: COHERE_URL=https://example.com/wiki_all_1M.tar ./download_cohere.sh
BASE_URL="${COHERE_URL:-https://data.rapids.ai/raft/datasets/wiki_all_1M}"
TAR_FILE="wiki_all_1M.tar"

# Idempotency check
if [[ "${1:-}" != "--force" ]]; then
    if [[ -f "$RAW_DIR/base.fbin" ]] && [[ -f "$RAW_DIR/query.fbin" ]] && \
       [[ -f "$RAW_DIR/groundtruth.neighbors.ibin" ]]; then
        echo "[download_cohere] Raw files already exist, skipping. Use --force to re-download."
        exit 0
    fi
fi

mkdir -p "$RAW_DIR"

# --- Download ---
echo "[download_cohere] Downloading $TAR_FILE (~2.9GB)..."
echo "[download_cohere] URL: $BASE_URL/$TAR_FILE"
curl -L --retry 3 --retry-delay 10 --max-time 7200 \
    -o "$RAW_DIR/$TAR_FILE" "$BASE_URL/$TAR_FILE" || {
    echo "[download_cohere] ERROR: Failed to download $TAR_FILE"
    exit 1
}
sz=$(stat -c%s "$RAW_DIR/$TAR_FILE" 2>/dev/null || stat -f%z "$RAW_DIR/$TAR_FILE" 2>/dev/null)
echo "[download_cohere] Downloaded: $sz bytes"

# --- Extract ---
echo "[download_cohere] Extracting..."
tar -xf "$RAW_DIR/$TAR_FILE" -C "$RAW_DIR" || {
    echo "[download_cohere] ERROR: Failed to extract $TAR_FILE"
    exit 1
}
rm -f "$RAW_DIR/$TAR_FILE"
echo "[download_cohere] Extracted to $RAW_DIR"

# --- Verify raw files ---
for f in base.fbin query.fbin groundtruth.neighbors.ibin; do
    if [[ ! -f "$RAW_DIR/$f" ]]; then
        echo "[download_cohere] ERROR: Missing extracted file: $f"
        ls -la "$RAW_DIR/"
        exit 1
    fi
done
echo "[download_cohere] Raw files verified."

# --- Convert fbin → fvecs (base + query only; GT computed by Makefile) ---
PYTHON="${PYTHON:-python3}"
CONVERTER="$SCRIPT_DIR/convert_fbin.py"
echo "[download_cohere] Converting fbin → fvecs..."
$PYTHON "$CONVERTER" \
    --base "$RAW_DIR/base.fbin" \
    --query "$RAW_DIR/query.fbin" \
    --out-dir "$RAW_DIR" || {
    echo "[download_cohere] ERROR: Conversion failed"
    exit 1
}

# --- Rename to match Makefile expectations (cohere_base.fvecs, cohere_query.fvecs) ---
mv "$RAW_DIR/base.fvecs"  "$RAW_DIR/cohere_base.fvecs"
mv "$RAW_DIR/query.fvecs" "$RAW_DIR/cohere_query.fvecs"

# --- Clean up raw fbin files ---
rm -f "$RAW_DIR/base.fbin" "$RAW_DIR/query.fbin" \
      "$RAW_DIR/groundtruth.neighbors.ibin" \
      "$RAW_DIR/groundtruth.distances.fbin"

echo "[download_cohere] Done. Output files in $RAW_DIR:"
ls -la "$RAW_DIR/"
