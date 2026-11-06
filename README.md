# Team 11 — Server and IT Infrastructure Health Monitoring

A complete software-only IoT mini-project built around the fixed
`server_health_synthetic.csv` dataset. It replays server sensors, communicates
over MQTT, classifies health state, forecasts 15-minute demand, applies an
auditable resource policy, stores an audit trail, and presents an operational
dashboard. No physical hardware is required.

## What is included

- **Dataset:** 80,640 one-minute readings from four simulated servers over 14
  days, with normal workload and six fault families.
- **Analytics:** traditional Gaussian NB, ensemble Random Forest, three-layer
  neural MLP, validation-only model selection, and ridge demand forecasting.
- **IoT:** HiveMQ Cloud with authenticated TLS, Node-RED validation/routing,
  CSV replay publisher, analytics subscriber and software actuator
  acknowledgements. Local Mosquitto remains available as an offline fallback.
- **Backend:** SQLite telemetry, predictions and command audit log.
- **Dashboard:** responsive, dependency-free web UI and read-only JSON API.
- **Advanced analytics:** deterministic health score, forecast capacity
  headroom, local prediction explanations, training-baseline drift detection
  and telemetry completeness monitoring.
- **Safety:** explicit action reasons, operator-approval flags and five-minute
  per-server/action cooldown.
- **Verification:** integrity and system tests plus saved test metrics.

The dataset is **synthetic, scenario-based and reproducible**. It must not be
described as production, patient, hospital or clinical data.

## One-command HiveMQ Cloud evaluation launch

Create a HiveMQ Cloud cluster and copy `.env.hivemq.example` to `.env.hivemq`
on both laptops. Enter the same cluster hostname and project credential. Start
the other PC first:

```bash
./team11.sh hivemq-edge
```

On the main presentation laptop run:

```bash
TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

The main command creates the Python environment when needed, validates the
dataset, rebuilds the analysis and models, runs the tests, starts the ML node
and dashboard, publishes a class-balanced live stream, then restores a mixed
fleet state for discussion. Use `./team11.sh local` as a one-laptop backup.
See [the HiveMQ Cloud setup guide](docs/hivemq_cloud_setup.md) for the one-time
credential and permission steps.

## Fastest fully local demonstration

Python 3.10+ is required. Create the project environment first:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```bash
make validate
make analyze
make benchmark
python3 src/replay.py --mode local --split test --limit 0
python3 src/dashboard.py
```

Open <http://127.0.0.1:8080>. The generated database is
`output/server_health.db`; the exact model results are in
`output/evaluation_report.json`.

To rebuild everything and run the automated checks:

```bash
make test
make demo
```

## Offline Mosquitto + Node-RED fallback

Docker and Docker Compose are required for Mosquitto and Node-RED. Install the
small Python MQTT client first:

```bash
.venv/bin/pip install -r requirements.txt
docker compose up -d
```

Then use three terminals:

```bash
.venv/bin/python src/mqtt_processor.py
.venv/bin/python src/actuator_simulator.py
.venv/bin/python src/replay.py --mode mqtt --split test --limit 1000 --delay 0.05
```

- Node-RED: <http://127.0.0.1:1880>
- Project dashboard: run `python3 src/dashboard.py` and open
  <http://127.0.0.1:8080>

The supplied Node-RED flow subscribes to telemetry, predictions, decisions and
acknowledgements. The Python analytics service remains the single source of
model inference and database writes in both local and MQTT modes.

## Verified performance

The current reproducible run produces:

| Selected model | Validation macro-F1 | Test accuracy | Test macro-F1 |
|---|---:|---:|---:|
| Random Forest | 0.994 | 99.3% | 0.947 |

Test forecasting errors are 4.48 CPU percentage points MAE and 1.93 memory
percentage points MAE. Run `python3 src/train_models.py` to independently
regenerate the model and report.

## Important ML boundary

The classifier uses only current sensor values, time-of-day and weekday. These
columns are forbidden as inputs: `condition_label`, `fault_type`,
`recommended_action`, `scenario_id`, `cpu_next_15m_pct` and
`memory_next_15m_pct`. They are ground truth or future targets. The test suite
checks this boundary.

## Project map

| Path | Purpose |
|---|---|
| `data/server_health_synthetic.csv` | Fixed primary dataset |
| `src/simulate_server_health.py` | Reproducible dataset generator |
| `src/train_models.py` | Train/evaluate classifier and forecasters |
| `src/benchmark_models.py` | Compare traditional, ensemble and neural models |
| `src/evaluate_closed_loop.py` | Control, latency, stability and energy evaluation |
| `src/server_health/advanced.py` | Health score, headroom, explanations and drift monitoring |
| `src/analyze_dataset.py` | Generate hourly workload and correlation analysis |
| `src/replay.py` | Local or MQTT telemetry replay |
| `src/mqtt_processor.py` | MQTT inference, policy and storage service |
| `src/actuator_simulator.py` | Safe command acknowledgement service |
| `src/dashboard.py`, `dashboard/` | Web API and operational interface |
| `infra/nodered/flows.json` | Importable Node-RED flow |
| `models/server_health_model.json` | Portable trained model |
| `output/evaluation_report.json` | Full metrics and confusion matrices |
| `output/model_comparison.json` | Three-model and computational comparison |
| `output/closed_loop_evaluation.json` | Closed-loop performance metrics |
| `output/dataset_profile.json` | Dataset statistics and metric correlations |
| `output/drift_baseline.json` | Training-only reference distributions for drift detection |
| `team11.sh` | One-command main, edge and local launch modes |
| `docs/project_report.md` | Submission-ready technical report content |
| `docs/demo_script.md` | Evaluation demo and viva preparation |
| `docs/architecture.md` | Architecture, trust boundary and MQTT contract |
| `docs/team11_architecture.png` | Presentation-ready two-laptop diagram |

See also the [data dictionary](docs/data_dictionary.md), [dataset decision](docs/dataset_decision.md), and [project report](docs/project_report.md).

## Two-laptop evaluation

For the distributed demonstration, use the other laptop for cloud-connected
Node-RED, the software actuator and browser; use the main laptop for the
dataset, training, ML inference, forecasting, SQLite and dashboard server.
Both use HiveMQ Cloud as the shared broker. Follow the exact startup order in
the [two-laptop guide](docs/two_laptop_demo.md).
