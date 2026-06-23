#!/usr/bin/env python3
"""
Brute-force ground truth computation for ANN datasets.

Reads base.fvecs and query.fvecs, computes exhaustive L2-squared distance
for each query, and outputs top-K nearest neighbor indices as ivecs.

ivecs format (little-endian):
  [int32: k] [int32 * k] ... repeated per query
"""

import argparse
import os
import struct
import sys
import time

import numpy as np


def read_fvecs(filepath):
    """Read an fvecs file into a NumPy array of shape (N, dim)."""
    with open(filepath, "rb") as f:
        data = f.read()
    vectors = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            break
        dim = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if dim <= 0 or offset + dim * 4 > len(data):
            break
        vec = np.frombuffer(data, dtype=np.float32, count=dim, offset=offset)
        vectors.append(vec)
        offset += dim * 4
    if not vectors:
        raise ValueError(f"No vectors found in {filepath}")
    return np.stack(vectors)


def write_ivecs(filepath, indices, k):
    """
    Write ivecs file from a (Q, k) int32 array of neighbor indices.

    Each entry: [int32: k] [int32 * k]
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        for i in range(indices.shape[0]):
            f.write(struct.pack("<i", k))
            f.write(indices[i].astype(np.int32).tobytes())


def compute_groundtruth(base_vecs, query_vecs, k, metric="L2", batch_size=100):
    """
    Brute-force nearest neighbors with specified distance metric.

    Args:
        base_vecs: (N, dim) float32 array
        query_vecs: (Q, dim) float32 array
        k: number of nearest neighbors
        metric: "L2", "IP", or "COSINE"
        batch_size: number of queries per batch (for memory)

    Returns:
        indices: (Q, k) int32 array of neighbor indices
    """
    Q = query_vecs.shape[0]
    all_indices = np.zeros((Q, k), dtype=np.int32)

    base_f64 = base_vecs.astype(np.float64)
    base_norms = np.sum(base_f64 ** 2, axis=1)

    # Process queries in batches
    for start in range(0, Q, batch_size):
        end = min(start + batch_size, Q)
        batch = query_vecs[start:end].astype(np.float64)
        dots = np.dot(batch, base_f64.T)

        if metric == "L2":
            query_norms = np.sum(batch ** 2, axis=1)
            dists = query_norms[:, np.newaxis] + base_norms[np.newaxis, :] - 2 * dots
            order = np.argsort  # smaller = closer
        elif metric == "IP":
            dists = -dots  # larger dot = more similar
            order = np.argsort  # sort negative dots ascending
        elif metric == "COSINE":
            query_norms = np.sqrt(np.sum(batch ** 2, axis=1))
            base_norms_sqrt = np.sqrt(base_norms)
            norms = np.maximum(query_norms[:, np.newaxis] * base_norms_sqrt[np.newaxis, :], 1e-12)
            dists = 1.0 - dots / norms
            order = np.argsort  # smaller = more similar
        else:
            raise ValueError(f"Unknown metric: {metric}")

        # Find top-k
        for j in range(end - start):
            part = np.argpartition(dists[j], k)[:k]
            part = part[order(dists[j][part])]
            all_indices[start + j] = part.astype(np.int32)

        print(f"  [gt] batch {start // batch_size + 1}/"
              f"{(Q + batch_size - 1) // batch_size} done ({end}/{Q})")

    return all_indices


def validate_ivecs(indices, k, max_id):
    """Validate that all indices are in range [0, max_id)."""
    if indices.shape[1] != k:
        raise ValueError(f"Expected k={k}, got shape {indices.shape}")
    lo, hi = indices.min(), indices.max()
    if lo < 0 or hi >= max_id:
        raise ValueError(f"Index out of range [{lo}, {hi}] for max_id={max_id}")
    print(f"[validate] All {indices.shape[0]}x{k} indices in range [0, {max_id})")


def main():
    parser = argparse.ArgumentParser(description="Compute ground truth")
    parser.add_argument("--base", required=True, help="Base fvecs file")
    parser.add_argument("--query", required=True, help="Query fvecs file")
    parser.add_argument("-k", default="10,100", help="K values, comma-separated")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Queries per batch (default: 100)")
    parser.add_argument("--metric", default="L2", choices=["L2", "IP", "COSINE"],
                        help="Distance metric (default: L2)")
    args = parser.parse_args()

    ks = [int(x.strip()) for x in args.k.split(",")]

    print(f"[gt] Loading base: {args.base}")
    t0 = time.time()
    base = read_fvecs(args.base)
    N, dim = base.shape
    print(f"[gt] Base: {N} vectors, dim={dim}, {base.nbytes / 1e6:.1f} MB "
          f"({time.time() - t0:.1f}s)")

    print(f"[gt] Loading query: {args.query}")
    t0 = time.time()
    query = read_fvecs(args.query)
    Q = query.shape[0]
    print(f"[gt] Query: {Q} vectors, dim={dim}, {query.nbytes / 1e6:.1f} MB "
          f"({time.time() - t0:.1f}s)")

    assert query.shape[1] == dim, "Base and query dimension mismatch"

    for k in ks:
        print(f"[gt] Computing top-{k}...")
        t0 = time.time()
        indices = compute_groundtruth(base, query, k, metric=args.metric, batch_size=args.batch_size)
        elapsed = time.time() - t0
        print(f"[gt] top-{k} done in {elapsed:.1f}s "
              f"({elapsed / Q * 1000:.1f} ms/query)")

        validate_ivecs(indices, k, N)

        suffix = f"_{args.metric.lower()}" if args.metric != "L2" else ""
        out_path = os.path.join(args.out_dir, f"gt_top{k}{suffix}.ivecs")
        write_ivecs(out_path, indices, k)
        print(f"[gt] Written: {out_path} ({os.path.getsize(out_path)} bytes)")


if __name__ == "__main__":
    main()
