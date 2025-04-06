import os
import json
import uuid
import logging
import time
import shutil
from fastapi import BackgroundTasks, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..database import Document, Folder, BatchTask, get_db_session
from ..services.chunking import ChunkService
from ..config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用已有的切块服务
chunk_service = ChunkService()

class BatchChunkingService:
    """批量切片处理服务"""
    
    async def upload_documents_to_folder(self, 
                                  folder_id: int, 
                                  files: List[UploadFile], 
                                  db: Session) -> Dict[str, Any]:
        """上传多个文档到指定文件夹"""
        # 验证文件夹是否存在
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        allowed_extensions = get_config('ALLOWED_EXTENSIONS')
        result = {
            "success": [],
            "failed": [],
            "total": len(files)
        }
        
        for file in files:
            try:
                # 检查文件扩展名
                filename = file.filename
                ext = os.path.splitext(filename)[1].lower()
                
                if ext not in allowed_extensions:
                    result["failed"].append({
                        "filename": filename,
                        "reason": f"不支持的文件类型 {ext}，支持的类型: {', '.join(allowed_extensions)}"
                    })
                    continue
                
                # 处理文件路径，支持子文件夹
                relative_path = filename.replace("\\", "/")
                file_dir = os.path.dirname(relative_path)
                base_filename = os.path.basename(relative_path)
                
                # 构建目标路径
                target_dir = os.path.join(folder.folder_path, file_dir)
                os.makedirs(target_dir, exist_ok=True)
                
                # 处理文件名冲突
                file_path = os.path.join(target_dir, base_filename)
                if os.path.exists(file_path):
                    name, ext = os.path.splitext(base_filename)
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    new_filename = f"{name}_{timestamp}{ext}"
                    file_path = os.path.join(target_dir, new_filename)
                    relative_path = os.path.join(file_dir, new_filename) if file_dir else new_filename
                
                # 保存文件
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                # 创建文档记录
                document = Document(
                    filename=relative_path,
                    filepath=file_path,
                    filetype=ext,
                    filesize=os.path.getsize(file_path),
                    folder_id=folder_id,
                    upload_time=datetime.now(),
                    status="未切块"
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                result["success"].append({
                    "id": document.id,
                    "filename": document.filename,
                    "size": document.filesize
                })
                
            except Exception as e:
                logger.error(f"上传文件 {file.filename} 失败: {str(e)}")
                result["failed"].append({
                    "filename": file.filename,
                    "reason": str(e)
                })
        
        return result
    
    async def start_batch_chunking(self, 
                           folder_id: int, 
                           document_ids: List[int], 
                           chunk_strategy: str, 
                           chunk_size: int, 
                           overlap: int,
                           background_tasks: BackgroundTasks,
                           db: Session) -> Dict[str, Any]:
        """开始批量切片任务"""
        # 验证文件夹是否存在
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        # 如果没有指定文档ID，则获取文件夹中所有可处理的文档
        if not document_ids:
            documents = db.query(Document).filter(
                Document.folder_id == folder_id,
                Document.status != "处理中"  # 排除正在处理的文档
            ).all()
            document_ids = [doc.id for doc in documents]
        
        if not document_ids:
            raise HTTPException(status_code=400, detail="没有可处理的文档")
        
        # 创建批处理任务
        task_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 保存切块设置
        settings = {
            "chunk_strategy": chunk_strategy,
            "chunk_size": chunk_size,
            "overlap": overlap
        }
        
        # 创建任务记录
        task = BatchTask(
            id=task_id,
            task_type="chunk",
            name=f"批量切块 - {timestamp}",
            folder_id=folder_id,
            status="waiting",
            created_at=datetime.now(),
            total_count=len(document_ids),
            success_count=0,
            error_count=0,
            document_ids=json.dumps(document_ids),
            task_results=json.dumps({}),
            settings=json.dumps(settings)
        )
        
        db.add(task)
        db.commit()
        
        # 启动后台任务
        background_tasks.add_task(
            self._process_batch_chunking,
            task_id=task_id,
            document_ids=document_ids,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        return {
            "status": "processing",
            "message": "批量切块任务已启动",
            "task_id": task_id,
            "total_documents": len(document_ids)
        }
    
    async def _process_batch_chunking(self, 
                              task_id: str, 
                              document_ids: List[int], 
                              chunk_strategy: str, 
                              chunk_size: int, 
                              overlap: int):
        """执行批量切片任务（后台）"""
        db = get_db_session()  # 获取新的会话
        task = db.query(BatchTask).filter(BatchTask.id == task_id).first()
        
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return
        
        # 更新任务状态为处理中
        task.status = "processing"
        db.commit()
        
        # 任务结果字典
        results = {}
        success_count = 0
        error_count = 0
        
        # 处理每个文档
        for doc_id in document_ids:
            document = None
            try:
                document = db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    results[str(doc_id)] = {"status": "failed", "error": "文档不存在", "time": datetime.now().isoformat()}
                    error_count += 1
                    continue
                
                # 如果文档正在处理中，则跳过
                if document.status == "处理中":
                    results[str(doc_id)] = {"status": "skipped", "error": "文档正在被其他任务处理", "time": datetime.now().isoformat()}
                    continue
                
                # 标记文档为处理中
                document.status = "处理中"
                db.commit()
                
                # 调用ChunkService的切块功能
                logger.info(f"开始处理文档 {document.filename}")
                chunk_service._process_chunks(
                    document_id=doc_id,
                    chunk_strategy=chunk_strategy,
                    chunk_size=chunk_size,
                    overlap=overlap
                )
                
                # 处理成功
                results[str(doc_id)] = {"status": "completed", "error": None, "time": datetime.now().isoformat()}
                success_count += 1
                logger.info(f"文档 {document.filename} 处理完成")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"处理文档 ID:{doc_id} 失败: {error_msg}")
                results[str(doc_id)] = {"status": "failed", "error": error_msg, "time": datetime.now().isoformat()}
                error_count += 1
                
                # 如果出现异常，将文档状态改回未处理
                if document:
                    try:
                        document.status = "未切块"
                        db.commit()
                    except Exception as db_error:
                        logger.error(f"更新文档状态失败: {str(db_error)}")
            
            # 更新任务状态
            task.task_results = json.dumps(results)
            task.success_count = success_count
            task.error_count = error_count
            db.commit()
            
            # 添加短暂延迟避免系统过载
            time.sleep(0.2)
        
        # 完成任务
        task.status = "completed"
        task.completed_at = datetime.now()
        db.commit()
        
        # 关闭数据库会话
        db.close()
    
    def get_task_status(self, task_id: str, db: Session) -> Dict[str, Any]:
        """获取任务状态"""
        task = db.query(BatchTask).filter(BatchTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 解析JSON字段
        document_ids = json.loads(task.document_ids)
        task_results = json.loads(task.task_results)
        settings = json.loads(task.settings)
        
        # 计算进度
        progress = 0
        if task.total_count > 0:
            done_count = task.success_count + task.error_count
            progress = int((done_count / task.total_count) * 100)
        
        return {
            "task_id": task.id,
            "name": task.name,
            "type": task.task_type,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
            "total_count": task.total_count,
            "success_count": task.success_count,
            "error_count": task.error_count,
            "progress": progress,
            "settings": settings,
            "documents": {
                "ids": document_ids,
                "results": task_results
            }
        }
    
    def get_folder_tasks(self, folder_id: int, db: Session) -> List[Dict[str, Any]]:
        """获取文件夹的任务列表"""
        tasks = db.query(BatchTask).filter(
            BatchTask.folder_id == folder_id,
            BatchTask.task_type == "chunk"
        ).order_by(BatchTask.created_at.desc()).all()
        
        result = []
        for task in tasks:
            # 计算进度
            progress = 0
            if task.total_count > 0:
                done_count = task.success_count + task.error_count
                progress = int((done_count / task.total_count) * 100)
            
            result.append({
                "task_id": task.id,
                "name": task.name,
                "status": task.status,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "total_count": task.total_count,
                "success_count": task.success_count,
                "error_count": task.error_count,
                "progress": progress
            })
        
        return result 