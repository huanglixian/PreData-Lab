from typing import List, Dict, Any
import sys
import os
sys.path.append(os.path.abspath('.'))  # 添加当前目录到路径
from app.chunk_func.base import BaseChunkStrategy

class TestChunkStrategy(BaseChunkStrategy):
    """测试切块策略"""
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """简单切块方法"""
        chunks = ["测试文本块1", "测试文本块2"]
        return chunks
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取元数据"""
        return {
            "name": "test",
            "display_name": "测试切块策略",
            "description": "用于测试上传功能的策略",
            "supported_types": [".txt", ".md"]
        } 