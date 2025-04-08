from typing import List, Dict, Any
from .base import BaseChunkStrategy
import pandas as pd
import numpy as np
import json
import os

class ExcelDictChunkStrategy(BaseChunkStrategy):
    """Excel转字典切块策略，每行作为一个切片"""
    
    def __init__(self):
        super().__init__()
    
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
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ['.xlsx', '.xls', '.csv']:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        # 读取Excel文件
        df = pd.read_csv(file_path) if file_ext == '.csv' else pd.read_excel(file_path)
        if df.empty:
            return []
        
        # 处理合并单元格
        df_filled = df.fillna(method='ffill')
        
        # 转换为字典列表
        return [
            {
                "content": json.dumps(
                    {
                        col: (
                            float(val) if isinstance(val, (np.integer, np.floating)) 
                            else str(val) if pd.isna(val)  # 将NaN转换为字符串"NaN"
                            else val
                        )
                        for col, val in row.items()
                    },
                    ensure_ascii=False,
                    indent=2
                ),
                "meta": {
                    "file_name": os.path.basename(file_path),
                    "row_index": index + 1  # Excel行号从1开始
                }
            }
            for index, row in df_filled.iterrows()
        ]
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取切块策略的元数据"""
        return {
            "name": "excel_normal",
            "display_name": "Excel转字典通用策略",
            "description": "将Excel文件按行转换为字典，每行作为一个切片，忽略切块大小和重叠度",
            "supported_types": [".xlsx", ".xls", ".csv"]
        } 