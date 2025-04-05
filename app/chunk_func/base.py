from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Callable

class BaseChunkStrategy(ABC):
    """
    切块策略基类 - 使用二选一实现方式，更加灵活
    
    开发者可以选择实现以下两个方法之一：
    1. chunk_no_meta - 只需返回文本列表（简单）
    2. chunk_with_meta - 返回带元数据的结果（高级）
    
    不需要两个都实现，系统会自动处理。
    """
    
    def __init__(self):
        """初始化时检测实现的方法类型"""
        # 在初始化时检查是否覆盖了其中一个方法
        self._check_implementation()
    
    def _check_implementation(self):
        """检查子类是否正确实现了至少一个切块方法"""
        has_text_impl = self.__class__.chunk_no_meta != BaseChunkStrategy.chunk_no_meta
        has_meta_impl = self.__class__.chunk_with_meta != BaseChunkStrategy.chunk_with_meta
        
        if not (has_text_impl or has_meta_impl):
            raise NotImplementedError(f"策略类 {self.__class__.__name__} 必须实现 chunk_no_meta 或 chunk_with_meta 方法之一")
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """
        将文档分割成多个纯文本块
        
        默认实现：如果子类实现了 chunk_with_meta，则从中提取内容
        
        Args:
            file_path: 文档文件路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            分割后的文本块列表
        """
        # 如果子类实现了带元数据的版本，从中提取文本内容
        chunks_with_meta = self.chunk_with_meta(file_path, chunk_size, overlap)
        return [chunk["content"] for chunk in chunks_with_meta]
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        将文档分割成多个带元数据的文本块
        
        默认实现：如果子类实现了 chunk_no_meta，则为每个块添加空元数据
        
        Args:
            file_path: 文档文件路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            包含内容和元数据的文本块列表
        """
        # 如果子类实现了纯文本版本，为每个文本块添加空元数据
        text_chunks = self.chunk_no_meta(file_path, chunk_size, overlap)
        return [{"content": chunk, "meta": {}} for chunk in text_chunks]
    
    def process_document(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        统一的文档处理方法，由系统调用
        
        这是对外暴露的主要方法，会根据子类实现的方法自动选择调用路径。
        开发者不需要覆盖此方法。
        
        Args:
            file_path: 文档文件路径
            chunk_size: 每个块的大小（字符数）
            overlap: 相邻块之间的重叠字符数
            
        Returns:
            包含内容和元数据的文本块列表
        """
        # 检测子类实现了哪个方法
        has_text_impl = self.__class__.chunk_no_meta != BaseChunkStrategy.chunk_no_meta
        has_meta_impl = self.__class__.chunk_with_meta != BaseChunkStrategy.chunk_with_meta
        
        # 优先使用带元数据的实现
        if has_meta_impl:
            return self.chunk_with_meta(file_path, chunk_size, overlap)
        else:
            # 使用纯文本实现并添加空元数据
            text_chunks = self.chunk_no_meta(file_path, chunk_size, overlap)
            return [{"content": chunk, "meta": {}} for chunk in text_chunks]
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取切块策略的元数据
        
        Returns:
            包含策略名称、描述和支持的文件类型的字典
        """
        pass 