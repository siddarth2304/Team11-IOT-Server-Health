from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "server_health_synthetic.csv"
MODEL_PATH = ROOT / "models" / "server_health_model.json"
BEST_CLASSIFIER_PATH = ROOT / "models" / "best_classifier.joblib"
MODEL_COMPARISON_PATH = ROOT / "output" / "model_comparison.json"
CLOSED_LOOP_REPORT_PATH = ROOT / "output" / "closed_loop_evaluation.json"
DATABASE = ROOT / "output" / "server_health.db"
REPORT_PATH = ROOT / "output" / "evaluation_report.json"
DRIFT_BASELINE_PATH = ROOT / "output" / "drift_baseline.json"

SENSOR_FIELDS = [
    "cpu_pct", "memory_pct", "disk_pct", "net_in_mbps", "net_out_mbps",
    "temperature_c", "power_w", "load_1m", "response_ms",
    "error_rate_pct", "service_up", "active_sessions",
]

CONDITIONS = ["underutilized", "normal", "overloaded", "anomalous"]
