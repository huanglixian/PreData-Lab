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

    // 禁用不符合条件的文档选择框（未切块或正在推送的文档）
    document.querySelectorAll('.document-checkbox').forEach(checkbox => {
        const docItem = checkbox.closest('.document-item');
        const hasToDifyBtn = docItem.querySelector('.btn-info') !== null;
        
        if (!hasToDifyBtn) {
            checkbox.disabled = true;
            checkbox.title = '该文档未完成切块或正在推送中，无法选择';
        }
    });
    
    // 全选按钮
    document.getElementById('selectAll').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.document-checkbox:not(:disabled)').forEach(checkbox => {
            checkbox.checked = true;
        });
    });

    // 全不选按钮
    document.getElementById('deselectAll').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.document-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
    });

    // 批量ToDify按钮
    document.getElementById('batchToDify').addEventListener('click', function() {
        const checkedDocs = document.querySelectorAll('.document-checkbox:checked');
        if (checkedDocs.length === 0) {
            showToast('warning', '请先选择要推送的文档');
            return;
        }
        
        // 获取所有选中的文档ID
        const selectedIds = Array.from(checkedDocs).map(cb => cb.value);
        
        // 设置批量模式标记
        const toDifyModal = document.getElementById('toDifyModal');
        toDifyModal.setAttribute('data-batch', 'true');
        
        // 打开模态框（简化调用方式）
        const modal = new bootstrap.Modal(toDifyModal);
        
        // 设置触发按钮
        const batchBtn = document.getElementById('batchToDify');
        batchBtn.setAttribute('data-batch', 'true');
        batchBtn.setAttribute('data-document-ids', selectedIds.join(','));
        
        // 直接显示模态框
        modal.show();
        
        // 手动触发show.bs.modal事件
        toDifyModal.dispatchEvent(new CustomEvent('show.bs.modal', {
            bubbles: true,
            detail: { relatedTarget: batchBtn }
        }));
    });
});

// 全局Toast通知函数
function showToast(type, message) {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    const toast = new bootstrap.Toast(toastElement, {
        delay: 5000,
        autohide: true
    });
    
    toast.show();
    
    // 自动移除
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1050';
    document.body.appendChild(container);
    return container;
}

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