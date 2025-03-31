# 切块策略包初始化文件 
import os
import importlib
import inspect
from typing import List, Dict, Any

from .base import BaseChunkStrategy
from .word_strategy import WordChunkStrategy

def list_strategies() -> List[Dict[str, Any]]:
    """
    列出所有可用的切块策略
    
    Returns:
        切块策略元数据列表
    """
    strategies = []
    
    # 获取当前目录下的所有Python文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for file in os.listdir(current_dir):
        if file.endswith('_strategy.py'):
            # 导入模块
            module_name = file[:-3]  # 去掉.py后缀
            module_path = f"app.chunklab.chunking.{module_name}"
            
            try:
                module = importlib.import_module(module_path)
                
                # 查找继承自BaseChunkStrategy的类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseChunkStrategy) and 
                        obj is not BaseChunkStrategy):
                        
                        # 实例化策略并获取元数据
                        strategy = obj()
                        metadata = strategy.get_metadata()
                        
                        # 添加显示名称
                        if 'name' in metadata and 'display_name' not in metadata:
                            metadata['display_name'] = metadata['name'].capitalize() + " 切块策略"
                        
                        strategies.append(metadata)
            except Exception as e:
                print(f"加载切块策略模块 {module_name} 时出错: {str(e)}")
    
    return strategies

# 切块策略模块 