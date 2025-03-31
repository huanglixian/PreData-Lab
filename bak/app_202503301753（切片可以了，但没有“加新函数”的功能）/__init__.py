from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from .database import create_tables

# 创建FastAPI应用
app = FastAPI(title="PreDataLab", description="数据处理工具集")

# 创建表
create_tables()

# 设置静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="app/templates")

# 不再需要直接导入路由，路由已在main.py中通过main_router注册
# 从旧的 from .routes import documents, chunks 改为：
# 此文件仅提供模板和应用实例 