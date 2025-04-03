# 🚀 PreDataLab 快速上手指南

嘿，欢迎来到预数据实验室！这份指南将帮助你在几分钟内启动并运行起这个强大的RAG前置处理工具。无需复杂操作，只需几个简单步骤！

## 📋 前置要求

- 推荐Python 3.11
- 基本的命令行操作能力

## 🔧 Step 1: 克隆代码仓库

从以下两个仓库任选一个克隆：

**GitHub仓库**：
```bash
# 从GitHub克隆代码仓库
git clone https://github.com/huanglixian/PreData-Lab.git
cd PreData-Lab
```

**Gitee仓库**（国内用户推荐）：
```bash
# 从Gitee克隆代码仓库
git clone https://gitee.com/lienshine/predata-lab.git
cd predata-lab
```

## 🐍 Step 2: 创建虚拟环境

选择下面适合你操作系统的命令：

**Windows:**
```bash
# 创建名为"predatalab"的虚拟环境
python -m venv predatalab
# 激活虚拟环境
predatalab\Scripts\activate
```

**macOS/Linux:**
```bash
# 创建名为"predatalab"的虚拟环境
python3 -m venv predatalab
# 激活虚拟环境
source predatalab/bin/activate
```

看到命令提示符前面出现`(predatalab)`了吗？太棒了！你已经成功进入虚拟环境！

## 📦 Step 3: 安装依赖项

```bash
# 安装所有必需的Python包
pip install -r requirements.txt
```

稍等片刻，让这些神奇的依赖包安装完成...喝口咖啡，马上就好！

## ⚙️ Step 4: 配置应用（可选）

### 基本配置

默认配置已足够使用，但如果你想自定义一些设置，可以编辑`app/config.py`文件：

```python
APP_CONFIG = {
    'HOST': '0.0.0.0',  # 监听所有网络接口
    'PORT': 8410,       # 应用端口，可以修改
    'DEBUG': True,      # 开发模式，生产环境设为False
    'ALLOWED_EXTENSIONS': {'.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.dwg'},  # 支持的文件类型
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB，最大文件上传大小
    'DEFAULT_CHUNK_SIZE': 300,  # 默认切块大小
    'DEFAULT_OVERLAP': 30,      # 默认重叠大小
}
```

端口被占用？别担心，随便改个数字就好，比如`8411`或`8080`！

### 敏感配置（API密钥等）

对于敏感配置（如API密钥、服务器地址等），我们使用环境变量方式配置，以避免泄露：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入您的实际配置
nano .env  # 或使用任何文本编辑器
```

.env文件示例：
```
# Dify API配置
DIFY_API_SERVER=https://your-api-server-url
DIFY_API_KEY=your-api-key
```

> **注意**：.env文件包含敏感信息，不会被提交到Git仓库。每次克隆新仓库后都需要重新配置。

更多关于配置管理的详细信息，请参阅[配置说明](../docs/配置说明.md)文档。

## 🚂 Step 5: 运行应用

一切准备就绪，现在启动预数据实验室！

```bash
python run.py
```

看到类似下面这样的输出了吗？太好了！
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8410 (Press CTRL+C to quit)
```

## 🌐 Step 6: 访问Web界面

打开你喜欢的浏览器，访问：
- 本地访问: http://localhost:8410
- 局域网访问: http://[你的IP地址]:8410

## 🎉 恭喜！

你已成功启动预数据实验室！现在你可以：
- 上传文档进行切块实验
- 尝试不同的切块策略
- 探索各种参数设置的效果

## 🆘 遇到问题？

使用我们的救星工具`chunklab_helper.py`解决常见问题：

```bash
python chunklab_helper.py
```

按照提示操作，大部分问题都能迎刃而解！

## 🧙‍♂️ 下一步

想了解更多？查看我们的其他指南：
- [切块策略开发指南](./Chunk_Strategy_Guide.md) - 学习如何开发自己的切块策略
- 更多精彩内容，敬请期待...

祝你在数据预处理的旅程中玩得开心！🚀✨ 