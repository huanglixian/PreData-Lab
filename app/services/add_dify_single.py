import requests
import json
import logging
import time
import os
from typing import List, Dict, Any, Optional
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..config import get_config
from ..database import Document, Chunk, get_db_session

# 配置日志
logger = logging.getLogger(__name__)

class AddDifySingleService:
    """处理将新切片添加到Dify现有文件的服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.api_server = get_config('DIFY_API_SERVER')
        self.api_key = get_config('DIFY_API_KEY')
        self.headers = {'Authorization': f'Bearer {self.api_key}'}
    
    def get_dataset_files(self, dataset_id: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        """获取知识库中的文件列表，可选搜索筛选"""
        try:
            url = f"{self.api_server}/v1/datasets/{dataset_id}/documents"
            params = {'page': 1, 'limit': 100}
            
            if search_term:
                params['keyword'] = search_term
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                return {'status': 'error', 'message': f'API错误: {response.status_code}'}
                
            data = response.json()
            return {'status': 'success', 'data': data.get('data', [])}
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def add_to_dify_file(self, document_id: int, dataset_id: str, target_file_id: str, db: Session) -> JSONResponse:
        """启动将切片添加到Dify现有文件的任务"""
        try:
            # 获取文档并检查状态
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return JSONResponse(status_code=404, content={'message': '文档不存在'})
                
            if document.dify_push_status == "pushing":
                return JSONResponse(status_code=409, content={'message': '文档正在推送中，请稍后再试'})
            
            # 更新状态为推送中
            document.dify_push_status = "pushing"
            db.commit()
            
            # 启动后台任务
            from threading import Thread
            thread = Thread(target=self._do_add_to_file, args=(document_id, dataset_id, target_file_id))
            thread.daemon = True
            thread.start()
            
            return JSONResponse(status_code=200, content={
                'message': '添加任务已启动',
                'status': 'processing'
            })
            
        except Exception as e:
            logger.error(f"启动添加任务失败: {str(e)}")
            return JSONResponse(status_code=500, content={'message': str(e)})
    
    def _do_add_to_file(self, document_id: int, dataset_id: str, target_file_id: str):
        """实际执行添加切片的后台任务"""
        db = get_db_session()
        document = None
        
        try:
            # 获取文档和切块
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
                
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.sequence).all()
            if not chunks or not os.path.exists(document.filepath):
                self._update_status(document, None, db)
                return
            
            # 验证目标文件存在
            if not self._verify_target_file(dataset_id, target_file_id):
                self._update_status(document, None, db)
                logger.error(f"目标文件 {target_file_id} 不存在或无法访问")
                return
            
            # 添加自定义切块
            add_response = self._add_segments_to_document(chunks, dataset_id, target_file_id)
            if add_response.get('status') != 'success':
                self._update_status(document, None, db)
                logger.error(f"添加段落失败: {add_response.get('message', '未知错误')}")
                return
            
            # 更新状态为已推送
            self._update_status(document, "pushed", db)
            
        except Exception as e:
            logger.error(f"添加切片失败: {str(e)}")
            if document:
                self._update_status(document, None, db)
    
    def _update_status(self, document, status, db):
        """更新文档状态并提交"""
        document.dify_push_status = status
        db.commit()
    
    def get_push_status(self, document_id: int, db: Session) -> Dict[str, Any]:
        """获取文档推送状态"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'status': 'error', 'message': '文档不存在'}
            
            if document.dify_push_status == "pushed":
                return {'status': 'pushed'}
            elif document.dify_push_status == "pushing":
                return {'status': 'pushing'}
            else:
                return {'status': 'not_pushed'}
        except Exception as e:
            logger.error(f"获取推送状态失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _verify_target_file(self, dataset_id: str, file_id: str) -> bool:
        """验证目标文件是否存在可访问"""
        try:
            url = f"{self.api_server}/v1/datasets/{dataset_id}/documents"
            params = {'page': 1, 'limit': 100}
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                return False
                
            data = response.json()
            file_list = data.get('data', [])
            
            for file in file_list:
                if file.get('id') == file_id:
                    logger.info(f"目标文件 {file_id} 存在，文件名: {file.get('name', '未知')}")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"验证目标文件失败: {str(e)}")
            return False
    
    def _add_segments_to_document(self, chunks: List[Chunk], dataset_id: str, document_id: str) -> Dict[str, Any]:
        """添加段落到Dify文档"""
        try:
            url = f"{self.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
            
            # 准备段落数据
            segments = []
            for chunk in chunks:
                # 将 chunk_metadata 转换为 keywords
                keywords = []
                if get_config('PASS_META_TO_DIFY') and chunk.chunk_metadata:
                    for key, value in chunk.chunk_metadata.items():
                        if isinstance(value, (list, dict)):
                            keywords.append(f"{key}:{json.dumps(value, ensure_ascii=False)}")
                        else:
                            keywords.append(f"{key}:{str(value)}")
                
                segments.append({
                    "content": chunk.content,
                    "answer": "",
                    "keywords": keywords
                })
            
            if not segments:
                return {'status': 'error', 'message': '没有可添加的段落'}
            
            # 一次性添加所有段落
            logger.info(f"一次性开始添加{len(segments)}个切块到文件 {document_id}")
            start_time = time.time()
            
            response = requests.post(
                url,
                headers=self.headers,
                json={"segments": segments}
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code < 400:
                logger.info(f"所有 {len(segments)} 个段落添加成功")
                logger.info(f"成功添加切块，耗时: {elapsed_time:.2f}秒")
                return {'status': 'success', 'data': {'message': '所有段落添加成功'}}
            else:
                logger.error(f"添加段落失败: HTTP {response.status_code}")
                return {'status': 'error', 'message': f'HTTP错误: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"添加段落失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}

# 实例化服务
add_dify_service = AddDifySingleService() 