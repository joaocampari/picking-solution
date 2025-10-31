from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Slot(Base):
    """Slots individuais dentro de uma prateleira"""
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    aisle_id = Column(Integer, ForeignKey("aisles.id"), nullable=False)
    shelf_id = Column(Integer, ForeignKey("shelves.id"), nullable=False)
    row_index = Column(Integer, nullable=False)  # 1..24
    col_index = Column(Integer, nullable=False)  # 1..40
    human_code = Column(String, unique=True, nullable=False, index=True)  # "R1-P1-L1-C1"
    occupied = Column(Boolean, default=False, nullable=False, index=True)

    aisle = relationship("Aisle")
    shelf = relationship("Shelf", back_populates="slots")
    device = relationship("Device", back_populates="slot", uselist=False)

    __table_args__ = (
        UniqueConstraint("shelf_id", "row_index", "col_index", name="uq_shelf_row_col"),
    )

