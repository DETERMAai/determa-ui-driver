from git_event_stream import get_recent_git_events, watch_git_events


def get_git_runtime_state(limit: int = 100):
    watch_git_events()
    return get_recent_git_events(limit)
