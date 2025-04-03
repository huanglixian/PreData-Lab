// 缓存DOM元素
let els = {};

// 获取文件扩展名的函数
function getFileExtension(filename) {
    return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 1).toLowerCase();
}

// 检查是否有正在进行的处理
document.addEventListener('DOMContentLoaded', function() {
    // 缓存常用DOM元素
    cacheElements();
    
    // 获取隐藏字段中的文档信息
    const documentStatus = els.statusInput?.value;
    const documentFilename = els.filenameInput?.value;
    const documentId = els.idInput?.value;
    
    if (documentStatus === '处理中') {
        // 显示进度条并开始轮询
        startPollingStatus();
    }
    
    // 获取文件扩展名并加载对应策略
    if (documentFilename) {
        fetchAvailableStrategies(getFileExtension(documentFilename));
    }
    
    // 添加表单验证和提交处理
    initFormHandlers();
});

// 缓存常用DOM元素，减少反复查询
function cacheElements() {
    els = {
        statusInput: document.getElementById('documentStatus'),
        filenameInput: document.getElementById('documentFilename'),
        idInput: document.getElementById('documentId'),
        progressContainer: document.getElementById('progressContainer'),
        submitButton: document.getElementById('submitButton'),
        progressBar: document.getElementById('chunkProgress'),
        progressStatus: document.getElementById('processingStatus'),
        chunkForm: document.getElementById('chunkForm'),
        strategySelect: document.getElementById('chunkStrategy'),
        chunkSizeInput: document.getElementById('chunkSize'),
        overlapInput: document.getElementById('overlap')
    };
}

// 获取可用的切块策略
async function fetchAvailableStrategies(fileExt) {
    try {
        const response = await fetchWithTimeout(`/chunklab/strategies/for-filetype?file_ext=${fileExt}`);
        if (!response.ok) return;
        
        const result = await response.json();
        const strategies = result.strategies;
        
        // 如果没有找到支持的策略，显示提示信息
        if (!strategies.length) {
            Swal.fire({
                icon: 'warning',
                title: '注意',
                text: `没有找到支持${fileExt}文件类型的切块策略`,
                confirmButtonColor: '#2c3e50'
            });
            return;
        }
        
        // 使用文档片段一次性更新DOM，避免多次重排
        const fragment = document.createDocumentFragment();
        strategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.name;
            option.textContent = strategy.display_name;
            fragment.appendChild(option);
        });
        
        // 清空现有选项并添加可用策略
        els.strategySelect.innerHTML = '';
        els.strategySelect.appendChild(fragment);
        
        // 如果只有一个策略，添加提示
        if (strategies.length === 1) {
            const infoEl = document.createElement('div');
            infoEl.className = 'form-text text-info';
            infoEl.textContent = `${fileExt}文件类型仅支持${strategies[0].display_name}`;
            els.strategySelect.parentNode.appendChild(infoEl);
        }
    } catch (error) {
        console.error('获取切块策略出错:', error.message);
    }
}

// 带超时的fetch，超时时间默认8秒
async function fetchWithTimeout(url, options = {}, timeout = 8000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        if (error.name === 'AbortError') {
            throw new Error('请求超时');
        }
        throw error;
    }
}

// 轮询任务状态
let pollingTimer = null;
let lastProgress = 0;
function startPollingStatus() {
    if (els.progressContainer) els.progressContainer.style.display = 'block';
    if (els.submitButton) els.submitButton.disabled = true;
    
    // 立即显示初始状态
    if (els.progressStatus) els.progressStatus.textContent = '正在初始化...';
    
    if (pollingTimer) clearInterval(pollingTimer);
    // 立即检查一次状态
    checkTaskStatus();
    pollingTimer = setInterval(checkTaskStatus, 1000);
}

// 检查任务状态
async function checkTaskStatus() {
    if (!els.idInput?.value) return;
    
    try {
        const response = await fetchWithTimeout(`/chunklab/documents/${els.idInput.value}/chunk/status`);
        const result = await response.json();
        
        const status = result.status;
        
        if (status === 'processing') {
            const progress = result.progress || 0;
            // 只有进度有变化时才更新UI
            if (Math.abs(progress - lastProgress) >= 1) {
                lastProgress = progress;
                
                if (els.progressBar) {
                    els.progressBar.style.width = `${progress}%`;
                    els.progressBar.textContent = `${progress}%`;
                    els.progressBar.setAttribute('aria-valuenow', progress);
                }
                
                // 根据进度更新状态文本
                if (els.progressStatus) {
                    if (progress < 10) els.progressStatus.textContent = '正在初始化...';
                    else if (progress < 50) els.progressStatus.textContent = '正在分析文档...';
                    else if (progress < 80) els.progressStatus.textContent = '正在保存切块结果...';
                    else els.progressStatus.textContent = '即将完成...';
                }
            }
        } else if (status === 'success') {
            // 处理完成
            if (els.progressBar) {
                els.progressBar.style.width = '100%';
                els.progressBar.textContent = '100%';
                els.progressBar.setAttribute('aria-valuenow', 100);
                els.progressBar.classList.remove('progress-bar-animated');
            }
            if (els.progressStatus) {
                els.progressStatus.textContent = '处理完成！';
            }
            
            clearInterval(pollingTimer);
            
            // 显示成功消息并刷新页面
            Swal.fire({
                icon: 'success',
                title: '切块成功',
                text: '文档切块已完成',
                confirmButtonColor: '#2c3e50',
                showConfirmButton: false,
                timer: 1500
            }).then(() => window.location.reload());
            
        } else if (status === 'error') {
            // 处理出错
            if (els.progressBar) {
                els.progressBar.classList.replace('bg-primary', 'bg-danger');
                els.progressBar.classList.remove('progress-bar-animated');
            }
            if (els.progressStatus) {
                els.progressStatus.textContent = `处理错误: ${result.message || '未知错误'}`;
            }
            
            clearInterval(pollingTimer);
            
            // 显示错误信息
            Swal.fire({
                icon: 'error',
                title: '切块失败',
                text: result.message || '处理过程中发生错误',
                confirmButtonColor: '#2c3e50'
            });
            
            if (els.submitButton) els.submitButton.disabled = false;
        }
    } catch (error) {
        let errorMessage = '检查任务状态出错';
        if (error.message === '请求超时') {
            errorMessage = '检查状态请求超时，将继续尝试';
            // 轻微增加进度，让用户感知有活动
            if (lastProgress < 95 && els.progressStatus) {
                lastProgress += 0.5;
                els.progressStatus.textContent = '通信中，请耐心等待...';
            }
        }
        console.error(errorMessage);
        // 发生错误时不要立即放弃，等待下一次轮询
    }
}

// 初始化表单处理
function initFormHandlers() {
    if (!els.chunkForm) return;
    
    // 表单提交
    els.chunkForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 表单验证
        const form = this;
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }
        
        const chunkSize = parseInt(els.chunkSizeInput?.value || 0);
        const overlap = parseInt(els.overlapInput?.value || 0);
        
        if (chunkSize <= 0) {
            if (els.chunkSizeInput) els.chunkSizeInput.classList.add('is-invalid');
            return;
        }
        
        if (overlap < 0 || overlap >= chunkSize) {
            if (els.overlapInput) els.overlapInput.classList.add('is-invalid');
            return;
        }
        
        // 构建表单数据
        const formData = new FormData(form);
        
        // 显示加载状态
        const submitButton = form.querySelector('button[type="submit"]');
        if (!submitButton) return;
        
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
        
        try {
            const documentId = els.idInput?.value;
            const documentStatus = els.statusInput?.value;
            
            // 提前显示进度容器减少等待感
            if (els.progressContainer) {
                els.progressContainer.style.display = 'block';
                if (els.progressStatus) els.progressStatus.textContent = '准备处理...';
            }
            
            // 确认是否覆盖现有切块
            if (documentStatus === '已切块') {
                const result = await Swal.fire({
                    title: '确认重新切块',
                    text: '文档已有切块结果，重新切块将覆盖现有结果，是否继续？',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#2c3e50',
                    cancelButtonColor: '#732626',
                    confirmButtonText: '确定',
                    cancelButtonText: '取消'
                });
                
                if (!result.isConfirmed) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                    if (els.progressContainer) els.progressContainer.style.display = 'none';
                    return;
                }
            }
            
            const response = await fetchWithTimeout(`/chunklab/documents/${documentId}/chunk`, {
                method: 'POST',
                body: formData
            }, 15000); // 切块请求给15秒超时
            
            const result = await response.json();
            
            if (response.ok) {
                if (result.status === 'processing') {
                    // 重置进度，确保会更新
                    lastProgress = -1;
                    startPollingStatus();
                } else {
                    Swal.fire({
                        icon: 'success',
                        title: '切块成功',
                        text: '文档切块已完成',
                        confirmButtonColor: '#2c3e50',
                        showConfirmButton: false,
                        timer: 1500
                    }).then(() => window.location.reload());
                }
            } else {
                throw new Error(result.detail || '切块失败');
            }
        } catch (error) {
            let errorMessage = error.message || '处理请求时发生错误';
            if (error.message === '请求超时') {
                errorMessage = '服务器响应超时，请稍后查看处理结果或重试';
            }
            
            Swal.fire({
                icon: 'error',
                title: '切块失败',
                text: errorMessage,
                confirmButtonColor: '#2c3e50'
            });
            
            // 恢复按钮状态
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
            
            // 隐藏进度条
            if (els.progressContainer) els.progressContainer.style.display = 'none';
        }
    });
    
    // 输入验证 - 使用事件委托减少事件监听器
    if (els.chunkForm) {
        els.chunkForm.addEventListener('input', function(e) {
            if (e.target.id === 'chunkSize' || e.target.id === 'overlap') {
                validateInputs();
            }
        });
    }
}

// 验证输入字段
const validateInputs = debounce(function() {
    const chunkSize = parseInt(els.chunkSizeInput?.value || 0);
    const overlap = parseInt(els.overlapInput?.value || 0);
    
    if (els.chunkSizeInput) {
        els.chunkSizeInput.classList.toggle('is-invalid', chunkSize <= 0);
    }
    
    if (els.overlapInput && chunkSize > 0) {
        els.overlapInput.classList.toggle('is-invalid', overlap < 0 || overlap >= chunkSize);
    }
}, 200);

// 简单的防抖函数，减少频繁调用
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}