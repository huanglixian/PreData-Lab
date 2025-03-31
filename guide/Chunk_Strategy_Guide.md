# 切块策略开发指南

本指南将帮助您了解如何为 ChunkLab 创建新的切块策略。通过遵循这些步骤，您可以轻松地扩展系统的切块功能。

## 切块策略的基本原理

切块策略是将文档分割成多个小块的算法。在 ChunkLab 中，每个策略都是一个继承自 `BaseChunkStrategy` 的类，需要实现特定的方法。

## "二选一"的实现方式

为了减少冗余和提高开发效率，您只需要实现以下两个方法之一：

1. `chunk_no_meta` - 返回纯文本块列表（简单方式）
2. `chunk_with_meta` - 返回带元数据的文本块列表（高级方式）

系统会自动处理其余部分。这种"二选一"的实现方式让您可以根据需求选择最合适的实现方法。

## 切块结果格式建议

为确保系统能够正确处理您的切块结果，请遵循以下格式建议：

### chunk_no_meta 方法返回值格式

该方法应返回一个**字符串列表**，其中：
- 列表中的每个元素应为非空字符串
- 建议不要包含空字符串或只有空白字符的字符串

示例：`["块1内容", "块2内容", "块3内容"]`

### chunk_with_meta 方法返回值格式

该方法应返回一个**字典列表**，其中每个字典应包含：
- `content` 键：值为字符串，代表块的内容
- `meta` 键：值为字典，包含该块的元数据

示例：
```python
[
    {
        "content": "块1内容",
        "meta": {"start_pos": 0, "end_pos": 100}
    },
    {
        "content": "块2内容", 
        "meta": {"start_pos": 90, "end_pos": 190}
    }
]
```

## 使用约定

为了使您的切块策略能够被系统自动识别和加载，请遵循以下命名约定：

1. 文件名必须以 `_strategy.py` 结尾，例如：`pdf_strategy.py`
2. 文件必须放在 `app/chunklab/chunking/` 目录下
3. 实现的类名应该与策略名称相对应，例如：`PdfChunkStrategy`

## 实现方法一：chunk_no_meta（简单）

如果您的切块算法不需要关注元数据，只需要实现 `chunk_no_meta` 方法，返回纯文本块列表：

```python
from typing import List, Dict, Any
from .base import BaseChunkStrategy

class SimpleChunkStrategy(BaseChunkStrategy):
    """简单的文本切块策略示例"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_no_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[str]:
        """简单地按指定大小切分文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            # 确保切块不为空
            chunk = text[start:end].strip()
            if chunk:  # 只添加非空切块
                chunks.append(chunk)
            start = end - overlap if overlap > 0 else end
        
        return chunks
    
    def get_metadata(self) -> Dict[str, Any]:
        """返回策略元数据"""
        return {
            "name": "simple",
            "display_name": "简单切块策略",
            "description": "一个简单的文本切块示例",
            "supported_types": [".txt"]
        }
```

在这种方式下，系统会自动为每个文本块添加空元数据。

## 实现方法二：chunk_with_meta（高级）

如果您的切块算法需要添加自定义元数据，请实现 `chunk_with_meta` 方法：

```python
from typing import List, Dict, Any
from .base import BaseChunkStrategy

class AdvancedChunkStrategy(BaseChunkStrategy):
    """高级切块策略示例"""
    
    def __init__(self):
        super().__init__()  # 必须调用父类初始化
    
    def chunk_with_meta(self, file_path: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """按指定大小切分文本，并添加元数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        result_chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            chunk_text = text[start:end]
            
            # 添加元数据
            result_chunks.append({
                "content": chunk_text,
                "meta": {
                    "start_pos": start,
                    "end_pos": end,
                    "char_count": len(chunk_text)
                }
            })
            
            start = end - overlap if overlap > 0 else end
        
        return result_chunks
    
    def get_metadata(self) -> Dict[str, Any]:
        """返回策略元数据"""
        return {
            "name": "advanced",
            "display_name": "高级切块策略",
            "description": "一个带有详细元数据的切块示例",
            "supported_types": [".txt", ".md"]
        }
```

## 必须实现的方法

无论您选择哪种实现方式，以下方法都是必须实现的：

### get_metadata 方法

```python
def get_metadata(self) -> Dict[str, Any]:
    """
    获取切块策略的元数据
    
    Returns:
        包含策略信息的字典
    """
    return {
        "name": "your_strategy_name",  # 策略的唯一标识符（必须）
        "display_name": "您的策略显示名称",  # 在UI中显示的名称（可选，如果未提供会自动生成）
        "description": "您的策略描述",  # 策略的描述（可选）
        "supported_types": [".pdf", ".txt"]  # 支持的文件类型（可选）
    }
```

## 系统如何处理您的策略

当您的策略类被实例化时，系统会：

1. 检测您实现了哪个方法（`chunk_no_meta` 或 `chunk_with_meta`）
2. 自动为未实现的方法提供默认实现
3. 通过统一的 `process_document` 方法调用您的实现

这种设计使您可以专注于实现最适合您需求的方法，无需担心接口兼容性问题。

## 自动化加载机制

当您按照上述约定创建了新的切块策略后，系统将自动执行以下操作：

1. 在应用启动时，系统会扫描 `app/chunklab/chunking/` 目录中所有以 `_strategy.py` 结尾的文件
2. 找到并加载所有继承自 `BaseChunkStrategy` 的类
3. 实例化这些类并获取它们的元数据
4. 将这些策略添加到可用策略列表中，在 UI 中显示

无需修改任何其他代码，您的新策略将自动出现在切块策略下拉列表中！

## 注意事项

1. 每个策略类必须实现父类的 `__init__` 方法并调用 `super().__init__()`，以便系统能够检查实现情况
2. 如果既没有实现 `chunk_no_meta` 也没有实现 `chunk_with_meta`，系统会在初始化时抛出 `NotImplementedError` 异常
3. 元数据的格式没有严格限制，但应该是可以序列化为 JSON 的数据结构
4. 为了提高代码质量，建议添加详细的文档字符串和注释

## 元数据处理

在 ChunkLab 中，元数据会被保存到数据库中的 `chunk_metadata` 字段。系统自动处理元数据的存储和检索，无需开发者手动处理。

在渲染切块时，如果元数据中存在 `heading` 字段，它会被特殊处理并显示为该块所属的标题。您可以在元数据中添加其他信息，这些信息可以通过自定义前端模板来显示。 