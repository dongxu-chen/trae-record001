let mapManager = null;
let simulationController = null;

document.addEventListener('DOMContentLoaded', function() {
    initApp();
});

function initApp() {
    try {
        mapManager = new MapManager();
        simulationController = new SimulationController(mapManager);

        console.log('交通态势仿真系统已初始化');
        console.log('可用功能:');
        console.log('  - 元胞自动机交通流仿真');
        console.log('  - 车速分布热力图');
        console.log('  - 排队长度实时监控');
        console.log('  - 拥堵指数计算');
        console.log('  - 信号配时优化 (爬山法/遗传算法/网格搜索)');
    } catch (error) {
        console.error('应用初始化失败:', error);
        showErrorMessage('应用初始化失败，请刷新页面重试');
    }
}

function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #e74c3c;
        color: white;
        padding: 20px 40px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 10000;
        text-align: center;
    `;
    errorDiv.innerHTML = `
        <h3 style="margin-bottom: 10px;">❌ 错误</h3>
        <p>${message}</p>
    `;
    document.body.appendChild(errorDiv);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
    }

    @keyframes slideUp {
        from {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
        to {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        }
    }
`;
document.head.appendChild(style);
