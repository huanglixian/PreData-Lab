from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateChunkStrategy(BaseChunkStrategy):
    """示例切块策略 - 可以复制此文件作为您自己策略的起点"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    # ============================================================================
    # 二选一：请选择下面两个方法中的一个实现（删除或注释掉另一个）
    # ============================================================================
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """
        方法一：返回纯文本块列表（简单方式）
        
        当您只需要将文档分割成多个文本块，不需要额外元数据时，实现此方法
        """
        try:
            # 读取文件（根据您的需求修改此部分）
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 切分文本
            chunks = []
            start = 0
            
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end].strip()  # 确保切块不为空
                if chunk:  # 只添加非空切块
                    chunks.append(chunk)
                start = end - overlap if overlap > 0 else end
            
            # 返回格式: 字符串列表 ["块1内容", "块2内容", ...]
            return chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        方法二：返回带元数据的文本块列表（高级方式）
        
        当您需要为每个文本块添加额外信息（如位置、标题等）时，实现此方法
        """
        try:
            # 读取文件（根据您的需求修改此部分）
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 切分文本并添加元数据
            result_chunks = []
            start = 0
            
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end].strip()  # 确保切块不为空
                
                if chunk_text:  # 只添加非空切块
                    # 添加元数据（根据您的需求修改）
                    result_chunks.append({
                        "content": chunk_text,  # 文本内容
                        "meta": {               # 元数据
                            "start_position": start,
                            "end_position": end,
                            "char_count": len(chunk_text)
                            # 您可以添加任何其他需要的元数据
                        }
                    })
                
                start = end - overlap if overlap > 0 else end
            
            # 返回格式: [{"content": "块1内容", "meta": {元数据1}}, {"content": "块2内容", "meta": {元数据2}}, ...]
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    # ============================================================================
    # 必须实现的方法
    # ============================================================================
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取切块策略的元数据（必须实现）
        
        Returns:
            包含策略信息的字典
        """
        return {
            "name": "template",             # 必需：策略的唯一标识符
            "display_name": "模板切块策略",  # 可选：在UI中显示的名称
            "description": "这是一个示例策略，供开发者参考", # 可选：描述
            "supported_types": [".txt", ".md", ".json"]  # 可选：支持的文件类型
        } 