#!/usr/bin/env bash
#
# Download BioASQ embeddings dataset.
#
# Source: Cohere/beir-embed-english-v3 on HuggingFace.
# BioASQ biomedical QA passage embeddings (1024-dim, ~14.9M documents).
# Extracts 1M subset for ANN benchmark use.
#
# Dependencies: pip install datasets pyarrow
#
# Data format: parquet → fvecs/ivecs via embedded Python.
#
# HF mirror: set HF_ENDPOINT to use a mirror (e.g. https://hf-mirror.com).
#            Falls back to hf-mirror.com automatically if HF is unreachable.
#
# Usage: ./download_bioasq.sh [--force]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_DIR="$SCRIPT_DIR/../bioasq/raw"

# --- HuggingFace mirror fallback ---
# Use mirror for environments where huggingface.co is unreachable.
# Set HF_ENDPOINT env var to override; defaults to auto-detection.
if [[ -z "${HF_ENDPOINT:-}" ]]; then
    export HF_ENDPOINT="https://hf-mirror.com"
    echo "[download_bioasq] Using HF mirror: $HF_ENDPOINT"
fi

# --- Configuration ---
N_VECTORS="${BIOASQ_N_VECTORS:-1000000}"
HF_DATASET="Cohere/beir-embed-english-v3"

# Idempotency check
if [[ "${1:-}" != "--force" ]]; then
    if [[ -f "$RAW_DIR/bioasq_base.fvecs" ]] && [[ -f "$RAW_DIR/bioasq_query.fvecs" ]]; then
        echo "[download_bioasq] Raw files already exist, skipping. Use --force to re-download."
        exit 0
    fi
fi

mkdir -p "$RAW_DIR"

PYTHON="${PYTHON:-python3}"
echo "[download_bioasq] Extracting $N_VECTORS vectors from $HF_DATASET..."

$PYTHON - "$HF_DATASET" "$RAW_DIR" "$N_VECTORS" << 'PYEOF'
import os, struct, sys
from collections import defaultdict
import numpy as np

dataset_name = sys.argv[1]
out_dir = sys.argv[2]
n_vectors = int(sys.argv[3])

try:
    from datasets import load_dataset
except ImportError:
    print("[download_bioasq] ERROR: 'datasets' library not installed.", file=sys.stderr)
    print("  Install via: pip install datasets pyarrow", file=sys.stderr)
    sys.exit(1)

# --- Load corpus embeddings (streaming, first N vectors) ---
print(f"[download_bioasq] Loading corpus (first {n_vectors} vectors)...")
corpus = load_dataset(dataset_name, "bioasq-corpus", split="train", streaming=True)

base_vecs, base_ids = [], []
count = 0
for row in corpus:
    base_vecs.append(np.array(row["emb"], dtype=np.float32))
    base_ids.append(row["_id"])
    count += 1
    if count >= n_vectors:
        break
    if count % 100000 == 0:
        print(f"  {count}/{n_vectors} corpus vectors...")

base = np.stack(base_vecs)
N, dim = base.shape
print(f"[download_bioasq] Corpus: {N} vectors, dim={dim}")

with open(os.path.join(out_dir, "bioasq_base.fvecs"), "wb") as f:
    for i in range(N):
        f.write(struct.pack("<i", dim))
        f.write(base[i].tobytes())
print(f"[download_bioasq] Written: bioasq_base.fvecs")

# --- Load query embeddings ---
print(f"[download_bioasq] Loading queries...")
queries = load_dataset(dataset_name, "bioasq-queries", split="test")
query_vecs, query_ids = [], []
for row in queries:
    query_vecs.append(np.array(row["emb"], dtype=np.float32))
    query_ids.append(row["_id"])
query = np.stack(query_vecs)
Q = query.shape[0]
print(f"[download_bioasq] Queries: {Q} vectors")

with open(os.path.join(out_dir, "bioasq_query.fvecs"), "wb") as f:
    for i in range(Q):
        f.write(struct.pack("<i", dim))
        f.write(query[i].tobytes())
print(f"[download_bioasq] Written: bioasq_query.fvecs")

# --- Compute ground truth from qrels ---
print(f"[download_bioasq] Loading relevance judgments...")
qrels = load_dataset(dataset_name, "bioasq-qrels", split="test")

id_to_idx = {bid: i for i, bid in enumerate(base_ids)}
qid_to_idx = {qid: i for i, qid in enumerate(query_ids)}

gt = defaultdict(list)
for row in qrels:
    qid, cid = row["query_id"], row["corpus_id"]
    score = row.get("score", 1)
    if qid in qid_to_idx and cid in id_to_idx:
        gt[qid_to_idx[qid]].append((id_to_idx[cid], score))

# Build top-k ground truth
max_gt = max((len(v) for v in gt.values()), default=0)
k = min(100, max_gt) if max_gt > 0 else 10
print(f"[download_bioasq] Writing ground truth (k={k}, queries with qrels: {len(gt)}/{Q})")

neighbors = np.zeros((Q, k), dtype=np.int32)
for q_idx in range(Q):
    if q_idx in gt:
        items = sorted(gt[q_idx], key=lambda x: -x[1])[:k]
        for j, (cidx, _) in enumerate(items):
            neighbors[q_idx, j] = cidx

for k_val in [10, 100]:
    if k_val <= k:
        gt_out = os.path.join(out_dir, f"bioasq_gt_top{k_val}.ivecs")
        with open(gt_out, "wb") as f:
            for i in range(Q):
                actual_k = min(k_val, len(gt.get(i, []))) if i in gt else k_val
                f.write(struct.pack("<i", actual_k))
                f.write(neighbors[i, :actual_k].tobytes())
        print(f"[download_bioasq] Written: bioasq_gt_top{k_val}.ivecs")

print("[download_bioasq] Done.")
PYEOF

# --- Verify ---
for f in bioasq_base.fvecs bioasq_query.fvecs; do
    if [[ ! -f "$RAW_DIR/$f" ]]; then
        echo "[download_bioasq] ERROR: Missing output file: $f"
        exit 1
    fi
done
echo "[download_bioasq] Raw files verified."
ls -la "$RAW_DIR/"
