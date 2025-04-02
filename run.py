#!/usr/bin/env python3
"""
预数据实验室启动脚本
"""
import os
import sys
import uvicorn
import subprocess
import platform
import signal
import time
from app.config import APP_CONFIG

def main():
    """运行预数据实验室应用"""
    port = APP_CONFIG['PORT']
    # 先尝试杀死占用端口的进程
    kill_process_on_port(port)
    
    print(f"""
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃  预数据实验室 - 数据处理工具集        ┃
    ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
    ┃  运行地址: http://{APP_CONFIG['HOST']}:{port}  ┃
    ┃  调试模式: {'开启' if APP_CONFIG['DEBUG'] else '关闭'}                    ┃
    ┃  按 Ctrl+C 退出                        ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=APP_CONFIG['HOST'],
            port=port,
            reload=APP_CONFIG['DEBUG'],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n已停止预数据实验室服务")
        sys.exit(0)

def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    print(f"尝试释放端口 {port}...")
    
    try:
        if platform.system() == "Windows":
            # Windows系统
            subprocess.run(f"FOR /F \"tokens=5\" %a in ('netstat -ano ^| findstr :{port} ^| findstr LISTENING') do taskkill /F /PID %a", shell=True)
        elif platform.system() == "Darwin":  # macOS
            # 更直接的方式杀死进程
            subprocess.run(f"lsof -ti tcp:{port} | xargs kill -9", shell=True)
        else:  # Linux
            subprocess.run(f"fuser -k {port}/tcp", shell=True)
            
        # 等待端口释放
        time.sleep(1)
        print(f"端口 {port} 已释放")
    except Exception as e:
        print(f"尝试终止占用端口 {port} 的进程失败: {e}")

if __name__ == "__main__":
    main() 