# Makefile 目标扩展

**日期：** 2026-06-24
**类型：** 子设计文档
**依赖：** [主文档](../DESIGN.md), [CSV](csv-format.md), [Iceberg](iceberg-format.md)

## 新增 Makefile 目标

```makefile
# 现有目标（不变）
make sift              # fvecs + ivecs + ground truth
make ci                # 1k fvecs only
make bench             # up to BENCH_MAX_SIZE

# 新增
make csv               # 为所有数据集生成 CSV 格式
make iceberg           # 为所有数据集生成 Iceberg 格式
make all-formats       # make all + csv + iceberg (全量)
```

## 目标依赖链

```
make csv:
  sift/1k/base.csv      ← sift/1k/base.fvecs → scripts/fvecs2csv.py
  sift/10k/base.csv     ← sift/10k/base.fvecs
  ...
  gist/1k/base.csv      ← gist/1k/base.fvecs
  ...

make iceberg:
  sift/1k/iceberg/metadata/metadata.json  ← sift/1k/base.fvecs → scripts/fvecs2iceberg.py
  ...
```

## 模式规则

```makefile
# CSV: fvecs → CSV
%/base.csv: %/base.fvecs scripts/fvecs2csv.py
	$(PYTHON) scripts/fvecs2csv.py $< $@

%/query.csv: %/query.fvecs scripts/fvecs2csv.py
	$(PYTHON) scripts/fvecs2csv.py $< $@

# Iceberg: fvecs → Parquet + metadata
%/iceberg/metadata/metadata.json: %/base.fvecs scripts/fvecs2iceberg.py
	@echo "=== all-formats: DONE ==="
```

## 并行构建

数据集构建是 IO 密集型（读写 fvecs/Parquet）。使用 Make 的 `-j` 标志并行构建多个数据集：

```bash
make -j4 csv       # 4 个数据集并行转换
make -j8 iceberg   # 8 个 Iceberg 表并行构建
```

Makefile 中无需特殊配置——模式规则天然支持并行。每个 `%/base.csv` 目标互不依赖，GNU Make 自动调度。

## 与现有 CI 集成

```makefile
# gsvector-pg CI 准备数据
make csv DATASET=sift SIZE=1k

# gsiceberg CI 准备数据  
make iceberg DATASET=sift SIZE=1k
```

消费者仓库通过 `make fetch-datasets-ci` 获取 fvecs 后，按需运行 `make csv` 或 `make iceberg`。
