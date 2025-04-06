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
import requests

from ..database import get_db, Document, Chunk
from ..config import APP_CONFIG, get_config
from .. import templates
from .document_service import DocumentService
from .chunk_service import ChunkService
from .to_dify_single import DifySingleService
from .to_dify_batch import DifyBatchService

router = APIRouter()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 文档服务和切块服务实例
document_service = DocumentService()
chunk_service = ChunkService()
dify_single_service = DifySingleService()
dify_batch_service = DifyBatchService()

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
            "now": datetime.now,
            "dify_api_server": get_config('DIFY_API_SERVER')
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
            "now": datetime.now,
            "dify_api_server": get_config('DIFY_API_SERVER')
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

@router.get("/strategies/for-filetype")
async def get_strategies_for_filetype(file_ext: str):
    """
    根据文件扩展名获取可用的切块策略
    
    Args:
        file_ext: 文件扩展名，例如 '.txt', '.docx' 等
    
    Returns:
        可用策略列表
    """
    # 如果传入的扩展名不以点开头，则添加点
    if not file_ext.startswith('.'):
        file_ext = f".{file_ext}"
    
    # 获取所有可用策略
    all_strategies = get_config('CHUNK_STRATEGIES')
    
    # 筛选支持该文件类型的策略
    supported_strategies = []
    for strategy in all_strategies:
        # 检查策略元数据中是否有supported_types字段
        supported_types = strategy.get('supported_types', [])
        
        # 如果没有明确指定supported_types，或者文件类型在supported_types中，则认为策略支持该文件类型
        if not supported_types or file_ext.lower() in [t.lower() for t in supported_types]:
            supported_strategies.append(strategy)
    
    return JSONResponse({
        "file_type": file_ext,
        "strategies": supported_strategies
    })

# Dify 相关路由
@router.get("/dify/knowledge-bases")
async def get_dify_knowledge_bases():
    """获取Dify知识库列表"""
    return dify_single_service.get_knowledge_bases()

@router.get("/dify/test-connection")
async def test_dify_connection():
    """测试与Dify服务器的连接"""
    return dify_single_service.test_connection()

@router.post("/dify/push/{document_id}")
async def push_to_dify(document_id: int, dataset_id: str = Form(...), db: Session = Depends(get_db)):
    """推送单个文档到Dify知识库"""
    return dify_single_service.push_document_to_dify(document_id, dataset_id, db)

@router.post("/dify/push-batch")
async def push_batch_to_dify(document_ids: str = Form(...), dataset_id: str = Form(...), db: Session = Depends(get_db)):
    """批量推送多个文档到Dify知识库"""
    doc_ids = document_ids.split(',')
    return dify_batch_service.push_batch_to_dify(doc_ids, dataset_id, db)

@router.get("/dify/batch-status/{task_id}")
async def get_batch_status(task_id: str):
    """获取批量处理的状态"""
    return dify_batch_service.get_batch_status(task_id)

@router.get("/dify/status/{document_id}")
async def get_dify_push_status(document_id: int, db: Session = Depends(get_db)):
    """获取文档推送到Dify的状态"""
    return dify_single_service.get_push_status(document_id, db) 