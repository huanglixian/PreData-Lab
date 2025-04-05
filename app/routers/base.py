from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
from sqlalchemy.orm import Session

from .. import templates
from ..database import get_db, Document
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

# ChunkLab主页路由
@router.get("/chunklab", response_class=RedirectResponse)
async def redirect_to_chunklab_index():
    """重定向到ChunkLab主页"""
    return RedirectResponse(url="/chunklab/index")

@router.get("/chunklab/index")
async def chunklab_index(request: Request, db: Session = Depends(get_db)):
    """ChunkLab主页面 - 文档上传和列表"""
    documents = db.query(Document).order_by(Document.upload_time.desc()).all()
    
    return templates.TemplateResponse(
        "chunklab/index.html",
        {
            "request": request,
            "documents": documents,
            "allowed_extensions": ", ".join(APP_CONFIG['ALLOWED_EXTENSIONS']),
            "now": datetime.now,
            "dify_api_server": get_config('DIFY_API_SERVER')
        }
    ) 