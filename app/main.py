# 标准库导入
import sys

# 第三方库导入
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# 本地模块导入
from . import templates
from .database import Base, engine
from .routes import main_router
from .config import APP_CONFIG
from datetime import datetime

# 创建FastAPI应用
app = FastAPI(title="预数据实验室", description="文档和数据预处理工具集")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 注册路由
app.include_router(main_router)

# 主页路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """系统主页"""
    return templates.TemplateResponse("index.html", {"request": request, "now": datetime.now})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=APP_CONFIG['HOST'],
        port=APP_CONFIG['PORT'],
        reload=APP_CONFIG['DEBUG']
    ) 