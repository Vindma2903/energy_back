from pydantic import BaseModel

from users.models import UserStatus


class ChangeUserStatusSchema(BaseModel):
    user_id: int
    status: UserStatus = UserStatus.PENDING
