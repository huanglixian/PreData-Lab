import requests
import json
import time
import sys

# API配置
API_BASE_URL = "https://dify.huanglixian.com:1984/v1"
API_KEY = "dataset-Rj9QfzNmO2llomIhp0S42pB7"

def api_request(method, url, headers=None, json_data=None):
    """通用API请求处理函数，统一处理错误"""
    try:
        if method.lower() == 'get':
            response = requests.get(url, headers=headers)
        elif method.lower() == 'post':
            response = requests.post(url, headers=headers, json=json_data)
        elif method.lower() == 'delete':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"不支持的请求方法: {method}")
        
        # 检查HTTP状态码
        response.raise_for_status()
        
        # 检查是否有内容返回
        if not response.content:
            return {"success": True}
        
        # 尝试将返回内容解析为JSON
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
        if response.content:
            try:
                error_json = response.json()
                print(f"API错误详情: {json.dumps(error_json, ensure_ascii=False)}")
                return error_json
            except:
                print(f"API返回内容: {response.text}")
        return {"error": f"HTTP错误: {e}", "success": False}
    except requests.exceptions.ConnectionError:
        print(f"连接错误: 无法连接到服务器 {url}")
        return {"error": "连接错误", "success": False}
    except requests.exceptions.Timeout:
        print("请求超时")
        return {"error": "请求超时", "success": False}
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return {"error": f"请求错误: {e}", "success": False}
    except json.JSONDecodeError:
        print(f"JSON解析错误: API返回的内容不是有效的JSON格式")
        print(f"API返回内容: {response.text}")
        return {"error": "JSON解析错误", "success": False}
    except Exception as e:
        print(f"未知错误: {e}")
        return {"error": f"未知错误: {e}", "success": False}

def create_document_by_text(dataset_id, name, text_content):
    """通过文本创建文档"""
    url = f"{API_BASE_URL}/datasets/{dataset_id}/document/create-by-text"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "text": text_content,
        "indexing_technique": "high_quality",
        "process_rule": {"mode": "automatic"}
    }
    
    return api_request('post', url, headers, payload)

def get_all_documents(dataset_id):
    """获取知识库中的所有文档"""
    url = f"{API_BASE_URL}/datasets/{dataset_id}/documents"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    return api_request('get', url, headers)

def get_document_status(dataset_id, document_id):
    """获取特定文档的状态"""
    docs = get_all_documents(dataset_id)
    if not docs.get('data'):
        return None
        
    for doc in docs.get('data', []):
        if doc.get('id') == document_id:
            return {
                'name': doc.get('name'),
                'status': doc.get('display_status'),
                'indexing_status': doc.get('indexing_status'),
                'word_count': doc.get('word_count'),
                'tokens': doc.get('tokens')
            }
    return None

def wait_for_document_indexing(dataset_id, document_id, timeout=60, check_interval=5):
    """等待文档索引完成
    
    Args:
        dataset_id: 知识库ID
        document_id: 文档ID
        timeout: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        成功时返回文档信息，超时返回None
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        doc_status = get_document_status(dataset_id, document_id)
        if not doc_status:
            return None
        
        if doc_status['indexing_status'] == 'completed':
            return doc_status
        
        print(f"文档 '{doc_status['name']}' 当前状态: {doc_status['indexing_status']}，继续等待...")
        time.sleep(check_interval)
    
    # 超时返回最后状态
    return get_document_status(dataset_id, document_id)

def delete_document(dataset_id, document_id):
    """删除文档
    
    Args:
        dataset_id: 知识库ID
        document_id: 文档ID
        
    Returns:
        API响应
    """
    url = f"{API_BASE_URL}/datasets/{dataset_id}/documents/{document_id}"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    return api_request('delete', url, headers)

def get_document_content(dataset_id, document_id):
    """获取文档详情
    
    Args:
        dataset_id: 知识库ID
        document_id: 文档ID
        
    Returns:
        文档详情
    """
    url = f"{API_BASE_URL}/datasets/{dataset_id}/documents/{document_id}/segments"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    return api_request('get', url, headers)

def get_all_datasets():
    """获取所有知识库"""
    url = f"{API_BASE_URL}/datasets"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    return api_request('get', url, headers)

def find_dataset_id_by_name(dataset_name):
    """根据知识库名称查找知识库ID
    
    Args:
        dataset_name: 知识库名称
        
    Returns:
        找到时返回知识库ID，否则返回None
    """
    datasets = get_all_datasets()
    if not datasets.get('data'):
        return None
        
    for dataset in datasets.get('data', []):
        if dataset.get('name') == dataset_name:
            return dataset.get('id')
    return None

def show_all_datasets():
    """显示所有知识库信息"""
    datasets = get_all_datasets()
    
    if datasets.get('error'):
        print(f"获取知识库列表失败: {datasets.get('error')}")
        return None
        
    print(f"知识库总数: {datasets.get('total', 0)}")
    
    if datasets.get('data') and len(datasets['data']) > 0:
        print("\n知识库列表:")
        for i, dataset in enumerate(datasets['data']):
            print(f"{i+1}. {dataset.get('name')} - ID: {dataset.get('id')} - 文档数: {dataset.get('document_count')}")
    else:
        print("没有找到任何知识库")
    
    return datasets

def validate_dataset_id(dataset_id):
    """验证知识库ID是否有效"""
    if not dataset_id:
        return False
        
    # 尝试获取知识库文档列表来验证ID是否有效
    result = get_all_documents(dataset_id)
    return not result.get('error')

def select_dataset():
    """选择知识库"""
    print("\n请选择知识库:")
    print("1. 输入知识库ID")
    print("2. 从列表中选择知识库")
    choice = input("请选择 (1-2): ")
    
    dataset_id = None
    if choice == '1':
        dataset_id = input("请输入知识库ID: ")
        # 验证ID是否有效
        if not validate_dataset_id(dataset_id):
            print(f"无效的知识库ID: {dataset_id}")
            return None
    elif choice == '2':
        datasets = get_all_datasets()
        if datasets.get('error'):
            print(f"获取知识库列表失败: {datasets.get('error')}")
            return None
            
        if datasets.get('total', 0) == 0:
            print("没有可用的知识库")
            return None
        
        print("\n可用的知识库:")
        for i, dataset in enumerate(datasets.get('data', [])):
            print(f"{i+1}. {dataset.get('name')} - 文档数: {dataset.get('document_count')}")
        
        try:
            index = int(input("\n请选择知识库编号: ")) - 1
            if 0 <= index < len(datasets.get('data', [])):
                dataset_id = datasets['data'][index]['id']
                print(f"已选择: {datasets['data'][index]['name']} (ID: {dataset_id})")
            else:
                print("无效的选择")
                return None
        except ValueError:
            print("请输入有效的数字")
            return None
    else:
        print("无效的选择")
        return None
    
    return dataset_id

def search_dataset_id():
    """功能1：查询知识库ID"""
    print("\n===== 知识库ID查询 =====")
    print("1. 显示所有知识库")
    print("2. 根据名称查询知识库ID")
    choice = input("请选择操作 (1-2): ")
    
    if choice == '1':
        show_all_datasets()
    elif choice == '2':
        dataset_name = input("请输入知识库名称: ")
        dataset_id = find_dataset_id_by_name(dataset_name)
        if dataset_id:
            print(f"\n成功找到知识库 '{dataset_name}' 的ID: {dataset_id}")
        else:
            print(f"\n未找到名为 '{dataset_name}' 的知识库")
    else:
        print("无效的选择")

def create_document():
    """功能2：创建文档"""
    print("\n===== 创建文档 =====")
    
    # 先获取知识库ID
    dataset_id = select_dataset()
    if not dataset_id:
        return
    
    # 获取文档信息
    document_name = input("\n请输入文档名称: ")
    document_content = input("请输入文档内容: ")
    
    if not document_name or not document_content:
        print("文档名称和内容不能为空")
        return
    
    # 创建文档
    print("\n创建文档中...")
    result = create_document_by_text(dataset_id, document_name, document_content)
    
    if result.get('error'):
        print(f"创建文档失败: {result.get('error')}")
        return
        
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 等待索引完成
    doc_id = result.get('document', {}).get('id')
    if not doc_id:
        print("创建文档失败")
        return
    
    wait_indexing = input("\n是否等待索引完成? (y/n): ")
    if wait_indexing.lower() == 'y':
        print("\n等待文档索引完成...")
        final_status = wait_for_document_indexing(dataset_id, doc_id, timeout=60, check_interval=3)
        
        if final_status and final_status['indexing_status'] == 'completed':
            print(f"\n文档索引已完成!")
            print(f"名称: {final_status['name']}")
            print(f"状态: {final_status['status']}")
            print(f"词数: {final_status['word_count']}")
            print(f"令牌数: {final_status['tokens']}")
        else:
            print(f"\n文档索引未在限定时间内完成，当前状态: {final_status['indexing_status'] if final_status else '未知'}")

def list_documents():
    """功能3：列出知识库中的所有文档"""
    print("\n===== 列出知识库中的文档 =====")
    
    # 选择知识库
    dataset_id = select_dataset()
    if not dataset_id:
        return
    
    # 获取文档列表
    docs = get_all_documents(dataset_id)
    
    if docs.get('error'):
        print(f"获取文档列表失败: {docs.get('error')}")
        return
        
    print(f"\n文档总数: {docs.get('total', 0)}")
    
    if docs.get('data') and len(docs['data']) > 0:
        print("\n文档列表:")
        for i, doc in enumerate(docs['data']):
            print(f"{i+1}. {doc.get('name')} - 状态: {doc.get('display_status')} - 词数: {doc.get('word_count')} - ID: {doc.get('id')}")
    else:
        print("知识库中没有文档")

def view_document():
    """功能4：查看文档详情"""
    print("\n===== 查看文档详情 =====")
    
    # 选择知识库
    dataset_id = select_dataset()
    if not dataset_id:
        return
    
    # 获取文档列表
    docs = get_all_documents(dataset_id)
    
    if docs.get('error'):
        print(f"获取文档列表失败: {docs.get('error')}")
        return
        
    if not docs.get('data') or len(docs['data']) == 0:
        print("知识库中没有文档")
        return
    
    print("\n文档列表:")
    for i, doc in enumerate(docs['data']):
        print(f"{i+1}. {doc.get('name')} - 状态: {doc.get('display_status')} - 词数: {doc.get('word_count')}")
    
    try:
        index = int(input("\n请选择要查看的文档编号: ")) - 1
        if 0 <= index < len(docs['data']):
            document_id = docs['data'][index]['id']
            doc_name = docs['data'][index]['name']
            print(f"已选择: {doc_name} (ID: {document_id})")
        else:
            print("无效的选择")
            return
    except ValueError:
        print("请输入有效的数字")
        return
    
    # 获取文档详情
    print(f"\n正在获取 '{doc_name}' 的详情...")
    result = get_document_content(dataset_id, document_id)
    
    if result.get('error'):
        print(f"获取文档详情失败: {result.get('error')}")
        return
        
    if result.get('data'):
        print("\n文档内容片段:")
        for i, segment in enumerate(result.get('data', [])):
            print(f"片段 {i+1}:")
            print(f"内容: {segment.get('content')}")
            print(f"标记: {segment.get('keywords', [])}")
            print("---")
    else:
        print("文档没有内容片段")
    
    # 显示文档状态
    doc_status = get_document_status(dataset_id, document_id)
    if doc_status:
        print("\n文档状态:")
        print(f"名称: {doc_status['name']}")
        print(f"状态: {doc_status['status']}")
        print(f"索引状态: {doc_status['indexing_status']}")
        print(f"词数: {doc_status['word_count']}")
        print(f"令牌数: {doc_status['tokens']}")

def delete_document_ui():
    """功能5：删除文档"""
    print("\n===== 删除文档 =====")
    
    # 选择知识库
    dataset_id = select_dataset()
    if not dataset_id:
        return
    
    # 获取文档列表
    docs = get_all_documents(dataset_id)
    
    if docs.get('error'):
        print(f"获取文档列表失败: {docs.get('error')}")
        return
        
    if not docs.get('data') or len(docs['data']) == 0:
        print("知识库中没有文档")
        return
    
    print("\n文档列表:")
    for i, doc in enumerate(docs['data']):
        print(f"{i+1}. {doc.get('name')} - 状态: {doc.get('display_status')} - 词数: {doc.get('word_count')}")
    
    try:
        index = int(input("\n请选择要删除的文档编号: ")) - 1
        if 0 <= index < len(docs['data']):
            document_id = docs['data'][index]['id']
            doc_name = docs['data'][index]['name']
            print(f"已选择: {doc_name} (ID: {document_id})")
        else:
            print("无效的选择")
            return
    except ValueError:
        print("请输入有效的数字")
        return
    
    # 确认删除
    confirm = input(f"\n确认删除文档 '{doc_name}'? (y/n): ")
    if confirm.lower() != 'y':
        print("已取消删除")
        return
    
    # 删除文档
    print(f"\n正在删除文档 '{doc_name}'...")
    result = delete_document(dataset_id, document_id)
    
    if result.get('success', False):
        print("文档删除成功")
    else:
        print(f"文档删除失败: {result.get('error', '未知错误')}")

def show_menu():
    """显示主菜单"""
    print("\n===== Dify API 测试工具 =====")
    print("1. 知识库ID查询")
    print("2. 向知识库创建文档")
    print("3. 列出知识库中的文档")
    print("4. 查看文档详情")
    print("5. 删除文档")
    print("0. 退出程序")
    choice = input("请选择功能 (0-5): ")
    return choice

def main():
    """主程序"""
    while True:
        choice = show_menu()
        
        if choice == '1':
            search_dataset_id()
        elif choice == '2':
            create_document()
        elif choice == '3':
            list_documents()
        elif choice == '4':
            view_document()
        elif choice == '5':
            delete_document_ui()
        elif choice == '0':
            print("程序已退出")
            break
        else:
            print("无效的选择，请重新输入")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1) 