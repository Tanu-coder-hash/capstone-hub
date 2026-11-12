
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db

from app.notifications import service
from app.notifications.schemas import NotificationOut


router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
)


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return service.get_notifications(db, user.id)


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    count = service.get_unread_count(db, user.id)

    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.mark_as_read(
            db,
            notification_id,
            user.id,
        )
    except service.NotificationNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    count = service.mark_all_as_read(db, user.id)

    return {
        "message": "All notifications marked as read",
        "updated_count": count,
    }
