# gsvector-dataset 多格式数据集设计

**日期：** 2026-06-24
**类型：** 架构设计
**状态：** Draft

## 问题

gsvector-dataset 当前仅提供 `.fvecs`/`.ivecs` 格式。各消费者仓库需要不同格式：

| 仓库 | 测试类型 | 需要格式 | 当前状态 |
|------|---------|---------|:--:|
| gsvector (C++) | benchmark, recall | `.fvecs` + `.ivecs` | ✅ |
| gsvector (Python) | binding test, perf | numpy array (加载 `.fvecs`) | ✅ |
| gsvector-pg | SQL regression | `.csv` (PG COPY) | ❌ |
| gsiceberg | FDW integration | Iceberg table (Parquet + metadata) | ❌ |

## 方案：从 fvecs 单向转换

不重造源数据。从已就绪的 `.fvecs` 文件生成目标格式：

```
.fvecs (source, LFS-tracked)
  ├── fvecs2csv.py       → .csv        (gsvector-pg)
  └── fvecs2iceberg.py   → Parquet +   (gsiceberg)
                            metadata.json
```

## 目录结构（以 sift/1k 为例）

```
sift/1k/
  base.fvecs          ← 现有（LFS）
  query.fvecs         ← 现有（LFS）
  gt_top10.ivecs      ← 现有（LFS）
  gt_top100.ivecs     ← 现有（LFS）
  base.csv            ← 新增
  query.csv           ← 新增
  iceberg/            ← 新增
    data/
      base.parquet
      query.parquet
    metadata/
      metadata.json
      snap-*.avro
```

## 子文档

| 文档 | 内容 |
|------|------|
| [docs/csv-format.md](docs/csv-format.md) | CSV 格式生成器 |
| [docs/iceberg-format.md](docs/iceberg-format.md) | Iceberg 格式生成器 |
| [docs/makefile-targets.md](docs/makefile-targets.md) | Makefile 扩展 (`make csv`, `make iceberg`) |

## 规模

| 数据集 | 1k | 10k | 100k |
|--------|----|-----|------|
| SIFT (128-dim) | ~0.5 MB | ~5 MB | ~50 MB |
| GIST (960-dim) | ~4 MB | ~38 MB | ~380 MB |

CSV + Iceberg 增量约为原始大小的 2×。100k 规模在 LFS 可接受范围内。

## 构建性能

格式转换是 IO 密集型。使用 `make -jN csv` 或 `make -jN iceberg` 并行构建多个数据集（模式规则天然无依赖，GNU Make 自动并行调度）。
