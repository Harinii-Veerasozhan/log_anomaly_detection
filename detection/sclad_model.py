"""Statistical Clustering for Log Anomaly Detection (SCLAD).

This module is intentionally batch-only. It mines Drain3 templates, clusters
their TF-IDF representations, and scores a line by its distance from the
nearest normal cluster centroid.
"""

from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

MODEL_PATH = Path(__file__).resolve().parent / "models" / "sclad_model.pkl"
ELBOW_PATH = Path(__file__).resolve().parent.parent / "docs" / "report_assets" / "sclad_elbow_method.png"
MODEL_PATH.parent.mkdir(exist_ok=True)
ELBOW_PATH.parent.mkdir(parents=True, exist_ok=True)


def _new_template_miner() -> TemplateMiner:
    config = TemplateMinerConfig()
    config.drain_sim_th = 0.4
    config.drain_depth = 4
    return TemplateMiner(config=config)


def _templates(log_lines, miner: TemplateMiner):
    templates = []
    for line in log_lines:
        result = miner.add_log_message(str(line).strip())
        templates.append(result["template_mined"])
    return templates


def _cluster_count(vectors, requested=None):
    distinct_count = max(1, len(np.unique(vectors, axis=0)))
    if requested is not None:
        return max(1, min(int(requested), distinct_count))
    return min(8, distinct_count)


def _save_elbow_plot(vectors, max_clusters):
    cluster_range = range(1, max_clusters + 1)
    inertias = []
    for count in cluster_range:
        model = KMeans(n_clusters=count, random_state=42, n_init=10)
        model.fit(vectors)
        inertias.append(model.inertia_)

    plt.figure(figsize=(7, 4))
    plt.plot(list(cluster_range), inertias, marker="o")
    plt.xlabel("Number of clusters")
    plt.ylabel("Within-cluster sum of squares")
    plt.title("SCLAD elbow method")
    plt.xticks(list(cluster_range))
    plt.tight_layout()
    plt.savefig(ELBOW_PATH)
    plt.close()


def train_model(log_lines, normal_labels=None, n_clusters=None, k: float = 3.0):
    """Train and persist SCLAD on raw log lines.

    ``normal_labels`` is optional and uses ``True`` for normal lines. When it
    is omitted, every supplied line is treated as normal training data.
    """
    log_lines = [str(line).strip() for line in log_lines if str(line).strip()]
    if not log_lines:
        raise ValueError("SCLAD requires at least one non-empty log line")
    if normal_labels is None:
        normal_labels = [True] * len(log_lines)
    if len(normal_labels) != len(log_lines):
        raise ValueError("normal_labels must match log_lines")

    miner = _new_template_miner()
    templates = _templates(log_lines, miner)
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(templates).toarray()
    max_clusters = _cluster_count(vectors, n_clusters)
    _save_elbow_plot(vectors, max_clusters)
    cluster_count = _cluster_count(vectors, n_clusters)
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    assignments = kmeans.fit_predict(vectors)

    normal_vectors = vectors[np.asarray(normal_labels, dtype=bool)]
    normal_assignments = assignments[np.asarray(normal_labels, dtype=bool)]
    thresholds = {}
    for cluster_id in range(cluster_count):
        members = normal_vectors[normal_assignments == cluster_id]
        if len(members) == 0:
            members = vectors[assignments == cluster_id]
        distances = np.linalg.norm(members - kmeans.cluster_centers_[cluster_id], axis=1)
        standard_deviation = float(np.std(distances))
        thresholds[cluster_id] = max(float(k) * standard_deviation, 1e-6)

    bundle = {
        "miner": miner,
        "vectorizer": vectorizer,
        "kmeans": kmeans,
        "thresholds": thresholds,
        "k": float(k),
    }
    joblib.dump(bundle, MODEL_PATH)
    return bundle


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("No SCLAD model found. Run train_model() first.")
    return joblib.load(MODEL_PATH)


def predict(model, log_line: str) -> dict:
    """Return ``is_anomaly``, distance score, and the mined template."""
    result = model["miner"].add_log_message(str(log_line).strip())
    template = result["template_mined"]
    vector = model["vectorizer"].transform([template]).toarray()
    cluster_id = int(model["kmeans"].predict(vector)[0])
    distance = float(np.linalg.norm(vector[0] - model["kmeans"].cluster_centers_[cluster_id]))
    return {
        "is_anomaly": distance > model["thresholds"].get(cluster_id, 1e-6),
        "score": round(distance, 4),
        "template": template,
        "cluster_id": cluster_id,
    }


def load_log_lines(path: Path):
    """Read non-empty raw lines from a text log file."""
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "linux.logs"
    model = train_model(load_log_lines(default_path))
    print(predict(model, "2025-01-01 00:00:00 | Server-1 | ERROR | unexpected failure"))