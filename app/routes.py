from fastapi import APIRouter
from .chunklab.routes import router as chunklab_router

# 创建主路由
main_router = APIRouter()

# 注册ChunkLab模块路由
main_router.include_router(
    chunklab_router,
    prefix="/chunklab",
    tags=["chunklab"]
)

# 未来可以在这里注册其他模块的路由
# 例如:
# from .ocrlab.routes import router as ocrlab_router
# main_router.include_router(
#     ocrlab_router,
#     prefix="/ocrlab",
#     tags=["ocrlab"]
# )

# from .embedlab.routes import router as embedlab_router
# main_router.include_router(
#     embedlab_router,
#     prefix="/embedlab",
#     tags=["embedlab"]
# ) 