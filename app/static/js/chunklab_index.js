document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseButton = document.getElementById('browseButton');
    const progressContainer = document.getElementById('progressContainer');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // 点击浏览按钮选择文件
    browseButton.addEventListener('click', () => fileInput.click());
    
    // 点击整个区域选择文件
    dropZone.addEventListener('click', (e) => {
        if (e.target !== browseButton) fileInput.click();
    });
    
    // 拖拽事件处理
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('drop-zone-active');
        });
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drop-zone-active');
    });
    
    // 拖拽事件 - 放置
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drop-zone-active');
        
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            uploadFile();
        }
    });
    
    // 选择文件后自动上传
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) uploadFile();
    });
    
    // 上传文件
    function uploadFile() {
        const file = fileInput.files[0];
        if (!file) return;
        
        // 检查文件类型
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        const allowedExts = document.getElementById('allowedExtensions').dataset.extensions.split(',').map(ext => ext.trim());
        
        if (!allowedExts.includes(fileExt)) {
            Swal.fire({
                icon: 'error',
                title: '不支持的文件类型',
                text: `请上传以下格式的文件: ${allowedExts.join(', ')}`,
                confirmButtonColor: '#2c3e50'
            });
            return;
        }
        
        // 显示进度条
        progressContainer.style.display = 'block';
        
        const formData = new FormData();
        formData.append('file', file);
        
        // 设置XHR请求
        const xhr = new XMLHttpRequest();
        
        // 进度事件
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                uploadProgress.style.width = percentComplete + '%';
                uploadProgress.textContent = percentComplete + '%';
                uploadStatus.textContent = '上传中...';
            }
        });
        
        // 完成事件
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                uploadProgress.style.width = '100%';
                uploadStatus.textContent = '上传完成，正在刷新...';
                setTimeout(() => window.location.reload(), 600);
            } else {
                handleUploadError(xhr);
            }
        });
        
        // 错误事件
        xhr.addEventListener('error', () => handleUploadError(xhr));
        
        // 发送请求
        xhr.open('POST', '/chunklab/upload', true);
        xhr.send(formData);
    }
    
    // 处理上传错误
    function handleUploadError(xhr) {
        let errorMessage = '上传过程中发生错误';
        
        try {
            const response = JSON.parse(xhr.responseText);
            errorMessage = response.message || errorMessage;
        } catch (error) {
            console.error('解析错误响应失败:', error);
        }
        
        uploadProgress.classList.add('bg-danger');
        uploadStatus.textContent = '上传失败';
        
        Swal.fire({
            icon: 'error',
            title: '上传失败',
            text: errorMessage,
            confirmButtonColor: '#2c3e50'
        });
    }
});

// 确认删除文档
function confirmDelete(url, filename) {
    Swal.fire({
        title: '确认删除',
        html: `您确定要删除文档 <strong>${filename}</strong> 吗？<br>此操作将同时删除文件及其所有切块。`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed) {
            // 删除文档
            fetch(url, { method: 'DELETE' })
                .then(response => response.json())
                .then(() => {
                    // 简化成功处理
                    setTimeout(() => window.location.reload(), 500);
                })
                .catch(error => {
                    console.error('删除文档失败:', error);
                    Swal.fire({
                        icon: 'error',
                        title: '删除失败',
                        text: '删除文档时发生错误',
                        confirmButtonColor: '#2c3e50'
                    });
                });
        }
    });
} 