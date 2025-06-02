from pydantic import BaseModel


class ClientCreateSchema(BaseModel):
    name: str
    surname: str | None = None
    phone_number: str | None = None
    inn: str | None = None
