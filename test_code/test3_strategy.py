from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test3ChunkStrategy(BaseChunkStrategy):
    """测试策略3 - JSON解析分割"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """解析JSON并按对象分割"""
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result_chunks = []
            
            # 如果是对象列表
            if isinstance(data, list):
                for i, item in enumerate(data):
                    item_str = json.dumps(item, ensure_ascii=False)
                    
                    # 如果单项超过块大小，尝试分解
                    if len(item_str) > chunk_size and isinstance(item, dict):
                        # 分解大对象
                        sub_items = []
                        current_sub = {}
                        current_size = 0
                        
                        for key, value in item.items():
                            value_str = json.dumps({key: value}, ensure_ascii=False)
                            if current_size + len(value_str) > chunk_size and current_sub:
                                sub_items.append(current_sub)
                                current_sub = {}
                                current_size = 0
                                
                            current_sub[key] = value
                            current_size += len(value_str)
                        
                        if current_sub:
                            sub_items.append(current_sub)
                        
                        # 为每个子项创建块
                        for j, sub_item in enumerate(sub_items):
                            sub_str = json.dumps(sub_item, ensure_ascii=False)
                            result_chunks.append({
                                "content": sub_str,
                                "meta": {
                                    "item_index": i,
                                    "sub_index": j,
                                    "is_partial": True,
                                    "total_parts": len(sub_items)
                                }
                            })
                    else:
                        # 直接作为一个块
                        result_chunks.append({
                            "content": item_str,
                            "meta": {
                                "item_index": i,
                                "is_partial": False
                            }
                        })
            
            # 如果是单个对象
            elif isinstance(data, dict):
                # 按键分割
                for i, (key, value) in enumerate(data.items()):
                    value_str = json.dumps({key: value}, ensure_ascii=False)
                    result_chunks.append({
                        "content": value_str,
                        "meta": {
                            "key": key,
                            "index": i
                        }
                    })
            
            # 其他情况当作一个块
            else:
                data_str = json.dumps(data, ensure_ascii=False)
                result_chunks.append({
                    "content": data_str,
                    "meta": {
                        "type": type(data).__name__
                    }
                })
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "name": "test3",
            "display_name": "测试策略3-JSON解析",
            "description": "解析JSON文件并按对象分割，提供结构元数据",
            "supported_types": [".json"]
        } 