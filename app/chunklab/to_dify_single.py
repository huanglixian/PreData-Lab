import requests
import json
import logging
import time
import os
from typing import List, Dict, Any
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..config import get_config
from ..database import Document, Chunk, get_db, get_db_session

# 配置日志
logger = logging.getLogger(__name__)

class DifySingleService:
    """处理与Dify API交互的服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.api_server = get_config('DIFY_API_SERVER')
        self.api_key = get_config('DIFY_API_KEY')
        
    def get_headers(self):
        """获取API请求头"""
        return {
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def get_knowledge_bases(self) -> Dict[str, Any]:
        """获取Dify知识库列表"""
        try:
            url = f"{self.api_server}/v1/datasets"
            response = requests.get(url, headers=self.get_headers(), params={'page': 1, 'limit': 100})
            response.raise_for_status()
            return {'status': 'success', 'data': response.json()}
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def test_connection(self) -> Dict[str, Any]:
        """测试与Dify服务器的连接"""
        try:
            url = f"{self.api_server}/v1/health"
            response = requests.get(url, headers=self.get_headers(), timeout=5)
            
            # 如果健康检查接口返回成功
            if response.status_code < 300:
                return {'status': 'success', 'message': '连接成功', 'details': {'api_server': self.api_server}}
            
            # 尝试请求几个常见的端点
            alt_endpoints = ['/v1/datasets', '/datasets', '/v1', '/']
            for endpoint in alt_endpoints:
                try:
                    test_url = f"{self.api_server}{endpoint}"
                    test_response = requests.get(test_url, headers=self.get_headers(), timeout=5)
                    if test_response.status_code < 300 or test_response.status_code == 401:
                        return {'status': 'success', 'message': '连接成功', 'details': {'api_server': self.api_server}}
                except:
                    continue
            
            return {'status': 'error', 'message': f'服务器响应异常: {response.status_code}', 'details': {'api_server': self.api_server}}
        except requests.exceptions.Timeout:
            return {'status': 'error', 'message': '连接超时，请检查服务器地址和网络', 'details': {'api_server': self.api_server}}
        except requests.exceptions.ConnectionError:
            return {'status': 'error', 'message': '无法连接到服务器，请检查服务器地址', 'details': {'api_server': self.api_server}}
        except Exception as e:
            return {'status': 'error', 'message': f'连接测试失败: {str(e)}', 'details': {'api_server': self.api_server}}
    
    def push_document_to_dify(self, document_id: int, dataset_id: str, db: Session) -> JSONResponse:
        """启动文档推送到Dify知识库的任务"""
        try:
            # 获取文档
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return JSONResponse(status_code=404, content={'message': '文档不存在'})
                
            # 检查文档是否已经在推送中
            if document.dify_push_status == "pushing":
                return JSONResponse(status_code=409, content={'message': '文档正在推送中，请稍后再试'})
            
            # 更新状态为推送中
            document.dify_push_status = "pushing"
            db.commit()
            
            # 启动后台任务
            from threading import Thread
            thread = Thread(target=self._do_push_document, args=(document_id, dataset_id))
            thread.daemon = True
            thread.start()
            
            return JSONResponse(status_code=200, content={
                'message': '推送任务已启动',
                'status': 'processing'
            })
            
        except Exception as e:
            logger.error(f"启动推送任务失败: {str(e)}")
            return JSONResponse(status_code=500, content={'message': str(e)})
    
    def _do_push_document(self, document_id: int, dataset_id: str):
        """实际执行推送的后台任务"""
        db = get_db_session()
        
        # 开始计时
        start_time = time.time()
        
        try:
            # 获取文档和切块
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
                
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.sequence).all()
            chunk_count = len(chunks) if chunks else 0
            
            if not chunks or not os.path.exists(document.filepath):
                document.dify_push_status = None
                db.commit()
                return
            
            # 记录文件大小和切块数量
            file_size_mb = os.path.getsize(document.filepath) / 1024 / 1024
            logger.info(f"开始推送文档 {document_id}，共 {chunk_count} 个切块，文件大小: {file_size_mb:.2f}MB")
            
            # 创建文档并获取ID
            logger.info("正在创建Dify文档...")
            document_response = self._create_dify_document_by_file(document, dataset_id)
            if document_response.get('status') != 'success':
                document.dify_push_status = None
                db.commit()
                logger.error(f"创建Dify文档失败: {document_response.get('message', '未知错误')}")
                return
            
            data = document_response.get('data', {})
            dify_document_id = data.get('document', {}).get('id') if 'document' in data else data.get('id')
            batch_id = data.get('batch', dify_document_id)
            
            if not dify_document_id:
                document.dify_push_status = None
                db.commit()
                logger.error("无法获取Dify文档ID")
                return
            
            # 等待文档处理完成
            logger.info("等待Dify文档处理...")
            process_success = self._wait_for_document_processing(dataset_id, batch_id)
            
            # 删除自动生成的段落
            logger.info("正在删除自动生成的段落...")
            segments_response = self._get_document_segments(dataset_id, dify_document_id)
            if segments_response.get('status') == 'success':
                segments_data = segments_response.get('data', {})
                delete_result = self._delete_all_segments(dataset_id, dify_document_id, segments_data)
                if delete_result.get('status') != 'success':
                    logger.warning(f"删除段落失败: {delete_result.get('message', '未知错误')}")
            
            # 添加自定义切块
            if chunk_count > 100:
                logger.info(f"开始添加大量切块 ({chunk_count} 个)，这可能需要较长时间...")
            else:
                logger.info(f"正在添加 {chunk_count} 个切块...")
                
            add_response = self._add_segments_to_document(chunks, dataset_id, dify_document_id)
            if add_response.get('status') != 'success':
                document.dify_push_status = None
                db.commit()
                logger.error(f"添加段落失败: {add_response.get('message', '未知错误')}")
                return
            
            # 更新状态为已推送
            document.dify_push_status = "pushed"
            db.commit()
            
            # 计算总耗时
            elapsed_time = time.time() - start_time
            if elapsed_time > 60:
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                logger.info(f"文档 {document_id} 推送完成，共 {chunk_count} 个切块，耗时 {minutes}分{seconds}秒")
            else:
                logger.info(f"文档 {document_id} 推送完成，共 {chunk_count} 个切块，耗时 {elapsed_time:.2f}秒")
            
        except Exception as e:
            # 记录错误和耗时
            elapsed_time = time.time() - start_time
            if elapsed_time > 60:
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                logger.error(f"推送任务执行失败: {str(e)}，耗时 {minutes}分{seconds}秒")
            else:
                logger.error(f"推送任务执行失败: {str(e)}，耗时 {elapsed_time:.2f}秒")
            
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.dify_push_status = None
                    db.commit()
            except:
                pass
        finally:
            db.close()
    
    def get_push_status(self, document_id: int, db: Session) -> Dict[str, Any]:
        """获取文档推送状态"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {'status': 'error', 'message': '文档不存在'}
        
        status = document.dify_push_status
        if status is None:
            return {'status': 'not_pushed', 'message': '未推送'}
        elif status == "pushing":
            return {'status': 'pushing', 'message': '推送中'}
        elif status == "pushed":
            return {'status': 'pushed', 'message': '已推送'}
        else:
            return {'status': 'unknown', 'message': f'未知状态: {status}'}
    
    def _create_dify_document_by_file(self, document: Document, dataset_id: str) -> Dict[str, Any]:
        """使用文件创建Dify文档"""
        file_obj = None
        try:
            url = f"{self.api_server}/v1/datasets/{dataset_id}/document/create-by-file"
            
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
            
            response = requests.post(
                url,
                headers={'Authorization': f'Bearer {self.api_key}'},
                files=files,
                data=data
            )
            
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
                url = f"{self.api_server}/v1/datasets/{dataset_id}/documents/{batch_id}/indexing-status"
                response = requests.get(url, headers=self.get_headers())
                
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
            url = f"{self.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
            response = requests.get(url, headers=self.get_headers())
            
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
            for segment_id in segment_ids:
                try:
                    url = f"{self.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}"
                    requests.delete(url, headers=self.get_headers())
                except Exception as e:
                    logger.warning(f"删除段落 {segment_id} 失败: {str(e)}")
            
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _add_segments_to_document(self, chunks: List[Chunk], dataset_id: str, document_id: str) -> Dict[str, Any]:
        """添加段落到Dify文档"""
        try:
            url = f"{self.api_server}/v1/datasets/{dataset_id}/documents/{document_id}/segments"
            
            # 一次性提交所有切块（测试用）
            all_chunks = list(chunks)
            total_chunks = len(all_chunks)
            
            # 记录开始时间
            start_time = time.time()
            
            # 单批处理所有段落
            segments = []
            for chunk in all_chunks:
                segments.append({
                    "content": chunk.content,
                    "answer": "",
                    "keywords": [],
                    "metadata": {}
                })
            
            logger.info(f"正在一次性添加所有 {len(segments)} 个段落...")
            response = requests.post(
                url,
                headers={**self.get_headers(), 'Content-Type': 'application/json'},
                json={"segments": segments}
            )
            
            response.raise_for_status()
            
            # 记录耗时
            elapsed = time.time() - start_time
            logger.info(f"添加 {len(segments)} 个段落完成，耗时 {elapsed:.2f} 秒")
            
            return {'status': 'success', 'data': response.json()}
                
        except Exception as e:
            logger.error(f"添加段落失败: {str(e)}")
            return {'status': 'error', 'message': str(e)} 