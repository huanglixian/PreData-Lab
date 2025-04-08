from typing import List, Dict, Any
from .base import BaseChunkStrategy
import pandas as pd
import json
import logging
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelDictChunkStrategy(BaseChunkStrategy):
    """Excel转字典切块策略，每行作为一个切片"""
    
    def __init__(self):
        super().__init__()  # 调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        将Excel文件按行转换为字典列表，每行作为一个切片
        
        Args:
            file_path: Excel文件路径
            chunk_size: 忽略此参数
            overlap: 忽略此参数
            
        Returns:
            包含内容和元数据的文本块列表
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 检查文件扩展名
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in ['.xlsx', '.xls', '.csv']:
                raise ValueError(f"不支持的文件类型: {file_ext}")
            
            logger.info(f"开始处理Excel文件: {file_path}")
            
            # 读取Excel文件
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # 检查数据是否为空
            if df.empty:
                logger.warning(f"Excel文件为空: {file_path}")
                return []
            
            # 获取列名
            columns = df.columns.tolist()
            
            # 转换为字典列表
            result_chunks = []
            for index, row in df.iterrows():
                # 将行转换为字典
                row_dict = row.to_dict()
                
                # 将字典转换为JSON字符串作为内容
                content = json.dumps(row_dict, ensure_ascii=False, indent=2)
                
                # 添加元数据
                result_chunks.append({
                    "content": content,
                    "meta": {
                        "row_index": index,
                        "columns": columns,
                        "file_name": os.path.basename(file_path),
                        "sheet_name": getattr(df, 'name', 'Sheet1')
                    }
                })
            
            logger.info(f"已成功处理Excel文件，共生成 {len(result_chunks)} 个切片")
            return result_chunks
            
        except Exception as e:
            logger.error(f"Excel切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取切块策略的元数据
        
        Returns:
            包含策略信息的字典
        """
        return {
            "name": "excel_dict",
            "display_name": "Excel转字典切块策略",
            "description": "将Excel文件按行转换为字典，每行作为一个切片，忽略切块大小和重叠度",
            "supported_types": [".xlsx", ".xls", ".csv"]
        } 