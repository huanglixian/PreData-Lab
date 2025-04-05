import importlib.util
import inspect
import logging
import os
import time
from pathlib import Path

from ..chunk_func.base import BaseChunkStrategy
from ..config import get_config, STRATEGY_DIR, DOCS_DIR

# 配置日志
logger = logging.getLogger(__name__)

# 系统内置的策略，不允许删除
BUILTIN_STRATEGIES = ['text', 'word', 'excel_dict']


def get_documentation_content(doc_type):
    """获取文档内容（模板或指南）"""
    if doc_type == "template":
        file_path = DOCS_DIR / "template_strategy.py"
        title = "策略模板示例"
    elif doc_type == "guide":
        file_path = DOCS_DIR / "Chunk_Strategy_Guide.md"
        title = "切块策略开发指南"
    else:
        return None, None, "请求的文档类型不存在"
    
    if not os.path.exists(file_path):
        return None, None, f"文档文件 {file_path.name} 不存在"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return title, content, None


async def validate_and_save_strategy(file_content, filename):
    """验证并保存切块策略文件"""
    try:
        # 验证文件名和扩展名
        if not filename.endswith('.py'):
            return None, "只接受Python文件(.py)"
        
        # 验证文件名必须以_strategy.py结尾
        if not filename.endswith('_strategy.py'):
            return None, "文件名必须以_strategy.py结尾"
        
        # 把二进制内容转为字符串
        file_content_str = file_content.decode('utf-8')
        
        # 验证文件内容是否包含正确的基类继承
        if "BaseChunkStrategy" not in file_content_str and "class" not in file_content_str:
            return None, "文件必须包含类定义并继承自BaseChunkStrategy"
        
        # 创建临时文件以导入模块
        temp_dir = Path("temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = temp_dir / f"temp_strategy_{int(time.time())}.py"
        with open(temp_file, 'wb') as f:
            f.write(file_content)
        
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("temp_strategy", temp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找模块中的策略类
            strategy_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseChunkStrategy) and 
                    obj is not BaseChunkStrategy):
                    strategy_class = obj
                    break
            
            if not strategy_class:
                os.remove(temp_file)
                return None, "文件中未找到有效的切块策略类，必须继承自BaseChunkStrategy"
            
            # 验证策略类是否实现了必要的方法
            has_chunk_no_meta = hasattr(strategy_class, 'chunk_no_meta') and callable(getattr(strategy_class, 'chunk_no_meta'))
            has_chunk_with_meta = hasattr(strategy_class, 'chunk_with_meta') and callable(getattr(strategy_class, 'chunk_with_meta'))
            has_get_metadata = hasattr(strategy_class, 'get_metadata') and callable(getattr(strategy_class, 'get_metadata'))
            
            # 根据指南要求，必须实现get_metadata，并且chunk_no_meta和chunk_with_meta至少实现一个
            if not has_get_metadata:
                os.remove(temp_file)
                return None, "策略类必须实现get_metadata方法"
            
            if not (has_chunk_no_meta or has_chunk_with_meta):
                os.remove(temp_file)
                return None, "策略类必须实现chunk_no_meta或chunk_with_meta方法之一"
            
            # 实例化策略以获取元数据
            strategy = strategy_class()
            metadata = strategy.get_metadata()
            
            # 验证元数据格式是否符合指南要求
            if not isinstance(metadata, dict):
                os.remove(temp_file)
                return None, "get_metadata方法必须返回字典类型"
            
            # 验证元数据
            if not metadata.get('name'):
                os.remove(temp_file)
                return None, "策略元数据必须提供name属性"
            
            if not metadata.get('display_name'):
                os.remove(temp_file)
                return None, "策略元数据必须提供display_name属性"
            
            # 验证supported_types格式（如果存在）
            if 'supported_types' in metadata and not isinstance(metadata['supported_types'], list):
                os.remove(temp_file)
                return None, "supported_types必须是文件扩展名列表"
            
            # 从元数据中获取策略名称
            strategy_name = metadata.get('name')
            
            # 确保策略名称是有效的Python标识符
            if not strategy_name.isidentifier():
                os.remove(temp_file)
                return None, "策略名称必须是有效的Python标识符"
            
            # 确保策略名称不是内置策略
            if strategy_name in BUILTIN_STRATEGIES:
                os.remove(temp_file)
                return None, f"不能覆盖内置策略: {strategy_name}"
            
            # 使用上传的文件名
            target_filename = filename
            target_path = STRATEGY_DIR / target_filename
            
            # 检查文件是否已存在
            if os.path.exists(target_path):
                os.remove(temp_file)
                return None, f"策略文件 {target_filename} 已存在"
            
            # 将临时文件移动到最终位置
            with open(temp_file, 'r', encoding='utf-8') as f:
                file_content_str = f.read()
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(file_content_str)
            
            # 清理临时文件
            os.remove(temp_file)
            
            result = {
                "strategy_name": strategy_name,
                "filename": target_filename
            }
            
            return result, None
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
            logger.error(f"验证策略文件时出错: {str(e)}")
            return None, f"策略文件验证失败: {str(e)}"
    
    except Exception as e:
        logger.error(f"处理策略文件失败: {str(e)}")
        return None, f"处理失败: {str(e)}"


def get_strategy_content(strategy_name):
    """获取策略文件内容和元数据"""
    target_filename = f"{strategy_name}_strategy.py"
    target_path = STRATEGY_DIR / target_filename
    
    if not os.path.exists(target_path):
        return None, None, f"策略文件 {target_filename} 不存在"
    
    # 读取文件内容
    with open(target_path, 'r', encoding='utf-8') as f:
        strategy_content = f.read()
    
    # 获取策略元数据
    try:
        strategies = get_config('CHUNK_STRATEGIES')
        metadata = None
        for strategy in strategies:
            if strategy.get('name') == strategy_name:
                metadata = strategy
                break
    except Exception as e:
        metadata = {"name": strategy_name, "error": str(e)}
    
    return strategy_name, strategy_content, metadata


def delete_strategy(strategy_name):
    """删除策略文件"""
    # 不允许删除内置策略
    if strategy_name in BUILTIN_STRATEGIES:
        return False, f"不能删除内置策略: {strategy_name}"
    
    # 构建文件路径
    target_filename = f"{strategy_name}_strategy.py"
    target_path = STRATEGY_DIR / target_filename
    
    # 检查文件是否存在
    if not os.path.exists(target_path):
        return False, f"策略文件 {target_filename} 不存在"
    
    try:
        # 删除文件
        os.remove(target_path)
        logger.info(f"成功删除策略文件: {target_filename}")
        return True, "策略文件已删除"
    except Exception as e:
        logger.error(f"删除策略文件失败: {str(e)}")
        return False, f"删除失败: {str(e)}" 