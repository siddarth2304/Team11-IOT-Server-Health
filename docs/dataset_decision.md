# Final dataset decision — Team 11

## Decision

Adopt the included scenario-based **software server-farm simulator** as the final
primary dataset source and MQTT publisher input. No physical hardware is needed.
It is the strongest fit for the complete marking flow:

`simulated sensors -> MQTT -> Node-RED -> database -> dashboard -> ML -> decision -> MQTT actuator`

The simulator has explicit metric names and units, deterministic generation,
known fault intervals, and actions that can be demonstrated live. It also makes
live modification straightforward: the evaluator can request a threshold,
server count, sampling interval, fault duration, or fault severity change.

Unlike replaying a fixed public CSV, the live simulator can respond to commands.
For example, `start_server` increases available capacity, `redistribute_load`
reduces pressure on an overloaded server, `shutdown_server` consolidates quiet
workloads, and `restart_service` restores a failed service. This creates a real
software IoT feedback loop rather than a dashboard-only demonstration.

## Why not use a public dataset alone?

| Candidate | Strength | Project risk | Decision |
|---|---|---|---|
| Alibaba Cluster Trace 2017 | Real server CPU, memory, disk, load and machine error events | Large/awkward trace; no temperature or network in the core machine table | Use as real-world justification or optional benchmark |
| Alibaba Cluster Trace 2018 | Real production trace across about 4,000 machines over 8 days | Machine-usage download is about 1.7 GB compressed; weak fit for a small live demo | Optional benchmark only |
| SMD (Server Machine Dataset) | Five weeks, 28 machines, 38 dimensions, point anomaly labels | Primary data files have no headers and the official README does not define the column mapping; it also lacks our explicit operating-condition/action labels | Do not use as the primary dashboard dataset |
| Google Cluster 2019 | Large, credible production trace | About 2.4 TiB compressed and BigQuery-oriented; unnecessary complexity | Reject for this mini-project |
| Scenario-based simulator | Exact required fields, known causes and labels, easy MQTT replay and live fault injection | Synthetic-to-real generalization is not proven | **Primary choice**, with limitation stated clearly |

## Research basis to show faculty

- Alibaba Cluster Trace program: https://github.com/alibaba/clusterdata
- Alibaba 2017 schema: https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/trace_201708.md
- Alibaba 2018 trace: https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md
- SMD/OmniAnomaly: https://github.com/NetManAIOps/OmniAnomaly
- Google Cluster 2019: https://github.com/google/cluster-data/blob/master/ClusterData2019.md

These sources establish that CPU, memory, disk, load, workload variation, and
machine anomalies are legitimate server-monitoring variables. They are not used
to disguise the generated dataset as real data.

## Faculty dataset-confirmation message (copy/paste)

> Team 11 proposes a reproducible scenario-based synthetic dataset for “Server
> and IT Infrastructure Health Monitoring.” It contains one-minute telemetry
> from four simulated servers: CPU, memory, disk, network in/out, temperature,
> power, load, response time, error rate, service state, and active sessions.
> Normal workload has time-of-day patterns and correlated metrics. Controlled
> episodes inject CPU stress, memory leak, disk saturation, network storm,
> cooling failure, service failure, and legitimate peak workload. Ground-truth
> labels distinguish underutilized, normal, overloaded, and anomalous states.
> We will use chronological train/validation/test splits, exclude labels/actions
> from model inputs, replay rows over MQTT, classify server condition, forecast
> 15-minute CPU/memory demand, and publish resource-management actions back over
> MQTT. Public Alibaba server traces are used only to justify the metric choices.
> Please confirm approval of this synthetic dataset strategy.

## Validity rules

1. Never describe the dataset as patient, hospital, or clinical data.
2. Never rename anonymous SMD dimensions as named physical metrics.
3. Treat generated labels as scenario ground truth, not human-expert diagnosis.
4. Report performance separately on validation and untouched chronological test
   data; do not tune on the test period.
5. Include per-class precision, recall, F1, a confusion matrix, and false-alarm
   rate. Accuracy alone is misleading because anomalies are intentionally rare.
6. Keep decisions deterministic and inspectable. ML should not directly execute
   a destructive action; an action policy and cooldown should validate it.
7. In the final report, state that external validity on a real deployment remains
   future work.

## Recommended MQTT contract

Telemetry topic: `team11/servers/{server_id}/telemetry`

```json
{
  "timestamp": "2026-01-01T00:00:00Z",
  "cpu_pct": 43.2,
  "memory_pct": 57.1,
  "disk_pct": 48.0,
  "net_in_mbps": 82.6,
  "net_out_mbps": 30.1,
  "temperature_c": 55.4,
  "power_w": 171.2,
  "load_1m": 3.8,
  "response_ms": 71.0,
  "error_rate_pct": 0.2,
  "service_up": 1,
  "active_sessions": 216
}
```

Decision topic: `team11/servers/{server_id}/command`

Use a command ID, reason, timestamp, and cooldown state in every action message so
replayed MQTT packets cannot repeatedly trigger the same actuator.
