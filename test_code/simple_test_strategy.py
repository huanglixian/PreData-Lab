
from typing import List, Dict, Any

class SimpleTestStrategy:
    def get_metadata(self):
        return {
            "name": "simple_test", 
            "display_name": "简单测试",
            "description": "测试上传"
        }
        
    def chunk_no_meta(self, file_path, chunk_size, overlap):
        return ["测试块1", "测试块2"]
