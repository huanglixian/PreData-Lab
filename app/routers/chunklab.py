from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..database import get_db, Document, Chunk
from ..config import APP_CONFIG, get_config
from .. import templates
from ..services.document import DocumentService
from ..services.chunking import ChunkService
from ..services.to_dify_single import DifySingleService
from ..services.add_dify_single import add_dify_service

router = APIRouter(
    tags=["chunklab"],
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 服务实例
document_service = DocumentService()
chunk_service = ChunkService()
dify_service = DifySingleService()

# 模板设置
templates = Jinja2Templates(directory="app/templates")

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
    return dify_service.get_knowledge_bases()

@router.get("/dify/test-connection")
async def test_dify_connection():
    """测试与Dify服务器的连接"""
    return dify_service.test_connection()

@router.post("/dify/push/{document_id}")
async def push_to_dify(document_id: int, dataset_id: str = Form(...), db: Session = Depends(get_db)):
    """推送文档到Dify知识库"""
    return dify_service.push_document_to_dify(document_id, dataset_id, db)

@router.get("/dify/status/{document_id}")
async def get_dify_push_status(document_id: int, db: Session = Depends(get_db)):
    """获取文档推送到Dify的状态"""
    return dify_service.get_push_status(document_id, db)

# AddDify相关路由
@router.get("/dify/files/{dataset_id}")
async def get_dify_files(dataset_id: str, keyword: Optional[str] = None):
    """获取Dify知识库中的文件列表，支持搜索"""
    return add_dify_service.get_dataset_files(dataset_id, keyword)

@router.post("/dify/add/{document_id}")
async def add_to_dify_file(document_id: int, dataset_id: str = Form(...), target_file_id: str = Form(...), db: Session = Depends(get_db)):
    """添加切片到Dify现有文件"""
    return add_dify_service.add_to_dify_file(document_id, dataset_id, target_file_id, db) 