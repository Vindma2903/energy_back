class OrderNotFoundException(Exception):
    detail = 'Заказ не найден'


class ClientNotFoundException(Exception):
    detail = 'Клиент не найден'


class UserNotFoundException(Exception):
    detail = 'Пользователь не найден'


class UserNotConfirmedByAdminException(Exception):
    detail = 'Пользователь не подтверждён по электронной почте. Ожидайте подтверждения аккаунта администратором.'


class UserNotCorrectPasswordException(Exception):
    detail = 'Неверный пароль'


class MailConfigError(Exception):
    detail = 'Неверная конфигурация почты'


class MailNotSendedException(Exception):
    detail = 'Письмо не отправлено'


class TokenNotCorrectException(Exception):
    detail = 'Неверный токен'


class TokenExpiredException(Exception):
    detail = 'Срок действия токена истёк'


class AccessTokenNotFound(Exception):
    detail = 'Токен доступа отсутствует или недействителен'


class UserNotAdminException(Exception):
    detail = 'У пользователя нет прав администратора'
