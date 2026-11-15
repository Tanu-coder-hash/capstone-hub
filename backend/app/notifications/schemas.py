
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.notifications.models import NotificationType


class NotificationOut(BaseModel):

    id: int
    user_id: int
    team_id: int
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
