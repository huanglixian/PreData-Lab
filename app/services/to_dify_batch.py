import json
import uuid
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import Document, Folder, BatchTask, Chunk, get_db_session
from ..services.to_dify_single import DifySingleService
from ..config import get_config

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
        
        # 处理每个文档
        for doc_id in document_ids:
            try:
                document = db.query(Document).filter(Document.id == doc_id).first()
                if not document:
                    results[str(doc_id)] = {"status": "failed", "error": "文档不存在", "time": datetime.now().isoformat()}
                    error_count += 1
                    continue
                
                # 如果文档未切块，则跳过
                if document.status != "已切块":
                    results[str(doc_id)] = {"status": "skipped", "error": "文档尚未切块", "time": datetime.now().isoformat()}
                    error_count += 1
                    continue
                
                # 如果文档正在被推送，则跳过
                if document.dify_push_status == "pushing":
                    results[str(doc_id)] = {"status": "skipped", "error": "文档正在被其他任务推送", "time": datetime.now().isoformat()}
                    continue
                
                # 标记文档为推送中
                document.dify_push_status = "pushing"
                db.commit()
                
                # 获取文档的切块
                chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).order_by(Chunk.sequence).all()
                if not chunks:
                    document.dify_push_status = None  # 恢复状态
                    db.commit()
                    results[str(doc_id)] = {"status": "failed", "error": "文档没有切块", "time": datetime.now().isoformat()}
                    error_count += 1
                    continue
                
                # 调用推送函数
                push_result = self._push_document_to_dify(
                    document=document,
                    chunks=chunks,
                    dataset_id=dataset_id
                )
                
                if push_result.get("status") == "success":
                    # 更新文档状态
                    document.dify_push_status = "pushed"
                    db.commit()
                    results[str(doc_id)] = {"status": "completed", "error": None, "time": datetime.now().isoformat()}
                    success_count += 1
                else:
                    # 恢复文档状态
                    document.dify_push_status = None
                    db.commit()
                    results[str(doc_id)] = {
                        "status": "failed", 
                        "error": push_result.get("message", "推送失败"), 
                        "time": datetime.now().isoformat()
                    }
                    error_count += 1
                
            except Exception as e:
                logger.error(f"推送文档 {doc_id} 到Dify失败: {str(e)}")
                results[str(doc_id)] = {"status": "failed", "error": str(e), "time": datetime.now().isoformat()}
                error_count += 1
                
                # 如果出现异常，恢复文档状态
                try:
                    document = db.query(Document).filter(Document.id == doc_id).first()
                    if document and document.dify_push_status == "pushing":
                        document.dify_push_status = None
                        db.commit()
                except:
                    pass
            
            # 更新任务状态
            task.task_results = json.dumps(results)
            task.success_count = success_count
            task.error_count = error_count
            db.commit()
            
            # 为了避免过多连续请求，在文档之间添加短暂延迟
            time.sleep(0.5)  # Dify API可能有频率限制，添加适当延迟
        
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

    def _push_document_to_dify(self, document: Document, chunks: List[Chunk], dataset_id: str) -> Dict[str, Any]:
        """将文档推送到Dify知识库"""
        try:
            # 步骤1: 使用文件创建Dify文档
            logger.info(f"开始推送文档 '{document.filename}' 到Dify知识库")
            document_response = self._create_dify_document_by_file(document, dataset_id)
            if document_response.get("status") != "success":
                return {"status": "error", "message": f"创建文档失败: {document_response.get('message', '未知错误')}"}
            
            # 获取文档ID和批次ID
            data = document_response.get("data", {})
            dify_document_id = None
            if 'document' in data and 'id' in data['document']:
                dify_document_id = data['document']['id']
            elif 'id' in data:
                dify_document_id = data['id']
            
            batch_id = data.get('batch', dify_document_id)
            
            if not dify_document_id:
                return {"status": "error", "message": "无法获取文档ID"}
            
            # 步骤2: 等待文档处理完成
            logger.info("等待Dify文档处理...")
            process_success = self._wait_for_document_processing(dataset_id, batch_id)
            
            # 步骤3: 删除自动生成的段落
            logger.info("正在删除自动生成的段落...")
            segments_response = self._get_document_segments(dataset_id, dify_document_id)
            if segments_response.get('status') == 'success':
                segments_data = segments_response.get('data', {})
                delete_result = self._delete_all_segments(dataset_id, dify_document_id, segments_data)
                if delete_result.get('status') != 'success':
                    logger.warning(f"删除段落失败: {delete_result.get('message', '未知错误')}")
            
            # 步骤4: 添加自定义切块
            chunk_count = len(chunks)
            if chunk_count > 100:
                logger.info(f"开始添加大量切块 ({chunk_count} 个)，这可能需要较长时间...")
            else:
                logger.info(f"正在添加 {chunk_count} 个切块...")
                
            add_response = self._add_segments_to_document(chunks, dataset_id, dify_document_id)
            if add_response.get('status') != 'success':
                return {"status": "error", "message": f"添加段落失败: {add_response.get('message', '未知错误')}"}
            
            logger.info(f"文档 '{document.filename}' 推送完成")
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"推送文档失败: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _create_dify_document_by_file(self, document: Document, dataset_id: str) -> Dict[str, Any]:
        """使用文件创建Dify文档"""
        file_obj = None
        try:
            url = f"{dify_service.api_server}/v1/datasets/{dataset_id}/document/create-by-file"
            
            file_obj = open(document.filepath, 'rb')
            files = {'file': (document.filename, file_obj, 'application/octet-stream')}
            
            data = {'data': json.dumps({
                "indexing_technique": "high_quality",
                "process_rule": {
                    "mode": "custom",
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": True},
                            {"id": "remove_urls_emails", "enabled": True}
                        ],
                        "segmentation": {"separator": "###", "max_tokens": 500}
                    }
                }
            })}
            
            headers = {'Authorization': f'Bearer {dify_service.api_key}'}
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            
            return {'status': 'success', 'data': response.json()}
        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        finally:
            if file_obj:
                file_obj.close()
                
    def _wait_for_document_processing(self, dataset_id: str, batch_id: str) -> bool:
        """等待文档处理完成，支持大文件处理"""
        start_wait = time.time()
        max_wait_time = 600  # 最长等待10分钟
        
        while time.time() - start_wait < max_wait_time:
            try:
                url = f"{dify_service.api_server}/v1/datasets/{dataset_id}/documents/{batch_id}/indexing-status"
                headers = {'Authorization': f'Bearer {dify_service.api_key}'}
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    time.sleep(5)
                    continue
                
                data = response.json()
                
                # 尝试从不同可能的格式获取状态
                status = ""
                if 'data' in data and isinstance(data['data'], list) and data['data']:
                    status = data['data'][0].get('indexing_status', '')
                else:
                    status = data.get('status', data.get('indexing_status', ''))
                
                if status in ['completed', 'ready', 'done']:
                    return True
                
                if status in ['failed', 'error']:
                    return False
                
                # 根据已等待时间调整检查频率
                elapsed = time.time() - start_wait
                if elapsed < 60:
                    time.sleep(2)       # 前1分钟：每2秒
                elif elapsed < 180:
                    time.sleep(5)       # 1-3分钟：每5秒
                else:
                    time.sleep(10)      # 3分钟后：每10秒
                    
                # 每分钟记录一次日志
                if elapsed > 60 and int(elapsed) % 60 < 1:
                    logger.info(f"文档处理中，已等待 {int(elapsed//60)}分{int(elapsed%60)}秒")
                    
            except Exception as e:
                logger.warning(f"检查文档状态出错: {str(e)}")
                time.sleep(10)
        
        # 超时但继续处理
        logger.warning(f"等待文档处理超时(>{max_wait_time//60}分钟)，继续处理")
        return True
    
    def _get_document_segments(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """获取文档的段落列表"""
        try:
            url = f"{dify_service.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
            headers = {'Authorization': f'Bearer {dify_service.api_key}'}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return {'status': 'error', 'message': f"状态码: {response.status_code}"}
            
            return {'status': 'success', 'data': response.json()}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _delete_all_segments(self, dataset_id: str, document_id: str, segments_data: Dict[str, Any]) -> Dict[str, Any]:
        """删除文档的所有段落"""
        try:
            # 获取段落列表
            segments = []
            
            # 处理不同格式的响应
            if isinstance(segments_data, dict) and 'data' in segments_data:
                data = segments_data['data']
                if isinstance(data, dict) and 'data' in data:
                    segments = data['data']
                elif isinstance(data, list):
                    segments = data
            elif isinstance(segments_data, list):
                segments = segments_data
            
            if not segments:
                return {'status': 'success'}
            
            # 获取段落ID
            segment_ids = []
            for segment in segments:
                if isinstance(segment, dict) and 'id' in segment:
                    segment_ids.append(segment['id'])
            
            if not segment_ids:
                return {'status': 'success'}
            
            logger.info(f"删除 {len(segment_ids)} 个段落...")
            
            # 逐个删除段落
            headers = {'Authorization': f'Bearer {dify_service.api_key}'}
            for segment_id in segment_ids:
                try:
                    url = f"{dify_service.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}"
                    requests.delete(url, headers=headers)
                except Exception as e:
                    logger.warning(f"删除段落 {segment_id} 失败: {str(e)}")
            
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _add_segments_to_document(self, chunks: List[Chunk], dataset_id: str, document_id: str) -> Dict[str, Any]:
        """添加段落到Dify文档"""
        try:
            url = f"{dify_service.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
            
            # 记录开始时间
            start_time = time.time()
            
            # 准备段落数据
            segments = []
            for chunk in chunks:
                # 解析元数据
                metadata = {}
                if chunk.chunk_metadata:
                    if isinstance(chunk.chunk_metadata, dict):
                        metadata = chunk.chunk_metadata
                    elif isinstance(chunk.chunk_metadata, str):
                        try:
                            metadata = json.loads(chunk.chunk_metadata)
                        except:
                            metadata = {}
                
                segments.append({
                    "content": chunk.content,
                    "answer": "",
                    "keywords": [],
                    "metadata": metadata
                })
            
            logger.info(f"正在一次性添加所有 {len(segments)} 个段落...")
            headers = {'Authorization': f'Bearer {dify_service.api_key}', 'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, json={"segments": segments})
            response.raise_for_status()
            
            # 记录耗时
            elapsed = time.time() - start_time
            logger.info(f"添加 {len(segments)} 个段落完成，耗时 {elapsed:.2f} 秒")
            
            return {'status': 'success', 'data': response.json()}
                
        except Exception as e:
            logger.error(f"添加段落失败: {str(e)}")
            return {'status': 'error', 'message': str(e)} 