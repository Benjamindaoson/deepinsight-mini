from app.skills.continuous_monitoring import get_verified_changes


def active_signals(store):
    return get_verified_changes(store, None)
