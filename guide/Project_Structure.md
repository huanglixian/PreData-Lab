# PreDataLab 项目结构

本文档描述了 PreDataLab（预数据实验室）项目的整体结构和各个文件的功能，旨在帮助开发者快速了解项目架构。

## 项目结构树

```
PreDataLab/
├── app/                      # 应用主目录
│   ├── chunk_func/          # 切块策略实现
│   │   ├── __init__.py         # 初始化切块策略模块，自动加载策略
│   │   ├── base.py             # 基础切块策略类定义
│   │   ├── text_strategy.py    # 纯文本文件切块策略
│   │   ├── word_strategy.py    # Word 文档切块策略
│   │   ├── word2_strategy.py   # Word 文档替代切块策略
│   │   └── excel_dict_strategy.py # Excel 字典切块策略
│   ├── routers/              # 路由模块
│   │   ├── __init__.py         # 初始化路由模块
│   │   ├── base.py             # 基础路由和主页
│   │   └── chunklab.py         # ChunkLab 相关路由
│   ├── services/             # 服务模块
│   │   ├── __init__.py         # 初始化服务模块
│   │   ├── document.py         # 文档处理服务（上传和删除等）
│   │   ├── chunking.py         # 切块服务
│   │   └── to_dify_single.py   # 单文件推送Dify平台的集成服务
│   ├── static/              # 静态资源（CSS、JS、图片等）
│   ├── templates/           # 页面模板（Jinja2）
│   │   ├── base.html          # 基础模板文件
│   │   ├── index.html         # 主页模板
│   │   └── chunklab/          # ChunkLab模块模板
│   │       ├── index.html     # ChunkLab主页
│   │       ├── chunk.html     # 文档切块页面
│   │       └── to_dify_box.html # Dify集成页面
│   ├── __init__.py          # 初始化 Python 包
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库模型
│   └── main.py              # 主应用入口
├── data/                    # 数据存储
│   ├── db/                  # 数据库文件
│   └── uploads/             # 上传文件存储
├── .env                     # 环境配置文件
├── .env.example             # 环境配置示例
├── requirements.txt         # 项目依赖列表
├── run.py                   # 应用启动脚本
├── server.log               # 服务器日志
└── LICENSE                  # 项目许可证

```

## 文件和目录详细介绍

### 根目录文件

- **README.md** - 项目主要说明文档，提供项目概述、功能介绍、使用流程等信息
- **run.py** - 应用启动脚本，启动 FastAPI 服务器
- **requirements.txt** - 项目依赖列表，包含所有必要的 Python 包
- **.env** / **.env.example** - 环境变量配置文件及其示例
- **server.log** - 服务器运行日志文件
- **LICENSE** - 项目许可证文件

### app/ 目录 - 应用主目录

- **__init__.py** - 初始化 Python 包
- **main.py** - 主应用入口，初始化 FastAPI 应用，注册路由
- **config.py** - 配置文件，包含应用配置和设置，负责动态加载切块策略
- **database.py** - 数据库模型定义，包含文档和切块的数据模型

#### app/chunk_func/ - 切块策略实现

- **__init__.py** - 初始化切块策略模块，自动加载策略
- **base.py** - 基础切块策略类定义，定义策略接口和基本方法
- **text_strategy.py** - 纯文本文件切块策略
- **word_strategy.py** - Word 文档切块策略
- **word2_strategy.py** - Word 文档替代切块策略
- **excel_dict_strategy.py** - Excel 字典切块策略

#### app/routers/ - 路由模块

- **__init__.py** - 初始化路由模块，统一注册各模块路由
- **base.py** - 基础路由和主页，包括系统主页和ChunkLab入口
- **chunklab.py** - ChunkLab相关路由，包括文档管理、切块操作和Dify集成

#### app/services/ - 服务模块

- **__init__.py** - 初始化服务模块
- **document.py** - 文档处理服务，负责文档上传、解析和删除等
- **chunking.py** - 切块服务，处理文档分块逻辑和切块任务管理
- **to_dify_single.py** - 与Dify平台集成的服务，处理数据推送和同步

#### app/templates/ - 页面模板

Jinja2模板文件目录，用于渲染HTML页面：

- **base.html** - 基础模板文件，包含公共页面结构、导航栏和页脚
- **index.html** - 应用主页模板，展示各实验室入口

##### app/templates/chunklab/ - ChunkLab模块模板

- **index.html** - ChunkLab主页，提供文档上传和处理入口
- **chunk.html** - 文档切块页面，展示切块结果和切块参数配置界面
- **view_chunks.html** - 切块列表查看页面，展示切块结果
- **to_dify_box.html** - Dify集成页面，用于配置和发送数据到Dify平台

#### app/static/ - 静态资源

包含 CSS、JavaScript、图片等静态资源文件

### data/ 目录 - 数据存储

- **db/** - 数据库文件目录，存储SQLite数据库
- **uploads/** - 用户上传文件的存储目录

### guide/ 目录 - 开发指南

- **QuickStart.md** - 快速上手指南
- **Chunk_Strategy_Guide.md** - 切块策略开发文档
- **template_strategy.py** - 切块策略代码模板
- **Project_Structure.md** - 本文档，项目结构描述

### bak/ 目录 - 备份文件

存储项目的备份和历史版本文件

## 技术架构

- **后端**：FastAPI (Python)
- **前端**：Bootstrap + Jinja2模板
- **数据库**：SQLite
- **文档处理**：python-docx, PyPDF2等
- **部署**：支持Docker容器化部署

## 开发流程

1. 从根目录的 `run.py` 启动应用
2. FastAPI 应用在 `app/main.py` 中初始化
3. 路由根据功能模块分组在 `app/routers/` 目录下
4. 数据库模型在 `app/database.py` 中定义
5. 业务逻辑在 `app/services/` 各服务中实现
6. 切块策略放置在 `app/chunk_func/` 目录下，遵循 `base.py` 中的接口

## 主要功能模块

### 文档管理模块

- 支持多种文档格式（Word、PDF、TXT、Excel等）的上传和处理
- 文档列表展示和管理
- 文档状态跟踪和管理

### 切块处理模块

- 提供多种切块策略，支持不同类型文档的处理
- 可配置的切块参数（大小、重叠度）
- 切块任务异步处理
- 可视化预览切块结果
- 元数据保留（如标题层级、页码等）

### Dify 集成模块

- 支持文档数据批量发送到 Dify 平台
- 提供 API 接口测试功能
- 支持文档段落自定义处理
- 支持向量数据同步

## 切块策略说明

系统支持多种切块策略，每种策略针对特定类型的文档优化：

1. **基本文本切块** (text_strategy.py)
   - 适用于纯文本文件
   - 简单按字符数切分

2. **Word 文档切块** (word_strategy.py)
   - 基于标题和段落结构
   - 保留文档层次信息

3. **Word 智能标题切块** (word2_strategy.py)
   - 标题树结构的智能处理
   - 合并空标题，优化切块质量

4. **Excel 字典切块** (excel_dict_strategy.py)
   - 将Excel文件按行转换为字典
   - 每行作为独立切片

开发者可以参考 `template_strategy.py` 和 `Chunk_Strategy_Guide.md` 添加自己的切块策略。 