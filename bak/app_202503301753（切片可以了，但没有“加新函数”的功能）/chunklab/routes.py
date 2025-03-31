from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import logging
import traceback
import os
import time
import json
import shutil
from pathlib import Path

from ..database import get_db, Document, Chunk
from ..config import APP_CONFIG, get_config
from .. import templates
from .document_service import DocumentService
from .chunk_service import ChunkService

router = APIRouter()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 文档服务和切块服务实例
document_service = DocumentService()
chunk_service = ChunkService()

# 主页面路由
@router.get("/", response_class=RedirectResponse)
async def redirect_to_index():
    """重定向到ChunkLab主页"""
    return RedirectResponse(url="/chunklab/index")

@router.get("/index")
async def index(request: Request, db: Session = Depends(get_db)):
    """ChunkLab主页面 - 文档上传和列表"""
    documents = db.query(Document).order_by(Document.upload_time.desc()).all()
    
    return templates.TemplateResponse(
        "chunklab/index.html",
        {
            "request": request,
            "documents": documents,
            "allowed_extensions": ", ".join(APP_CONFIG['ALLOWED_EXTENSIONS']),
            "now": datetime.now
        }
    )

# 文档管理路由
@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传文档"""
    return await document_service.upload_document(file, db)

@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """删除文档"""
    return document_service.delete_document(document_id, db)

# 切块管理路由
@router.get("/documents/{document_id}/chunk")
async def chunk_page(document_id: int, request: Request, db: Session = Depends(get_db)):
    """切块页面"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 获取文档的切块列表
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.sequence).all()
    
    return templates.TemplateResponse(
        "chunklab/chunk.html",
        {
            "request": request,
            "document": document,
            "chunks": chunks,
            "chunk_strategies": get_config('CHUNK_STRATEGIES'),
            "default_chunk_size": APP_CONFIG['DEFAULT_CHUNK_SIZE'],
            "default_overlap": APP_CONFIG['DEFAULT_OVERLAP'],
            "now": datetime.now
        }
    )

@router.post("/documents/{document_id}/chunk")
async def create_chunks(
    document_id: int,
    background_tasks: BackgroundTasks,
    chunk_strategy: str = Form(...),
    chunk_size: int = Form(...),
    overlap: int = Form(...),
    db: Session = Depends(get_db)
):
    """开始执行切块操作（异步）"""
    return await chunk_service.create_chunks(
        document_id, 
        background_tasks,
        chunk_strategy, 
        chunk_size, 
        overlap, 
        db
    )

@router.get("/documents/{document_id}/chunk/status")
async def get_chunk_status(document_id: int):
    """获取切块任务状态"""
    return chunk_service.get_chunk_status(document_id)

@router.get("/documents/{document_id}/chunks")
async def view_chunks(document_id: int, request: Request, db: Session = Depends(get_db)):
    """查看切块列表页面"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.sequence).all()
    
    return templates.TemplateResponse(
        "chunklab/view_chunks.html",
        {
            "request": request, 
            "document": document, 
            "chunks": chunks, 
            "chunk_strategies": get_config('CHUNK_STRATEGIES'),
            "now": datetime.now
        }
    ) 