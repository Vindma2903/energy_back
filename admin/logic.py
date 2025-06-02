from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import UserNotFoundException
from users.logic import UserLogic
from users.models import UserStatus


@dataclass
class AdminLogic:
    db_session: AsyncSession
    user_logic: UserLogic

    async def change_user_status(self, user_id: int, status: UserStatus):
        user = await self.user_logic.get_user_by_id(user_id)

        if not user:
            raise UserNotFoundException

        user.status = status
        async with self.db_session as session:
            session.add(user)
            await session.commit()

        return {"message": f"User {user_id} status successfully changed to {str(status)}"}
