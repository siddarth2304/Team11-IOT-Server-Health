# Two laptop evaluation setup

## Responsibility split

| Computer | Role | Services |
|---|---|---|
| Main presentation laptop | Data, training, analytics and demonstration | Dataset validation, model training, inference, forecasting, drift monitoring, SQLite, dashboard and replay publisher |
| Other PC | IoT flow processing and control | Cloud-connected Node-RED and software digital-twin actuator |

The main laptop displays the dashboard at `http://127.0.0.1:8081`. The other PC
displays Node-RED at `http://127.0.0.1:1880`. Both connect to HiveMQ Cloud using
TLS port 8883.

## Preparation

1. Copy the complete project folder to both computers.
2. Do not copy `.venv`; each computer creates its own environment.
3. Give both computers working internet access. They do not need to share the
   same local network.
4. Install Python 3.10 or later on both computers. Install Docker with the
   Compose plugin on the other PC.
5. Copy `.env.hivemq.example` to `.env.hivemq` on both machines and enter the
   same HiveMQ cluster hostname and project-only access credential.
6. On the other PC, pull the image before evaluation day with
   `docker compose -f docker-compose.hivemq.yml pull`.

## Evaluation startup

Run this first on the other PC:

```bash
cd /path/to/IOT
./team11.sh hivemq-edge
```

On the main laptop run:

```bash
cd /path/to/IOT
TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

The main command performs training and verification before it starts the live
services. Keep both terminals open.

Open these tabs on the main laptop:

- Dashboard on main laptop: `http://127.0.0.1:8081`
- Node-RED on other laptop: `http://127.0.0.1:1880`

The launcher first establishes a mixed fleet state, then publishes a balanced
live stream containing normal, underutilized, overloaded and anomalous rows.
It finishes by restoring two normal servers, one overloaded server and one
underutilized server. Dataset labels select demonstration rows but never enter
MQTT payloads or model features.

## Faster repeat run

After the first successful training run, the saved models can be reused:

```bash
TEAM11_SKIP_TRAIN=1 TEAM11_DASHBOARD_PORT=8081 ./team11.sh hivemq-main
```

To use another dashboard port:

```bash
TEAM11_DASHBOARD_PORT=8082 ./team11.sh hivemq-main
```

## Single laptop backup

If the second computer or network fails, run:

```bash
./team11.sh local
```

This starts local Mosquitto, Node-RED, training, analytics, dashboard, actuator and
live replay on one computer while preserving the same MQTT architecture.

## Connectivity check

Both launchers print `mqtts://...:8883` after loading the private configuration.
Successful output includes `Subscribed to team11/servers/+/processed` on the
main laptop and `Software actuator ready` on the other PC.

## Shutdown

Press `Ctrl+C` in both launcher terminals. To stop Node-RED on the other PC, run
`docker compose -f docker-compose.hivemq.yml down`.
