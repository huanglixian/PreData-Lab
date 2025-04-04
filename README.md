# PreDataLab - 预数据实验室

预数据实验室（PreDataLab）是一个专为RAG（检索增强生成）系统设计的前置数据处理工具集，旨在提供文档处理、OCR识别和向量嵌入等核心功能的开发和测试环境。


## - 项目概述

RAG系统的效果很大程度上依赖于数据的预处理质量。预数据实验室提供了一套工具，让开发者可以更灵活地处理和优化RAG系统的输入数据，包括：

- **文档切块（ChunkLab）**：将各种格式的文档切分为适合嵌入的文本块
- **OCR识别（OcrLab）**：测试和比较不同的OCR识别方法，优化文档文本提取
- **向量嵌入（EmbedLab）**：将文本进行向量化处理，测试不同嵌入模型的效果


## - 快速上手

迫不及待想要尝试？查看我们的[快速上手指南](./guide/QuickStart.md)，只需几分钟即可启动并运行预数据实验室！

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

### 1、文档切块实验室（ChunkLab）

ChunkLab是当前已完成的主要模块，提供以下功能：

- 支持多种文档格式（Word、PDF、TXT等）的上传和处理
- 提供多种切块策略，并且可以手动**添加切块策略**
- 可配置的切块参数（大小、重叠度）
- 可视化预览切块结果
- 元数据保留（如标题层级、页码等）

### 2、OCR识别实验室（OcrLab）- 开发中

计划功能：
- 支持多种OCR引擎的集成和对比
- 图像预处理选项
- OCR结果准确性评估
- 自定义OCR参数配置

### 3、向量嵌入实验室（EmbedLab）- 开发中

计划功能：
- 接入多种嵌入模型
- 嵌入结果可视化
- 相似度搜索测试
- 向量数据库连接与存储


## - 文档切块实验室（ChunkLab）使用流程

1. 启动应用：执行 `python run.py` 启动应用服务器
2. 从主页选择要使用的实验室模块（如ChunkLab）
3. 上传文档：选择并上传要处理的文档文件
4. 配置参数：选择切块策略，设置切块大小和重叠度
5. 执行处理：点击"开始切块"按钮进行处理
6. 查看结果：在结果页面查看切块详情
7. 导出数据：下载切块结果或进一步处理


## - 技术架构

- **后端**：FastAPI (Python)
- **前端**：Bootstrap + Jinja2模板
- **数据库**：SQLite
- **文档处理**：python-docx, PyPDF2等
- **部署**：支持Docker容器化部署


## - 添加自定义切块策略

ChunkLab支持灵活添加自定义切块策略。若要开发和添加自己的切块策略，请参考：

- [切块策略开发指南](./guide/Chunk_Strategy_Guide.md) - 详细介绍如何开发和注册新的切块策略
- [策略模板文件](./guide/template_strategy.py) - 提供了切块策略的代码模板

添加新策略的基本步骤：
1. 参考模板创建新的策略文件，文件名以`_strategy.py`结尾
2. 实现`BaseChunkStrategy`的子类
3. 将文件放置在`app/chunklab/chunking/`目录下
4. 重启应用，系统将自动加载新策略


## - 项目结构介绍

```
PreDataLab/
├── app/                      # 应用主目录
│   ├── chunklab/            # 文档切块实验室
│   │   ├── chunking/        # 切块策略实现
│   │   ├── document_service.py  # 文档处理服务
│   │   ├── chunk_service.py     # 切块服务
│   │   └── routes.py            # 路由定义
│   ├── common/              # 公共组件
│   ├── static/              # 静态资源
│   ├── templates/           # 页面模板
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库模型
│   └── main.py              # 主应用入口
├── data/                    # 数据存储
│   ├── db/                  # 数据库文件
│   └── uploads/             # 上传文件存储
├── guide/                   # 开发指南
│   ├── Chunk_Strategy_Guide.md  # 切块策略开发文档
│   └── template_strategy.py     # 策略模板
├── chunklab_helper.py       # 辅助工具脚本
├── requirements.txt         # 依赖项
├── .env                     # 环境文件
└── run.py                   # 应用启动脚本
```


## - 问题排查工具

如果在使用过程中遇到以下问题：
- 端口被占用
- Python缓存问题
- 进程卡死
- 文档处理状态异常

我们提供了一个辅助工具`chunklab_helper.py`来解决这些常见问题。只需在命令行中运行：

```bash
python chunklab_helper.py
```

该工具提供交互式菜单，可帮助您：
- 清理Python缓存
- 关闭占用端口的进程
- 重置卡在"处理中"状态的文档
- 重启服务器
- 检查环境配置