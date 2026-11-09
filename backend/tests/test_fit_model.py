"""FR-09 with the real M0 weights (runs only where requirements-model.txt is installed, as in CI)."""
import statistics
import time

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from app import config, fit_model  # noqa: E402
from cvfiles import CV_LINES  # noqa: E402

JOB = ("Data Analyst\nTurn sales data into weekly reports and dashboards for store managers.\n"
       "Required skills: sql, python, excel")


@pytest.fixture()
def real(monkeypatch):
    monkeypatch.setattr(config, "FIT_ENABLED", True)
    fit_model.reset()
    st = fit_model.status()
    assert st["available"], st["reason"]
    return fit_model


def test_real_model_gives_three_probabilities(real):
    r = real.predict("\n".join(CV_LINES), JOB)
    assert set(r.probabilities) == {"No Fit", "Potential Fit", "Good Fit"}
    assert abs(sum(r.probabilities.values()) - 1) < 1e-5
    print("Sara vs Data Analyst:", r)


def test_real_model_is_deterministic(real):
    a = real.predict("\n".join(CV_LINES), JOB).probabilities
    b = real.predict("\n".join(CV_LINES), JOB).probabilities
    assert a == b


def test_real_model_latency(real):
    cv = "\n".join(CV_LINES) * 5  # long enough to fill 256 tokens
    times = []
    for _ in range(30):
        t = time.perf_counter()
        real.predict(cv, JOB)
        times.append(1000 * (time.perf_counter() - t))
    p95 = sorted(times)[int(0.95 * len(times)) - 1]
    print(f"median {statistics.median(times):.1f} ms, p95 {p95:.1f} ms")
    assert p95 < 2000
