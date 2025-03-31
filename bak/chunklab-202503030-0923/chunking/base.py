from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseChunkStrategy(ABC):
    """切块策略基类"""
    
    @abstractmethod
    def chunk(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """
        将文档分割成多个文本块
        
        Args:
            file_path: 文档文件路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            分割后的文本块列表
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取切块策略的元数据
        
        Returns:
            包含策略名称、描述和支持的文件类型的字典
        """
        pass 