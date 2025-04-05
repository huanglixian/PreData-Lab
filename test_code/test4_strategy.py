from typing import List, Dict, Any
from app.chunk_func.base import BaseChunkStrategy
import logging
import re

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test4ChunkStrategy(BaseChunkStrategy):
    """测试策略4 - 代码分割"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按函数/类/代码块分割"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 识别Python代码结构
            # 简单起见，我们按以下规则分割：
            # 1. 函数定义（以def开头的行）
            # 2. 类定义（以class开头的行）
            # 3. 顶层代码块（其他代码）
            
            # 匹配函数和类定义
            pattern = r'((?:^\s*(?:def|class)\s+\w+.*?:)(?:.*?)(?=^\s*(?:def|class)\s+\w+.*?:|$))'
            matches = re.finditer(pattern, code, re.MULTILINE | re.DOTALL)
            
            # 提取所有函数和类定义
            definitions = []
            for match in matches:
                definitions.append((match.start(), match.end(), match.group(0)))
            
            # 如果没有找到任何定义，则返回整个文件
            if not definitions:
                return [{
                    "content": code,
                    "meta": {
                        "type": "full_file",
                        "line_count": code.count('\n') + 1
                    }
                }]
            
            # 处理每个定义块
            result_chunks = []
            code_lines = code.split('\n')
            
            for i, (start, end, content) in enumerate(definitions):
                # 找出行号范围
                start_line = code[:start].count('\n') + 1
                end_line = start_line + content.count('\n')
                
                # 提取函数/类名称
                first_line = content.split('\n')[0].strip()
                match = re.match(r'(?:def|class)\s+(\w+)', first_line)
                name = match.group(1) if match else f"block_{i}"
                
                # 检查是否需要拆分大块
                if len(content) > chunk_size:
                    # 按行分割大块
                    block_lines = content.split('\n')
                    current_lines = []
                    current_size = 0
                    part = 1
                    
                    for line in block_lines:
                        line_size = len(line) + 1  # +1 for newline
                        
                        if current_size + line_size > chunk_size and current_lines:
                            # 创建当前子块
                            sub_content = '\n'.join(current_lines)
                            result_chunks.append({
                                "content": sub_content,
                                "meta": {
                                    "type": "code_block",
                                    "name": name,
                                    "part": part,
                                    "is_partial": True,
                                    "line_range": f"{start_line}-{end_line}"
                                }
                            })
                            part += 1
                            current_lines = []
                            current_size = 0
                        
                        current_lines.append(line)
                        current_size += line_size
                    
                    # 最后一个子块
                    if current_lines:
                        sub_content = '\n'.join(current_lines)
                        result_chunks.append({
                            "content": sub_content,
                            "meta": {
                                "type": "code_block",
                                "name": name,
                                "part": part,
                                "is_partial": True,
                                "line_range": f"{start_line}-{end_line}"
                            }
                        })
                else:
                    # 整块添加
                    result_chunks.append({
                        "content": content,
                        "meta": {
                            "type": "code_block",
                            "name": name,
                            "is_partial": False,
                            "line_range": f"{start_line}-{end_line}"
                        }
                    })
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"切块过程中发生错误: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "name": "test4",
            "display_name": "测试策略4-代码分割",
            "description": "按函数和类定义分割代码文件，提供代码结构元数据",
            "supported_types": [".py", ".js", ".java", ".cpp", ".c"]
        } 