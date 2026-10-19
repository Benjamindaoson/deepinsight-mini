"""The same source integrity and review policy used by analytical tools."""

from app.tools.contracts import document as verify_original
from app.analytics.engine import Analytics, QuerySpec


def eligible_observations(store, **scope):
    return Analytics(store).query(QuerySpec(**scope))


__all__ = ["verify_original", "eligible_observations"]
