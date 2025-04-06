import os
import shutil
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..database import Folder, Document
from ..config import UPLOADS_DIR

class FolderManager:
    """文件夹管理服务"""
    
    def create_folder(self, name: str, db: Session) -> Dict[str, Any]:
        """创建新文件夹"""
        # 检查文件夹名称是否已存在
        existing = db.query(Folder).filter(Folder.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"文件夹 '{name}' 已存在")
        
        # 在上传目录中创建物理文件夹
        folder_path = os.path.join(UPLOADS_DIR, name)
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")
        
        # 创建数据库记录
        folder = Folder(
            name=name,
            folder_path=folder_path,
            create_time=datetime.now()
        )
        
        try:
            db.add(folder)
            db.commit()
            db.refresh(folder)
            
            return {
                "status": "success",
                "message": f"文件夹 '{name}' 创建成功",
                "data": {
                    "id": folder.id,
                    "name": folder.name,
                    "path": folder.folder_path,
                    "create_time": folder.create_time
                }
            }
        except Exception as e:
            # 如果数据库操作失败，删除已创建的物理文件夹
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
            db.rollback()
            raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")
    
    def get_folders(self, db: Session) -> List[Dict[str, Any]]:
        """获取所有文件夹列表"""
        folders = db.query(Folder).all()
        
        result = []
        for folder in folders:
            # 获取文件夹中的文档数量
            doc_count = db.query(Document).filter(Document.folder_id == folder.id).count()
            
            # 获取最近更新时间
            latest_doc = db.query(Document).filter(Document.folder_id == folder.id).order_by(Document.upload_time.desc()).first()
            latest_update = latest_doc.upload_time if latest_doc else folder.create_time
            
            result.append({
                "id": folder.id,
                "name": folder.name,
                "path": folder.folder_path,
                "create_time": folder.create_time,
                "document_count": doc_count,
                "latest_update": latest_update
            })
        
        return result
    
    def get_folder(self, folder_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """获取单个文件夹详情"""
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return None
        
        # 获取文件夹中的文档数量
        doc_count = db.query(Document).filter(Document.folder_id == folder.id).count()
        
        # 获取最近更新时间
        latest_doc = db.query(Document).filter(Document.folder_id == folder.id).order_by(Document.upload_time.desc()).first()
        latest_update = latest_doc.upload_time if latest_doc else folder.create_time
        
        return {
            "id": folder.id,
            "name": folder.name,
            "path": folder.folder_path,
            "create_time": folder.create_time,
            "document_count": doc_count,
            "latest_update": latest_update
        }
    
    def delete_folder(self, folder_id: int, db: Session) -> Dict[str, Any]:
        """删除文件夹"""
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        # 检查文件夹中是否有文档
        doc_count = db.query(Document).filter(Document.folder_id == folder_id).count()
        if doc_count > 0:
            raise HTTPException(status_code=400, detail=f"文件夹中仍有 {doc_count} 个文档，请先删除它们")
        
        # 删除物理文件夹
        if os.path.exists(folder.folder_path):
            try:
                shutil.rmtree(folder.folder_path, ignore_errors=True)
            except Exception as e:
                # 删除物理文件夹失败但继续删除数据库记录
                print(f"警告: 删除物理文件夹失败 {str(e)}")
        
        # 删除数据库记录
        try:
            db.delete(folder)
            db.commit()
            return {
                "status": "success",
                "message": f"文件夹 '{folder.name}' 删除成功"
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除文件夹失败: {str(e)}") 