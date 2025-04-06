from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel
import os

from ..database import get_db, Folder, Document, BatchTask
from ..config import get_config
from .. import templates
from ..services.folder_manager import FolderManager
from ..services.batch_chunking import BatchChunkingService
from ..services.to_dify_batch import DifyBatchService
from ..services.to_dify_single import DifySingleService

router = APIRouter()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 服务实例
folder_manager = FolderManager()
batch_chunking_service = BatchChunkingService()
dify_batch_service = DifyBatchService()
dify_service = DifySingleService()  # 用于获取知识库列表等

# 请求模型
class FolderCreate(BaseModel):
    name: str

class BatchChunkRequest(BaseModel):
    document_ids: List[int] = []
    chunk_strategy: str
    chunk_size: int
    overlap: int

class BatchDifyRequest(BaseModel):
    document_ids: List[int] = []
    dataset_id: str

# 主页 - 文件夹列表
@router.get("")
async def index(request: Request, db: Session = Depends(get_db)):
    """ChunkGo主页 - 显示文件夹列表"""
    folders = folder_manager.get_folders(db)
    
    return templates.TemplateResponse(
        "chunkgo/index.html",
        {
            "request": request,
            "folders": folders,
            "now": datetime.now
        }
    )

# 创建文件夹
@router.post("/folders")
async def create_folder(folder: FolderCreate, db: Session = Depends(get_db)):
    """创建新文件夹"""
    result = folder_manager.create_folder(folder.name, db)
    return result

# 删除文件夹
@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    """删除文件夹"""
    result = folder_manager.delete_folder(folder_id, db)
    return result

# 文件夹详情页 - 显示文件夹中的文档
@router.get("/folders/{folder_id}")
async def folder_details(folder_id: int, request: Request, db: Session = Depends(get_db)):
    """文件夹详情页 - 显示文件夹中的文档和批处理任务"""
    folder = folder_manager.get_folder(folder_id, db)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    
    # 获取文件夹中的文档
    documents = db.query(Document).filter(Document.folder_id == folder_id).order_by(Document.upload_time.desc()).all()
    
    # 获取文件夹的批处理任务
    chunk_tasks = batch_chunking_service.get_folder_tasks(folder_id, db)
    dify_tasks = dify_batch_service.get_folder_tasks(folder_id, db)
    
    return templates.TemplateResponse(
        "chunkgo/batchdocs.html",
        {
            "request": request,
            "folder": folder,
            "documents": documents,
            "chunk_tasks": chunk_tasks,
            "dify_tasks": dify_tasks,
            "chunk_strategies": get_config('CHUNK_STRATEGIES'),
            "default_chunk_size": get_config('DEFAULT_CHUNK_SIZE'),
            "default_overlap": get_config('DEFAULT_OVERLAP'),
            "allowed_extensions": get_config('ALLOWED_EXTENSIONS'),
            "dify_api_server": get_config('DIFY_API_SERVER'),
            "now": datetime.now
        }
    )

# 上传文档到文件夹
@router.post("/folders/{folder_id}/upload")
async def upload_documents(
    folder_id: int, 
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
):
    """上传多个文档到文件夹"""
    try:
        logger.info(f"开始上传文档到文件夹 {folder_id}, 文件数: {len(files)}")
        result = await batch_chunking_service.upload_documents_to_folder(folder_id, files, db)
        logger.info(f"上传结果: 成功 {len(result['success'])}, 失败 {len(result['failed'])}")
        return result
    except Exception as e:
        logger.error(f"上传文档到文件夹 {folder_id} 失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": [], "failed": [{"filename": "处理错误", "reason": str(e)}], "total": len(files)}
        )

# 批量切块
@router.post("/folders/{folder_id}/chunk")
async def batch_chunk(
    folder_id: int,
    request: BatchChunkRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """开始批量切块任务"""
    result = await batch_chunking_service.start_batch_chunking(
        folder_id=folder_id,
        document_ids=request.document_ids,
        chunk_strategy=request.chunk_strategy,
        chunk_size=request.chunk_size,
        overlap=request.overlap,
        background_tasks=background_tasks,
        db=db
    )
    return result

# 批量推送到Dify
@router.post("/folders/{folder_id}/to-dify")
async def batch_to_dify(
    folder_id: int,
    request: BatchDifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """开始批量推送到Dify任务"""
    result = await dify_batch_service.start_batch_to_dify(
        folder_id=folder_id,
        document_ids=request.document_ids,
        dataset_id=request.dataset_id,
        background_tasks=background_tasks,
        db=db
    )
    return result

# 获取任务状态
@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态"""
    task = db.query(BatchTask).filter(BatchTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.task_type == "chunk":
        return batch_chunking_service.get_task_status(task_id, db)
    elif task.task_type == "to_dify":
        return dify_batch_service.get_task_status(task_id, db)
    else:
        raise HTTPException(status_code=400, detail=f"未知的任务类型: {task.task_type}")

# Dify知识库列表
@router.get("/dify/knowledge-bases")
async def get_dify_knowledge_bases():
    """获取Dify知识库列表"""
    try:
        logger.info("正在获取Dify知识库列表...")
        result = dify_service.get_knowledge_bases()
        logger.info(f"知识库API响应: {result}")
        
        if result['status'] == 'success':
            data_list = []
            if isinstance(result['data'], dict) and 'data' in result['data']:
                # 处理嵌套数据结构
                data_list = result['data']['data']
                logger.info(f"从data.data解析出知识库数量: {len(data_list)}")
            elif isinstance(result['data'], list):
                # 处理直接的列表结构
                data_list = result['data']
                logger.info(f"从data直接解析出知识库数量: {len(data_list)}")
            else:
                logger.warning(f"未识别的数据结构: {result['data']}")
            
            return {"status": "success", "data": data_list}
        else:
            logger.error(f"获取知识库失败: {result.get('message', '未知错误')}")
            return {"status": "error", "message": result.get('message', '获取知识库列表失败')}
    except Exception as e:
        logger.error(f"获取知识库列表异常: {str(e)}")
        return {"status": "error", "message": str(e)}

# 测试Dify连接
@router.get("/dify/test-connection")
async def test_dify_connection():
    """测试与Dify服务器的连接"""
    try:
        logger.info("测试Dify连接...")
        result = dify_service.test_connection()
        logger.info(f"连接测试结果: {result}")
        return result
    except Exception as e:
        logger.error(f"连接测试异常: {str(e)}")
        return {"status": "error", "message": str(e)} 