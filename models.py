from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ExcelFile(Base):
    __tablename__ = 'excel_files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    tables = relationship("ExcelTable", back_populates="excel_file")

class ExcelTable(Base):
    __tablename__ = 'excel_tables'
    id = Column(Integer, primary_key=True, autoincrement=True)
    excel_file_id = Column(Integer, ForeignKey('excel_files.id'))
    sheet_name = Column(String(255), nullable=False)
    table_name = Column(String(255), nullable=False)
    data = Column(JSON, nullable=False)
    excel_file = relationship("ExcelFile", back_populates="tables")
