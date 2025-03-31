#!/usr/bin/env python3
"""
预数据实验室启动脚本
"""
import os
import sys
import uvicorn
from app.config import APP_CONFIG

def main():
    """运行预数据实验室应用"""
    print(f"""
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃  预数据实验室 - 数据处理工具集        ┃
    ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
    ┃  运行地址: http://{APP_CONFIG['HOST']}:{APP_CONFIG['PORT']}  ┃
    ┃  调试模式: {'开启' if APP_CONFIG['DEBUG'] else '关闭'}                    ┃
    ┃  按 Ctrl+C 退出                        ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=APP_CONFIG['HOST'],
            port=APP_CONFIG['PORT'],
            reload=APP_CONFIG['DEBUG'],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n已停止预数据实验室服务")
        sys.exit(0)

if __name__ == "__main__":
    main() 