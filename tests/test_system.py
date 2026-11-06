from __future__ import annotations

import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from server_health.config import CLOSED_LOOP_REPORT_PATH, DATASET, MODEL_COMPARISON_PATH, MODEL_PATH, REPORT_PATH
from server_health.advanced import DRIFT_METRICS, DriftMonitor, operational_assessment
from server_health.engine import MonitoringEngine
from server_health.features import SENSOR_FIELDS, feature_vector, telemetry_payload
from server_health.model import ServerHealthModel
from server_health.policy import decide
from server_health.storage import Storage


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ServerHealthModel.load(MODEL_PATH)
        with DATASET.open(newline="", encoding="utf-8") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_no_target_leakage_in_model_features(self):
        forbidden = {"condition_label", "fault_type", "recommended_action", "scenario_id", "cpu_next_15m_pct", "memory_next_15m_pct"}
        self.assertTrue(forbidden.isdisjoint(self.model.document["features"]))
        self.assertTrue(set(SENSOR_FIELDS).issubset(self.model.document["features"]))

    def test_prediction_contract(self):
        row = next(row for row in self.rows if row["split"] == "test")
        payload = telemetry_payload(row)
        label, confidence, probabilities = self.model.classify(payload)
        cpu, memory = self.model.forecast(payload)
        self.assertIn(label, self.model.classes)
        self.assertAlmostEqual(sum(probabilities.values()), 1.0, places=8)
        self.assertTrue(0 <= confidence <= 1)
        self.assertTrue(0 <= cpu <= 100 and 0 <= memory <= 100)
        self.assertEqual(len(feature_vector(payload)), len(self.model.document["features"]))

    def test_advanced_assessment_contract(self):
        payload = telemetry_payload(next(row for row in self.rows if row["split"] == "test"))
        assessment = operational_assessment(payload, "normal", 50.0, 55.0)
        self.assertTrue(0 <= assessment["health_score"] <= 100)
        self.assertTrue(0 <= assessment["capacity_headroom_pct"] <= 100)
        self.assertIn(assessment["risk_level"], {"low", "medium", "high", "critical"})
        self.assertGreaterEqual(len(assessment["explanations"]), 1)

    def test_drift_monitor_detects_large_distribution_shift(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.json"
            baseline_path.write_text(json.dumps({"metrics": {metric: {"mean": 0.0, "std": 1.0} for metric in DRIFT_METRICS}}))
            monitor = DriftMonitor(baseline_path, window=20, minimum_samples=5)
            telemetry = {metric: 10.0 for metric in DRIFT_METRICS}
            result = {}
            for _ in range(5):
                result = monitor.update(telemetry)
            self.assertEqual(result["status"], "drift_detected")
            self.assertGreaterEqual(result["score"], 2.5)

    def test_safety_rules_override_model_condition(self):
        row = telemetry_payload(self.rows[0])
        row["service_up"] = 0
        row["temperature_c"] = 100
        command = decide(row, "normal", 0.99)
        self.assertEqual(command["action"], "restart_service")
        self.assertEqual(command["severity"], "critical")

    def test_end_to_end_storage_and_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            storage = Storage(database)
            engine = MonitoringEngine(self.model, storage)
            anomalous = next(row for row in self.rows if row["fault_type"] == "service_failure" and row["service_up"] == "0")
            payload = telemetry_payload(anomalous)
            _, first = engine.process(payload)
            payload["timestamp"] = payload["timestamp"].replace(":00Z", ":01Z")
            _, second = engine.process(payload)
            storage.close()
            self.assertEqual(first["action"], "restart_service")
            self.assertEqual(second["action"], "none")
            connection = sqlite3.connect(database)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM action_log").fetchone()[0], 1)
            advanced = connection.execute("SELECT health_score,risk_level,capacity_headroom_pct,explanation_json,drift_status FROM readings LIMIT 1").fetchone()
            self.assertIsNotNone(advanced[0])
            self.assertIn(advanced[1], {"low", "medium", "high", "critical"})
            self.assertIsNotNone(advanced[2])
            self.assertTrue(json.loads(advanced[3]))
            self.assertIn(advanced[4], {"warming_up", "stable", "watch", "drift_detected"})
            connection.close()

    def test_saved_test_metrics_meet_project_baseline(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(report["splits"]["test"]["accuracy"], 0.85)
        self.assertGreaterEqual(report["splits"]["test"]["macro_f1"], 0.75)
        self.assertLessEqual(report["splits"]["test"]["anomaly_false_alarm_rate"], 0.02)
        self.assertLessEqual(report["forecast_test"]["cpu"]["mae"], 7.0)

    def test_three_model_families_and_validation_selection(self):
        report = json.loads(MODEL_COMPARISON_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(report["models"]),
            {"traditional_gaussian_nb", "ensemble_random_forest", "deep_mlp"},
        )
        expected = max(report["models"], key=lambda name: report["models"][name]["validation"]["macro_f1"])
        self.assertEqual(report["selected_model"], expected)
        self.assertGreater(report["models"][expected]["test"]["macro_f1"], 0.90)

    def test_closed_loop_evaluation_is_complete(self):
        report = json.loads(CLOSED_LOOP_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["fault_scenarios_detected"], report["fault_scenarios_total"])
        self.assertGreater(report["cooldown_suppressions"], 0)
        self.assertEqual(report["unnecessary_command_rate_on_normal_rows"], 0)


if __name__ == "__main__":
    unittest.main()
