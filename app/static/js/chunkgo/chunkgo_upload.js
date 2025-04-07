/**
 * chunkgo_upload.js
 * 
 * 职责：处理文件上传和文档删除相关功能
 * 
 * 主要功能：
 * 1. 文件选择和上传处理
 * 2. 文件夹选择和上传处理
 * 3. 文件拖放上传处理
 * 4. 上传进度显示
 * 5. 文档删除功能
 */

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
    const folderId = window.location.pathname.split('/').pop();
    
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