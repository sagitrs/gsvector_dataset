#!/usr/bin/env bash
#
# Download BioASQ embeddings dataset.
#
# BioASQ (Biomedical Question Answering) — passage embeddings from biomedical
# literature. Typically sourced from the BEIR benchmark or ANN-benchmarks
# data mirrors.
#
# Data format: fvecs binary files.
#
# Usage: ./download_bioasq.sh [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_DIR="$SCRIPT_DIR/../bioasq/raw"

# --- Configuration ---
# Set BIOASQ_BASE_URL environment variable to override the default mirror.
# Example: BIOASQ_BASE_URL=https://example.com/files ./download_bioasq.sh
BASE_URL="${BIOASQ_BASE_URL:-https://storage.googleapis.com/ann-datasets/bioasq}"

FILES=("bioasq_base.fvecs" "bioasq_query.fvecs")

# Idempotency check
if [[ "${1:-}" != "--force" ]]; then
    ALL_EXIST=true
    for f in "${FILES[@]}"; do
        if [[ ! -f "$RAW_DIR/$f" ]]; then
            ALL_EXIST=false
            break
        fi
    done
    if $ALL_EXIST; then
        echo "[download_bioasq] Raw files already exist, skipping. Use --force to re-download."
        exit 0
    fi
fi

mkdir -p "$RAW_DIR"

download_file() {
    local filename="$1"
    local url="$BASE_URL/$filename"
    echo "[download_bioasq] Downloading $filename from $url"
    curl -L --retry 3 --retry-delay 5 --max-time 3600 \
        -o "$RAW_DIR/$filename" "$url" || {
        echo "[download_bioasq] ERROR: Failed to download $filename"
        exit 1
    }
    local sz
    sz=$(stat -c%s "$RAW_DIR/$filename" 2>/dev/null || stat -f%z "$RAW_DIR/$filename" 2>/dev/null)
    echo "[download_bioasq]   $filename: $sz bytes"
}

for f in "${FILES[@]}"; do
    download_file "$f"
done

echo "[download_bioasq] Done."
