#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ChunkLab 辅助工具脚本

帮助解决 ChunkLab 使用过程中可能遇到的常见问题：
1. 端口被占用
2. Python 缓存问题
3. 进程卡死问题
4. 数据库状态问题
"""

import os
import sys
import signal
import subprocess
import shutil
import time
import socket
import glob
import sqlite3
from pathlib import Path
import logging
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('chunklab_helper')

# 项目路径
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

def check_port_status(port=8410):
    """检查指定端口是否被占用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0  # 如果结果为0，说明端口已被占用

def kill_process_on_port(port=8410):
    """关闭占用指定端口的进程"""
    try:
        if sys.platform.startswith('win'):
            cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{port}\') do taskkill /F /PID %a'
            subprocess.run(cmd, shell=True)
        elif sys.platform.startswith('darwin'):  # macOS
            cmd = f"lsof -ti:{port} | xargs kill -9"
            subprocess.run(cmd, shell=True)
        else:  # Linux
            cmd = f"fuser -k {port}/tcp"
            subprocess.run(cmd, shell=True)
        logger.info(f"已关闭占用端口 {port} 的进程")
        return True
    except Exception as e:
        logger.error(f"关闭端口 {port} 的进程失败: {e}")
        return False

def clean_python_cache():
    """清理Python缓存文件"""
    try:
        # 找到所有的__pycache__目录
        pycache_dirs = []
        for root, dirs, files in os.walk(PROJECT_PATH):
            if '__pycache__' in dirs:
                pycache_dirs.append(os.path.join(root, '__pycache__'))
        
        # 删除找到的__pycache__目录
        for pycache_dir in pycache_dirs:
            shutil.rmtree(pycache_dir)
            logger.info(f"已删除: {pycache_dir}")
        
        # 删除.pyc文件
        pyc_files = glob.glob(f"{PROJECT_PATH}/**/*.pyc", recursive=True)
        for pyc_file in pyc_files:
            os.remove(pyc_file)
            logger.info(f"已删除: {pyc_file}")
        
        logger.info(f"清理Python缓存完成，共清理 {len(pycache_dirs)} 个__pycache__目录和 {len(pyc_files)} 个.pyc文件")
        return True
    except Exception as e:
        logger.error(f"清理Python缓存失败: {e}")
        return False

def kill_python_processes():
    """关闭所有Python进程"""
    try:
        if sys.platform.startswith('win'):
            # Windows系统
            cmd = "taskkill /F /IM python.exe"
            subprocess.run(cmd, shell=True)
        else:
            # macOS/Linux系统
            cmd = "pkill -9 python"
            subprocess.run(cmd, shell=True)
        logger.info("已关闭所有Python进程")
        return True
    except Exception as e:
        logger.error(f"关闭Python进程失败: {e}")
        return False

def reset_stuck_documents():
    """重置数据库中状态为'处理中'的文档"""
    try:
        db_path = os.path.join(PROJECT_PATH, 'data', 'db', 'chunklab.db')
        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 首先列出所有文档
        cursor.execute("SELECT id, filename, status FROM documents")
        all_docs = cursor.fetchall()
        if all_docs:
            print("\n所有文档列表：")
            for doc_id, doc_filename, doc_status in all_docs:
                print(f"- ID: {doc_id}, 状态: {doc_status}, 文件名: {doc_filename}")
        
        # 查询处于"处理中"状态的文档
        cursor.execute("SELECT id, filename FROM documents WHERE status = '处理中'")
        stuck_docs = cursor.fetchall()
        
        # 如果没有发现卡住的文档，询问是否手动指定要重置的文档ID
        if not stuck_docs:
            print("\n没有发现状态为'处理中'的文档。")
            
            # 询问是否要查看已切块文档
            check_chunked = input("是否要列出并重置某个'已切块'状态的文档？(y/n): ").strip().lower()
            if check_chunked == 'y':
                # 查询"已切块"状态的文档
                cursor.execute("SELECT id, filename FROM documents WHERE status = '已切块'")
                chunked_docs = cursor.fetchall()
                
                if not chunked_docs:
                    print("没有'已切块'状态的文档。")
                else:
                    print("\n'已切块'状态的文档列表：")
                    for i, (doc_id, doc_filename) in enumerate(chunked_docs, 1):
                        print(f"{i}. ID: {doc_id}, 文件名: {doc_filename}")
                    
                    doc_choice = input("\n请选择要重置的文档序号 (输入数字): ").strip()
                    try:
                        choice_idx = int(doc_choice) - 1
                        if 0 <= choice_idx < len(chunked_docs):
                            doc_id = chunked_docs[choice_idx][0]
                            print(f"选择了文档: ID={doc_id}, 文件名={chunked_docs[choice_idx][1]}")
                            confirm = input(f"确认将此文档状态重置为'未切块'？(y/n): ").strip().lower()
                            
                            if confirm == 'y':
                                cursor.execute("UPDATE documents SET status = '未切块' WHERE id = ?", (doc_id,))
                                conn.commit()
                                print(f"已将文档 {doc_id} 的状态重置为'未切块'")
                        else:
                            print("无效的选择！")
                    except ValueError:
                        print("请输入有效的数字！")
            
            # 询问是否手动指定ID
            manual_reset = input("是否要手动指定文档ID进行重置？(y/n): ").strip().lower()
            if manual_reset == 'y':
                doc_id = input("请输入要重置的文档ID: ").strip()
                try:
                    doc_id = int(doc_id)
                    # 检查文档是否存在
                    cursor.execute("SELECT id, filename, status FROM documents WHERE id = ?", (doc_id,))
                    doc = cursor.fetchone()
                    
                    if not doc:
                        print(f"未找到ID为 {doc_id} 的文档！")
                        conn.close()
                        return False
                    
                    print(f"\n找到文档: ID={doc[0]}, 状态={doc[2]}, 文件名={doc[1]}")
                    confirm = input(f"确认将此文档状态重置为'未切块'？(y/n): ").strip().lower()
                    
                    if confirm == 'y':
                        cursor.execute("UPDATE documents SET status = '未切块' WHERE id = ?", (doc_id,))
                        conn.commit()
                        print(f"已将文档 {doc_id} 的状态重置为'未切块'")
                except ValueError:
                    print("请输入有效的数字ID！")
                    conn.close()
                    return False
            else:
                print("未执行任何重置操作。")
                conn.close()
                return True
        else:
            # 有处于"处理中"状态的文档
            print(f"\n发现 {len(stuck_docs)} 个处于'处理中'状态的文档:")
            for doc_id, doc_filename in stuck_docs:
                print(f"- ID: {doc_id}, 文件名: {doc_filename}")
            
            confirm = input("确认将这些文档状态重置为'未切块'？(y/n): ").strip().lower()
            
            if confirm == 'y':
                cursor.execute("UPDATE documents SET status = '未切块' WHERE status = '处理中'")
                conn.commit()
                print(f"已重置 {len(stuck_docs)} 个卡住的文档状态")
        
        # 提示重启服务器
        print("\n注意: 为确保内存中的任务状态被清除，请重启服务器.")
        restart = input("是否立即重启服务器？(y/n): ").strip().lower()
        if restart == 'y':
            print("正在重启服务器...")
            restart_server()
        else:
            print("请稍后手动重启服务器，以确保任务状态被彻底清除.")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"重置文档状态失败: {e}")
        return False

def restart_server():
    """重启服务器"""
    try:
        # 先尝试关闭正在运行的服务器
        kill_process_on_port()
        time.sleep(1)
        
        # 切换到项目目录
        os.chdir(PROJECT_PATH)
        
        # 启动服务器
        if sys.platform.startswith('win'):
            # Windows平台使用start命令启动新进程
            command = 'start python run.py'
            subprocess.run(command, shell=True)
        else:
            # Linux/macOS平台使用nohup启动后台进程
            command = 'nohup python run.py > server.log 2>&1 &'
            subprocess.run(command, shell=True)
        
        logger.info("服务器已在后台重启，请稍等片刻后刷新浏览器")
        return True
    except Exception as e:
        logger.error(f"重启服务器失败: {e}")
        return False

def check_env():
    """检查环境"""
    try:
        # 检查Python版本
        python_version = sys.version
        logger.info(f"Python版本: {python_version}")
        
        # 检查操作系统
        os_info = sys.platform
        logger.info(f"操作系统: {os_info}")
        
        # 检查端口状态
        port_status = check_port_status()
        logger.info(f"端口8410状态: {'已占用' if port_status else '未占用'}")
        
        # 检查项目目录结构
        app_dir = os.path.join(PROJECT_PATH, 'app')
        if not os.path.exists(app_dir):
            logger.warning(f"app目录不存在: {app_dir}")
        else:
            logger.info(f"app目录存在: {app_dir}")
        
        # 检查数据库文件
        db_path = os.path.join(PROJECT_PATH, 'data', 'db', 'chunklab.db')
        if not os.path.exists(db_path):
            logger.warning(f"数据库文件不存在: {db_path}")
        else:
            logger.info(f"数据库文件存在: {db_path}")
            # 检查数据库表
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(f"数据库表: {', '.join([t[0] for t in tables])}")
                conn.close()
            except Exception as e:
                logger.error(f"检查数据库失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"环境检查失败: {e}")
        return False

def interactive_menu():
    """交互式菜单"""
    while True:
        print("\n==== ChunkLab 辅助工具 ====")
        print("1. 检查端口状态")
        print("2. 关闭占用端口进程")
        print("3. 清理Python缓存")
        print("4. 关闭所有Python进程")
        print("5. 重置卡住的文档状态")
        print("6. 重启服务器")
        print("7. 检查环境")
        print("8. 执行全套修复（2+3+5+6）")
        print("0. 退出")
        
        choice = input("\n请选择操作 [0-8]: ").strip()
        
        if choice == '1':
            port = 8410
            status = check_port_status(port)
            print(f"端口 {port} 状态: {'已占用' if status else '未占用'}")
        
        elif choice == '2':
            port = 8410
            kill_process_on_port(port)
        
        elif choice == '3':
            clean_python_cache()
        
        elif choice == '4':
            confirm = input("确定关闭所有Python进程吗？(y/n): ").strip().lower()
            if confirm == 'y':
                kill_python_processes()
        
        elif choice == '5':
            reset_stuck_documents()
        
        elif choice == '6':
            restart_server()
        
        elif choice == '7':
            check_env()
        
        elif choice == '8':
            confirm = input("确定执行全套修复吗？这将关闭所有进程并重启服务器! (y/n): ").strip().lower()
            if confirm == 'y':
                kill_process_on_port()
                clean_python_cache()
                reset_stuck_documents()
                restart_server()
        
        elif choice == '0':
            print("感谢使用！")
            break
        
        else:
            print("无效的选择，请重试。")
        
        input("\n按回车键继续...")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='ChunkLab辅助工具')
    parser.add_argument('--port', type=int, default=8410, help='要检查的端口号')
    parser.add_argument('--check-port', action='store_true', help='检查端口状态')
    parser.add_argument('--kill-port', action='store_true', help='关闭占用端口的进程')
    parser.add_argument('--clean-cache', action='store_true', help='清理Python缓存')
    parser.add_argument('--kill-python', action='store_true', help='关闭所有Python进程')
    parser.add_argument('--reset-docs', action='store_true', help='重置卡住的文档状态')
    parser.add_argument('--restart', action='store_true', help='重启服务器')
    parser.add_argument('--check-env', action='store_true', help='检查环境')
    parser.add_argument('--fix-all', action='store_true', help='执行全套修复')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 检查是否有提供任何参数，如果没有则显示交互式菜单
    if not any([args.check_port, args.kill_port, args.clean_cache, args.kill_python, 
                args.reset_docs, args.restart, args.check_env, args.fix_all]):
        interactive_menu()
        return
    
    # 执行命令行指定的操作
    if args.check_port:
        status = check_port_status(args.port)
        print(f"端口 {args.port} 状态: {'已占用' if status else '未占用'}")
    
    if args.kill_port:
        kill_process_on_port(args.port)
    
    if args.clean_cache:
        clean_python_cache()
    
    if args.kill_python:
        kill_python_processes()
    
    if args.reset_docs:
        reset_stuck_documents()
    
    if args.restart:
        restart_server()
    
    if args.check_env:
        check_env()
    
    if args.fix_all:
        kill_process_on_port(args.port)
        clean_python_cache()
        reset_stuck_documents()
        restart_server()

if __name__ == "__main__":
    main() 