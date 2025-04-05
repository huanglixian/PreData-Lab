from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test1ChunkStrategy(BaseChunkStrategy):
    """测试策略1 - 段落分割"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """按段落分割文本"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 按段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            # 将段落组合成指定大小的块
            chunks = []
            current_chunk = []
            current_size = 0
            
            for para in paragraphs:
                para_size = len(para)
                
                # 如果段落自身超过块大小，需要单独处理
                if para_size > chunk_size:
                    # 先处理现有累积
                    if current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # 处理大段落
                    start = 0
                    while start < len(para):
                        end = min(start + chunk_size, len(para))
                        chunks.append(para[start:end])
                        start = end - overlap if overlap > 0 else end
                else:
                    # 检查是否需要新建块
                    if current_size + para_size > chunk_size and current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    current_chunk.append(para)
                    current_size += para_size
            
            # 别忘了最后一块
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            return chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "name": "test1",
            "display_name": "测试策略1-段落分割",
            "description": "按段落分割文本，并根据大小限制合并段落",
            "supported_types": [".txt", ".md"]
        } 