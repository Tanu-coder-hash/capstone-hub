
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.notifications.models import Notification, NotificationType


class NotificationNotFound(Exception):
    pass



def create_notification(
    db: Session,
    user_id: int,
    team_id: int,
    notification_type: NotificationType,
    message: str,
    commit: bool = True,
) -> Notification:

    notification = Notification(
        user_id=user_id,
        team_id=team_id,
        type=notification_type,
        message=message,
    )

    db.add(notification)

    if commit:
        db.commit()
        db.refresh(notification)
    else:
        db.flush()

    return notification



def get_notifications(
    db: Session,
    user_id: int,
) -> list[Notification]:

    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        ).all()
    )


def get_unread_count(
    db: Session,
    user_id: int,
) -> int:

    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ) or 0


def mark_as_read(
    db: Session,
    notification_id: int,
    user_id: int,
) -> Notification:

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )

    if notification is None:
        raise NotificationNotFound("Notification not found")

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


def mark_all_as_read(
    db: Session,
    user_id: int,
) -> int:

    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return len(notifications)
