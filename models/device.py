from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum


class DeviceStatus(str, enum.Enum):
    IN_STOCK = "IN_STOCK"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_STOCK = "OUT_STOCK"
    RESERVED = "RESERVED"


class Device(Base):
    """Devices armazenados nos slots"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, nullable=False, index=True)
    index = Column(Integer)  # Índice para ordenação
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.OUT_STOCK, nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), unique=True, nullable=True)

    slot = relationship("Slot", back_populates="device")
    movements = relationship("Movement", back_populates="device")

