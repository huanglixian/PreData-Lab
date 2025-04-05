from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging
import csv
import io

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test5ChunkStrategy(BaseChunkStrategy):
    """测试策略5 - CSV智能分割"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """智能分割CSV文件，保持表头"""
        try:
            # 读取CSV文件
            with open(file_path, 'r', encoding='utf-8') as f:
                # 先读取所有内容
                content = f.read()
                f.seek(0)  # 重置文件指针
                
                # 使用csv模块解析
                reader = csv.reader(f)
                all_rows = list(reader)
            
            # 如果文件为空或只有表头
            if not all_rows or len(all_rows) <= 1:
                return [{
                    "content": content,
                    "meta": {
                        "row_count": len(all_rows),
                        "is_empty": len(all_rows) == 0
                    }
                }]
            
            # 提取表头和数据行
            header = all_rows[0]
            data_rows = all_rows[1:]
            
            # 计算每行的平均大小
            avg_row_size = sum(len(','.join(row)) for row in data_rows) / len(data_rows)
            
            # 计算每个块可以容纳的行数
            rows_per_chunk = max(1, int(chunk_size / avg_row_size))
            
            # 分割数据成多个块
            result_chunks = []
            
            # 处理每个块
            for i in range(0, len(data_rows), rows_per_chunk):
                # 获取当前块的行
                chunk_rows = data_rows[i:i + rows_per_chunk]
                
                # 创建带表头的CSV块
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(header)
                writer.writerows(chunk_rows)
                
                chunk_content = output.getvalue()
                
                # 添加到结果
                result_chunks.append({
                    "content": chunk_content,
                    "meta": {
                        "start_row": i + 1,  # +1是因为0行是表头
                        "end_row": i + len(chunk_rows),
                        "row_count": len(chunk_rows),
                        "includes_header": True,
                        "column_count": len(header)
                    }
                })
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "name": "test5",
            "display_name": "测试策略5-CSV智能分割",
            "description": "智能分割CSV文件，每个块都保留表头行，提供行列元数据",
            "supported_types": [".csv", ".tsv"]
        } 