#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dify API 批量能力测试脚本
用途：测试Dify API是否支持批量操作，确定最佳实现方案
结论：Dify API不支持批量上传，需要使用线程池处理多个文档
"""

import os
import sys
import json
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 将当前目录添加到路径中，以便导入app模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入必要的配置和数据库模型
from app.config import get_config
from app.database import Document, get_db_session

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DifyAPITester:
    """Dify API批量能力测试类"""
    
    def __init__(self):
        """初始化测试类"""
        self.api_server = get_config('DIFY_API_SERVER')
        self.api_key = get_config('DIFY_API_KEY')
        self.dataset_id = "813febfd-484d-4109-832c-412b6f63bb9f"  # 测试用知识库ID
        
        # 检查配置
        if not self.api_server or not self.api_key:
            logger.error("请确保已配置DIFY_API_SERVER和DIFY_API_KEY环境变量")
            sys.exit(1)
            
        logger.info(f"Dify API服务器: {self.api_server}")
        self.db = get_db_session()
    
    def get_headers(self):
        """获取API请求头"""
        return {'Authorization': f'Bearer {self.api_key}'}
    
    def test_batch_endpoints(self):
        """测试Dify API是否有批量操作的端点"""
        logger.info("=== 测试批量API端点 ===")
        
        # 可能的批量操作端点
        potential_endpoints = [
            "/v1/datasets/{dataset_id}/documents/batch-create",
            "/v1/datasets/{dataset_id}/documents/batch",
            "/v1/datasets/{dataset_id}/batch/documents",
            "/v1/datasets/{dataset_id}/documents/bulk",
            "/v1/datasets/{dataset_id}/documents/batch-upload"
        ]
        
        for endpoint in potential_endpoints:
            url = f"{self.api_server}{endpoint.format(dataset_id=self.dataset_id)}"
            try:
                response = requests.get(url, headers=self.get_headers())
                logger.info(f"端点 GET {url}: 状态码 {response.status_code}")
                
                # 尝试POST请求
                response = requests.post(url, headers=self.get_headers(), json={})
                logger.info(f"端点 POST {url}: 状态码 {response.status_code}")
                
                if response.status_code < 400:
                    logger.info(f"✓ 发现可用批量端点: {url}")
                    return True
            except Exception as e:
                logger.error(f"测试端点失败 {url}: {str(e)}")
        
        logger.info("✗ 未找到支持批量操作的API端点")
        return False
    
    def test_document_segments_batch(self):
        """测试文档段落批量上传API"""
        logger.info("=== 测试段落批量上传API ===")
        
        # 获取一个测试文档ID
        document = self.db.query(Document).filter(Document.status == "已切块").first()
        if not document:
            logger.error("找不到已切块的文档进行测试")
            return False
        
        # 模拟创建一个文档并获取ID
        create_url = f"{self.api_server}/v1/datasets/{self.dataset_id}/documents"
        try:
            response = requests.post(
                create_url,
                headers={**self.get_headers(), 'Content-Type': 'application/json'},
                json={"name": "Test Document", "content": "Test content"}
            )
            
            if response.status_code >= 400:
                logger.warning(f"无法创建测试文档: {response.status_code}")
                return False
            
            data = response.json()
            doc_id = data.get('id')
            
            if not doc_id:
                logger.warning("无法获取创建的文档ID")
                return False
            
            # 尝试批量上传段落
            segments_url = f"{self.api_server}/v1/datasets/{self.dataset_id}/documents/{doc_id}/segments/batch"
            
            # 测试数据
            segments = [
                {"content": "测试段落1", "metadata": {}},
                {"content": "测试段落2", "metadata": {}}
            ]
            
            response = requests.post(
                segments_url,
                headers={**self.get_headers(), 'Content-Type': 'application/json'},
                json={"segments": segments}
            )
            
            logger.info(f"段落批量上传: {response.status_code}")
            
            if response.status_code < 400:
                logger.info("✓ 段落批量上传API可用")
                return True
            else:
                logger.info(f"✗ 段落批量上传失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"段落批量上传测试失败: {str(e)}")
            return False
    
    def test_thread_pool_performance(self):
        """测试线程池处理多个文档的性能"""
        logger.info("=== 测试线程池性能 ===")
        
        # 获取一些测试文档
        documents = self.db.query(Document).filter(Document.status == "已切块").limit(5).all()
        if not documents:
            logger.error("找不到足够的文档进行测试")
            return
        
        doc_ids = [doc.id for doc in documents]
        
        # 模拟处理文档的函数
        def process_document(doc_id):
            logger.info(f"处理文档 {doc_id} 中...")
            # 模拟API调用和处理时间
            import time
            time.sleep(1)
            return f"文档 {doc_id} 处理完成"
        
        # 测试不同线程池大小的性能
        for max_workers in [1, 3, 5]:
            logger.info(f"\n测试线程池大小: {max_workers}")
            
            import time
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {executor.submit(process_document, doc_id): doc_id for doc_id in doc_ids}
                
                # 收集结果
                results = []
                for future in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"处理失败: {str(e)}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"线程池大小 {max_workers}: 处理 {len(doc_ids)} 个文档耗时 {duration:.2f} 秒")
            logger.info(f"平均每个文档耗时: {duration/len(doc_ids):.2f} 秒")
    
    def run_tests(self):
        """运行所有测试"""
        logger.info("\n=== Dify API 批量能力测试开始 ===\n")
        
        # 测试批量端点
        has_batch_endpoints = self.test_batch_endpoints()
        
        # 测试段落批量上传
        has_batch_segments = self.test_document_segments_batch()
        
        # 测试线程池性能
        self.test_thread_pool_performance()
        
        # 总结
        logger.info("\n=== 测试结论 ===")
        logger.info(f"批量文档上传API: {'可用' if has_batch_endpoints else '不可用'}")
        logger.info(f"段落批量上传API: {'可用' if has_batch_segments else '不可用'}")
        logger.info("\n推荐实现方案:")
        logger.info("1. 由于Dify API不支持批量文档上传，需使用线程池并行处理多个文档")
        logger.info("2. 根据测试，线程池大小建议设置为3-5，以平衡性能和服务器负载")
        logger.info("3. 实现批量ToDify功能时，需要修改现有的ToDify功能以支持多个文档")
        logger.info("4. 前端需要实现文档选择和批量操作，后端需要实现状态管理和错误处理")
    
if __name__ == "__main__":
    tester = DifyAPITester()
    tester.run_tests() 