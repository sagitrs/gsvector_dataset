#!/usr/bin/env python3
"""
Extract fvecs/ivecs from ann-benchmarks HDF5 files by direct data block reading.

The ann-benchmarks HDF5 files have a known layout:
  [header] [train float32] [test float32] [neighbors int32] [distances float64]

Each dataset is stored contiguously without padding between vectors.
"""

import argparse
import os
import struct
import numpy as np


def find_train_offset(data, dim, expected_train=1000000):
    """Find the start of train data by scanning for float32 vectors."""
    # The header is typically < 1MB. Scan in 4KB steps
    for off in range(0, min(2_000_000, len(data)), 4096):
        # Check first vector
        vals = struct.unpack_from('<' + 'f' * dim, data, off)
        # SIFT values: 0-255, mostly in range. GIST: wider range
        valid = sum(1 for v in vals if -1e10 < v < 1e10)
        if valid < dim:
            continue
        # Check a few more vectors
        ok = True
        for i in range(1, 5):
            vals2 = struct.unpack_from('<' + 'f' * dim, data, off + i * dim * 4)
            v2 = sum(1 for v in vals2 if -1e10 < v < 1e10)
            if v2 < dim:
                ok = False
                break
        if ok:
            return off
    raise ValueError("Could not find train data start")


def main():
    parser = argparse.ArgumentParser(
        description="Extract fvecs/ivecs from ann-benchmarks HDF5"
    )
    parser.add_argument("--input", required=True, help="HDF5 file path")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--dim", type=int, required=True, help="Vector dimension")
    parser.add_argument("--train-count", type=int, default=1000000,
                        help="Number of base vectors")
    parser.add_argument("--query-count", type=int, default=10000,
                        help="Number of query vectors")
    parser.add_argument("--neighbors-k", type=int, default=100,
                        help="K for neighbors dataset")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print(f"[extract] Reading {args.input}...")
    with open(args.input, "rb") as f:
        data = f.read()
    fsize = len(data)
    print(f"[extract] File size: {fsize:,} bytes")

    # Header detection: find where train data starts
    train_off = find_train_offset(data, args.dim, args.train_count)
    print(f"[extract] Train offset: 0x{train_off:x}")

    # Train data
    train_bytes = args.train_count * args.dim * 4
    train_end = train_off + train_bytes
    print(f"[extract] Train: {args.train_count:,} × {args.dim} float32 "
          f"({train_bytes:,} bytes)")

    # Test data (immediately after train)
    test_off = train_end
    test_bytes = args.query_count * args.dim * 4
    test_end = test_off + test_bytes
    print(f"[extract] Test: {args.query_count:,} × {args.dim} float32 "
          f"({test_bytes:,} bytes)")

    # Neighbors data (immediately after test)
    neighbors_off = test_end
    neighbors_bytes = args.query_count * args.neighbors_k * 4
    neighbors_end = neighbors_off + neighbors_bytes
    print(f"[extract] Neighbors: {args.query_count:,} × {args.neighbors_k} int32 "
          f"({neighbors_bytes:,} bytes)")

    # Read arrays
    train = np.frombuffer(
        data, dtype=np.float32,
        count=args.train_count * args.dim, offset=train_off
    ).reshape(args.train_count, args.dim)
    print(f"[extract] Train array: {train.shape}")

    test = np.frombuffer(
        data, dtype=np.float32,
        count=args.query_count * args.dim, offset=test_off
    ).reshape(args.query_count, args.dim)
    print(f"[extract] Test array: {test.shape}")

    neighbors = np.frombuffer(
        data, dtype=np.int32,
        count=args.query_count * args.neighbors_k, offset=neighbors_off
    ).reshape(args.query_count, args.neighbors_k)
    print(f"[extract] Neighbors array: {neighbors.shape}, "
          f"range=[{neighbors.min()}, {neighbors.max()}]")

    # Validate
    assert neighbors.min() >= 0, f"Negative index in neighbors: {neighbors.min()}"
    assert neighbors.max() < args.train_count, \
        f"Index {neighbors.max()} >= {args.train_count}"

    # Write base.fvecs
    base_path = os.path.join(args.out_dir, "base.fvecs")
    print(f"[extract] Writing {base_path}...")
    with open(base_path, "wb") as f:
        for vec in train:
            f.write(struct.pack("<i", args.dim))
            f.write(vec.astype(np.float32).tobytes())

    # Write query.fvecs
    query_path = os.path.join(args.out_dir, "query.fvecs")
    print(f"[extract] Writing {query_path}...")
    with open(query_path, "wb") as f:
        for vec in test:
            f.write(struct.pack("<i", args.dim))
            f.write(vec.astype(np.float32).tobytes())

    # Write gt_top10.ivecs and gt_top100.ivecs
    for k, label in [(10, "gt_top10.ivecs"), (100, "gt_top100.ivecs")]:
        gt_path = os.path.join(args.out_dir, label)
        print(f"[extract] Writing {gt_path} (top-{k})...")
        with open(gt_path, "wb") as f:
            for row in neighbors:
                f.write(struct.pack("<i", k))
                f.write(row[:k].astype(np.int32).tobytes())

    # Report sizes
    for fname in ["base.fvecs", "query.fvecs", "gt_top10.ivecs", "gt_top100.ivecs"]:
        path = os.path.join(args.out_dir, fname)
        sz = os.path.getsize(path)
        print(f"[extract]   {fname}: {sz:,} bytes ({sz/1e6:.1f} MB)")

    print("[extract] Done.")


if __name__ == "__main__":
    main()
