from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import shutil
from pathlib import Path
import logging
import hashlib
from datetime import datetime

from ..database import Document
from ..config import APP_CONFIG, UPLOADS_DIR

# 配置日志
logger = logging.getLogger(__name__)

class DocumentService:
    """文档服务类 - 处理文档上传、删除等操作"""
    
    async def upload_document(self, file: UploadFile, db: Session) -> JSONResponse:
        """
        上传文档并保存到数据库
        
        Args:
            file: 上传的文件对象
            db: 数据库会话
            
        Returns:
            JSONResponse: 上传结果
        """
        try:
            # 检查文件扩展名
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in APP_CONFIG['ALLOWED_EXTENSIONS']:
                logger.warning(f"不支持的文件类型: {file_ext}")
                return JSONResponse(
                    status_code=400,
                    content={"message": f"不支持的文件类型。允许的类型: {', '.join(APP_CONFIG['ALLOWED_EXTENSIONS'])}"}
                )
            
            # 保存文件
            file_path = UPLOADS_DIR / file.filename
            
            # 检查文件是否已存在，若存在则添加时间戳
            if os.path.exists(file_path):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                name, ext = os.path.splitext(file.filename)
                new_filename = f"{name}_{timestamp}{ext}"
                file_path = UPLOADS_DIR / new_filename
            else:
                new_filename = file.filename
            
            # 创建目标文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # 计算文件大小
            file_size = os.path.getsize(file_path)
            
            # 计算文件哈希值
            file_hash = self._calculate_file_hash(file_path)
            
            # 保存文档信息到数据库
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
        """
        删除文档及其切块
        
        Args:
            document_id: 文档ID
            db: 数据库会话
            
        Returns:
            JSONResponse: 删除结果
        """
        try:
            # 查找文档
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.warning(f"文档不存在: ID {document_id}")
                return JSONResponse(
                    status_code=404,
                    content={"message": "文档不存在"}
                )
            
            # 删除文件
            file_path = document.filepath
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除文件: {file_path}")
            
            # 删除关联的切块
            db.query(Document.chunks).filter(Document.id == document_id).delete()
            
            # 删除文档记录
            db.delete(document)
            db.commit()
            
            logger.info(f"已删除文档: ID {document_id}, 文件名 {document.filename}")
            
            return JSONResponse(
                status_code=200,
                content={"message": "文档已删除"}
            )
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"message": f"删除文档失败: {str(e)}"}
            )
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件的MD5哈希值
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest() 