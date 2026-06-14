#!/usr/bin/env python3
"""
Convert fbin/ibin format (RAFT ANN benchmarks) to fvecs/ivecs format.

fbin format: [uint32: num_vectors] [uint32: dim] [float32 × num_vectors × dim]
ibin format: [uint32: num_vectors] [uint32: k] [int32 × num_vectors × k]

fvecs format: [int32: dim] [float32 × dim] ... repeated per vector
ivecs format: [int32: k] [int32 × k] ... repeated per query
"""

import argparse
import os
import struct
import numpy as np


def read_fbin(filepath):
    """Read fbin file. Returns (num_vectors, dim, data as numpy array)."""
    with open(filepath, "rb") as f:
        num_vectors = struct.unpack("<I", f.read(4))[0]
        dim = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(), dtype=np.float32).reshape(num_vectors, dim)
    return data


def read_ibin(filepath):
    """Read ibin file. Returns (num_queries, k, data as numpy array)."""
    with open(filepath, "rb") as f:
        num_queries = struct.unpack("<I", f.read(4))[0]
        k = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(), dtype=np.int32).reshape(num_queries, k)
    return data


def write_fvecs(filepath, vecs):
    """Write numpy array (N, dim) as fvecs file."""
    N, dim = vecs.shape
    with open(filepath, "wb") as f:
        for i in range(N):
            f.write(struct.pack("<i", dim))
            f.write(vecs[i].astype(np.float32).tobytes())


def write_ivecs(filepath, indices):
    """Write numpy array (Q, k) as ivecs file."""
    Q, k = indices.shape
    with open(filepath, "wb") as f:
        for i in range(Q):
            f.write(struct.pack("<i", k))
            f.write(indices[i].astype(np.int32).tobytes())


def main():
    parser = argparse.ArgumentParser(
        description="Convert fbin/ibin to fvecs/ivecs format")
    parser.add_argument("--base", help="Input base.fbin")
    parser.add_argument("--query", help="Input query.fbin")
    parser.add_argument("--gt-neighbors", help="Input groundtruth.neighbors.ibin")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--gt-k", type=int, default=100,
                        help="Top-K to extract from ground truth (default: 100)")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.base:
        print(f"[convert] Reading base: {args.base}")
        base = read_fbin(args.base)
        N, dim = base.shape
        print(f"[convert] Base: {N} vectors, dim={dim}")
        out = os.path.join(args.out_dir, "base.fvecs")
        write_fvecs(out, base)
        print(f"[convert] Written: {out} ({os.path.getsize(out)} bytes)")

    if args.query:
        print(f"[convert] Reading query: {args.query}")
        query = read_fbin(args.query)
        Q, dim = query.shape
        print(f"[convert] Query: {Q} vectors, dim={dim}")
        out = os.path.join(args.out_dir, "query.fvecs")
        write_fvecs(out, query)
        print(f"[convert] Written: {out} ({os.path.getsize(out)} bytes)")

    if args.gt_neighbors:
        print(f"[convert] Reading ground truth: {args.gt_neighbors}")
        gt = read_ibin(args.gt_neighbors)
        Q, full_k = gt.shape
        print(f"[convert] GT: {Q} queries, k={full_k}")
        for k in [10, 100]:
            if k <= full_k:
                subset = gt[:, :k]
                out = os.path.join(args.out_dir, f"gt_top{k}.ivecs")
                write_ivecs(out, subset)
                print(f"[convert] Written: {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
