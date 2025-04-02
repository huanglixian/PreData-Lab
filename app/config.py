import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR / 'data'
UPLOADS_DIR = DATA_DIR / 'uploads'
DB_DIR = DATA_DIR / 'db'

# 创建必要的目录
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# 数据库配置
DB_PATH = DB_DIR / 'chunklab.db'
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Dify配置
DIFY_CONFIG = {
    'API_SERVER': 'https://dify.huanglixian.com:1984',
    'API_KEY': 'dataset-Rj9QfzNmO2llomIhp0S42pB7'
}

# 应用配置
APP_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 8410,
    'DEBUG': True,
    'ALLOWED_EXTENSIONS': {'.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.dwg'},
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'DEFAULT_CHUNK_SIZE': 300,
    'DEFAULT_OVERLAP': 30,
}

# 更新切块策略列表
# 为避免循环导入问题，使用函数延迟加载
def get_chunk_strategies():
    try:
        from app.chunklab.chunking import list_strategies
        return list_strategies()
    except ImportError:
        # 如果模块还未准备好，返回默认列表
        return [{'name': 'word', 'display_name': 'Word文档切块策略'}]

# 在请求时动态加载策略列表
def get_config(key=None):
    """获取配置项，某些配置项需要动态加载"""
    if key == 'CHUNK_STRATEGIES':
        return get_chunk_strategies()
    elif key == 'DIFY_API_SERVER':
        return DIFY_CONFIG['API_SERVER']
    elif key == 'DIFY_API_KEY':
        return DIFY_CONFIG['API_KEY']
    return APP_CONFIG.get(key, None) if key else APP_CONFIG 