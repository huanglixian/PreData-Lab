from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from datetime import datetime

from .. import templates
from ..config import get_config, APP_CONFIG

# 创建主路由
router = APIRouter()

# 主页路由
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """系统主页"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "now": datetime.now}
    ) 