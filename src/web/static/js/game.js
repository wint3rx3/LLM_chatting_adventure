// 게임 상태 관리
let gameState = {
    sessionId: null,
    currentEncounter: null,
    state: null
};

// DOM 요소
const welcomeScreen = document.getElementById('welcome-screen');
const gameScreen = document.getElementById('game-screen');
const gameOverScreen = document.getElementById('game-over-screen');
const startBtn = document.getElementById('start-btn');
const restartBtn = document.getElementById('restart-btn');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');

// 게임 시작 (중복 요청 방지: 클릭 즉시 비활성화, 채팅 초기화 후 1회만 요청)
startBtn.addEventListener('click', async () => {
    if (startBtn.disabled) return;
    startBtn.disabled = true;

    chatMessages.innerHTML = '';
    try {
        const response = await fetch('/api/game/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            startBtn.disabled = false;
            return;
        }

        gameState.sessionId = data.session_id;
        gameState.currentEncounter = data.encounter;
        gameState.state = data.state;

        welcomeScreen.style.display = 'none';
        gameScreen.style.display = 'block';
        updateGameState(data.state);
        addEncounterBubbles(data.messages || []);
    } catch (error) {
        console.error('게임 시작 오류:', error);
        alert('게임을 시작할 수 없습니다.');
        startBtn.disabled = false;
    }
});

// 다시 시작
restartBtn.addEventListener('click', () => {
    gameState = { sessionId: null, currentEncounter: null, state: null };
    gameOverScreen.style.display = 'none';
    welcomeScreen.style.display = 'block';
    chatMessages.innerHTML = '';
    startBtn.disabled = false;
});

// 선택 전송
sendBtn.addEventListener('click', sendChoice);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendChoice();
    }
});

async function sendChoice() {
    const input = chatInput.value.trim();
    if (!input) {
        return;
    }
    
    if (!gameState.sessionId) {
        alert('게임을 먼저 시작해주세요.');
        return;
    }
    
    // 입력 표시
    addMessage(input, 'player');
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;
    
    try {
        const response = await fetch(`/api/game/${gameState.sessionId}/choice`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ input: input })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage(data.error, 'system');
            chatInput.disabled = false;
            sendBtn.disabled = false;
            return;
        }
        
        // 선택 스토리 (유저 선택 + 그 결과로 벌어진 일)
        const story = (data.choice_mapped && (data.choice_mapped.story || data.choice_mapped.explanation)) || '';
        if (story) {
            addMessage(story, 'story');
        }
        
        // 결과 표시
        if (data.result) {
            let resultText = '';
            if (data.result.resources) {
                const resources = data.result.resources;
                const changes = [];
                if (resources.health !== undefined && resources.health !== 0) {
                    changes.push(`체력: ${resources.health > 0 ? '+' : ''}${resources.health}`);
                }
                if (resources.mental !== undefined && resources.mental !== 0) {
                    changes.push(`멘탈: ${resources.mental > 0 ? '+' : ''}${resources.mental}`);
                }
                if (resources.money !== undefined && resources.money !== 0) {
                    changes.push(`돈: ${resources.money > 0 ? '+' : ''}${resources.money}`);
                }
                if (changes.length > 0) {
                    resultText += `자원 변화: ${changes.join(', ')}\n`;
                }
            }
            
            if (data.result.gadgets && data.result.gadgets.length > 0) {
                const gadgetChanges = data.result.gadgets.map(g => {
                    if (g.action === 'acquire') {
                        return `${g.id} 획득 (+${g.amount})`;
                    } else if (g.action === 'lose') {
                        return `${g.id} 손실 (-${g.amount})`;
                    }
                }).filter(Boolean);
                if (gadgetChanges.length > 0) {
                    resultText += `가젯 변화: ${gadgetChanges.join(', ')}\n`;
                }
            }
            
            if (resultText) {
                addMessage(resultText.trim(), 'result');
            }
        }
        
        // 게임 상태 업데이트
        updateGameState(data.state);
        
        // 게임 오버 확인
        if (data.game_over) {
            gameOverScreen.style.display = 'block';
            gameScreen.style.display = 'none';
            document.getElementById('game-over-reason').textContent = data.game_over_reason || '게임이 종료되었습니다.';
            return;
        }
        
        // 다음 인카운터 표시 (말풍선·이미지)
        if (data.next_encounter) {
            gameState.currentEncounter = data.next_encounter;
            addEncounterBubbles(data.messages || []);
        }
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
        
    } catch (error) {
        console.error('선택 처리 오류:', error);
        addMessage('오류가 발생했습니다. 다시 시도해주세요.', 'system');
        chatInput.disabled = false;
        sendBtn.disabled = false;
    }
}

function updateGameState(state) {
    if (!state) return;

    const resources = state.resources || {};
    const health = Math.min(3, Math.max(0, resources.health ?? 3));
    const mental = Math.min(3, Math.max(0, resources.mental ?? 3));
    const money = Math.min(3, Math.max(0, resources.money ?? 0));

    // 아이콘 9개: 채움/빈칸
    updateIconGroup('health-icons', health, 3);
    updateIconGroup('mental-icons', mental, 3);
    updateIconGroup('money-icons', money, 3);

    // 팝업 내 세부 상태
    document.getElementById('health-value').textContent = `${health}/3`;
    document.getElementById('mental-value').textContent = `${mental}/3`;
    document.getElementById('money-value').textContent = `${money}/3`;

    const gadgets = state.gadgets || {};
    const gadgetsList = Object.keys(gadgets).join(', ') || '없음';
    document.getElementById('gadgets-list').textContent = gadgetsList;
}

function updateIconGroup(groupId, value, max) {
    const el = document.getElementById(groupId);
    if (!el) return;
    const spans = el.querySelectorAll('span');
    spans.forEach((s, i) => {
        s.classList.toggle('empty', i >= value);
    });
}

// 상태 팝업 열기/닫기
(function () {
    const overlay = document.getElementById('state-popup-overlay');
    const btn = document.getElementById('state-popup-btn');
    const closeBtn = document.getElementById('state-popup-close');
    if (!overlay || !btn || !closeBtn) return;

    btn.addEventListener('click', () => overlay.classList.add('open'));
    closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('open');
    });
})();

function addMessage(text, type = 'system') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/** 인카운터 메시지: 말풍선 여러 개 + 이미지. items: [ { type, content? }, { type, url?, alt? } ] */
function addEncounterBubbles(items) {
    if (!Array.isArray(items) || !items.length) return;
    const wrap = document.createElement('div');
    wrap.className = 'message-group encounter';
    chatMessages.appendChild(wrap);
    
    // 각 메시지를 순차적으로 딜레이를 두고 추가
    items.forEach((m, index) => {
        setTimeout(() => {
            if (m.type === 'image') {
                const url = m.url || '';
                if (!url) return;
                const img = document.createElement('img');
                img.src = url;
                img.alt = m.alt || '';
                img.className = 'message encounter-image';
                wrap.appendChild(img);
            } else {
                const text = (m.content || '').trim();
                if (!text) return;
                const bubble = document.createElement('div');
                bubble.className = 'message encounter-bubble';
                bubble.textContent = text;
                wrap.appendChild(bubble);
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, index * 500); // 각 말풍선마다 300ms 딜레이
    });
}
