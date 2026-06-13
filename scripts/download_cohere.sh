#!/usr/bin/env bash
#
# Download Cohere embeddings dataset.
#
# Cohere Wikipedia embeddings — text embeddings generated with Cohere's
# multilingual-22-12 model (768-dim). Typically sourced from HuggingFace
# datasets or ANN-benchmarks data mirrors.
#
# Data format: fvecs binary files.
#
# Usage: ./download_cohere.sh [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_DIR="$SCRIPT_DIR/../cohere/raw"

# --- Configuration ---
# Set COHERE_BASE_URL environment variable to override the default mirror.
# Example: COHERE_BASE_URL=https://example.com/files ./download_cohere.sh
BASE_URL="${COHERE_BASE_URL:-https://storage.googleapis.com/ann-datasets/cohere}"

FILES=("cohere_base.fvecs" "cohere_query.fvecs")

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
        echo "[download_cohere] Raw files already exist, skipping. Use --force to re-download."
        exit 0
    fi
fi

mkdir -p "$RAW_DIR"

download_file() {
    local filename="$1"
    local url="$BASE_URL/$filename"
    echo "[download_cohere] Downloading $filename from $url"
    curl -L --retry 3 --retry-delay 5 --max-time 7200 \
        -o "$RAW_DIR/$filename" "$url" || {
        echo "[download_cohere] ERROR: Failed to download $filename"
        exit 1
    }
    local sz
    sz=$(stat -c%s "$RAW_DIR/$filename" 2>/dev/null || stat -f%z "$RAW_DIR/$filename" 2>/dev/null)
    echo "[download_cohere]   $filename: $sz bytes"
}

for f in "${FILES[@]}"; do
    download_file "$f"
done

echo "[download_cohere] Done."
