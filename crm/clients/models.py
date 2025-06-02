from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from infrastructure.database.base import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    inn = Column(String, nullable=True)

    orders = relationship("Order", back_populates="client")
