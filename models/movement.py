from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum


class MovementType(str, enum.Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"
    MOVE = "MOVE"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"


class Movement(Base):
    """Auditoria de movimentos de devices"""
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False)
    from_slot_id = Column(Integer, ForeignKey("slots.id"), nullable=True)
    to_slot_id = Column(Integer, ForeignKey("slots.id"), nullable=True)
    type = Column(SQLEnum(MovementType), nullable=False)
    ts = Column(DateTime, server_default=func.now(), nullable=False)
    meta_json = Column(JSON, nullable=True)

    device = relationship("Device", back_populates="movements")

