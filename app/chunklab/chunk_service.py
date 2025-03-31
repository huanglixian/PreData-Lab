from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import traceback
import os
import time
import importlib
import inspect

from ..database import Document, Chunk, get_db
from ..config import APP_CONFIG, get_config
from .chunking.base import BaseChunkStrategy
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
            logger.info(f"开始处理文档 {document_id} 的切块任务: strategy={chunk_strategy}, size={chunk_size}, overlap={overlap}")
            
            # 检查文档和文件
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document or not os.path.exists(document.filepath):
                error_msg = "文档不存在" if not document else "文件不存在或已被删除"
                logger.error(f"文档 {document_id} {error_msg}")
                CHUNK_TASKS[document_id] = {"status": "error", "message": error_msg}
                return
            
            # 设置任务状态为处理中
            CHUNK_TASKS[document_id]["progress"] = 10
            
            # 选择切块策略
            strategy = self._get_strategy_instance(chunk_strategy)
            if not strategy:
                logger.error(f"不支持的切块策略: {chunk_strategy}")
                CHUNK_TASKS[document_id] = {"status": "error", "message": f"不支持的切块策略: {chunk_strategy}"}
                return
            
            # 执行切块处理
            start_time = time.time()
            chunk_results = strategy.process_document(document.filepath, chunk_size, overlap)
            processing_time = time.time() - start_time
            
            logger.info(f"切块处理完成，耗时: {processing_time:.2f}秒，共产生 {len(chunk_results)} 个块")
            CHUNK_TASKS[document_id]["progress"] = 50
            
            # 保存结果
            db.query(Chunk).filter(Chunk.document_id == document_id).delete()
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
                    chunk_metadata=chunk_data.get("meta", {})
                )
                db.add(chunk)
                
                # 每处理20%的块更新一次进度
                if i % max(1, len(chunk_results) // 5) == 0:
                    progress = 50 + int(i / len(chunk_results) * 40)
                    CHUNK_TASKS[document_id]["progress"] = min(progress, 90)
            
            db.commit()
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

    def _get_strategy_instance(self, strategy_name: str) -> BaseChunkStrategy:
        """
        根据策略名称获取策略实例
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略实例，如果找不到返回None
        """
        # 获取所有可用策略
        strategies = get_config('CHUNK_STRATEGIES')
        
        # 寻找匹配的策略
        for strategy_meta in strategies:
            if strategy_meta.get('name') == strategy_name:
                # 根据策略名称构建类名
                class_name = f"{strategy_name.capitalize()}ChunkStrategy"
                module_path = f"app.chunklab.chunking.{strategy_name}_strategy"
                
                try:
                    # 动态导入模块
                    module = importlib.import_module(module_path)
                    
                    # 查找策略类
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseChunkStrategy) and 
                            obj is not BaseChunkStrategy):
                            return obj()
                            
                except Exception as e:
                    logger.error(f"加载切块策略 {strategy_name} 时出错: {str(e)}")
                    
        # 如果是内置策略
        if strategy_name == "word":
            return WordChunkStrategy()
            
        return None 