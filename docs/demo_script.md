# Exact two-laptop evaluation demonstration

Use the prepared architecture image in `docs/team11_architecture.png`. A good
demonstration takes 10–12 minutes. Do not retrain while the evaluator is waiting
unless specifically asked; run `make demo` before the session and keep the saved
reports available.

## Screens to prepare

### Laptop 1 — IoT/UI

Open two browser tabs:

1. Node-RED: `http://127.0.0.1:1880`
2. HiveMQ Cloud console connection overview (without exposing credentials)

Keep one terminal visible with the software actuator running.

### Laptop 2 — ML/analytics

Keep three terminals ready:

1. `src/run_ml_node.py` — analytics subscriber and dashboard server
2. `src/replay.py` — live IoT telemetry publisher
3. commands such as `make test` and model-report inspection

## Startup order

### Other laptop

```bash
./team11.sh hivemq-edge
```

### Main laptop

```bash
TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

Do not start replay yet. First confirm that the ML terminal says:

```text
Subscribed to team11/servers/+/processed (Node-RED output)
```

## What to demonstrate

### Optional: establish a mixed fleet state

Before showing the fleet table, publish four genuine dataset records that the
selected model classifies as two normal servers, one overloaded server and one
underutilized server:

```bash
./team11.sh hivemq-replay --demo-mix --delay 0.2
```

This option uses the ground-truth condition only to select suitable rows for
the demonstration. The condition label is removed from every MQTT payload, so
the displayed condition still comes from model inference.

### 1. Problem and architecture — 60 seconds

Show the architecture image and say:

> Our project monitors software-simulated servers without physical hardware.
> The main laptop publishes raw telemetry securely to HiveMQ Cloud. Node-RED on
> the other laptop validates and enriches each message, then republishes it.
> The main laptop performs model inference, forecasting, storage and decision-making.
> Commands return over MQTT to a safe digital-twin actuator, completing the
> feedback loop.

Point to steps 1–8 in order. Emphasize that Node-RED is an actual processing
dependency, not only a decorative flow.

### 2. Dataset and sampling — 60 seconds

On Laptop 2 show `output/dataset_profile.json` and explain:

- 80,640 readings from four servers over 14 days;
- one-minute sampling;
- CPU, memory, disk, network, temperature, power, load, latency, errors,
  service status and sessions;
- six fault types and four health conditions;
- first 10 days training, next 2 validation, final 2 untouched testing;
- synthetic, scenario-based and reproducible—not production data.

Mention that peak average CPU is at 11:00 UTC and that CPU has strong positive
correlation with power and temperature.

### 3. Model comparison — 90 seconds

On the dashboard scroll to **Analytics & ML**. Show all three families:

- Traditional ML: Gaussian Naive Bayes;
- Ensemble ML: Random Forest;
- Deep neural model: three-hidden-layer MLP (64–32–16);
- Forecasting: ridge regression for CPU and memory 15 minutes ahead.

Explain that model selection uses validation macro-F1 only. The test set is not
used to choose the winner. The current winner is Random Forest.

Show accuracy, macro precision, recall, F1, training time, inference latency and
serialized model size. Then show CPU/memory MAE, RMSE and R² in
`output/evaluation_report.json` if asked.

### 4. Live IoT flow — 2 minutes

On Laptop 2 start:

```bash
./team11.sh hivemq-replay --split test --limit 2400 --delay 0.05
```

On Laptop 1 show messages moving through Node-RED:

```text
telemetry → Validate + route telemetry → processed
```

Open the Node-RED debug sidebar and show:

- validated telemetry;
- ML prediction and forecast;
- decision command;
- actuator acknowledgement with pre-action and simulated post-action state.

To demonstrate a service failure immediately instead of waiting for its position
in the test period, run:

```bash
./team11.sh hivemq-replay --split test --fault service_failure --limit 40 --delay 0.15
```

The publisher uses the hidden fault label only to choose demonstration rows; it
removes `fault_type`, `condition_label` and expected action from MQTT payloads.

### 5. Dashboard and workload analytics — 90 seconds

On the main laptop switch to `http://127.0.0.1:8081` and show:

- four server status cards;
- live CPU, memory and temperature trend;
- 15-minute forecasts;
- condition distribution;
- selected-model metrics and three-model comparison;
- recent controlled actions and reasons.

Select one server using the dashboard filter to demonstrate per-server analysis.

Show the advanced monitoring columns and explain:

- health score is a deterministic operating-risk score from current telemetry;
- forecast headroom uses predicted CPU, predicted memory and disk utilization;
- the primary explanation names the strongest local pressure factor;
- drift compares a rolling live window with training-only feature baselines;
- data completeness checks the critical fields used by inference.

Run a short balanced stream to make the drift detector observable:

```bash
./team11.sh hivemq-replay --demo-stream --limit 100 --delay 0.05
```

State that demo sampling changes the presentation frequency of classes but does
not publish labels to the classifier.

### 6. Decision and control — 90 seconds

Choose a command in Node-RED or the dashboard and explain its reason. Show the
same command in the actuator terminal. Point out:

- service failure → restart service;
- overheating → increase cooling and alert;
- overload → redistribute workload or start standby;
- underutilisation → consolidation candidate requiring approval;
- every command has a UUID, severity, reason and five-minute cooldown;
- disk clearing and consolidation require human approval.

Show `post_action_state` in the actuator acknowledgement. State clearly that it
is a digital-twin response and does not modify a physical or production server.

### 7. Closed-loop evaluation — 60 seconds

On the dashboard show **Closed-loop performance**:

- detected fault scenarios;
- simulated control effectiveness;
- decision latency;
- cooldown suppressions;
- unnecessary command rate;
- estimated energy-saving potential.

Explain that energy saving is an estimate based on a documented 35% avoidance
assumption during ground-truth underutilized intervals.

### 8. Verification and limitations — 45 seconds

Run on Laptop 2:

```bash
make test
```

State the limitations honestly:

- external validity requires future testing on real infrastructure;
- digital-twin control effectiveness is simulated;
- HiveMQ Cloud uses verified TLS and a project-only access credential kept out
  of the repository; production would additionally use narrower roles and
  credential rotation.

## High-value evaluator tests

Be ready for these live modifications:

- Change replay speed: `--delay 0.2` or `--delay 0.01`.
- Change record count: `--limit 200`.
- Select a fault safely: `--fault cooling_fault` or `--fault service_failure`.
- Stop Node-RED and show that processed ML input stops.
- Restart Node-RED and show recovery.
- Use `--baseline-model` to compare live Gaussian NB with the selected ensemble.
- Change a decision threshold in `src/server_health/policy.py` and rerun tests.
- Use dashboard port 8081 if 8080 is occupied.

## Likely viva questions

- **Why chronological splitting?** Random row splitting would leak adjacent
  time-series patterns from the future into training.
- **Why macro-F1?** Accuracy can hide weak performance on rare overload and
  anomaly classes; macro-F1 gives each class equal weight.
- **Why Random Forest?** It achieved the highest validation macro-F1 and was
  selected before viewing final test performance.
- **Is the MLP genuinely neural?** Yes. It is a feed-forward neural network with
  three hidden layers. It is included as a deep-neural baseline, not claimed to
  be a production-scale transformer or sequence model.
- **Why combine ML with rules?** ML recognizes statistical operating patterns;
  deterministic safety rules enforce service, thermal and capacity priorities.
- **Where is IoT without hardware?** Software sensors publish over MQTT,
  Node-RED processes messages, analytics decides, and an actuator acknowledges
  control commands using the same messaging structure as physical deployment.
- **Is the dataset real-world?** No. It is explicitly synthetic and
  reproducible. Real-infrastructure validation is future work.
