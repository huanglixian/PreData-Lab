import json
import uuid
import time
import logging
import requests
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from functools import wraps

from ..database import Document, Folder, BatchTask, Chunk, get_db_session
from ..services.to_dify_single import DifySingleService
from ..config import get_config, BASE_DIR

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用已有的Dify服务
dify_service = DifySingleService()

# 重试装饰器（异步版本）
def async_retry(max_retries=3, delay=1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries < max_retries:
                        logger.warning(f"操作失败: {str(e)}，{delay}秒后第{retries}次重试...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"操作失败，已达最大重试次数: {str(e)}")
                        raise
            return None
        return wrapper
    return decorator

class DifyBatchService:
    """批量推送到Dify服务"""
    
    async def start_batch_to_dify(self,
                          folder_id: int,
                          document_ids: List[int],
                          dataset_id: str,
                          background_tasks: BackgroundTasks,
                          db: Session) -> Dict[str, Any]:
        """开始批量推送到Dify任务"""
        # 验证文件夹是否存在
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        # 如果没有指定文档ID，则获取文件夹中所有已切块的文档
        if not document_ids:
            documents = db.query(Document).filter(
                Document.folder_id == folder_id,
                Document.status == "已切块",
                Document.dify_push_status != "pushing"  # 排除正在推送的文档
            ).all()
            document_ids = [doc.id for doc in documents]
        else:
            # 验证这些文档是否存在且已切块
            for doc_id in document_ids:
                document = db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    raise HTTPException(status_code=404, detail=f"文档 ID {doc_id} 不存在")
                if document.status != "已切块":
                    raise HTTPException(status_code=400, detail=f"文档 '{document.filename}' 尚未切块")
                if document.dify_push_status == "pushing":
                    raise HTTPException(status_code=400, detail=f"文档 '{document.filename}' 正在被其他任务推送")
        
        if not document_ids:
            raise HTTPException(status_code=400, detail="没有可推送的文档")
        
        # 测试Dify连接
        connection_test = dify_service.test_connection()
        if connection_test.get("status") != "success":
            raise HTTPException(status_code=500, detail=f"Dify连接测试失败: {connection_test.get('message', '未知错误')}")
        
        # 验证知识库ID
        kb_check = self._check_knowledge_base(dataset_id)
        if not kb_check.get("valid", False):
            raise HTTPException(status_code=400, detail=f"无效的知识库ID: {dataset_id}")
        
        # 创建批处理任务
        task_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 保存任务设置
        settings = {
            "dataset_id": dataset_id,
            "dataset_name": kb_check.get("name", "未知知识库")
        }
        
        # 创建任务记录
        task = BatchTask(
            id=task_id,
            task_type="to_dify",
            name=f"批量推送 - {timestamp}",
            folder_id=folder_id,
            dataset_id=dataset_id,
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
            self._process_batch_to_dify,
            task_id=task_id,
            document_ids=document_ids,
            dataset_id=dataset_id
        )
        
        return {
            "status": "processing",
            "message": "批量推送任务已启动",
            "task_id": task_id,
            "total_documents": len(document_ids),
            "knowledge_base": {
                "id": dataset_id,
                "name": kb_check.get("name", "未知知识库")
            }
        }
    
    async def _process_batch_to_dify(self,
                             task_id: str,
                             document_ids: List[int],
                             dataset_id: str):
        """执行批量推送到Dify任务（后台）- 异步版本"""
        # 获取数据库会话
        db = get_db_session()
        try:
            task = db.query(BatchTask).filter(BatchTask.id == task_id).first()
            
            if not task:
                logger.error(f"任务 {task_id} 不存在")
                db.close()
                return
            
            # 更新任务状态为处理中
            task.status = "processing"
            db.commit()
            
            # 任务结果字典
            results = {}
            success_count = 0
            error_count = 0
            
            # 计算动态批次大小和并发数
            batch_size = min(40, max(5, len(document_ids) // 2))
            max_concurrency = min(8, len(document_ids))
            
            # 定义批量更新任务状态的函数
            def update_task_status(force=False):
                # 已处理文档数量
                processed = success_count + error_count
                
                # 只有达到更新阈值或强制更新时才更新
                if force or processed % 5 == 0 or processed == len(document_ids):
                    nonlocal task
                    task.task_results = json.dumps(results)
                    task.success_count = success_count
                    task.error_count = error_count
                    db.commit()
                    
                    # 计算进度
                    progress = int(processed / len(document_ids) * 100)
                    logger.info(f"任务 {task_id} 进度: {progress}% (成功: {success_count}, 失败: {error_count})")
            
            # 定义处理单个文档的异步函数
            @async_retry(max_retries=3, delay=2.0)
            async def process_single_document(doc_id):
                # 每个协程使用自己的数据库会话
                thread_db = get_db_session()
                try:
                    document = thread_db.query(Document).filter(Document.id == doc_id).first()
                    if not document:
                        return {"status": "failed", "error": "文档不存在", "time": datetime.now().isoformat()}
                    
                    # 检查文档状态
                    if document.status != "已切块":
                        return {"status": "skipped", "error": "文档尚未切块", "time": datetime.now().isoformat()}
                    
                    if document.dify_push_status == "pushing":
                        return {"status": "skipped", "error": "文档正在被其他任务推送", "time": datetime.now().isoformat()}
                    
                    # 标记文档为推送中
                    document.dify_push_status = "pushing"
                    thread_db.commit()
                    
                    # 获取文档的切块
                    chunks = thread_db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.sequence).all()
                    if not chunks:
                        document.dify_push_status = None
                        thread_db.commit()
                        return {"status": "failed", "error": "文档没有切块", "time": datetime.now().isoformat()}
                    
                    # 调用推送函数
                    logger.info(f"开始推送文档 '{document.filename}' 到Dify知识库")
                    
                    # 处理文件路径 - 支持相对路径
                    filepath = document.filepath
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(BASE_DIR, filepath)
                    
                    # 检查文件是否存在
                    if not os.path.exists(filepath):
                        document.dify_push_status = None
                        thread_db.commit()
                        return {
                            "status": "failed", 
                            "error": f"文件不存在: {filepath}", 
                            "time": datetime.now().isoformat()
                        }
                    
                    # 在事件循环的线程池中执行同步代码
                    document_response = await asyncio.to_thread(
                        dify_service._create_dify_document_by_file, 
                        document, dataset_id, filepath
                    )
                    
                    if document_response.get("status") != "success":
                        document.dify_push_status = None
                        thread_db.commit()
                        return {
                            "status": "failed", 
                            "error": f"创建文档失败: {document_response.get('message', '未知错误')}", 
                            "time": datetime.now().isoformat()
                        }
                    
                    # 获取文档ID和批次ID
                    data = document_response.get("data", {})
                    dify_document_id = None
                    if 'document' in data and 'id' in data['document']:
                        dify_document_id = data['document']['id']
                    elif 'id' in data:
                        dify_document_id = data['id']
                    
                    batch_id = data.get('batch', dify_document_id)
                    
                    if not dify_document_id:
                        document.dify_push_status = None
                        thread_db.commit()
                        return {"status": "failed", "error": "无法获取文档ID", "time": datetime.now().isoformat()}
                    
                    # 等待文档处理完成
                    logger.info(f"文档 '{document.filename}': 等待Dify文档处理...")
                    process_success = await asyncio.to_thread(
                        dify_service._wait_for_document_processing, 
                        dataset_id, batch_id
                    )
                    
                    # 根据配置决定是否删除自动生成的段落
                    if get_config('DIFY_DELETE_EXISTING_SEGMENTS'):
                        logger.info(f"文档 '{document.filename}': 正在删除自动生成的段落...")
                        segments_response = await asyncio.to_thread(
                            dify_service._get_document_segments, 
                            dataset_id, dify_document_id
                        )
                        
                        if segments_response.get('status') == 'success':
                            segments_data = segments_response.get('data', {})
                            delete_result = await asyncio.to_thread(
                                dify_service._delete_all_segments, 
                                dataset_id, dify_document_id, segments_data
                            )
                            
                            if delete_result.get('status') != 'success':
                                logger.warning(f"文档 '{document.filename}': 删除段落失败: {delete_result.get('message', '未知错误')}")
                    else:
                        logger.info(f"文档 '{document.filename}': 已跳过删除段落步骤，根据配置 DIFY_DELETE_EXISTING_SEGMENTS=False")
                    
                    # 添加自定义切块
                    logger.info(f"文档 '{document.filename}': 正在添加 {len(chunks)} 个切块...")
                    add_response = await asyncio.to_thread(
                        dify_service._add_segments_to_document, 
                        chunks, dataset_id, dify_document_id
                    )
                    
                    if add_response.get('status') != 'success':
                        document.dify_push_status = None
                        thread_db.commit()
                        return {
                            "status": "failed", 
                            "error": f"添加段落失败: {add_response.get('message', '未知错误')}", 
                            "time": datetime.now().isoformat()
                        }
                    
                    # 成功处理
                    document.dify_push_status = "pushed"
                    thread_db.commit()
                    logger.info(f"文档 '{document.filename}' 推送完成")
                    return {"status": "completed", "error": None, "time": datetime.now().isoformat()}
                    
                except Exception as e:
                    logger.error(f"推送文档 {doc_id} 到Dify失败: {str(e)}")
                    # 如果出现异常，恢复文档状态
                    try:
                        document = thread_db.query(Document).filter(Document.id == doc_id).first()
                        if document and document.dify_push_status == "pushing":
                            document.dify_push_status = None
                            thread_db.commit()
                    except:
                        pass
                    # 重新抛出异常以允许重试
                    raise
                finally:
                    # 关闭线程数据库会话
                    thread_db.close()
            
            logger.info(f"任务 {task_id}: 共 {len(document_ids)} 个文档，批次大小 {batch_size}，并发数 {max_concurrency}")
            
            # 按批次处理，使用异步方式
            for i in range(0, len(document_ids), batch_size):
                batch = document_ids[i:i+batch_size]
                logger.info(f"任务 {task_id}: 处理批次 {i//batch_size+1}/{(len(document_ids)+batch_size-1)//batch_size}，共 {len(batch)} 个文档")
                
                # 使用信号量控制并发数
                semaphore = asyncio.Semaphore(max_concurrency)
                
                # 批量异步处理文档
                async def process_with_semaphore(doc_id):
                    async with semaphore:
                        return doc_id, await process_single_document(doc_id)
                
                # 创建所有任务
                tasks = [process_with_semaphore(doc_id) for doc_id in batch]
                
                # 等待所有任务完成
                batch_results = {}
                for completed_task in asyncio.as_completed(tasks):
                    try:
                        doc_id, result = await completed_task
                        batch_results[str(doc_id)] = result
                        
                        if result["status"] == "completed":
                            success_count += 1
                        elif result["status"] == "failed":
                            error_count += 1
                            
                        # 更新结果
                        results.update(batch_results)
                        update_task_status()
                        
                    except Exception as e:
                        logger.error(f"处理文档时发生异常: {str(e)}")
                        # 由于无法获取doc_id，这里无法更新特定文档的结果
                        error_count += 1
                
                # 批次处理完成后强制更新一次任务状态
                update_task_status(force=True)
                
                # 批次间短暂休息
                if i + batch_size < len(document_ids):
                    await asyncio.sleep(1)
            
            # 完成任务
            task.status = "completed"
            task.completed_at = datetime.now()
            task.task_results = json.dumps(results)
            task.success_count = success_count
            task.error_count = error_count
            db.commit()
            
            logger.info(f"批量推送任务 {task_id} 完成，共 {len(document_ids)} 个文档，成功 {success_count} 个，失败 {error_count} 个")
        except Exception as e:
            # 如果发生异常，记录错误
            logger.error(f"批量处理任务 {task_id} 失败: {str(e)}")
            try:
                # 尝试更新任务状态为失败
                task = db.query(BatchTask).filter(BatchTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    db.commit()
            except:
                pass
        finally:
            # 关闭数据库连接
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
        """获取文件夹的推送任务列表"""
        tasks = db.query(BatchTask).filter(
            BatchTask.folder_id == folder_id,
            BatchTask.task_type == "to_dify"
        ).order_by(BatchTask.created_at.desc()).all()
        
        result = []
        for task in tasks:
            # 计算进度
            progress = 0
            if task.total_count > 0:
                done_count = task.success_count + task.error_count
                progress = int((done_count / task.total_count) * 100)
            
            # 解析设置
            settings = json.loads(task.settings)
            
            result.append({
                "task_id": task.id,
                "name": task.name,
                "status": task.status,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "total_count": task.total_count,
                "success_count": task.success_count,
                "error_count": task.error_count,
                "progress": progress,
                "dataset_id": task.dataset_id,
                "dataset_name": settings.get("dataset_name", "未知知识库")
            })
        
        return result

    def _check_knowledge_base(self, dataset_id: str) -> Dict[str, Any]:
        """检查知识库ID是否有效"""
        try:
            # 获取知识库列表
            kb_result = dify_service.get_knowledge_bases()
            if kb_result['status'] != 'success':
                return {'valid': False, 'message': '获取知识库列表失败'}
            
            # 提取知识库列表
            kb_list = []
            if isinstance(kb_result['data'], dict) and 'data' in kb_result['data']:
                kb_list = kb_result['data']['data']
            elif isinstance(kb_result['data'], list):
                kb_list = kb_result['data']
            
            # 查找指定ID的知识库
            for kb in kb_list:
                if kb.get('id') == dataset_id:
                    return {'valid': True, 'name': kb.get('name', '未命名知识库')}
            
            return {'valid': False, 'message': '未找到指定ID的知识库'}
        except Exception as e:
            logger.error(f"检查知识库失败: {str(e)}")
            return {'valid': False, 'message': str(e)}