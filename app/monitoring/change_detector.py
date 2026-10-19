"""One existing metric detector; no alternate comparison logic."""

from app.skills.monitor import create_metric_signals as detect_metric_changes

__all__ = ["detect_metric_changes"]
