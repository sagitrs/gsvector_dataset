#!/usr/bin/env python3
"""gsvector-dataset CLI — get dataset paths without remembering directory layout.

Usage:
  python3 get.py sift 1k                     # list available formats
  python3 get.py sift 1k csv                 # CSV paths
  python3 get.py sift 1k fvecs --gt top10    # fvecs + ground truth
  python3 get.py sift 10k iceberg            # Iceberg paths
  python3 get.py sift --all                  # all sizes, csv
  python3 get.py gist 10k --json             # JSON output for scripts
"""

import argparse, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = ["1k", "10k", "100k", "1m"]

DATASETS = ["sift", "gist", "bioasq", "cohere"]

FORMATS = {
    "fvecs":  {"base": "base.fvecs",  "query": "query.fvecs"},
    "ivecs":  {},  # handled separately with --gt
    "csv":    {"base": "base.csv",    "query": "query.csv"},
    "iceberg": {"meta": "iceberg/metadata/metadata.json"},
    "iceberg-data": {"base": "iceberg/data/base.parquet",
                     "query": "iceberg/data/query.parquet"},
}

GT_FILES = {
    "top10":  "gt_top10.ivecs",
    "top100": "gt_top100.ivecs",
}


def list_formats(ds, sz):
    """Print available formats for a dataset+size."""
    ds_dir = ROOT / ds / sz
    print(f"{ds}/{sz}:")
    for fmt, files in FORMATS.items():
        if fmt == "ivecs":
            continue
        first = list(files.values())[0]
        if (ds_dir / first).exists():
            print(f"  {fmt:<14s} ✓")
        else:
            print(f"  {fmt:<14s} (run: make {fmt if fmt != 'iceberg-data' else 'iceberg'})")


def resolve(ds, sz, fmt):
    """Return dict of file paths for a fmt. Key = role ('base', 'query', 'meta')."""
    ds_dir = ROOT / ds / sz
    result = {}
    for role, filename in FORMATS.get(fmt, {}).items():
        path = ds_dir / filename
        if path.exists():
            result[role] = str(path)
        else:
            result[role] = f"MISSING:{path}"
    return result


def resolve_gt(ds, sz, k):
    """Return ground truth path."""
    filename = GT_FILES.get(k)
    if not filename:
        return None
    path = ROOT / ds / sz / filename
    if path.exists():
        return str(path)
    return f"MISSING:{path}"


def output_paths(paths, fmt):
    """Print paths in shell-friendly format."""
    if fmt == "json":
        import json
        print(json.dumps(paths))
    else:
        for k, v in paths.items():
            if v:
                print(f"{k}={v}")


def main():
    parser = argparse.ArgumentParser(
        description="gsvector-dataset CLI — resolve dataset paths")
    parser.add_argument("dataset", choices=DATASETS + ["all"],
                        help="Dataset name")
    parser.add_argument("size", nargs="?", default=None,
                        help=f"Size: {', '.join(SIZES)}")
    parser.add_argument("format", nargs="?", choices=list(FORMATS.keys()),
                        help="Output format")
    parser.add_argument("--gt", choices=list(GT_FILES.keys()),
                        help="Ground truth k-value")
    parser.add_argument("--all", action="store_true",
                        help="All sizes (requires --format)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output")
    args = parser.parse_args()

    # Mode 1: list
    if not args.format:
        if not args.size:
            print(f"Usage: {sys.argv[0]} <dataset> <size> [format] [--gt k]", file=sys.stderr)
            print(f"Datasets: {', '.join(DATASETS)}", file=sys.stderr)
            print(f"Sizes:    {', '.join(SIZES)}", file=sys.stderr)
            print(f"Formats:  {', '.join(FORMATS.keys())}", file=sys.stderr)
            sys.exit(1)
        list_formats(args.dataset, args.size)
        if args.gt:
            gt_path = resolve_gt(args.dataset, args.size, args.gt)
            print(f"  gt_{args.gt}: {gt_path}")
        return

    # Mode 2: resolve
    sizes = SIZES if args.all else [args.size]
    datasets = DATASETS if args.dataset == "all" else [args.dataset]

    for ds in datasets:
        for sz in sizes:
            ds_dir = ROOT / ds / sz
            if not ds_dir.exists():
                if args.json:
                    print(f'{{"dataset":"{ds}","size":"{sz}","error":"not found"}}')
                continue

            if args.json:
                import json
                out = {"dataset": ds, "size": sz, "format": args.format}
                out["files"] = {k: v for k, v in resolve(ds, sz, args.format).items()}
                if args.gt:
                    out["gt"] = {args.gt: resolve_gt(ds, sz, args.gt)}
                print(json.dumps(out))
            else:
                prefix = f"{ds}/{sz}"
                for role, path in resolve(ds, sz, args.format).items():
                    print(f"{path}")
                if args.gt:
                    print(resolve_gt(ds, sz, args.gt))


if __name__ == "__main__":
    main()
