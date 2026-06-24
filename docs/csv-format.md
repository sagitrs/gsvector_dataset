# CSV 格式生成器

**日期：** 2026-06-24
**类型：** 子设计文档
**依赖：** [主文档](../DESIGN.md)

## 目标

为 gsvector-pg 的 SQL regression 测试生成 CSV 格式数据集（PG COPY 兼容）。

## CSV 格式

```csv
id,v1,v2,...,vd
0,0.0607,-0.0295,...,0.0535
1,0.0131,0.0154,...,0.0221
```

- 第一行为列名（PG COPY WITH HEADER）
- 第一列 `id` 为 uint64 行号（0-based）
- 后续列为 float32 向量值
- gsvector-pg 测试通过 `COPY ... FROM 'base.csv' WITH (FORMAT CSV, HEADER)` 加载

## 转换脚本：`scripts/fvecs2csv.py`

```python
# fvecs2csv.py <input.fvecs> <output.csv>
# 读取 .fvecs 文件，写出 CSV
```

### 实现要点

1. 读取 fvecs 头 4 字节 → dim
2. 逐行：4 字节 dim + dim×4 字节 float32
3. 写入 CSV：`id, v0, v1, ..., v{dim-1}`

### 处理规模

- SIFT 1k (1000 行): <1s
- SIFT 100k (100k 行): ~5s
- GIST 1m (1M 行 × 960-dim): ~30s

**并行加速**：多个数据集通过 `make -jN csv` 并行转换，IO 密集，建议 `N` 不超过 CPU 核心数。

## Makefile 集成

```makefile
sift/1k/base.csv: sift/1k/base.fvecs scripts/fvecs2csv.py
        $(PYTHON) scripts/fvecs2csv.py $< $@
```

所有 CSV 文件可批量生成、LFS 追踪。
