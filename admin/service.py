from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette import status

from exceptions import TokenNotCorrectException, AccessTokenNotFound, UserNotAdminException
from users.auth.service import AuthService


@dataclass
class AdminService:
    auth_service: AuthService

    def check_admin_privileges(self, request: Request):
        try:
            self.auth_service.user_is_admin(request)

        except (TokenNotCorrectException, AccessTokenNotFound, UserNotAdminException) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED if isinstance(e,
                                                                       (TokenNotCorrectException, AccessTokenNotFound))
                else status.HTTP_403_FORBIDDEN,
                detail=e.detail, )
