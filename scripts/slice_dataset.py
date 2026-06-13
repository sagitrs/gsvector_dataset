#!/usr/bin/env python3
"""
First-N slicing of fvecs binary files.

Reads a full fvecs base file and query file, writes first-N subsets for each
target size. The query file is copied whole to each size directory (shared
across all sizes).

fvecs format (little-endian):
  [int32: dim] [float32 * dim] ... repeated per vector
"""

import argparse
import os
import struct
import sys


def read_fvecs_header(filepath):
    """Return (dim, num_vectors, record_size_bytes) by scanning the file."""
    record_size = None
    count = 0
    with open(filepath, "rb") as f:
        while True:
            header = f.read(4)
            if len(header) < 4:
                break
            dim = struct.unpack("<i", header)[0]
            if dim <= 0 or dim > 100000:
                raise ValueError(
                    f"Invalid dimension {dim} at vector {count} in {filepath}"
                )
            if record_size is None:
                record_size = 4 + dim * 4
            elif record_size != 4 + dim * 4:
                raise ValueError(
                    f"Inconsistent dimension at vector {count} in {filepath}: "
                    f"expected dim={record_size}, got dim={dim}"
                )
            data = f.read(dim * 4)
            if len(data) < dim * 4:
                break
            count += 1
    if record_size is None:
        raise ValueError(f"No vectors found in {filepath}")
    dim = (record_size - 4) // 4
    return dim, count, record_size


def slice_first_n(input_path, output_path, n_vectors, record_size):
    """Copy first N vectors from input to output using binary copy."""
    bytes_to_copy = n_vectors * record_size
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(input_path, "rb") as fin:
        data = fin.read(bytes_to_copy)
    if len(data) < bytes_to_copy:
        raise ValueError(
            f"Input file {input_path} has fewer than {n_vectors} vectors "
            f"(got {len(data) // record_size})"
        )
    with open(output_path, "wb") as fout:
        fout.write(data)
    expected_size = n_vectors * record_size
    actual_size = os.path.getsize(output_path)
    if actual_size != expected_size:
        raise ValueError(
            f"Output size mismatch: expected {expected_size}, got {actual_size}"
        )


def copy_file(src, dst):
    """Copy an entire file."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as fin:
        data = fin.read()
    with open(dst, "wb") as fout:
        fout.write(data)


def main():
    parser = argparse.ArgumentParser(description="Slice fvecs dataset")
    parser.add_argument("--base", required=True, help="Full base.fvecs path")
    parser.add_argument("--query", required=True, help="Full query.fvecs path")
    parser.add_argument(
        "--sizes",
        default="1000,10000,100000,1000000",
        help="Comma-separated target sizes (default: 1000,10000,100000,1000000)",
    )
    parser.add_argument("--dataset", required=True, help="Dataset name (sift/gist/bioasq/cohere)")
    parser.add_argument(
        "--out-dir", required=True, help="Dataset root directory (e.g., third_party/gsvector_dataset/sift)"
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",")]
    size_labels = {1000: "1k", 10000: "10k", 100000: "100k", 1000000: "1m"}

    # Scan base file
    dim, total_base, record_size = read_fvecs_header(args.base)
    print(f"[slice] Base: dim={dim}, total_vectors={total_base}, "
          f"record_size={record_size}")
    _, total_query, q_record_size = read_fvecs_header(args.query)
    print(f"[slice] Query: dim={dim}, total_vectors={total_query}")

    if q_record_size != record_size:
        raise ValueError("Base and query dimension mismatch")

    for size in sizes:
        if size not in size_labels:
            raise ValueError(f"Unknown size label for size={size}")
        label = size_labels[size]
        out_subdir = os.path.join(args.out_dir, label)
        out_base = os.path.join(out_subdir, "base.fvecs")
        out_query = os.path.join(out_subdir, "query.fvecs")

        print(f"[slice] Creating {label}: {size} base vectors")
        slice_first_n(args.base, out_base, size, record_size)

        print(f"[slice] Copying query to {label}")
        copy_file(args.query, out_query)

        # Verify
        _, cnt, _ = read_fvecs_header(out_base)
        print(f"[slice]   {label}/base.fvecs: {cnt} vectors OK")


if __name__ == "__main__":
    main()
