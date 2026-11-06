.PHONY: validate analyze train benchmark closed-loop demo dashboard test mqtt-up mqtt-down ml-node launch-main launch-edge launch-local

BROKER_HOST ?= 127.0.0.1
DASHBOARD_HOST ?= 127.0.0.1
DASHBOARD_PORT ?= 8080

validate:
	python3 tests/validate_dataset.py

train:
	python3 src/train_models.py

benchmark: train
	.venv/bin/python src/benchmark_models.py

closed-loop: benchmark
	.venv/bin/python src/evaluate_closed_loop.py

analyze:
	python3 src/analyze_dataset.py

demo: analyze closed-loop
	python3 src/replay.py --mode local --split test --limit 0

dashboard:
	python3 src/dashboard.py --host $(DASHBOARD_HOST) --port $(DASHBOARD_PORT)

ml-node:
	.venv/bin/python src/run_ml_node.py --broker $(BROKER_HOST) --dashboard-port $(DASHBOARD_PORT)

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

mqtt-up:
	docker compose up -d

mqtt-down:
	docker compose down

launch-main:
	./team11.sh main $(BROKER_HOST)

launch-edge:
	./team11.sh edge

launch-local:
	./team11.sh local
