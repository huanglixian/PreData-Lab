# ChunkSpace - 切块工作室

ChunkSpace（切块工作室）是一个专为RAG（检索增强生成）系统设计的前置数据处理工具集，提供以下功能：

1. 切片-函数实验室（Chunk-Func）：管理和上传自定义切片策略，创建和部署新的切片函数。
2. 切片-核心实验室（Chunk-Lab）：将不同格式的文档，通过不同的切片策略，进行切片实验。
3. 切片-批量ToDify（Chunk-Go）：进行批量文档切片，推送至Dify知识库。（规划中）


## - 项目概述

RAG系统的效果很大程度上依赖于数据的预处理质量。ChunkSpace提供了一套工具，让开发者可以更灵活地处理和优化RAG系统的输入数据，包括：

- **文档切片（ChunkLab）**：将各种格式的文档切分为适合嵌入的文本块
- **切片函数（ChunkFunc）**：管理和上传自定义切片策略，便于尝试不同的切片方法
- **Dify集成**：支持将切片后的数据直接推送至Dify平台的知识库


## - 快速上手

迫不及待想要尝试？查看我们的[快速上手指南](./guide/QuickStart.md)，只需几分钟即可启动并运行ChunkSpace！

简单说，👉 首先你要我fork我这个仓库，git代码，然后cd进入该文件夹，之后：

```bash
# 创建虚拟环境并激活
python -m venv predatalab
source predatalab/bin/activate  # Linux/macOS
# 或
predatalab\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 复制环境变量模板
# 编辑.env文件，填入您的配置信息

# 启动应用
python run.py
```

更多详细步骤请参考[快速上手指南](./guide/QuickStart.md)。


## - 核心功能

### 1、切片核心实验室（Chunk-Lab）

ChunkLab提供以下功能：

- 支持多种文档格式（Word、PDF、TXT、Excel等）的上传和处理
- 文档列表展示和管理
- 文档状态跟踪和管理
- 提供多种切片策略，支持不同类型文档的处理
- 可配置的切片参数（大小、重叠度）
- 切片任务异步处理
- 可视化预览切片结果
- 元数据保留（如标题层级、页码等）

### 2、切片函数实验室（Chunk-Func）

ChunkFunc提供以下功能：
- 切片函数上传、查看和管理
- 支持自定义切片函数的在线验证
- 函数元数据展示
- 函数开发文档和模板查看

### 3、切片批量ToDify（Chunk-Go）- 规划中

计划功能：
- 支持文档数据批量发送到Dify平台
- 提供API接口测试功能
- 支持文档段落自定义处理
- 支持向量数据同步


## - 技术架构

- **后端**：FastAPI (Python)
- **前端**：Bootstrap + Jinja2模板
- **数据库**：SQLite
- **文档处理**：python-docx, PyPDF2等
- **部署**：支持Docker容器化部署


## - 项目结构介绍

请参考[项目结构详细文档](./guide/Project_Structure.md)以获取完整的项目结构信息。


## - 问题排查工具

如果在使用过程中遇到以下问题：
- 端口被占用
- Python缓存问题
- 进程卡死
- 文档处理状态异常

我们提供了一个辅助工具`chunklab_helper.py`（./guide/chunklab_helper.py）来解决这些常见问题。只需在命令行中运行：

```bash
python ./guide/chunklab_helper.py
```

该工具提供交互式菜单，可帮助您：
- 清理Python缓存
- 关闭占用端口的进程
- 重置卡在"处理中"状态的文档
- 重启服务器
- 检查环境配置