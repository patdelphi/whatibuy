// 模拟数据和交互

function setActiveLink() {
    const currentPage = window.location.pathname.split('/').pop();
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}

// 平台同步模拟
function syncPlatform(platformName) {
    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = '同步中...';
    btn.disabled = true;
    
    // 模拟 API 调用
    setTimeout(() => {
        btn.innerText = '刚刚同步';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
        alert(`${platformName} 数据同步成功！`);
    }, 2000);
}

// AI 对话模拟
function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    const chatMessages = document.getElementById('chatMessages');
    
    // 用户消息
    const userDiv = document.createElement('div');
    userDiv.className = 'message message-user';
    userDiv.innerText = message;
    chatMessages.appendChild(userDiv);
    
    input.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 模拟 AI 思考
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message message-ai';
    typingDiv.innerText = '思考中...';
    chatMessages.appendChild(typingDiv);
    
    setTimeout(() => {
        chatMessages.removeChild(typingDiv);
        const aiDiv = document.createElement('div');
        aiDiv.className = 'message message-ai';
        
        // 简单的模拟回复逻辑
        let response = "正在分析您的数据...";
        if (message.includes('总') || message.includes('多少钱') || message.includes('消费')) {
            response = "根据您的历史记录，2023年您在所有平台的总消费为 ¥45,230.50。";
        } else if (message.includes('咖啡')) {
            response = "您今年共购买了 12 次咖啡，总计 ¥850。大部分订单来自京东。";
        } else {
            response = "我找到了 3 个相关的订单。您想要查看详细的分类统计吗？";
        }
        
        aiDiv.innerText = response;
        chatMessages.appendChild(aiDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1500);
}

// 设置保存模拟
function saveSettings() {
    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = '保存中...';
    
    setTimeout(() => {
        btn.innerText = '已保存！';
        setTimeout(() => {
            btn.innerText = originalText;
        }, 2000);
    }, 1000);
}

document.addEventListener('DOMContentLoaded', setActiveLink);
