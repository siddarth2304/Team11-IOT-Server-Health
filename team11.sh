#!/usr/bin/env bash
set -Eeuo pipefail

task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$task_root"

usage() {
  echo "Usage:"
  echo "  ./team11.sh edge                 # Other PC: MQTT, Node-RED, actuator"
  echo "  ./team11.sh main OTHER_PC_IP     # Main laptop: train, evaluate, dashboard, replay"
  echo "  ./team11.sh hivemq-edge          # Other PC: cloud Node-RED and actuator"
  echo "  ./team11.sh hivemq-main          # Main laptop: cloud ML, dashboard and replay"
  echo "  ./team11.sh hivemq-replay ARGS   # Main laptop: publish a cloud demo/fault stream"
  echo "  ./team11.sh cloud-edge           # Other PC: EMQX Cloud Node-RED + actuator"
  echo "  ./team11.sh cloud-main           # Main laptop: EMQX Cloud ML + dashboard"
  echo "  ./team11.sh cloud-replay ARGS    # Main laptop: publish an EMQX demo/fault stream"
  echo "  ./team11.sh local                # Backup: run the complete demo on one laptop"
  echo
  echo "Optional environment variables:"
  echo "  TEAM11_SKIP_TRAIN=1              # Reuse saved models for a faster repeat demo"
  echo "  TEAM11_DASHBOARD_PORT=8080       # Change the dashboard port"
  echo "  TEAM11_REPLAY_LIMIT=600          # Number of live messages; 0 means all"
  echo "  TEAM11_REPLAY_DELAY=0.05         # Seconds between live messages"
}

load_cloud_environment() {
  local env_file="$task_root/.env.mqtt-cloud"
  if [[ ! -f "$env_file" ]]; then
    echo "Missing $env_file" >&2
    echo "Copy .env.mqtt-cloud.example to .env.mqtt-cloud and enter the EMQX Cloud connection details." >&2
    exit 1
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" != *=* || ! "${line%%=*}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "Invalid entry in .env.mqtt-cloud: $line" >&2
      exit 1
    fi
    export "$line"
  done < "$env_file"
  : "${MQTT_HOST:?MQTT_HOST is required in .env.mqtt-cloud}"
  : "${MQTT_PORT:=8883}"
  : "${MQTT_USERNAME:?MQTT_USERNAME is required in .env.mqtt-cloud}"
  : "${MQTT_PASSWORD:?MQTT_PASSWORD is required in .env.mqtt-cloud}"
  : "${MQTT_TLS:=1}"
  export MQTT_HOST MQTT_PORT MQTT_USERNAME MQTT_PASSWORD MQTT_TLS
}

load_hivemq_environment() {
  local env_file="$task_root/.env.hivemq"
  if [[ ! -f "$env_file" ]]; then
    echo "Missing $env_file" >&2
    echo "Copy .env.hivemq.example to .env.hivemq and enter the HiveMQ Cloud connection details." >&2
    exit 1
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" != *=* || ! "${line%%=*}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "Invalid entry in .env.hivemq: $line" >&2
      exit 1
    fi
    export "$line"
  done < "$env_file"
  : "${MQTT_HOST:?MQTT_HOST is required in .env.hivemq}"
  : "${MQTT_PORT:=8883}"
  : "${MQTT_USERNAME:?MQTT_USERNAME is required in .env.hivemq}"
  : "${MQTT_PASSWORD:?MQTT_PASSWORD is required in .env.hivemq}"
  : "${MQTT_TLS:=1}"
  export MQTT_HOST MQTT_PORT MQTT_USERNAME MQTT_PASSWORD MQTT_TLS
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_venv() {
  require_command python3
  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi
}

ensure_main_dependencies() {
  ensure_venv
  if ! .venv/bin/python -c 'import joblib, numpy, paho.mqtt.client, sklearn' >/dev/null 2>&1; then
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
  fi
}

ensure_edge_dependencies() {
  ensure_venv
  if ! .venv/bin/python -c 'import paho.mqtt.client' >/dev/null 2>&1; then
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install 'paho-mqtt==2.1.0'
  fi
}

run_training_and_checks() {
  if [[ "${TEAM11_SKIP_TRAIN:-0}" == "1" ]]; then
    echo "Reusing saved models because TEAM11_SKIP_TRAIN=1"
    return
  fi
  echo "[1/6] Validating the fixed dataset"
  .venv/bin/python tests/validate_dataset.py
  echo "[2/6] Analysing workload patterns and building the drift baseline"
  .venv/bin/python src/analyze_dataset.py
  echo "[3/6] Training the portable baseline and forecasting models"
  .venv/bin/python src/train_models.py
  echo "[4/6] Comparing traditional, ensemble and neural classifiers"
  .venv/bin/python src/benchmark_models.py
  echo "[5/6] Evaluating the closed-loop policy"
  .venv/bin/python src/evaluate_closed_loop.py
  echo "[6/6] Running automated tests"
  .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
}

check_dashboard_port() {
  local dashboard_port="$1"
  if ! .venv/bin/python - "$dashboard_port" <<'PY'
import socket, sys
sock = socket.socket()
try:
    sock.bind(("0.0.0.0", int(sys.argv[1])))
finally:
    sock.close()
PY
  then
    echo "Dashboard port $dashboard_port is already in use. Stop the old dashboard or set TEAM11_DASHBOARD_PORT=8081." >&2
    exit 1
  fi
}

local_ip() {
  ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}'
}

run_main() {
  local broker_host="$1"
  local broker_port="${MQTT_PORT:-1883}"
  local dashboard_port="${TEAM11_DASHBOARD_PORT:-8080}"
  local replay_limit="${TEAM11_REPLAY_LIMIT:-600}"
  local replay_delay="${TEAM11_REPLAY_DELAY:-0.05}"
  ensure_main_dependencies
  run_training_and_checks
  check_dashboard_port "$dashboard_port"

  .venv/bin/python src/run_ml_node.py --broker "$broker_host" --mqtt-port "$broker_port" --dashboard-port "$dashboard_port" &
  task_main_ml_pid=$!
  cleanup_main() {
    if [[ -n "${task_main_ml_pid:-}" ]]; then
      kill "$task_main_ml_pid" 2>/dev/null || true
      wait "$task_main_ml_pid" 2>/dev/null || true
    fi
  }
  trap cleanup_main EXIT
  trap 'exit 130' INT TERM
  sleep 3
  if ! kill -0 "$task_main_ml_pid" 2>/dev/null; then
    wait "$task_main_ml_pid"
  fi

  echo "Establishing a mixed fleet state with genuine model inference"
  .venv/bin/python src/replay.py --mode mqtt --host "$broker_host" --port "$broker_port" --demo-mix --delay 0.2
  echo
  echo "Dashboard: http://127.0.0.1:$dashboard_port"
  if [[ "${MQTT_TLS:-0}" == "1" ]]; then
    echo "Node-RED:  http://127.0.0.1:1880 on the other laptop"
    echo "HiveMQ:    mqtts://$broker_host:$broker_port"
  else
    echo "Node-RED:  http://$broker_host:1880"
  fi
  echo "Starting accelerated live telemetry. Press Ctrl+C to stop."
  .venv/bin/python src/replay.py --mode mqtt --host "$broker_host" --port "$broker_port" --split test --demo-stream --limit "$replay_limit" --delay "$replay_delay"
  echo "Restoring the mixed fleet state for discussion"
  .venv/bin/python src/replay.py --mode mqtt --host "$broker_host" --port "$broker_port" --demo-mix --delay 0.2
  wait "$task_main_ml_pid"
}

run_hivemq_edge() {
  require_command docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose is required. Install the Docker Compose plugin first." >&2
    exit 1
  fi
  ensure_edge_dependencies
  load_hivemq_environment
  docker compose -f docker-compose.hivemq.yml --env-file .env.hivemq up -d --remove-orphans
  docker compose -f docker-compose.hivemq.yml ps
  echo
  echo "HiveMQ Cloud edge is ready: mqtts://$MQTT_HOST:$MQTT_PORT"
  echo "Node-RED: http://127.0.0.1:1880"
  echo "The digital-twin actuator will remain in this terminal. Press Ctrl+C to stop it."
  exec .venv/bin/python src/actuator_simulator.py --host "$MQTT_HOST" --port "$MQTT_PORT"
}

run_hivemq_main() {
  load_hivemq_environment
  run_main "$MQTT_HOST"
}

run_hivemq_replay() {
  load_hivemq_environment
  ensure_main_dependencies
  .venv/bin/python src/replay.py --mode mqtt --host "$MQTT_HOST" --port "$MQTT_PORT" "$@"
}

run_cloud_edge() {
  require_command docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose is required. Install the Docker Compose plugin first." >&2
    exit 1
  fi
  ensure_edge_dependencies
  load_cloud_environment
  docker compose -f docker-compose.cloud.yml --env-file .env.mqtt-cloud up -d --remove-orphans
  docker compose -f docker-compose.cloud.yml ps
  echo
  echo "EMQX Cloud edge is ready: mqtts://$MQTT_HOST:$MQTT_PORT"
  echo "Node-RED: http://127.0.0.1:1880"
  echo "The digital-twin actuator will remain in this terminal. Press Ctrl+C to stop it."
  exec .venv/bin/python src/actuator_simulator.py --host "$MQTT_HOST" --port "$MQTT_PORT"
}

run_cloud_main() {
  load_cloud_environment
  : "${TEAM11_REPLAY_DELAY:=0.15}"
  export TEAM11_REPLAY_DELAY
  run_main "$MQTT_HOST"
}

run_cloud_replay() {
  load_cloud_environment
  ensure_main_dependencies
  .venv/bin/python src/replay.py --mode mqtt --host "$MQTT_HOST" --port "$MQTT_PORT" "$@"
}

run_edge() {
  require_command docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose is required. Install the Docker Compose plugin first." >&2
    exit 1
  fi
  ensure_edge_dependencies
  docker compose up -d
  docker compose ps
  local address
  address="$(local_ip)"
  echo
  echo "Other PC is ready. Give this IP to the main-laptop command: $address"
  echo "Node-RED: http://$address:1880"
  echo "MQTT:     mqtt://$address:1883"
  echo "The software actuator will remain in this terminal. Press Ctrl+C to stop it."
  exec .venv/bin/python src/actuator_simulator.py --host 127.0.0.1
}

run_local() {
  local dashboard_port="${TEAM11_DASHBOARD_PORT:-8080}"
  ensure_main_dependencies
  require_command docker
  docker compose up -d
  run_training_and_checks
  check_dashboard_port "$dashboard_port"
  .venv/bin/python src/actuator_simulator.py --host 127.0.0.1 &
  task_local_actuator_pid=$!
  .venv/bin/python src/run_ml_node.py --broker 127.0.0.1 --dashboard-port "$dashboard_port" &
  task_local_ml_pid=$!
  cleanup_local() {
    for task_pid in "${task_local_ml_pid:-}" "${task_local_actuator_pid:-}"; do
      if [[ -n "$task_pid" ]]; then kill "$task_pid" 2>/dev/null || true; fi
    done
    for task_pid in "${task_local_ml_pid:-}" "${task_local_actuator_pid:-}"; do
      if [[ -n "$task_pid" ]]; then wait "$task_pid" 2>/dev/null || true; fi
    done
  }
  trap cleanup_local EXIT
  trap 'exit 130' INT TERM
  sleep 3
  .venv/bin/python src/replay.py --mode mqtt --host 127.0.0.1 --demo-mix --delay 0.2
  echo "Dashboard: http://127.0.0.1:$dashboard_port"
  echo "Node-RED:  http://127.0.0.1:1880"
  .venv/bin/python src/replay.py --mode mqtt --host 127.0.0.1 --split test --demo-stream --limit "${TEAM11_REPLAY_LIMIT:-600}" --delay "${TEAM11_REPLAY_DELAY:-0.05}"
  .venv/bin/python src/replay.py --mode mqtt --host 127.0.0.1 --demo-mix --delay 0.2
  wait "$task_local_ml_pid"
}

role="${1:-}"
case "$role" in
  edge) run_edge ;;
  hivemq-edge) run_hivemq_edge ;;
  hivemq-main) run_hivemq_main ;;
  hivemq-replay)
    shift
    run_hivemq_replay "$@"
    ;;
  cloud-edge) run_cloud_edge ;;
  cloud-main) run_cloud_main ;;
  cloud-replay)
    shift
    run_cloud_replay "$@"
    ;;
  main)
    if [[ $# -ne 2 ]]; then usage; exit 2; fi
    run_main "$2"
    ;;
  local) run_local ;;
  *) usage; exit 2 ;;
esac
