# gsvector_dataset Makefile
# Orchestrates download, slicing, and ground truth computation.

PYTHON := $(HOME)/venv/bin/python
SCRIPTS := scripts
DATASET_DIR := $(shell pwd)

# Dataset configuration
# SIFT: 128-dim, all sizes LFS-tracked (1M base < 1GB)
# GIST: 960-dim, 1k/10k/100k LFS-tracked, 1m on-demand
# BIOASQ: 768-dim, 1k/10k/100k LFS-tracked, 1m on-demand
# COHERE: 768-dim, 1k/10k/100k LFS-tracked, 1m on-demand

SIZES := 1k 10k 100k 1m
NON_1M_SIZES := 1k 10k 100k
ALL_DATASETS := sift gist bioasq cohere

# ---- SIFT ----
.PHONY: sift
sift: $(foreach sz,$(SIZES),sift/$(sz)/base.fvecs) \
      $(foreach sz,$(SIZES),sift/$(sz)/gt_top10.ivecs) \
      $(foreach sz,$(SIZES),sift/$(sz)/gt_top100.ivecs)

sift/raw/sift_base.fvecs:
	$(SCRIPTS)/download_sift.sh

sift/%/base.fvecs: sift/raw/sift_base.fvecs $(SCRIPTS)/slice_dataset.py
	$(PYTHON) $(SCRIPTS)/slice_dataset.py \
		--base sift/raw/sift_base.fvecs \
		--query sift/raw/sift_query.fvecs \
		--dataset sift \
		--sizes 1000,10000,100000,1000000 \
		--out-dir $(DATASET_DIR)/sift

sift/1k/gt_top10.ivecs sift/1k/gt_top100.ivecs: sift/1k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base sift/1k/base.fvecs \
		--query sift/1k/query.fvecs \
		-k 10,100 \
		--out-dir sift/1k

sift/10k/gt_top10.ivecs sift/10k/gt_top100.ivecs: sift/10k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base sift/10k/base.fvecs \
		--query sift/10k/query.fvecs \
		-k 10,100 \
		--out-dir sift/10k

sift/100k/gt_top10.ivecs sift/100k/gt_top100.ivecs: sift/100k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base sift/100k/base.fvecs \
		--query sift/100k/query.fvecs \
		-k 10,100 \
		--out-dir sift/100k

sift/1m/gt_top10.ivecs sift/1m/gt_top100.ivecs: sift/1m/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base sift/1m/base.fvecs \
		--query sift/1m/query.fvecs \
		-k 10,100 \
		--out-dir sift/1m

# ---- GIST ----
.PHONY: gist gist-1m
gist: $(foreach sz,$(NON_1M_SIZES),gist/$(sz)/base.fvecs) \
      $(foreach sz,$(NON_1M_SIZES),gist/$(sz)/gt_top10.ivecs) \
      $(foreach sz,$(NON_1M_SIZES),gist/$(sz)/gt_top100.ivecs)

gist-1m: gist/1m/gt_top10.ivecs gist/1m/gt_top100.ivecs

gist/raw/gist_base.fvecs:
	$(SCRIPTS)/download_gist.sh

gist/%/base.fvecs: gist/raw/gist_base.fvecs $(SCRIPTS)/slice_dataset.py
	$(PYTHON) $(SCRIPTS)/slice_dataset.py \
		--base gist/raw/gist_base.fvecs \
		--query gist/raw/gist_query.fvecs \
		--dataset gist \
		--sizes 1000,10000,100000,1000000 \
		--out-dir $(DATASET_DIR)/gist

gist/1k/gt_top10.ivecs gist/1k/gt_top100.ivecs: gist/1k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base gist/1k/base.fvecs \
		--query gist/1k/query.fvecs \
		-k 10,100 \
		--out-dir gist/1k

gist/10k/gt_top10.ivecs gist/10k/gt_top100.ivecs: gist/10k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base gist/10k/base.fvecs \
		--query gist/10k/query.fvecs \
		-k 10,100 \
		--out-dir gist/10k

gist/100k/gt_top10.ivecs gist/100k/gt_top100.ivecs: gist/100k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base gist/100k/base.fvecs \
		--query gist/100k/query.fvecs \
		-k 10,100 \
		--out-dir gist/100k

gist/1m/gt_top10.ivecs gist/1m/gt_top100.ivecs: gist/1m/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base gist/1m/base.fvecs \
		--query gist/1m/query.fvecs \
		-k 10,100 \
		--out-dir gist/1m

# ---- BIOASQ ----
.PHONY: bioasq bioasq-1m
bioasq: $(foreach sz,$(NON_1M_SIZES),bioasq/$(sz)/base.fvecs) \
        $(foreach sz,$(NON_1M_SIZES),bioasq/$(sz)/gt_top10.ivecs) \
        $(foreach sz,$(NON_1M_SIZES),bioasq/$(sz)/gt_top100.ivecs)

bioasq-1m: bioasq/1m/gt_top10.ivecs bioasq/1m/gt_top100.ivecs

bioasq/raw/bioasq_base.fvecs:
	$(SCRIPTS)/download_bioasq.sh

bioasq/%/base.fvecs: bioasq/raw/bioasq_base.fvecs $(SCRIPTS)/slice_dataset.py
	$(PYTHON) $(SCRIPTS)/slice_dataset.py \
		--base bioasq/raw/bioasq_base.fvecs \
		--query bioasq/raw/bioasq_query.fvecs \
		--dataset bioasq \
		--sizes 1000,10000,100000,1000000 \
		--out-dir $(DATASET_DIR)/bioasq

bioasq/1k/gt_top10.ivecs bioasq/1k/gt_top100.ivecs: bioasq/1k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base bioasq/1k/base.fvecs \
		--query bioasq/1k/query.fvecs \
		-k 10,100 \
		--out-dir bioasq/1k

bioasq/10k/gt_top10.ivecs bioasq/10k/gt_top100.ivecs: bioasq/10k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base bioasq/10k/base.fvecs \
		--query bioasq/10k/query.fvecs \
		-k 10,100 \
		--out-dir bioasq/10k

bioasq/100k/gt_top10.ivecs bioasq/100k/gt_top100.ivecs: bioasq/100k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base bioasq/100k/base.fvecs \
		--query bioasq/100k/query.fvecs \
		-k 10,100 \
		--out-dir bioasq/100k

bioasq/1m/gt_top10.ivecs bioasq/1m/gt_top100.ivecs: bioasq/1m/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base bioasq/1m/base.fvecs \
		--query bioasq/1m/query.fvecs \
		-k 10,100 \
		--out-dir bioasq/1m

# ---- COHERE ----
.PHONY: cohere cohere-1m
cohere: $(foreach sz,$(NON_1M_SIZES),cohere/$(sz)/base.fvecs) \
        $(foreach sz,$(NON_1M_SIZES),cohere/$(sz)/gt_top10.ivecs) \
        $(foreach sz,$(NON_1M_SIZES),cohere/$(sz)/gt_top100.ivecs)

cohere-1m: cohere/1m/gt_top10.ivecs cohere/1m/gt_top100.ivecs

cohere/raw/cohere_base.fvecs:
	$(SCRIPTS)/download_cohere.sh

cohere/%/base.fvecs: cohere/raw/cohere_base.fvecs $(SCRIPTS)/slice_dataset.py
	$(PYTHON) $(SCRIPTS)/slice_dataset.py \
		--base cohere/raw/cohere_base.fvecs \
		--query cohere/raw/cohere_query.fvecs \
		--dataset cohere \
		--sizes 1000,10000,100000,1000000 \
		--out-dir $(DATASET_DIR)/cohere

cohere/1k/gt_top10.ivecs cohere/1k/gt_top100.ivecs: cohere/1k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base cohere/1k/base.fvecs \
		--query cohere/1k/query.fvecs \
		-k 10,100 \
		--out-dir cohere/1k

cohere/10k/gt_top10.ivecs cohere/10k/gt_top100.ivecs: cohere/10k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base cohere/10k/base.fvecs \
		--query cohere/10k/query.fvecs \
		-k 10,100 \
		--out-dir cohere/10k

cohere/100k/gt_top10.ivecs cohere/100k/gt_top100.ivecs: cohere/100k/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base cohere/100k/base.fvecs \
		--query cohere/100k/query.fvecs \
		-k 10,100 \
		--out-dir cohere/100k

cohere/1m/gt_top10.ivecs cohere/1m/gt_top100.ivecs: cohere/1m/base.fvecs
	$(PYTHON) $(SCRIPTS)/compute_groundtruth.py \
		--base cohere/1m/base.fvecs \
		--query cohere/1m/query.fvecs \
		-k 10,100 \
		--out-dir cohere/1m

# ---- All datasets (LFS-tracked) ----
.PHONY: all
all: sift gist bioasq cohere

# ---- Validation ----
.PHONY: validate
validate:
	@for ds in $(ALL_DATASETS); do \
		echo "=== Validating $$ds ==="; \
		$(PYTHON) $(SCRIPTS)/validate.py --dataset $$ds --dataset-dir $$ds; \
	done
	@echo "=== All datasets validated ==="

# ---- Cleanup ----
.PHONY: clean
clean:
	rm -rf sift/1k sift/10k sift/100k sift/1m sift/raw
	rm -rf gist/1k gist/10k gist/100k gist/1m gist/raw
	rm -rf bioasq/1k bioasq/10k bioasq/100k bioasq/1m bioasq/raw
	rm -rf cohere/1k cohere/10k cohere/100k cohere/1m cohere/raw

.PHONY: help
help:
	@echo "gsvector_dataset Makefile"
	@echo "  make sift        - Generate all SIFT sizes (LFS-tracked)"
	@echo "  make gist        - Generate GIST 1k/10k/100k (LFS-tracked)"
	@echo "  make gist-1m     - Generate GIST 1m (on-demand)"
	@echo "  make bioasq      - Generate BioASQ 1k/10k/100k (LFS-tracked)"
	@echo "  make bioasq-1m   - Generate BioASQ 1m (on-demand)"
	@echo "  make cohere      - Generate Cohere 1k/10k/100k (LFS-tracked)"
	@echo "  make cohere-1m   - Generate Cohere 1m (on-demand)"
	@echo "  make all         - Generate all LFS-tracked datasets"
	@echo "  make validate    - Validate all datasets"
	@echo "  make clean       - Remove all generated data"
