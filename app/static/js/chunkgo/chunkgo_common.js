/**
 * chunkgo_common.js
 * 
 * 职责：提供ChunkGo功能的公共功能模块
 * 
 * 主要功能：
 * 1. 文档全选/取消全选功能
 * 2. 任务状态轮询处理功能（供其他模块调用）
 */

document.addEventListener('DOMContentLoaded', function() {
    const selectAllDocs = document.getElementById('selectAllDocs');
    const folderId = window.location.pathname.split('/').pop();

    // 全选/取消全选文档
    if (selectAllDocs) {
        selectAllDocs.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.document-checkbox:not(:disabled)');
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllDocs.checked;
            });
        });
    }

    // 轮询任务状态
    window.pollTaskStatus = function(taskId) {
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
                        // 任务完成时显示通知，延迟刷新页面以确保通知显示
                        const statusText = data.status === 'completed' ? '已完成' : '失败';
                        const title = `任务${statusText}：${data.name}`;
                        const message = `成功: ${data.success_count}，失败: ${data.error_count}`;
                        
                        // 使用SweetAlert2显示通知，并在用户关闭或自动关闭后刷新页面
                        Swal.fire({
                            icon: data.status === 'completed' ? 'success' : 'error',
                            title: title,
                            text: message,
                            timer: 3000,
                            showConfirmButton: false,
                            willClose: () => {
                                window.location.reload();
                            }
                        });
                    }
                })
                .catch(error => {
                    console.error('轮询任务状态失败:', error);
                    clearInterval(intervalId);
                });
        }, 2000);
    }
}); 