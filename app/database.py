from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

from .config import DATABASE_URL

# 创建数据库引擎
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 创建会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Document模型
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=False)
    filetype = Column(String(50))
    filesize = Column(Integer)  # 文件大小（字节）
    upload_time = Column(DateTime, default=datetime.now)
    status = Column(String(50), default="未切块")
    last_chunk_params = Column(JSON, default=lambda: json.dumps({}))
    hash = Column(String(64))  # 文件哈希值
    
    # 关联到Chunk表
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document {self.filename}>"

# Chunk模型
class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    sequence = Column(Integer)  # 片段序号
    content = Column(Text)  # 切块内容
    chunk_size = Column(Integer)  # 切块大小
    overlap = Column(Integer)  # 重叠度
    chunk_strategy = Column(String(50))  # 使用的切块策略
    chunk_metadata = Column(JSON, default=lambda: json.dumps({}))  # 元数据
    
    # 关联到Document表
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<Chunk {self.id} of Document {self.document_id}>"

# 创建数据库表
def create_tables():
    Base.metadata.create_all(bind=engine) 