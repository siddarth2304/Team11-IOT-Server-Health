# System architecture

![Complete two-laptop architecture](team11_architecture.svg)

```mermaid
flowchart LR
  CSV[server_health_synthetic.csv\n80,640 rows] --> RP[Python replay publisher]
  RP -->|TLS 8883: team11/servers/+/telemetry| MQ[(EMQX Cloud Serverless)]
  MQ --> NR[Node-RED validation and flow processing]
  NR -->|team11/servers/+/processed| MQ
  MQ --> ML[Python analytics service]
  ML --> C[Condition classifier]
  ML --> F[15-minute forecaster]
  C --> P[Safety policy + 5-minute cooldown]
  F --> P
  ML --> DB[(SQLite audit database)]
  P -->|team11/servers/+/command| MQ
  MQ --> ACT[Software actuator]
  ACT -->|team11/servers/+/ack| MQ
  DB --> API[Read-only dashboard API]
  API --> UI[Web dashboard]
```

## Trust boundaries

- The CSV labels are available during training and evaluation only.
- MQTT telemetry contains sensor fields, timestamp and server ID; it does not
  contain the true condition, fault type or expected action.
- ML estimates condition and demand. A deterministic policy validates every
  proposed action and implements a per-server/action cooldown.
- Consolidation and disk-clearing recommendations require operator approval.
- The actuator is intentionally simulated and cannot modify a real server.
- EMQX Cloud connections use verified TLS plus a project-only username and
  password loaded from an ignored local environment file.

## MQTT topics

| Topic | Producer | Consumer | Purpose |
|---|---|---|---|
| `team11/servers/{id}/telemetry` | replay | Node-RED | Raw sensor readings |
| `team11/servers/{id}/processed` | Node-RED | analytics | Validated/enriched sensor readings |
| `team11/servers/{id}/prediction` | analytics | Node-RED | Condition probabilities and forecast |
| `team11/servers/{id}/command` | policy | actuator, Node-RED | Controlled resource action |
| `team11/servers/{id}/ack` | actuator | Node-RED | Simulated execution result |
