import json
import uuid
import time
import logging
import requests
import os
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..database import Document, Folder, BatchTask, Chunk, get_db_session
from ..services.to_dify_single import DifySingleService
from ..config import get_config, BASE_DIR

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用已有的Dify服务
dify_service = DifySingleService()

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
        """执行批量推送到Dify任务（后台）"""
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
        
        # 定义处理单个文档的函数
        def process_single_document(doc_id):
            # 每个线程需要自己的数据库连接
            thread_db = get_db_session()
            try:
                document = thread_db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    return {"status": "failed", "error": "文档不存在", "time": datetime.now().isoformat()}
                
                # 如果文档未切块，则跳过
                if document.status != "已切块":
                    return {"status": "skipped", "error": "文档尚未切块", "time": datetime.now().isoformat()}
                
                # 如果文档正在被推送，则跳过
                if document.dify_push_status == "pushing":
                    return {"status": "skipped", "error": "文档正在被其他任务推送", "time": datetime.now().isoformat()}
                
                # 标记文档为推送中
                document.dify_push_status = "pushing"
                thread_db.commit()
                
                # 获取文档的切块
                chunks = thread_db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.sequence).all()
                if not chunks:
                    document.dify_push_status = None  # 恢复状态
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
                
                # 创建文档 - 传递正确的参数
                document_response = dify_service._create_dify_document_by_file(document, dataset_id, filepath)
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
                process_success = dify_service._wait_for_document_processing(dataset_id, batch_id)
                
                # 删除自动生成的段落
                logger.info(f"文档 '{document.filename}': 正在删除自动生成的段落...")
                segments_response = dify_service._get_document_segments(dataset_id, dify_document_id)
                if segments_response.get('status') == 'success':
                    segments_data = segments_response.get('data', {})
                    delete_result = dify_service._delete_all_segments(dataset_id, dify_document_id, segments_data)
                    if delete_result.get('status') != 'success':
                        logger.warning(f"文档 '{document.filename}': 删除段落失败: {delete_result.get('message', '未知错误')}")
                
                # 添加自定义切块
                logger.info(f"文档 '{document.filename}': 正在添加 {len(chunks)} 个切块...")
                add_response = dify_service._add_segments_to_document(chunks, dataset_id, dify_document_id)
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
                return {"status": "failed", "error": str(e), "time": datetime.now().isoformat()}
            finally:
                thread_db.close()
        
        # 使用线程池并发处理文档
        max_workers = min(10, len(document_ids))  # 最多10个并发线程
        logger.info(f"启动并发处理，最大线程数: {max_workers}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_doc_id = {executor.submit(process_single_document, doc_id): doc_id for doc_id in document_ids}
            
            # 处理结果
            for future in as_completed(future_to_doc_id):
                doc_id = future_to_doc_id[future]
                try:
                    result = future.result()
                    results[str(doc_id)] = result
                    
                    if result["status"] == "completed":
                        success_count += 1
                    elif result["status"] == "failed":
                        error_count += 1
                        
                    # 及时更新任务状态
                    task.task_results = json.dumps(results)
                    task.success_count = success_count
                    task.error_count = error_count
                    db.commit()
                    
                    # 每完成一个任务，就更新进度
                    progress = int((success_count + error_count) / len(document_ids) * 100)
                    logger.info(f"任务 {task_id} 进度: {progress}% (成功: {success_count}, 失败: {error_count})")
                    
                except Exception as exc:
                    logger.error(f"处理文档 {doc_id} 时发生异常: {exc}")
                    results[str(doc_id)] = {"status": "failed", "error": str(exc), "time": datetime.now().isoformat()}
                    error_count += 1
        
        # 完成任务
        task.status = "completed"
        task.completed_at = datetime.now()
        db.commit()
        
        # 关闭数据库会话
        db.close()
        logger.info(f"批量推送任务 {task_id} 完成，共 {len(document_ids)} 个文档，成功 {success_count} 个，失败 {error_count} 个")
    
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