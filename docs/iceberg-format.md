# Iceberg 格式生成器

**日期：** 2026-06-24
**类型：** 子设计文档
**依赖：** [主文档](../DESIGN.md)

## 目标

为 gsiceberg 的 FDW 集成测试生成 Iceberg table 格式数据集。

## Iceberg table 结构

```
iceberg/
  data/
    base.parquet        ← 向量数据
    query.parquet       ← 查询向量
  metadata/
    metadata.json       ← table metadata + snapshot refs
    snap-*.avro         ← manifest list (Apache Avro)
```

### metadata.json（最小可挂载）

```json
{
  "format-version": 1,
  "table-uuid": "fb6c3100-...",
  "location": "/warehouse/test_sift_1k",
  "last-updated-ms": 1719000000000,
  "current-schema-id": 0,
  "schemas": [
    {"schema-id": 0, "type": "struct",
     "fields": [
       {"id": 1, "name": "id", "type": "long", "required": true},
       {"id": 2, "name": "v0", "type": "float", "required": true},
       ...
       {"id": 129, "name": "v127", "type": "float", "required": true}
     ]}
  ],
  "snapshots": [
    {"snapshot-id": 1, "parent-snapshot-id": null,
     "timestamp-ms": 1719000000000,
     "manifest-list": "metadata/snap-1.avro",
     "summary": {"operation": "append"}}
  ]
}
```

## 转换脚本：`scripts/fvecs2iceberg.py`

```
fvecs2iceberg.py <base.fvecs> <query.fvecs> <output_dir/>

生成:
  output_dir/iceberg/data/base.parquet
  output_dir/iceberg/data/query.parquet
  output_dir/iceberg/metadata/metadata.json
  output_dir/iceberg/metadata/snap-1.avro
```

### 依赖

- `pyarrow` — Parquet 写入
- `fastavro` 或 `avro` — manifest 写入

### 实现要点

1. 读取 fvecs → numpy array
2. 构建 PyArrow Table（id: int64, v0...v{d-1}: float32）
3. 写入 Parquet 文件
4. 生成 metadata.json（schema 从 dim 推导）
5. 生成单条目 manifest list（Avro）

## Makefile 集成

```makefile
sift/1k/iceberg/metadata/metadata.json: sift/1k/base.fvecs scripts/fvecs2iceberg.py
        $(PYTHON) scripts/fvecs2iceberg.py $< sift/1k/query.fvecs sift/1k/

iceberg: $(foreach ds,$(ALL_DATASETS),$(foreach sz,$(NON_1M_SIZES),$(ds)/$(sz)/iceberg/metadata/metadata.json))
```
