/**
 * chunkgo_chunking.js
 * 
 * 职责：处理文档批量切块相关功能
 * 
 * 主要功能：
 * 1. 选择并验证切块参数（策略、大小、重叠度）
 * 2. 批量文档切块任务处理
 * 3. 切块任务进度跟踪与状态更新
 */

document.addEventListener('DOMContentLoaded', function() {
    const folderId = window.location.pathname.split('/').pop();
    
    // 切块相关元素
    const startBatchChunkBtn = document.getElementById('startBatchChunkBtn');
    const chunkStrategy = document.getElementById('chunkStrategy');
    const chunkSize = document.getElementById('chunkSize');
    const overlap = document.getElementById('overlap');
    
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
}); 