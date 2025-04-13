from fastapi import UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
from pathlib import Path
import logging
import hashlib
from datetime import datetime

from ..database import Document, Chunk
from ..config import APP_CONFIG, UPLOADS_DIR

# 配置日志
logger = logging.getLogger(__name__)

class DocumentService:
    """文档服务类 - 处理文档上传、删除等操作"""
    
    async def upload_document(self, file: UploadFile, db: Session) -> JSONResponse:
        """上传文档并保存到数据库"""
        try:
            # 检查文件扩展名
            filename = file.filename
            file_ext = Path(filename).suffix.lower()
            if file_ext not in APP_CONFIG['ALLOWED_EXTENSIONS']:
                logger.warning(f"不支持的文件类型: {file_ext}")
                return JSONResponse(
                    status_code=400,
                    content={"message": f"不支持的文件类型。允许的类型: {', '.join(APP_CONFIG['ALLOWED_EXTENSIONS'])}"}
                )
            
            # 移除文件名中可能包含的路径分隔符，确保文件直接保存在UPLOADS_DIR
            safe_filename = os.path.basename(filename)
            new_filename = safe_filename
            file_path = UPLOADS_DIR / safe_filename
            
            if os.path.exists(file_path):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                name, ext = os.path.splitext(safe_filename)
                new_filename = f"{name}_{timestamp}{ext}"
                file_path = UPLOADS_DIR / new_filename
            
            # 读取文件内容并保存
            file_content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
                
            # 文件信息
            file_size = os.path.getsize(file_path)
            file_hash = hashlib.md5(file_content).hexdigest()
            
            # 保存到数据库
            document = Document(
                filename=new_filename,
                filepath=str(file_path),
                filetype=file_ext,
                filesize=file_size,
                upload_time=datetime.now(),
                status="未切块",
                hash=file_hash
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"文件上传成功: {new_filename}, ID: {document.id}")
            
            return JSONResponse(
                status_code=200,
                content={"message": "文件上传成功", "document_id": document.id, "filename": new_filename}
            )
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"message": f"文件上传失败: {str(e)}"}
            )
    
    def delete_document(self, document_id: int, db: Session) -> JSONResponse:
        """删除文档及其切块"""
        try:
            # 查找文档
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.warning(f"文档不存在: ID {document_id}")
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "文档不存在"}
                )
            
            # 删除文件
            file_path = document.filepath
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除文件: {file_path}")
            
            # 删除关联的切块和文档记录
            db.query(Chunk).filter(Chunk.document_id == document_id).delete()
            db.delete(document)
            db.commit()
            
            logger.info(f"已删除文档: ID {document_id}, 文件名 {document.filename}")
            
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "文档已删除"}
            )
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"删除文档失败: {str(e)}"}
            ) 