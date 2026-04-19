from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import TimelineEvent


def add_timeline_event(
    db: Session,
    *,
    incident_id: UUID,
    event_type: str,
    actor_type: str,
    title: str,
    description: str | None = None,
    actor_id: str | None = None,
    metadata: dict | None = None,
    event_time: datetime | None = None,
) -> TimelineEvent:
    item = TimelineEvent(
        incident_id=incident_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        title=title,
        description=description,
        event_metadata=metadata,
        event_time=event_time or datetime.now(UTC),
    )
    db.add(item)
    db.flush()
    return item
