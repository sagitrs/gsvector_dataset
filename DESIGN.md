# gsvector_dataset Design Spec

## Overview

为 gsvector 向量插件提供标准 ANN 基准数据集，包含 SIFT/GIST/BioASQ/Cohere 四个数据集的多尺度版本（1k/10k/100k/1m），格式为 fvecs（向量）和 ivecs（答案）。

## Directory Layout

```
third_party/gsvector_dataset/
├── .gitattributes              # LFS tracking rules
├── .gitignore                  # Exclude on-demand 1m directories
├── DESIGN.md                   # This file
├── Makefile                    # Top-level orchestration
├── README.md                   # Usage documentation
├── scripts/
│   ├── download_sift.sh        # Fetch sift.tar.gz from corpus-texmex.irisa.fr
│   ├── download_gist.sh        # Fetch gist.tar.gz from corpus-texmex.irisa.fr
│   ├── download_cohere.sh      # Fetch cohere embeddings archive
│   ├── download_bioasq.sh      # Fetch bioasq embeddings archive
│   ├── slice_dataset.py        # First-N extract: 1M → 100k → 10k → 1k
│   ├── compute_groundtruth.py  # Brute-force k-NN → top10/top100 ivecs
│   └── validate.py             # Format and integrity checks
├── sift/                       # All sizes LFS-tracked (<1GB total for 1m)
│   ├── 1k/{base,query,gt_top10,gt_top100}.{fvecs,ivecs}
│   ├── 10k/...
│   ├── 100k/...
│   └── 1m/...
├── gist/
│   ├── 1k/{base,query,gt_top10,gt_top100}.{fvecs,ivecs}
│   ├── 10k/...
│   ├── 100k/...                # 100K × 960 × 4 ≈ 384MB，within LFS limit
│   └── 1m/                     # .gitignore'd, generated on demand
├── bioasq/
│   ├── 1k/..., 10k/..., 100k/...
│   └── 1m/                     # .gitignore'd
└── cohere/
    ├── 1k/..., 10k/..., 100k/...
    └── 1m/                     # .gitignore'd
```

Each leaf directory contains exactly 4 files: `base.fvecs`, `query.fvecs`, `gt_top10.ivecs`, `gt_top100.ivecs`.

## Storage Strategy

| Dataset | Dim | 1M base size | LFS Policy |
|---------|------|-------------|------------|
| SIFT    | 128  | ~500MB      | All sizes LFS-tracked |
| GIST    | 960  | ~3.6GB      | 1k/10k/100k LFS-tracked; 1m on-demand only |
| BioASQ  | 768  | ~3GB        | 1k/10k/100k LFS-tracked; 1m on-demand only |
| Cohere  | 768  | ~3GB        | 1k/10k/100k LFS-tracked; 1m on-demand only |

**Rule:** No single file exceeds 1GB. GIST/BioASQ/Cohere 1m base files are too large — users generate them on demand via `make gist-1m` / `make bioasq-1m` / `make cohere-1m`.

## Binary Formats

### fvecs (float vectors)
```
[int32: dimension] [float32 × dimension] [int32: dimension] [float32 × dimension] ...
```
Little-endian. Dimension repeated before each vector (ANN-benchmarks convention).

### ivecs (integer vectors)
```
[int32: dimension] [int32 × dimension] [int32: dimension] [int32 × dimension] ...
```
Little-endian. Values are 0-based indices into base.fvecs.

## Subset Derivation

First-N slicing from the full 1M base set:
- 1m = first 1,000,000 vectors
- 100k = first 100,000 vectors
- 10k = first 10,000 vectors
- 1k = first 1,000 vectors

Query set is shared across all sizes (fixed 1K queries).

## Ground Truth Computation

Brute-force exhaustive k-NN search for each query:
- Distance: L2 squared
- Compute top-10 and top-100 for each query
- Output as `gt_top10.ivecs` and `gt_top100.ivecs`

Self-validation: check all returned IDs are in range, distances are ascending.

## Data Flow (per dataset)

```
[download_<dataset>.sh]
  → raw/*.fvecs, raw/*.ivecs (if published ground truth exists)

[slice_dataset.py]
  raw/base.fvecs → {1k,10k,100k,1m}/base.fvecs
  raw/query.fvecs → shared query.fvecs (copied to each size dir)

[compute_groundtruth.py]
  For each size: base.fvecs × query.fvecs → gt_top10.ivecs, gt_top100.ivecs
```

## Script Design

### download_<dataset>.sh
- Fetch archive from public mirror, extract to `raw/`
- Validate via file size check
- Idempotent: skip if raw files already exist

### slice_dataset.py
- Arguments: `--base <path>`, `--query <path>`, `--sizes 1000,10000,100000,1000000`, `--out-dir <path>`
- Reads full fvecs, writes first-N vectors for each size
- Query set copied as-is to each size directory

### compute_groundtruth.py
- Arguments: `--base <path>`, `--query <path>`, `-k 10,100`, `--distance l2`, `--out-dir <path>`
- Uses NumPy vectorized distance computation
- Validates output correctness

### validate.py
- Arguments: `--dataset <name>`, `--sizes <list>`
- Checks file existence, header dimension consistency, record count, value range

## Makefile Targets

```makefile
PYTHON := ~/venv/bin/python

# Pre-generated, LFS-tracked
make sift        # All 4 sizes
make gist        # Download 1M → slice → LFS 1k/10k/100k
make bioasq      # Same
make cohere      # Same
make all         # All of the above

# On-demand only (not LFS-tracked)
make gist-1m     # Download + generate gist/1m/
make bioasq-1m
make cohere-1m

# Validation
make validate    # Validate all LFS-tracked datasets
```

## Dependencies

- `curl`, `tar` — download and unpack
- `~/venv/bin/python` with `numpy` — format conversion and ground truth
- `git-lfs` — large file storage

## Error Handling

- Download: 3 retries with exponential backoff, checksum/size validation
- Slice: verify output record counts match expected sizes
- Ground truth: verify all IDs in range [0, N-1], distances non-decreasing
- Idempotency: each step checks for existing valid output before running

## Git LFS Configuration

`.gitattributes`:
```
**/*.fvecs filter=lfs diff=lfs merge=lfs -text
**/*.ivecs filter=lfs diff=lfs merge=lfs -text
```

`.gitignore`:
```
gist/1m/
bioasq/1m/
cohere/1m/
```

## Phase Plan

| Phase | Dataset | Deliverables |
|-------|---------|-------------|
| 1 | SIFT    | download + slice + ground truth, all LFS-tracked. Validates pipeline. |
| 2 | GIST    | download 1M → slice 1k/10k/100k → LFS; 1m on-demand only. |
| 3 | BioASQ  | Same pattern as Phase 2. |
| 4 | Cohere  | Same pattern as Phase 2. |
| 5 | CI/Integration | LFS config, .gitignore, README, `make validate` CI hook. |

Each phase is independently testable. Phase 1 establishes the template; Phases 2-4 follow the same pattern.

## Test & Integration

- `make validate` checks all LFS-tracked datasets
- CI runs `make validate` after `git lfs pull`
- README documents dataset sources, usage, and on-demand generation
