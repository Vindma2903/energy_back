from datetime import datetime
from pydantic import BaseModel, Field
from crm.orders.models import DeliveryMethod

class OrderCreateSchema(BaseModel):
    name: str  # ✅ Исправлено title → name
    description: str | None = None
    date_of_creation: datetime
    date_of_send: datetime
    address: str | None = None
    delivery_method: DeliveryMethod = Field(default=DeliveryMethod.COURIER)
    price: int = Field(default=0)
    column_id: str
    client_name: str
    client_phone: str
