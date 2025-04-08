#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试Excel合并单元格处理
"""

import pandas as pd
import numpy as np
import logging
import json
import os
import sys

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("excel_test")

def test_excel_processing(file_path):
    """测试处理Excel文件，重点关注合并单元格"""
    
    logger.info(f"测试文件: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return
    
    try:
        # 读取Excel文件
        logger.info("使用pandas读取文件...")
        df = pd.read_excel(file_path, header=0)
        
        # 查看原始数据
        logger.info("\n====== 原始数据 ======")
        logger.info(f"数据形状: {df.shape}")
        logger.info(f"列名: {df.columns.tolist()}")
        logger.info(f"前5行数据:\n{df.head().to_string()}")
        
        # 检查NaN
        nan_count = df.isna().sum().sum()
        logger.info(f"NaN值总数: {nan_count}")
        for col in df.columns:
            col_nan = df[col].isna().sum()
            if col_nan > 0:
                logger.info(f"列 '{col}' 有 {col_nan} 个NaN值")
        
        # 应用前向填充
        logger.info("\n====== 前向填充后 ======")
        filled_df = df.fillna(method='ffill')
        logger.info(f"前5行数据:\n{filled_df.head().to_string()}")
        
        # 检查填充后的NaN
        nan_count_after = filled_df.isna().sum().sum()
        logger.info(f"填充后NaN值总数: {nan_count_after}")
        
        # 转换为JSON
        logger.info("\n====== 转换为JSON ======")
        rows = []
        for index, row in filled_df.iterrows():
            row_dict = {}
            for col_name in filled_df.columns:
                value = row[col_name]
                if pd.isna(value):
                    row_dict[col_name] = None
                elif isinstance(value, (np.integer, np.floating)):
                    row_dict[col_name] = float(value) if np.issubdtype(type(value), np.floating) else int(value)
                else:
                    row_dict[col_name] = value
            
            # 转换为JSON
            json_str = json.dumps(row_dict, ensure_ascii=False, indent=2, default=str)
            logger.info(f"行 {index} JSON:\n{json_str}")
            rows.append(row_dict)
        
        logger.info(f"共处理 {len(rows)} 行数据")
        return rows
        
    except Exception as e:
        logger.error(f"处理Excel文件时发生错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python test_excel_reader.py <excel_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    test_excel_processing(file_path) 