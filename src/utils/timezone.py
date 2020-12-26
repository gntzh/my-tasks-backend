from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone Aware utcnow."""
    return datetime.utcnow().replace(tzinfo=timezone.utc)
