# routers包初始化文件
"""
ChunkWork应用路由模块

这个包包含应用的所有路由定义，按功能模块分组
"""

from fastapi import APIRouter

# 导入各模块路由
from .base import router as base_router
from .chunklab import router as chunklab_router

# 创建主路由（可选，如果需要统一注册的话）
main_router = APIRouter()

# 注册模块路由
main_router.include_router(base_router)
main_router.include_router(chunklab_router, prefix="/chunklab", tags=["chunklab"]) 