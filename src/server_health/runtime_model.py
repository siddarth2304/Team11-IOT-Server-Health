"""Runtime adapter for the selected benchmark winner plus ridge forecasts."""

from __future__ import annotations

from pathlib import Path

from .model import ServerHealthModel


class EnhancedServerHealthModel(ServerHealthModel):
    def __init__(self, baseline: ServerHealthModel, bundle: dict[str, object]):
        super().__init__(baseline.document)
        self.estimator = bundle["estimator"]
        # Live inference processes one MQTT message at a time. Spawning a joblib
        # worker pool for every single row is much slower than one local thread.
        if hasattr(self.estimator, "n_jobs"):
            self.estimator.n_jobs = 1
        self.model_name = str(bundle["model_name"])

    def classify(self, telemetry: dict[str, object]) -> tuple[str, float, dict[str, float]]:
        from .features import feature_vector

        probabilities_array = self.estimator.predict_proba([feature_vector(telemetry)])[0]
        labels = [str(label) for label in self.estimator.classes_]
        probabilities = {label: float(value) for label, value in zip(labels, probabilities_array)}
        label = max(probabilities, key=probabilities.get)
        return label, probabilities[label], probabilities


def load_runtime_model(baseline_path: Path, enhanced_path: Path, prefer_enhanced: bool = True) -> ServerHealthModel:
    baseline = ServerHealthModel.load(baseline_path)
    if not prefer_enhanced or not enhanced_path.exists():
        return baseline
    try:
        import joblib
    except ImportError:
        print("scikit-learn runtime unavailable; using dependency-free baseline model")
        return baseline
    bundle = joblib.load(enhanced_path)
    model = EnhancedServerHealthModel(baseline, bundle)
    print(f"Loaded selected classifier: {model.model_name}")
    return model
