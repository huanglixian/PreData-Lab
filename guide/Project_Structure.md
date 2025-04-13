# ChunkSpace 项目结构

PreDataLab（ChunkSpace（切块工作室））有如下功能：
1、切片函数管理（Chunk-Func）：管理和上传自定义切片策略，创建和部署新的切片函数。
2、切片核心实验室（Chunk-Lab）：将不同格式的文档，通过不同的切片策略，进行切片实验。
3、切片批量处理（Chunk-Go）：进行批量文档切片，并批量推送至Dify知识库。

本文档描述了项目的整体结构和各个文件的功能，旨在帮助开发者快速了解项目架构。

## 项目结构树

```
PreDataLab/
├── app/                      # 应用主目录
│   ├── chunk_func/           # 具体切块函数的文件夹
│   ├── routers/              # 路由模块
│   │   ├── __init__.py         # 初始化路由模块
│   │   ├── base.py             # 基础路由和主页
│   │   ├── chunklab.py         # ChunkLab的路由（单个文件切片和ToDify）
│   │   ├── chunkgo.py          # ChunkGo的路由（批处理切片和批量ToDify）
│   │   └── chunkfunc.py        # ChunkFunc的路由（切片函数管理）
│   ├── services/             # 服务模块
│   │   ├── __init__.py         # 初始化服务模块
│   │   ├── document.py         # 文档处理服务（上传和删除等）
│   │   ├── chunking.py         # 切块服务
│   │   ├── add_dify_single.py  # 向Dify某文件添加切片的服务（不创建文档）
│   │   ├── to_dify_single.py   # 单文件推送Dify平台服务
│   │   ├── to_dify_batch.py    # 批量文件推送至Dify平台服务
│   │   ├── batch_chunking.py   # 批量文档切块服务
│   │   ├── folder_manager.py   # 文件夹管理服务
│   │   └── func_manager.py     # 切片函数管理服务
│   ├── static/              # 静态资源（CSS、JS、图片等）
│   │   ├── css/               # CSS样式文件
│   │   │   └── chunkgo_batchdocs.css  # ChunkGo批量文档样式
│   │   └── js/                # JavaScript脚本文件
│   │       ├── chunklab_chunk.js     # ChunkLab切块页面脚本
│   │       ├── chunklab_index.js     # ChunkLab首页脚本
│   │       └── chunkgo/             # ChunkGo脚本文件夹
│   │           ├── chunkgo_upload.js    # 文件上传脚本
│   │           ├── chunkgo_common.js    # 公共函数脚本
│   │           ├── chunkgo_dify.js      # Dify集成脚本
│   │           └── chunkgo_chunking.js  # 批量切块脚本
│   ├── templates/           # 页面模板（Jinja2）
│   │   ├── base.html          # 基础模板文件
│   │   ├── index.html         # 主页模板
│   │   ├── chunklab/          # ChunkLab模块模板
│   │   │   ├── index.html     # ChunkLab主页
│   │   │   ├── chunk.html     # 文档切块页面
│   │   │   └── to_dify_box.html # Dify集成页面
│   │   ├── chunkgo/           # ChunkGo模块模板
│   │   │   ├── index.html     # ChunkGo主页（新建文件夹）
│   │   │   └── batchdocs.html # 批量文档处理页面
│   │   └── chunkfunc/         # ChunkFunc模块模板
│   │       ├── index.html     # 切块函数管理主页
│   │       ├── strategy_list.html # 切块函数列表
│   │       └── view.html      # 切块函数详情页面
│   ├── __init__.py          # 初始化 Python 包
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库模型
│   ├── main.py              # 主应用入口
├── data/                    # 数据存储
│   ├── db/                  # 数据库文件
│   └── uploads/             # 上传文件存储
├── guide/                   # 开发指南
│   ├── QuickStart.md            # 快速上手指南
│   ├── Chunk_Strategy_Guide.md  # 切块函数-开发文档
│   ├── template_strategy.py     # 切块函数-代码模板
│   ├── chunklab_helper.py       # ChunkLab辅助函数
│   └── Project_Structure.md     # 本文档，项目结构描述
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

#### app/chunk_func/ - 切块函数实现

切块函数模块，包含各种切块策略实现。该模块负责将文档按照不同策略切分为合适的文本块。

#### app/routers/ - 路由模块

- **__init__.py** - 初始化路由模块，统一注册各模块路由
- **base.py** - 基础路由和主页，包括系统主页和实验室入口
- **chunklab.py** - ChunkLab的路由（单个文件切片和ToDify）
- **chunkgo.py** - ChunkGo的路由（批处理切片和批量ToDify）
- **chunkfunc.py** - ChunkFunc的路由（切片函数管理）

#### app/services/ - 服务模块

- **__init__.py** - 初始化服务模块
- **document.py** - 文档处理服务，负责文档上传、解析和删除等
- **chunking.py** - 切块服务，处理文档分块逻辑和切块任务管理
- **add_dify_single.py** - 向Dify某文件添加切片的服务（不创建文档）
- **to_dify_single.py** - 单文件推送Dify平台服务
- **to_dify_batch.py** - 批量文件推送至Dify平台服务
- **batch_chunking.py** - 批量文档切块服务，处理多文档的同时切块处理
- **folder_manager.py** - 文件夹管理服务，处理文件和目录的管理
- **func_manager.py** - 策略管理服务，处理切块策略的验证、保存和管理

#### app/static/ - 静态资源

包含CSS、JavaScript等静态资源文件：

##### app/static/css/ - CSS样式文件

- **chunkgo_batchdocs.css** - ChunkGo批量文档处理页面的样式文件

##### app/static/js/ - JavaScript脚本文件

- **chunklab_chunk.js** - ChunkLab切块页面的交互脚本
- **chunklab_index.js** - ChunkLab首页的交互脚本

##### app/static/js/chunkgo/ - ChunkGo模块脚本

- **chunkgo_upload.js** - 批量文件上传的处理脚本
- **chunkgo_common.js** - ChunkGo模块共用函数
- **chunkgo_dify.js** - 批量推送至Dify的交互脚本
- **chunkgo_chunking.js** - 批量切块处理的交互脚本

#### app/templates/ - 页面模板

Jinja2模板文件目录，用于渲染HTML页面：

- **base.html** - 基础模板文件，包含公共页面结构、导航栏和页脚
- **index.html** - 应用主页模板，展示各实验室入口

##### app/templates/chunklab/ - ChunkLab模块模板

- **index.html** - ChunkLab主页，提供文档上传和处理入口
- **chunk.html** - 文档切块页面，展示切块结果和切块参数配置界面
- **to_dify_box.html** - Dify集成页面，用于配置和发送数据到Dify平台

##### app/templates/chunkgo/ - ChunkGo模块模板

- **index.html** - ChunkGo主页（新建文件夹）
- **batchdocs.html** - 批量文档处理页面，用于处理多个文档并推送至Dify

##### app/templates/chunkfunc/ - ChunkFunc模块模板

- **index.html** - 切块函数管理主页，展示和管理切块策略
- **strategy_list.html** - 切块函数列表部分模板
- **view.html** - 切块函数详情页面，展示策略代码和元数据

### data/ 目录 - 数据存储

- **db/** - 数据库文件目录，存储SQLite数据库
- **uploads/** - 用户上传文件的存储目录

### guide/ 目录 - 开发指南

- **QuickStart.md** - 快速上手指南
- **Chunk_Strategy_Guide.md** - 切块函数开发文档
- **template_strategy.py** - 切块函数代码模板
- **chunklab_helper.py** - ChunkLab辅助函数库，提供各种帮助函数
- **Project_Structure.md** - 本文档，项目结构描述

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

### 文档管理模块 (ChunkLab)

- 支持多种文档格式（Word、PDF、TXT、Excel等）的上传和处理
- 文档列表展示和管理
- 文档状态跟踪和管理

### 切块处理模块 (ChunkLab)

- 提供多种切块策略，支持不同类型文档的处理
- 可配置的切块参数（大小、重叠度）
- 切块任务异步处理
- 可视化预览切块结果
- 元数据保留（如标题层级、页码等）

### 批量处理模块 (ChunkGo)

- 批量文档上传和管理
- 批量切块处理
- 批量推送至Dify平台
- 批量处理状态监控和管理

### 策略管理模块 (ChunkFunc)

- 切块函数上传、查看和管理
- 支持自定义切块函数的在线验证
- 函数元数据展示
- 函数开发文档和模板查看

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

开发者可以通过ChunkFunc模块上传自定义切块函数，或参考 `template_strategy.py` 和 `Chunk_Strategy_Guide.md` 添加新的切块策略。 