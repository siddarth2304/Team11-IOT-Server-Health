# Data dictionary

Each row is one server reading. Numeric values are rounded only when written to
CSV; internal calculations use full precision.

| Column | Unit/type | Role and valid range |
|---|---|---|
| `timestamp` | ISO-8601 UTC | Event time |
| `server_id` | string | `srv-01` through `srv-04` by default |
| `split` | category | Chronological `train`, `validation`, or `test` |
| `cpu_pct` | percent | CPU utilization, 0–100 |
| `memory_pct` | percent | Memory utilization, 0–100 |
| `disk_pct` | percent | Used disk capacity, 0–100 |
| `net_in_mbps` | Mbit/s | Incoming network throughput, >= 0 |
| `net_out_mbps` | Mbit/s | Outgoing network throughput, >= 0 |
| `temperature_c` | °C | Simulated server sensor temperature |
| `power_w` | watts | Simulated server power draw |
| `load_1m` | runnable work | Approximate one-minute load average |
| `response_ms` | milliseconds | Service response latency, >= 0 |
| `error_rate_pct` | percent | Failed requests, 0–100 |
| `service_up` | 0/1 | Simulated service availability |
| `active_sessions` | count | Concurrent workload proxy |
| `condition_label` | target | `underutilized`, `normal`, `overloaded`, `anomalous` |
| `fault_type` | ground truth | Injected cause or `none` |
| `recommended_action` | policy output | Inspectable action derived from condition/cause |
| `scenario_id` | ground truth | Identifier joining rows from one injected episode |
| `cpu_next_15m_pct` | percent/blank | Supervised 15-minute-ahead CPU target |
| `memory_next_15m_pct` | percent/blank | Supervised 15-minute-ahead memory target |

## Label semantics

- `underutilized`: no injected fault and sustained low CPU/memory/workload.
- `normal`: no injected fault and resources are within the normal envelope.
- `overloaded`: legitimate demand causes high resource pressure/latency; this is
  not automatically a fault.
- `anomalous`: a known fault was injected. The specific cause is in `fault_type`.

`condition_label`, `fault_type`, `recommended_action`, and `scenario_id` are
ground-truth/evaluation metadata. They must not be present in live telemetry sent
to the inference model.

