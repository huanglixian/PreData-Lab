from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import logging

from ..config import get_config
from ..services.func_manager import get_documentation_content, validate_and_save_strategy, get_strategy_content, delete_strategy

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()

# 模板目录
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def chunkfunc_index(request: Request, partial: bool = False):
    """ChunkFunc主页 - 切块策略管理页面"""
    # 获取所有现有策略
    strategies = get_config('CHUNK_STRATEGIES')
    
    # 如果是部分加载请求，只返回策略列表部分
    if partial:
        return templates.TemplateResponse(
            "chunkfunc/strategy_list.html",
            {
                "request": request,
                "strategies": strategies
            }
        )
    
    # 渲染完整页面
    return templates.TemplateResponse(
        "chunkfunc/index.html",
        {
            "request": request,
            "strategies": strategies
        }
    )

@router.get("/doc/{doc_type}")
async def view_documentation(request: Request, doc_type: str):
    """查看文档（模板或指南）"""
    title, content, error = get_documentation_content(doc_type)
    
    if error:
        return JSONResponse(
            status_code=404,
            content={"message": error}
        )
    
    return templates.TemplateResponse(
        "chunkfunc/view.html",
        {
            "request": request,
            "strategy_name": title,
            "strategy_content": content,
            "metadata": None  # 不传递元数据，这样模板中的if判断不会显示元数据部分
        }
    )

@router.post("/upload")
async def upload_strategy(
    request: Request,
    file: UploadFile = File(...)
):
    """上传切块策略文件"""
    # 读取上传的文件内容
    file_content = await file.read()
    
    # 使用service进行验证和保存
    result, error = await validate_and_save_strategy(file_content, file.filename)
    
    if error:
        return JSONResponse(
            status_code=400,
            content={"message": error}
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "策略文件上传成功",
            "strategy_name": result["strategy_name"],
            "filename": result["filename"]
        }
    )

@router.get("/view/{strategy_name}")
async def view_strategy(request: Request, strategy_name: str):
    """查看策略文件内容"""
    strategy_name, strategy_content, error_or_metadata = get_strategy_content(strategy_name)
    
    if isinstance(error_or_metadata, str):  # 如果是错误消息
        return JSONResponse(
            status_code=404,
            content={"message": error_or_metadata}
        )
    
    return templates.TemplateResponse(
        "chunkfunc/view.html",
        {
            "request": request,
            "strategy_name": strategy_name,
            "strategy_content": strategy_content,
            "metadata": error_or_metadata
        }
    )

@router.delete("/delete/{strategy_name}")
async def delete_strategy_route(strategy_name: str):
    """删除策略文件"""
    success, message = delete_strategy(strategy_name)
    
    if not success:
        status_code = 404 if "不存在" in message else 400 if "内置策略" in message else 500
        return JSONResponse(
            status_code=status_code,
            content={"message": message, "success": False}
        )
    
    return JSONResponse(
        status_code=200,
        content={"message": message, "success": True}
    )