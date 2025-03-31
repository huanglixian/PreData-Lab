from typing import List, Dict, Any
from .base import BaseChunkStrategy
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextChunkStrategy(BaseChunkStrategy):
    """纯文本文件切块策略实现 - 超简单实现"""
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """简单切块方法"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end])
                start = end
            return chunks
        except Exception as e:
            logger.error(f"切块失败: {e}")
            return ["切块失败"]
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        return {
            "name": "text",
            "display_name": "纯文本切块策略",
            "description": "最简单的文本切块策略",
            "supported_types": [".txt"]
        } 