/**
 * chunkgo_dify.js
 * 
 * 职责：处理与Dify平台集成的相关功能
 * 
 * 主要功能：
 * 1. Dify API连接测试
 * 2. 获取Dify知识库列表
 * 3. 批量推送文档到Dify知识库
 * 4. Dify推送任务状态管理
 */

document.addEventListener('DOMContentLoaded', function() {
    const folderId = window.location.pathname.split('/').pop();
    
    // Dify相关元素
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    const difyKnowledgeBase = document.getElementById('difyKnowledgeBase');
    const startBatchDifyBtn = document.getElementById('startBatchDifyBtn');
    
    // 测试Dify连接
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', function() {
            testConnectionBtn.disabled = true;
            testConnectionBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>正在连接...';
            
            fetch('/chunkgo/dify/test-connection')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast('success', '连接成功！正在获取知识库列表...');
                        // 获取知识库列表
                        fetchKnowledgeBases();
                    } else {
                        showToast('error', `连接失败: ${data.message}`);
                        testConnectionBtn.disabled = false;
                        testConnectionBtn.innerHTML = '<i class="fas fa-plug me-2"></i>测试连接';
                    }
                })
                .catch(error => {
                    showToast('error', '连接测试失败: ' + error.message);
                    testConnectionBtn.disabled = false;
                    testConnectionBtn.innerHTML = '<i class="fas fa-plug me-2"></i>测试连接';
                });
        });
    }
    
    // 获取Dify知识库列表
    function fetchKnowledgeBases() {
        fetch('/chunkgo/dify/knowledge-bases')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.data && data.data.length > 0) {
                    // 清空现有选项
                    difyKnowledgeBase.innerHTML = '';
                    
                    // 添加默认选项
                    let defaultOption = document.createElement('option');
                    defaultOption.value = '';
                    defaultOption.disabled = true;
                    defaultOption.selected = true;
                    defaultOption.textContent = '请选择知识库';
                    difyKnowledgeBase.appendChild(defaultOption);
                    
                    // 添加知识库选项
                    data.data.forEach(kb => {
                        let option = document.createElement('option');
                        option.value = kb.id;
                        option.textContent = kb.name;
                        difyKnowledgeBase.appendChild(option);
                    });
                    
                    // 启用推送按钮
                    startBatchDifyBtn.disabled = false;
                    
                    // 恢复测试连接按钮
                    testConnectionBtn.disabled = false;
                    testConnectionBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i>连接成功';
                    testConnectionBtn.classList.remove('btn-outline-primary');
                    testConnectionBtn.classList.add('btn-success');
                } else {
                    showToast('error', '未找到知识库或获取失败');
                    testConnectionBtn.disabled = false;
                    testConnectionBtn.innerHTML = '<i class="fas fa-plug me-2"></i>测试连接';
                }
            })
            .catch(error => {
                showToast('error', '获取知识库列表失败: ' + error.message);
                testConnectionBtn.disabled = false;
                testConnectionBtn.innerHTML = '<i class="fas fa-plug me-2"></i>测试连接';
            });
    }
    
    // 批量推送到Dify
    if (startBatchDifyBtn) {
        startBatchDifyBtn.addEventListener('click', function() {
            // 获取选中的文档ID
            const selectedDocs = Array.from(document.querySelectorAll('.document-checkbox:checked')).map(el => parseInt(el.value));
            
            // 验证参数
            if (!difyKnowledgeBase.value) {
                showToast('warning', '请选择知识库');
                return;
            }
            
            // 如果没有选中任何文档，提示确认
            if (selectedDocs.length === 0) {
                Swal.fire({
                    title: '未选择文档',
                    text: '您没有选择任何文档，将处理文件夹中所有已切块的文档。确定继续吗？',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonColor: '#3085d6',
                    cancelButtonColor: '#d33',
                    confirmButtonText: '确定',
                    cancelButtonText: '取消'
                }).then((result) => {
                    if (result.isConfirmed) {
                        startBatchDifyProcess(selectedDocs);
                    }
                });
            } else {
                startBatchDifyProcess(selectedDocs);
            }
        });
    }
    
    // 开始批量推送到Dify处理
    function startBatchDifyProcess(docIds) {
        startBatchDifyBtn.disabled = true;
        startBatchDifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>处理中...';
        
        // 准备请求数据
        const requestData = {
            document_ids: docIds,
            dataset_id: difyKnowledgeBase.value
        };
        
        // 发送请求
        fetch(`/chunkgo/folders/${folderId}/to-dify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'processing') {
                showToast('success', '批量推送任务已启动');
                // 1秒后切换到任务标签页并刷新页面
                setTimeout(function() {
                    document.getElementById('dify-tasks-tab').click();
                    // 轮询任务状态
                    pollTaskStatus(data.task_id);
                }, 1000);
            } else {
                showToast('error', data.message || '启动批量推送任务失败');
                startBatchDifyBtn.disabled = false;
                startBatchDifyBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>批量推送';
            }
        })
        .catch(error => {
            showToast('error', '启动批量推送任务失败: ' + error.message);
            startBatchDifyBtn.disabled = false;
            startBatchDifyBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>批量推送';
        });
    }
}); 