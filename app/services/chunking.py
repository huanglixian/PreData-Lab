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
from ..config import get_config
from ..chunk_func.base import BaseChunkStrategy
from ..chunk_func.word_strategy import WordChunkStrategy

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
        """创建切块任务"""
        try:
            logger.info(f"开始切块处理: document_id={document_id}, strategy={chunk_strategy}, size={chunk_size}, overlap={overlap}")
            
            # 检查文档是否存在
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail="文档不存在")
            
            # 检查文件是否存在
            if not os.path.exists(document.filepath):
                raise HTTPException(status_code=400, detail="文件不存在或已被删除")
            
            # 检查切块参数
            valid_strategies = [s['name'] for s in get_config('CHUNK_STRATEGIES')]
            if chunk_strategy not in valid_strategies:
                raise HTTPException(status_code=400, detail="无效的切块策略")
            
            if chunk_size <= 0:
                raise HTTPException(status_code=400, detail="切块大小必须大于0")
            
            if overlap < 0 or overlap >= chunk_size:
                raise HTTPException(status_code=400, detail="重叠度必须大于等于0且小于切块大小")
            
            # 检查是否有正在进行的任务
            if document_id in CHUNK_TASKS and CHUNK_TASKS[document_id].get("status") == "processing":
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
            raise he
        except Exception as e:
            logger.error(f"未预期的异常: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
    
    def get_chunk_status(self, document_id: int) -> JSONResponse:
        """获取切块任务状态"""
        if document_id not in CHUNK_TASKS:
            return JSONResponse({"status": "unknown", "message": "未找到相关任务"})
        
        return JSONResponse(CHUNK_TASKS[document_id])
    
    def _process_chunks(self, document_id: int, chunk_strategy: str, chunk_size: int, overlap: int):
        """后台处理切块任务"""
        db = next(get_db())
        CHUNK_TASKS[document_id] = {"status": "processing", "progress": 0}
        
        try:
            # 检查文档和文件
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document or not os.path.exists(document.filepath):
                error_msg = "文档不存在" if not document else "文件不存在或已被删除"
                CHUNK_TASKS[document_id] = {"status": "error", "message": error_msg}
                return
            
            # 更新进度
            CHUNK_TASKS[document_id]["progress"] = 10
            
            # 选择切块策略
            strategy = self._get_strategy_instance(chunk_strategy)
            if not strategy:
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
            chunk_count = len(chunk_results)
            update_interval = max(1, chunk_count // 5)  # 每20%更新一次进度
            
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
                
                # 更新进度
                if i % update_interval == 0:
                    progress = 50 + int(i / chunk_count * 40)
                    CHUNK_TASKS[document_id]["progress"] = min(progress, 90)
            
            db.commit()
            CHUNK_TASKS[document_id] = {"status": "success", "progress": 100}
        
        except Exception as e:
            logger.error(f"切块处理异常: {str(e)}")
            logger.error(traceback.format_exc())
            CHUNK_TASKS[document_id] = {"status": "error", "message": f"切块处理失败: {str(e)}"}
            
            # 出错时恢复文档状态
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document and document.status == "处理中":
                    document.status = "未切块"
                    db.commit()
            except Exception:
                pass

    def _get_strategy_instance(self, strategy_name: str) -> BaseChunkStrategy:
        """获取策略实例"""
        # 如果是内置策略直接返回
        if strategy_name == "word":
            return WordChunkStrategy()
            
        # 获取所有可用策略
        strategies = get_config('CHUNK_STRATEGIES')
        
        # 寻找匹配的策略
        for strategy_meta in strategies:
            if strategy_meta.get('name') == strategy_name:
                module_path = f"app.chunk_func.{strategy_name}_strategy"
                
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
                    
        return None 