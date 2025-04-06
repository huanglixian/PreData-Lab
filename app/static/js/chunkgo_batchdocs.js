document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const browseButton = document.getElementById('browseButton');
    const browseFolderButton = document.getElementById('browseFolderButton');
    const progressContainer = document.getElementById('progressContainer');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadStatus = document.getElementById('uploadStatus');
    const selectAllDocs = document.getElementById('selectAllDocs');
    const folderId = window.location.pathname.split('/').pop();
    
    // Dify相关元素
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    const difyKnowledgeBase = document.getElementById('difyKnowledgeBase');
    const startBatchDifyBtn = document.getElementById('startBatchDifyBtn');
    
    // 切块相关元素
    const startBatchChunkBtn = document.getElementById('startBatchChunkBtn');
    const chunkStrategy = document.getElementById('chunkStrategy');
    const chunkSize = document.getElementById('chunkSize');
    const overlap = document.getElementById('overlap');
    
    // 文件上传处理 - 点击选择文件按钮
    if (browseButton) {
        browseButton.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // 文件上传处理 - 点击选择文件夹按钮
    if (browseFolderButton) {
        browseFolderButton.addEventListener('click', function() {
            folderInput.click();
        });
    }
    
    // 文件上传处理 - 监听文件选择
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                uploadFiles(fileInput.files);
            }
        });
    }
    
    // 文件夹上传处理 - 监听文件夹选择
    if (folderInput) {
        folderInput.addEventListener('change', function() {
            if (folderInput.files.length > 0) {
                uploadFiles(folderInput.files);
            }
        });
    }
    
    // 拖放处理
    if (dropZone) {
        // 阻止拖放的默认行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        // 高亮拖放区域
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        // 处理拖放文件
        dropZone.addEventListener('drop', handleDrop, false);
    }
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropZone.classList.add('drop-zone-active');
    }
    
    function unhighlight() {
        dropZone.classList.remove('drop-zone-active');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            uploadFiles(files);
        }
    }
    
    // 上传文件到服务器
    function uploadFiles(files) {
        if (files.length === 0) return;
        
        // 显示进度条
        progressContainer.style.display = 'block';
        
        // 创建FormData对象
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        
        // 显示上传信息
        uploadStatus.textContent = `准备上传 ${files.length} 个文件...`;
        
        // 创建XHR对象
        const xhr = new XMLHttpRequest();
        
        // 监听上传进度
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                uploadProgress.style.width = percentComplete + '%';
                uploadProgress.textContent = percentComplete + '%';
                uploadProgress.setAttribute('aria-valuenow', percentComplete);
                
                uploadStatus.textContent = `正在上传... ${percentComplete}%`;
            }
        });
        
        // 上传完成处理
        xhr.addEventListener('load', function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    
                    uploadStatus.textContent = `上传完成！成功: ${response.success.length}, 失败: ${response.failed.length}`;
                    
                    // 显示成功消息
                    showToast('success', `上传成功：${response.success.length} 个文件，失败：${response.failed.length} 个文件`);
                    
                    // 如果有失败的文件，显示详细信息
                    if (response.failed.length > 0) {
                        let failMessage = "上传失败的文件:\n";
                        response.failed.forEach(function(file) {
                            failMessage += `- ${file.filename}: ${file.reason}\n`;
                        });
                        console.error(failMessage);
                    }
                    
                    // 1秒后刷新页面
                    setTimeout(function() {
                        window.location.reload();
                    }, 1000);
                    
                } catch (e) {
                    uploadStatus.textContent = "解析响应失败";
                    showToast('error', '处理上传响应时发生错误');
                }
            } else {
                uploadStatus.textContent = `上传失败: ${xhr.status} ${xhr.statusText}`;
                showToast('error', `上传失败: ${xhr.status} ${xhr.statusText}`);
            }
        });
        
        // 上传错误处理
        xhr.addEventListener('error', function() {
            uploadStatus.textContent = "上传失败: 网络错误";
            showToast('error', '上传失败: 网络错误');
        });
        
        // 开始上传
        xhr.open('POST', `/chunkgo/folders/${folderId}/upload`, true);
        xhr.send(formData);
    }
    
    // 全选/取消全选文档
    if (selectAllDocs) {
        selectAllDocs.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.document-checkbox:not(:disabled)');
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllDocs.checked;
            });
        });
    }
    
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
    
    // 批量切块
    if (startBatchChunkBtn) {
        startBatchChunkBtn.addEventListener('click', function() {
            // 获取选中的文档ID
            const selectedDocs = Array.from(document.querySelectorAll('.document-checkbox:checked')).map(el => parseInt(el.value));
            
            // 验证参数
            if (!chunkStrategy.value) {
                showToast('warning', '请选择切块策略');
                return;
            }
            
            if (!chunkSize.value || chunkSize.value < 50 || chunkSize.value > 2000) {
                showToast('warning', '请输入有效的切块大小(50-2000)');
                return;
            }
            
            if (overlap.value < 0 || overlap.value > 200) {
                showToast('warning', '请输入有效的重叠度(0-200)');
                return;
            }
            
            // 如果没有选中任何文档，提示确认
            if (selectedDocs.length === 0) {
                Swal.fire({
                    title: '未选择文档',
                    text: '您没有选择任何文档，将处理文件夹中所有可切块的文档。确定继续吗？',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonColor: '#3085d6',
                    cancelButtonColor: '#d33',
                    confirmButtonText: '确定',
                    cancelButtonText: '取消'
                }).then((result) => {
                    if (result.isConfirmed) {
                        startBatchChunkProcess(selectedDocs);
                    }
                });
            } else {
                startBatchChunkProcess(selectedDocs);
            }
        });
    }
    
    // 开始批量切块处理
    function startBatchChunkProcess(docIds) {
        startBatchChunkBtn.disabled = true;
        startBatchChunkBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>处理中...';
        
        // 准备请求数据
        const requestData = {
            document_ids: docIds,
            chunk_strategy: chunkStrategy.value,
            chunk_size: parseInt(chunkSize.value),
            overlap: parseInt(overlap.value)
        };
        
        // 发送请求
        fetch(`/chunkgo/folders/${folderId}/chunk`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'processing') {
                showToast('success', '批量切块任务已启动');
                // 1秒后切换到任务标签页并刷新页面
                setTimeout(function() {
                    document.getElementById('chunk-tasks-tab').click();
                    // 轮询任务状态
                    pollTaskStatus(data.task_id);
                }, 1000);
            } else {
                showToast('error', data.message || '启动批量切块任务失败');
                startBatchChunkBtn.disabled = false;
                startBatchChunkBtn.innerHTML = '<i class="fas fa-cut me-2"></i>批量切块';
            }
        })
        .catch(error => {
            showToast('error', '启动批量切块任务失败: ' + error.message);
            startBatchChunkBtn.disabled = false;
            startBatchChunkBtn.innerHTML = '<i class="fas fa-cut me-2"></i>批量切块';
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
    
    // 轮询任务状态
    function pollTaskStatus(taskId) {
        const taskElement = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
        
        // 如果还没有该任务，刷新页面
        if (!taskElement) {
            window.location.reload();
            return;
        }
        
        // 如果已经有任务，开始轮询状态
        const intervalId = setInterval(function() {
            fetch(`/chunkgo/tasks/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(intervalId);
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('轮询任务状态失败:', error);
                    clearInterval(intervalId);
                });
        }, 2000);
    }
    
    // 删除文档按钮
    document.querySelectorAll('.delete-doc-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const docId = this.getAttribute('data-doc-id');
            const docName = this.getAttribute('data-doc-name');
            
            Swal.fire({
                title: '确认删除',
                text: `确定要删除文档 "${docName}" 吗？此操作不可恢复！`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#732626',
                cancelButtonColor: '#34495e',
                confirmButtonText: '确定删除',
                cancelButtonText: '取消'
            }).then((result) => {
                if (result.isConfirmed) {
                    deleteDocument(docId);
                }
            });
        });
    });
    
    // 删除文档
    function deleteDocument(docId) {
        fetch(`/chunklab/documents/${docId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast('success', data.message);
                // 移除文档元素或刷新页面
                const docElement = document.querySelector(`.document-item input[value="${docId}"]`).closest('.document-item');
                if (docElement) {
                    docElement.remove();
                } else {
                    window.location.reload();
                }
            } else {
                showToast('error', data.detail || '删除文档失败');
            }
        })
        .catch(error => {
            showToast('error', '删除文档失败: ' + error.message);
        });
    }
}); 