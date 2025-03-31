from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import traceback
import os
import time

from ..database import Document, Chunk, get_db
from ..config import APP_CONFIG, get_config
from .chunking.word_strategy import WordChunkStrategy

# 配置日志
logger = logging.getLogger(__name__)

# 用于跟踪后台任务
CHUNK_TASKS = {}

class ChunkService:
    """切块服务类 - 处理文档切块相关操作"""
    
    async def create_chunks(
        self,
        document_id: int,
        background_tasks: BackgroundTasks,
        chunk_strategy: str,
        chunk_size: int,
        overlap: int,
        db: Session
    ) -> JSONResponse:
        """
        创建切块任务
        
        Args:
            document_id: 文档ID
            background_tasks: 后台任务对象
            chunk_strategy: 切块策略名称
            chunk_size: 切块大小
            overlap: 重叠度
            db: 数据库会话
            
        Returns:
            JSONResponse: 任务创建结果
        """
        try:
            logger.info(f"开始切块处理: document_id={document_id}, strategy={chunk_strategy}, size={chunk_size}, overlap={overlap}")
            
            # 检查文档是否存在
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail="文档不存在")
            
            # 检查文件是否存在
            if not os.path.exists(document.filepath):
                logger.error(f"文件不存在: {document.filepath}")
                raise HTTPException(status_code=400, detail="文件不存在或已被删除")
            
            # 检查切块策略是否有效
            valid_strategies = [s['name'] for s in get_config('CHUNK_STRATEGIES')]
            if chunk_strategy not in valid_strategies:
                logger.error(f"无效的切块策略: {chunk_strategy}")
                raise HTTPException(status_code=400, detail="无效的切块策略")
            
            # 检查切块参数
            if chunk_size <= 0:
                logger.error(f"无效的切块大小: {chunk_size}")
                raise HTTPException(status_code=400, detail="切块大小必须大于0")
            
            if overlap < 0 or overlap >= chunk_size:
                logger.error(f"无效的重叠度: {overlap}")
                raise HTTPException(status_code=400, detail="重叠度必须大于等于0且小于切块大小")
            
            # 检查是否有正在进行的任务
            if document_id in CHUNK_TASKS and CHUNK_TASKS[document_id].get("status") == "processing":
                # 返回任务已经在进行中的状态
                return JSONResponse({
                    "status": "processing",
                    "message": "切块任务正在处理中",
                    "task_id": str(document_id)
                })
            
            # 设置文档状态为处理中
            document.status = "处理中"
            db.commit()
            
            # 启动后台任务
            background_tasks.add_task(
                self._process_chunks, 
                document_id, 
                chunk_strategy, 
                chunk_size, 
                overlap
            )
            
            # 初始化任务状态
            CHUNK_TASKS[document_id] = {"status": "processing", "progress": 0}
            
            return JSONResponse({
                "status": "processing",
                "message": "切块任务已开始处理",
                "task_id": str(document_id)
            })
            
        except HTTPException as he:
            # 直接传递HTTP异常
            raise he
        except Exception as e:
            # 处理意外异常
            logger.error(f"未预期的异常: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
    
    def get_chunk_status(self, document_id: int) -> JSONResponse:
        """
        获取切块任务状态
        
        Args:
            document_id: 文档ID
            
        Returns:
            JSONResponse: 任务状态
        """
        if document_id not in CHUNK_TASKS:
            return JSONResponse({"status": "unknown", "message": "未找到相关任务"})
        
        return JSONResponse(CHUNK_TASKS[document_id])
    
    def _process_chunks(self, document_id: int, chunk_strategy: str, chunk_size: int, overlap: int):
        """
        后台处理切块任务
        
        Args:
            document_id: 文档ID
            chunk_strategy: 切块策略名称
            chunk_size: 切块大小
            overlap: 重叠度
        """
        db = next(get_db())
        CHUNK_TASKS[document_id] = {"status": "processing", "progress": 0}
        
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                CHUNK_TASKS[document_id] = {"status": "error", "message": "文档不存在"}
                return
                
            # 检查文件是否存在
            if not os.path.exists(document.filepath):
                CHUNK_TASKS[document_id] = {"status": "error", "message": "文件不存在或已被删除"}
                return
                
            # 设置任务状态为处理中
            CHUNK_TASKS[document_id]["progress"] = 10
            
            # 选择切块策略
            strategy = None
            if chunk_strategy == "word":
                strategy = WordChunkStrategy()
            else:
                CHUNK_TASKS[document_id] = {"status": "error", "message": f"不支持的切块策略: {chunk_strategy}"}
                return
            
            start_time = time.time()
            
            # 获取切块结果
            chunk_results = strategy.chunk_with_metadata(
                document.filepath,
                chunk_size,
                overlap
            )
            
            processing_time = time.time() - start_time
            logger.info(f"切块处理时间: {processing_time:.2f}秒")
            
            CHUNK_TASKS[document_id]["progress"] = 50
            logger.info(f"切块完成，共产生 {len(chunk_results)} 个块")
            
            # 删除现有的切块
            db.query(Chunk).filter(Chunk.document_id == document_id).delete()
            
            # 保存切块参数
            document.last_chunk_params = {
                "strategy": chunk_strategy,
                "size": chunk_size,
                "overlap": overlap
            }
            document.status = "已切块"
            
            # 保存切块结果到数据库
            for i, chunk_data in enumerate(chunk_results, 1):
                chunk = Chunk(
                    document_id=document_id,
                    sequence=i,
                    content=chunk_data["content"],
                    chunk_size=chunk_size,
                    overlap=overlap,
                    chunk_strategy=chunk_strategy,
                    chunk_metadata=chunk_data["meta"]
                )
                db.add(chunk)
                
                # 更新进度
                if i % max(1, len(chunk_results) // 10) == 0:
                    progress = 50 + int(i / len(chunk_results) * 40)
                    CHUNK_TASKS[document_id]["progress"] = min(progress, 90)
            
            db.commit()
            logger.info(f"文档 {document_id} 切块成功保存到数据库")
            CHUNK_TASKS[document_id] = {"status": "success", "progress": 100}
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"切块处理异常: {error_message}")
            logger.error(traceback.format_exc())
            CHUNK_TASKS[document_id] = {"status": "error", "message": f"切块处理失败: {error_message}"}
            
            # 出错时恢复文档状态
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document and document.status == "处理中":
                    document.status = "未切块"
                    db.commit()
            except Exception:
                pass 