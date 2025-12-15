/**
 * 透明背景PNG下载功能
 * 通过后端API将白色背景转换为透明
 */

// 全局函数：下载透明背景PNG
window.downloadTransparentPNG = async function(chartId, chartName) {
    try {
        // 获取ECharts容器
        const chartContainer = document.getElementById(chartId);
        if (!chartContainer) {
            console.error('找不到图表容器:', chartId);
            alert('找不到图表，请刷新页面后重试');
            return;
        }
        
        // 尝试获取ECharts实例（dash_echarts存储在元素上）
        let echartsInstance = null;
        
        // 方法1: 通过echarts.getInstanceByDom获取
        if (typeof echarts !== 'undefined') {
            echartsInstance = echarts.getInstanceByDom(chartContainer);
        }
        
        // 方法2: 查找内部的echarts容器
        if (!echartsInstance) {
            const innerContainer = chartContainer.querySelector('[_echarts_instance_]') || 
                                   chartContainer.querySelector('.bindbindbindbindechbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindbindarts') ||
                                   chartContainer;
            if (typeof echarts !== 'undefined') {
                echartsInstance = echarts.getInstanceByDom(innerContainer);
            }
        }
        
        // 显示加载提示
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'transparent-download-loading';
        loadingDiv.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.8);color:white;padding:20px 40px;border-radius:8px;z-index:10000;font-size:16px;';
        loadingDiv.textContent = '正在生成透明背景图片...';
        document.body.appendChild(loadingDiv);
        
        let imageData;
        
        if (echartsInstance) {
            // 使用ECharts API获取高清图片
            imageData = echartsInstance.getDataURL({
                type: 'png',
                pixelRatio: 4,
                backgroundColor: '#fff',
                excludeComponents: ['toolbox']
            });
        } else {
            // 回退方案：直接从canvas获取
            const canvas = chartContainer.querySelector('canvas');
            if (!canvas) {
                document.body.removeChild(loadingDiv);
                alert('图表尚未加载完成，请稍后重试');
                return;
            }
            
            // 获取高清图片（4倍分辨率）
            const pixelRatio = 4;
            const width = canvas.width;
            const height = canvas.height;
            
            // 创建高分辨率canvas
            const highResCanvas = document.createElement('canvas');
            highResCanvas.width = width * pixelRatio;
            highResCanvas.height = height * pixelRatio;
            const ctx = highResCanvas.getContext('2d');
            
            // 设置白色背景
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, highResCanvas.width, highResCanvas.height);
            
            // 绘制原图（放大）
            ctx.scale(pixelRatio, pixelRatio);
            ctx.drawImage(canvas, 0, 0);
            
            imageData = highResCanvas.toDataURL('image/png');
        }
        
        // 发送到后端处理
        const response = await fetch('/api/process-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image: imageData })
        });
        
        const result = await response.json();
        
        // 移除加载提示
        document.body.removeChild(loadingDiv);
        
        if (result.success) {
            // 下载透明背景图片
            const link = document.createElement('a');
            link.download = (chartName || 'chart') + '_透明背景.png';
            link.href = result.image;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            alert('处理失败: ' + (result.error || '未知错误'));
        }
        
    } catch (error) {
        console.error('下载透明背景PNG失败:', error);
        // 移除加载提示
        const loadingDiv = document.getElementById('transparent-download-loading');
        if (loadingDiv) {
            document.body.removeChild(loadingDiv);
        }
        alert('下载失败: ' + error.message);
    }
};

// 为所有图表添加透明背景下载按钮
window.addTransparentDownloadButtons = function() {
    // 查找所有图表容器
    const chartContainers = document.querySelectorAll('[id$="-chart"], [id$="-echarts"], [id="category-sales-graph"]');
    
    chartContainers.forEach(container => {
        // 检查是否已添加按钮
        if (container.parentElement.querySelector('.transparent-download-btn')) {
            return;
        }
        
        // 获取图表名称（从容器的H6标题获取）
        let chartName = 'chart';
        const parentCard = container.closest('.card, [style*="backgroundColor: white"]');
        if (parentCard) {
            const h6 = parentCard.querySelector('h6');
            if (h6) {
                chartName = h6.textContent.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '');
            }
        }
        
        // 创建下载按钮
        const btn = document.createElement('button');
        btn.className = 'transparent-download-btn';
        btn.innerHTML = '📥 透明PNG';
        btn.title = '下载透明背景PNG（适合PPT）';
        btn.style.cssText = 'position:absolute;top:5px;right:60px;z-index:100;padding:4px 8px;font-size:11px;background:#17a2b8;color:white;border:none;border-radius:4px;cursor:pointer;opacity:0.8;transition:opacity 0.2s;';
        btn.onmouseover = () => btn.style.opacity = '1';
        btn.onmouseout = () => btn.style.opacity = '0.8';
        btn.onclick = () => window.downloadTransparentPNG(container.id, chartName);
        
        // 确保父容器是相对定位
        const parent = container.parentElement;
        if (parent && getComputedStyle(parent).position === 'static') {
            parent.style.position = 'relative';
        }
        
        parent.appendChild(btn);
    });
};

// 页面加载完成后添加按钮
document.addEventListener('DOMContentLoaded', function() {
    // 延迟执行，等待图表渲染
    setTimeout(window.addTransparentDownloadButtons, 2000);
    
    // 监听DOM变化，为新添加的图表添加按钮
    const observer = new MutationObserver(function(mutations) {
        setTimeout(window.addTransparentDownloadButtons, 500);
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

console.log('透明背景下载功能已加载');
