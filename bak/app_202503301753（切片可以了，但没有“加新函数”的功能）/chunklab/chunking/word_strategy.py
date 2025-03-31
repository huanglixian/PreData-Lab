from typing import List, Dict, Any
from .base import BaseChunkStrategy
from docx import Document
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WordChunkStrategy(BaseChunkStrategy):
    """Word文档切块策略实现"""
    
    def __init__(self):
        self.current_heading = ""
    
    def chunk(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """
        按照指定大小切分Word文档
        
        Args:
            file_path: Word文档路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            切分后的文本块列表
        """
        # 调用chunk_with_metadata，但只返回内容部分
        chunks_with_meta = self.chunk_with_metadata(file_path, chunk_size, overlap)
        return [chunk["content"] for chunk in chunks_with_meta]
    
    def chunk_with_metadata(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        按照指定大小切分Word文档，返回包含内容和元数据的结果
        
        Args:
            file_path: Word文档路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            包含内容和元数据的文本块列表
        """
        try:
            # 加载Word文档
            doc = Document(file_path)
            
            # 初始化结果
            result_chunks = []
            current_chunk = []
            current_size = 0
            self.current_heading = ""
            
            # 遍历段落
            for para in doc.paragraphs:
                # 跳过空段落
                if not para.text.strip():
                    continue
                
                # 检查是否是标题
                is_heading = False
                try:
                    if para.style.name.startswith('Heading'):
                        is_heading = True
                        self.current_heading = para.text
                        
                        # 如果当前chunk不为空，先输出
                        if current_chunk:
                            result_chunks.append(self._create_chunk(current_chunk, self.current_heading))
                            current_chunk = []
                            current_size = 0
                        
                        # 标题单独成一个块
                        continue
                except Exception:
                    pass  # 样式检测失败，当作普通段落处理
                
                # 处理普通段落
                text = para.text
                
                # 如果添加这个段落会超过chunk_size，且当前chunk不为空，先输出当前chunk
                if current_size + len(text) > chunk_size and current_chunk:
                    result_chunks.append(self._create_chunk(current_chunk, self.current_heading))
                    current_chunk = []
                    current_size = 0
                
                # 如果段落本身就超过chunk_size，分段处理
                if len(text) > chunk_size:
                    # 处理长段落
                    para_chunks = self._chunk_long_text(text, chunk_size, overlap)
                    for p_chunk in para_chunks:
                        result_chunks.append(self._create_chunk([p_chunk], self.current_heading))
                else:
                    # 正常添加段落
                    current_chunk.append(text)
                    current_size += len(text)
            
            # 处理最后一个chunk
            if current_chunk:
                result_chunks.append(self._create_chunk(current_chunk, self.current_heading))
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def _chunk_long_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        将长文本分割成多个块
        
        Args:
            text: 长文本
            chunk_size: 每个块的大小
            overlap: 重叠大小
            
        Returns:
            分割后的文本块列表
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # 避免在单词中间切断
            if end < len(text) and not text[end].isspace():
                # 向后查找空格
                space_pos = text.find(' ', end)
                if space_pos != -1 and space_pos - end < 20:  # 最多向后查找20个字符
                    end = space_pos
            
            chunks.append(text[start:end])
            
            # 考虑重叠
            start = end - overlap if overlap > 0 else end
        
        return chunks
    
    def _create_chunk(self, texts: List[str], heading: str) -> Dict[str, Any]:
        """
        创建包含内容和元数据的块
        
        Args:
            texts: 文本列表
            heading: 当前标题
            
        Returns:
            包含内容和元数据的字典
        """
        return {
            "content": "\n".join(texts),
            "meta": {
                "heading": heading,
                "char_count": sum(len(t) for t in texts)
            }
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取切块策略的元数据
        
        Returns:
            包含策略信息的字典
        """
        return {
            "name": "word",
            "description": "Word文档切块策略，基于标题和指定大小进行切块",
            "supported_types": [".docx"]
        } 