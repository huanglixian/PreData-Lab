# routers包初始化文件
"""
ChunkSpace应用路由模块

这个包包含应用的所有路由定义，按功能模块分组
"""

from fastapi import APIRouter
from . import base, chunklab, chunkfunc, chunkgo

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(base.router, prefix="", tags=["base"])
api_router.include_router(chunklab.router, prefix="/chunklab", tags=["chunklab"])
api_router.include_router(chunkfunc.router, prefix="/chunkfunc", tags=["chunkfunc"])
api_router.include_router(chunkgo.router, prefix="/chunkgo", tags=["chunkgo"]) 