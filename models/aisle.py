from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .database import Base


class Aisle(Base):
    """Ruas (RUA 1, RUA 2, RUA 3)"""
    __tablename__ = "aisles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # "RUA 1", "RUA 2", "RUA 3"

    shelves = relationship("Shelf", back_populates="aisle", cascade="all, delete-orphan")

