from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Shelf(Base):
    """Prateleiras por rua
    - RUA 1: P1 (esquerda)
    - RUA 2: P1 (esquerda), P2 (direita)
    - RUA 3: P1 (direita)
    """
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, index=True)
    aisle_id = Column(Integer, ForeignKey("aisles.id"), nullable=False)
    code = Column(String, nullable=False)  # "P1", "P2"

    aisle = relationship("Aisle", back_populates="shelves")
    slots = relationship("Slot", back_populates="shelf", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("aisle_id", "code", name="uq_aisle_shelf"),
    )

