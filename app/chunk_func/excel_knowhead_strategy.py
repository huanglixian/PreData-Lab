from typing import List, Dict, Any
import pandas as pd
import json
import logging
import os
import numpy as np
from .base import BaseChunkStrategy

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelKnowHeadStrategy(BaseChunkStrategy):
    """Excel智能表头识别切块策略，能够自动识别真正的表头位置"""
    
    def __init__(self):
        super().__init__()
    
    def _detect_header_row(self, df_sample: pd.DataFrame, max_rows: int = 20) -> int:
        """
        检测真正的表头行位置
        
        Args:
            df_sample: 数据帧样本
            max_rows: 最多检查的行数
            
        Returns:
            表头行索引
        """
        num_rows = min(max_rows, df_sample.shape[0])
        if num_rows <= 1:
            return 0
            
        # 计算每行的数字比例
        numeric_ratios = []
        for i in range(num_rows):
            row = df_sample.iloc[i]
            numeric_count = sum(isinstance(x, (int, float, np.integer, np.floating)) 
                              for x in row if not pd.isna(x))
            total_count = sum(1 for x in row if not pd.isna(x))
            ratio = numeric_count / total_count if total_count > 0 else 0
            numeric_ratios.append(ratio)
        
        # 寻找第一个数字比例显著增加的行
        for i in range(num_rows - 1):
            if numeric_ratios[i] < 0.3 and numeric_ratios[i+1] > 0.5:
                logger.info(f"检测到表头在第 {i} 行")
                return i
        
        return 0
        
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """
        将Excel文件按行转换为字典列表，自动识别表头
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in ['.xlsx', '.xls', '.csv']:
                raise ValueError(f"不支持的文件类型: {file_ext}")
            
            # 读取前20行用于表头检测
            df_sample = pd.read_csv(file_path, nrows=20) if file_ext == '.csv' else pd.read_excel(file_path, nrows=20)
            header_row = self._detect_header_row(df_sample)
            
            # 重新读取文件，使用检测到的表头
            df = pd.read_csv(file_path, header=header_row) if file_ext == '.csv' else pd.read_excel(file_path, header=header_row)
            
            if df.empty:
                return []
            
            # 转换为字典列表
            result_chunks = []
            for index, row in df.iterrows():
                row_dict = {k: "" if pd.isna(v) else v for k, v in row.to_dict().items()}
                # 使用indent参数使JSON格式化，每个键值对占一行
                result_chunks.append({
                    "content": json.dumps(row_dict, ensure_ascii=False, indent=2),
                    "meta": {
                        "row_index": int(index),
                        "columns": df.columns.tolist(),
                        "file_name": os.path.basename(file_path),
                        "sheet_name": getattr(df, 'name', 'Sheet1'),
                        "header_row": header_row
                    }
                })
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"Excel切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "excel_knowhead",
            "display_name": "Excel智能表头识别切块策略",
            "description": "自动识别Excel真正的表头位置，将每行数据转换为键值对形式的切片",
            "supported_types": [".xlsx", ".xls", ".csv"]
        }