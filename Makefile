# CostDNA — common workflows.
#
# Most things in this repo are a single command. The Makefile just makes them
# discoverable: `make help` shows the menu.

.PHONY: help install test demo scan benchmark ablate calibrate learn discover \
        simulate sim-stop tf-init tf-apply tf-destroy doctor lint clean

VENV ?= .venv
PY    = $(VENV)/bin/python
PIP   = $(VENV)/bin/pip
COSTDNA = $(VENV)/bin/costdna
SEED ?= 42

help:                ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1;36m%-15s\033[0m %s\n", $$1, $$2}'

install:             ## Set up venv, install deps + costdna in editable mode.
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test:                ## Run pytest suite.
	PYTHONPATH=src $(VENV)/bin/pytest tests/ -v

demo: scan benchmark ablate calibrate learn  ## Full synthetic walkthrough — every command.

scan:                ## costdna scan (synthetic).
	$(COSTDNA) scan --synthetic --show-kind --seed $(SEED)

benchmark:           ## Multi-seed benchmark across 5 seeds.
	$(COSTDNA) benchmark --synthetic --seeds 5 --seed $(SEED)

kfold:               ## 5-fold cross-validated benchmark.
	$(COSTDNA) benchmark --synthetic --kfold 5 --seed $(SEED)

ablate:              ## Feature + edge ablation (3 seeds).
	$(COSTDNA) ablate --synthetic --n-seeds 3 --seed $(SEED)

calibrate:           ## Confidence calibration plot.
	$(COSTDNA) calibrate --synthetic --seed $(SEED)

learn:               ## Active learning curves — all 3 strategies.
	$(COSTDNA) learn --synthetic --compare-all --seed $(SEED)

discover:            ## Auto-discover teams from IAM patterns.
	$(COSTDNA) discover

doctor:              ## Preflight a real AWS account (default profile).
	$(COSTDNA) doctor

simulate:            ## Run all simulators against the live AWS account (Ctrl+C to stop).
	$(PY) -m simulation.run_all

sim-stop:            ## Force-kill any background simulator processes.
	-pkill -f "simulation.run_all" || true

tf-init:             ## terraform init.
	cd terraform && terraform init

tf-apply:            ## terraform apply (creates the labeled AWS env).
	cd terraform && terraform apply

tf-destroy:          ## terraform destroy.
	cd terraform && terraform destroy

lint:                ## Lint with ruff.
	$(VENV)/bin/ruff check src/ tests/ simulation/

clean:               ## Remove build artifacts and caches.
	rm -rf build/ dist/ src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
