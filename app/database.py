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

# 创建新的会话供后台任务使用
def get_db_session():
    db = SessionLocal()
    return db

# Folder模型
class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    folder_path = Column(String(255), nullable=False)
    create_time = Column(DateTime, default=datetime.now)
    
    # 关联文档和批处理任务
    documents = relationship("Document", back_populates="folder")
    batch_tasks = relationship("BatchTask", back_populates="folder")
    
    def __repr__(self):
        return f"<Folder {self.name}>"

# BatchTask模型
class BatchTask(Base):
    __tablename__ = "batch_tasks"
    
    id = Column(String(36), primary_key=True)  # UUID
    task_type = Column(String(50))  # "chunk"或"to_dify"
    name = Column(String(255))
    folder_id = Column(Integer, ForeignKey("folders.id"))
    dataset_id = Column(String(255), nullable=True)  # 只有to_dify任务需要
    
    status = Column(String(50))  # waiting/processing/completed/failed
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    document_ids = Column(JSON)  # 文档ID列表
    task_results = Column(JSON)  # 处理结果
    settings = Column(JSON)  # 任务配置(chunk_size, overlap, strategy等)
    
    # 关联到文件夹
    folder = relationship("Folder", back_populates="batch_tasks")
    
    def __repr__(self):
        return f"<BatchTask {self.name} ({self.status})>"

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
    dify_push_status = Column(String(20), nullable=True)  # Dify推送状态：None=未推送，pushing=推送中，pushed=已推送
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # 关联文件夹ID
    
    # 关联到Chunk表和Folder表
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    folder = relationship("Folder", back_populates="documents")
    
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