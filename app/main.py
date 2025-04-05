# 标准库导入
import sys

# 第三方库导入
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 本地模块导入
from . import templates
from .database import Base, engine
from .routers import base
from .routers import chunklab
from .routers import chunkfunc
from .config import APP_CONFIG

# 创建FastAPI应用
app = FastAPI(title="ChunkWork", description="文档切块工作台")

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
app.mount("/guide", StaticFiles(directory="guide"), name="guide_files")

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 注册路由
app.include_router(base.router)
app.include_router(chunklab.router, prefix="/chunklab", tags=["chunklab"])
app.include_router(chunkfunc.router, prefix="/chunkfunc", tags=["chunkfunc"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=APP_CONFIG['HOST'],
        port=APP_CONFIG['PORT'],
        reload=APP_CONFIG['DEBUG']
    ) 