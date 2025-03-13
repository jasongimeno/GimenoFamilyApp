from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.database import Base

class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="checklists")
    items = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan")
    runs = relationship("ChecklistRun", back_populates="checklist", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_required = Column(Boolean, default=True)
    
    # Relationships
    checklist = relationship("Checklist", back_populates="items")
    run_items = relationship("ChecklistRunItem", back_populates="item")

class ChecklistRun(Base):
    __tablename__ = "checklist_runs"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    email_sent_to = Column(String(255))
    notes = Column(Text)
    
    # Relationships
    checklist = relationship("Checklist", back_populates="runs")
    run_items = relationship("ChecklistRunItem", back_populates="run", cascade="all, delete-orphan")

class ChecklistRunItem(Base):
    __tablename__ = "checklist_run_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("checklist_runs.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("checklist_items.id"), nullable=False)
    completed = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    run = relationship("ChecklistRun", back_populates="run_items")
    item = relationship("ChecklistItem", back_populates="run_items") 