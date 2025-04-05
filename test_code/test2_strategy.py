from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging
import re

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test2ChunkStrategy(BaseChunkStrategy):
    """测试策略2 - 句子分割"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按句子分割并提供元数据"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 分割句子 (中英文标点都考虑)
            sentence_ends = r'(?<=[.。!！?？;；])\s*'
            sentences = re.split(sentence_ends, text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # 组合句子到块
            result_chunks = []
            current_sentences = []
            current_size = 0
            current_position = 0
            
            for sentence in sentences:
                sentence_size = len(sentence)
                
                # 如果单句超过块大小
                if sentence_size > chunk_size:
                    # 处理现有累积
                    if current_sentences:
                        content = ' '.join(current_sentences)
                        result_chunks.append({
                            "content": content,
                            "meta": {
                                "start_position": current_position - len(content),
                                "end_position": current_position,
                                "sentence_count": len(current_sentences)
                            }
                        })
                        current_sentences = []
                        current_size = 0
                    
                    # 处理大句子
                    start = 0
                    while start < len(sentence):
                        end = min(start + chunk_size, len(sentence))
                        chunk_text = sentence[start:end]
                        result_chunks.append({
                            "content": chunk_text,
                            "meta": {
                                "start_position": current_position + start,
                                "end_position": current_position + end,
                                "sentence_count": 1,
                                "is_partial": True
                            }
                        })
                        start = end - overlap if overlap > 0 else end
                    
                    current_position += len(sentence)
                else:
                    # 检查是否需要新建块
                    if current_size + sentence_size > chunk_size and current_sentences:
                        content = ' '.join(current_sentences)
                        result_chunks.append({
                            "content": content,
                            "meta": {
                                "start_position": current_position - len(content),
                                "end_position": current_position,
                                "sentence_count": len(current_sentences)
                            }
                        })
                        current_sentences = []
                        current_size = 0
                    
                    current_sentences.append(sentence)
                    current_size += sentence_size
                    current_position += sentence_size
            
            # 最后一块
            if current_sentences:
                content = ' '.join(current_sentences)
                result_chunks.append({
                    "content": content,
                    "meta": {
                        "start_position": current_position - len(content),
                        "end_position": current_position,
                        "sentence_count": len(current_sentences)
                    }
                })
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "name": "test2",
            "display_name": "测试策略2-句子分割",
            "description": "按句子分割文本，带句子数量和位置元数据",
            "supported_types": [".txt", ".md", ".json"]
        } 