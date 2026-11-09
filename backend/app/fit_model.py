"""FR-09 fit classifier: BERT-Tiny M0 (seed 42) from the CS4085 Deep Learning project.

The model reads the CV text and the job text together and gives probabilities for No Fit, Potential Fit and
Good Fit. It is evidence for HR only: it never changes the score and never rejects anyone. Because the model
misses many Good Fit pairs (test recall 15%), a candidate whose P(Good Fit) reaches the review threshold is
flagged for HR review instead of being left to the predicted label.

NFR-10: the classifier sits behind this one interface (status, predict, predict_batch). The platform keeps
working without it: if PyTorch is not installed, the weights are missing or their SHA-256 is wrong, the status
says why and applications are processed without a fit prediction.
"""
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from . import config

log = logging.getLogger("hiremind.fit")

CARD = json.loads((config.MODEL_DIR / "fit_model.json").read_text())
LABELS: list[str] = CARD["labels"]
RETRY_AFTER_S = 60  # a failed load (for example no internet for the first tokenizer download) is retried after this


@dataclass
class FitResult:
    label: str
    probabilities: dict[str, float]
    needs_hr_review: bool
    model_version: str


def model_version() -> str:
    return f"{CARD['name']} ({CARD['weights_sha256'][:8]})"


def review_flag(p_good: float) -> bool:
    return p_good >= CARD["review_threshold"]


def job_text(job) -> str:
    """The job side of the pair: title, description and required skills, like a posted job description."""
    parts = [job.title or "", job.description or ""]
    if job.required_skills:
        parts.append("Required skills: " + ", ".join(job.required_skills))
    return "\n".join(p for p in parts if p)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class _TorchBackend:
    """Loads the pinned tokenizer and architecture, then the verified M0 weights, on CPU."""

    def __init__(self, weights: Path):
        import torch
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

        name, rev = CARD["base_model"], CARD["base_revision"]
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(name, revision=rev)
        cfg = AutoConfig.from_pretrained(name, revision=rev, num_labels=len(LABELS))
        self.model = AutoModelForSequenceClassification.from_config(cfg, attn_implementation="eager")
        state = torch.load(weights, map_location="cpu", weights_only=True)
        self.model.load_state_dict(state, strict=True)
        self.model.eval()

    def __call__(self, pairs: list[tuple[str, str]]) -> list[list[float]]:
        enc = self.tok([p[0] for p in pairs], [p[1] for p in pairs], truncation=CARD["truncation"],
                       max_length=CARD["max_length"], padding=CARD["padding"], return_tensors="pt")
        with self.torch.inference_mode():
            return self.model(**enc).logits.softmax(dim=-1).tolist()


_lock = threading.Lock()
_state: dict = {"backend": None, "error": None, "failed_at": None}


def _weights_path() -> Path:
    return config.FIT_WEIGHTS or (config.MODEL_DIR / CARD["weights_file"])


def _load():
    path = _weights_path()
    if not path.exists():
        raise RuntimeError(f"Weights file not found: {path.name}")
    digest = sha256_file(path)
    if digest != CARD["weights_sha256"]:
        raise RuntimeError(f"Weights SHA-256 does not match the model card ({digest[:12]}…); refusing to load")
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        raise RuntimeError("PyTorch is not installed; run: pip install -r requirements-model.txt") from None
    return _TorchBackend(path)


def _backend():
    if _state["backend"] is not None:
        return _state["backend"]
    if not config.FIT_ENABLED:
        _state["error"] = "Disabled by FIT_MODEL=off"
        return None
    with _lock:
        failed_at = _state["failed_at"]
        if _state["backend"] is None and (failed_at is None or time.monotonic() - failed_at > RETRY_AFTER_S):
            try:
                started = time.perf_counter()
                _state["backend"], _state["error"] = _load(), None
                log.info("Fit classifier %s loaded in %.1f s", model_version(), time.perf_counter() - started)
            except Exception as e:  # any failure leaves the platform working without the classifier
                _state["error"], _state["failed_at"] = str(e) or type(e).__name__, time.monotonic()
                log.warning("Fit classifier unavailable: %s", _state["error"])
    return _state["backend"]


def set_backend(fn) -> None:
    """Tests: replace the model with a function (list of (cv, job) pairs -> list of probability lists)."""
    _state.update(backend=fn, error=None, failed_at=None)


def reset() -> None:
    _state.update(backend=None, error=None, failed_at=None)


def status() -> dict:
    available = _backend() is not None
    return {"available": available, "model": model_version(), "labels": LABELS,
            "review_threshold": CARD["review_threshold"], "reason": None if available else _state["error"]}


def predict_batch(pairs: list[tuple[str, str]]) -> list[list[float]]:
    backend = _backend()
    if backend is None:
        raise RuntimeError(_state["error"] or "Fit classifier unavailable")
    return backend(pairs)


def predict(cv_text: str, job_text_: str) -> FitResult:
    probs = predict_batch([(cv_text, job_text_)])[0]
    best = max(range(len(LABELS)), key=lambda i: probs[i])
    return FitResult(label=LABELS[best], probabilities=dict(zip(LABELS, probs)),
                     needs_hr_review=review_flag(probs[LABELS.index("Good Fit")]), model_version=model_version())
