let socket = null;
let draggedCard = null;
let cardVersions = new Map();

function initWebSocket(boardId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/board/${boardId}/`;
    socket = new WebSocket(wsUrl);

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'card_moved') {
            handleCardMoved(data);
        } else if (data.type === 'card_updated') {
            handleCardUpdated(data);
        } else if (data.type === 'conflict_detected') {
            handleConflictDetected(data);
        }
    };

    socket.onclose = function(e) {
        console.error('WebSocket closed unexpectedly');
    };
}

function handleCardMoved(data) {
    const cardElement = document.querySelector(`[data-card-id="${data.card_id}"]`);
    if (cardElement) {
        const oldList = document.querySelector(`[data-list-id="${data.old_list_id}"] .cards-container`);
        const newList = document.querySelector(`[data-list-id="${data.new_list_id}"] .cards-container`);
        
        if (oldList && oldList.contains(cardElement)) {
            oldList.removeChild(cardElement);
        }
        
        if (newList) {
            const cards = Array.from(newList.children);
            if (data.new_order < cards.length) {
                newList.insertBefore(cardElement, cards[data.new_order]);
            } else {
                newList.appendChild(cardElement);
            }
        }

        if (data.new_version !== undefined) {
            cardVersions.set(parseInt(data.card_id), data.new_version);
        }
    }
}

function handleCardUpdated(data) {
    console.log('Card updated:', data);
}

function handleConflictDetected(data) {
    const cardElement = document.querySelector(`[data-card-id="${data.card_id}"]`);
    if (cardElement) {
        cardElement.classList.add('conflict');
        
        const conflictBanner = document.createElement('div');
        conflictBanner.className = 'conflict-banner';
        conflictBanner.innerHTML = `
            <div class="alert alert-warning alert-sm mb-0">
                <strong>冲突检测!</strong> ${data.message}
                <button class="btn btn-sm btn-primary ms-2" onclick="refreshBoard()">刷新</button>
            </div>
        `;
        cardElement.insertBefore(conflictBanner, cardElement.firstChild);
        
        setTimeout(() => {
            if (conflictBanner.parentNode) {
                conflictBanner.remove();
                cardElement.classList.remove('conflict');
            }
        }, 10000);
    }
    
    console.warn('Conflict detected:', data.message);
}

async function refreshBoard() {
    await loadBoard();
}

async function loadBoard() {
    try {
        const response = await fetch('/api/board/boards/');
        const boards = await response.json();
        
        cardVersions.clear();
        
        if (boards.length > 0) {
            const board = boards[0];
            board.lists.forEach(list => {
                list.cards.forEach(card => {
                    cardVersions.set(card.id, card.version);
                });
            });
            
            initWebSocket(board.id);
            renderBoard(board);
        }
    } catch (error) {
        console.error('Error loading board:', error);
        showDemoBoard();
    }
}

function renderBoard(board) {
    const container = document.getElementById('board-container');
    container.innerHTML = '';

    board.lists.forEach(list => {
        const listColumn = createListColumn(list);
        container.appendChild(listColumn);
    });
}

function createListColumn(list) {
    const column = document.createElement('div');
    column.className = 'list-column';
    column.setAttribute('data-list-id', list.id);

    const header = document.createElement('div');
    header.className = 'list-header';
    header.textContent = list.name;
    column.appendChild(header);

    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'cards-container';
    cardsContainer.setAttribute('data-list-id', list.id);

    list.cards.forEach(card => {
        const cardElement = createCardElement(card);
        cardsContainer.appendChild(cardElement);
    });

    setupDropTarget(cardsContainer);
    column.appendChild(cardsContainer);

    return column;
}

function createCardElement(card) {
    const cardElement = document.createElement('div');
    cardElement.className = `card-item priority-${card.priority}`;
    cardElement.setAttribute('data-card-id', card.id);
    cardElement.setAttribute('data-version', card.version);
    cardElement.setAttribute('draggable', 'true');

    const title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = card.title;
    cardElement.appendChild(title);

    if (card.description) {
        const desc = document.createElement('div');
        desc.className = 'card-description mt-2 small text-muted';
        desc.textContent = card.description.substring(0, 100);
        if (card.description.length > 100) desc.textContent += '...';
        cardElement.appendChild(desc);
    }

    const footer = document.createElement('div');
    footer.className = 'card-footer';
    
    if (card.story_points > 0) {
        const points = document.createElement('span');
        points.className = 'story-points';
        points.textContent = `${card.story_points} SP`;
        footer.appendChild(points);
    }

    if (card.assignee) {
        const assignee = document.createElement('span');
        assignee.textContent = card.assignee.username;
        footer.appendChild(assignee);
    }

    cardElement.appendChild(footer);

    setupDragEvents(cardElement);

    return cardElement;
}

function setupDragEvents(cardElement) {
    cardElement.addEventListener('dragstart', function(e) {
        draggedCard = cardElement;
        cardElement.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    });

    cardElement.addEventListener('dragend', function() {
        cardElement.classList.remove('dragging');
        document.querySelectorAll('.drop-target').forEach(el => {
            el.classList.remove('drop-target');
        });
        draggedCard = null;
    });
}

function setupDropTarget(container) {
    container.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        container.classList.add('drop-target');
    });

    container.addEventListener('dragleave', function() {
        container.classList.remove('drop-target');
    });

    container.addEventListener('drop', async function(e) {
        e.preventDefault();
        container.classList.remove('drop-target');

        if (draggedCard) {
            const cardId = draggedCard.getAttribute('data-card-id');
            const newListId = container.getAttribute('data-list-id');
            const currentVersion = cardVersions.get(parseInt(cardId));
            
            const rect = container.getBoundingClientRect();
            const cards = Array.from(container.children);
            let newOrder = cards.length;
            
            for (let i = 0; i < cards.length; i++) {
                const cardRect = cards[i].getBoundingClientRect();
                if (e.clientY < cardRect.top + cardRect.height / 2) {
                    newOrder = i;
                    break;
                }
            }

            try {
                const response = await fetch(`/api/board/cards/${cardId}/move/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        list_id: parseInt(newListId),
                        new_order: newOrder,
                        current_version: currentVersion
                    })
                });

                if (response.status === 409) {
                    const errorData = await response.json();
                    console.warn('Conflict detected:', errorData.message);
                }
            } catch (error) {
                console.error('Error moving card:', error);
            }
        }
    });
}

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

function showDemoBoard() {
    const container = document.getElementById('board-container');
    const demoLists = [
        { id: 1, name: '待办', cards: [
            { id: 101, title: '用户认证功能', description: '实现用户登录和注册功能', priority: 'high', story_points: 8, assignee: { username: '张三' }, version: 1 },
            { id: 102, title: '数据库设计', description: '设计项目数据库表结构', priority: 'medium', story_points: 5, assignee: { username: '李四' }, version: 1 }
        ]},
        { id: 2, name: '进行中', cards: [
            { id: 103, title: 'API接口开发', description: '开发RESTful API接口', priority: 'high', story_points: 13, assignee: { username: '王五' }, version: 1 }
        ]},
        { id: 3, name: '评审中', cards: [
            { id: 104, title: '前端页面设计', description: '设计项目前端页面原型', priority: 'medium', story_points: 3, assignee: { username: '赵六' }, version: 1 }
        ]},
        { id: 4, name: '已完成', cards: [
            { id: 105, title: '需求分析文档', description: '完成项目需求分析和文档编写', priority: 'low', story_points: 2, assignee: { username: '张三' }, version: 1 }
        ]}
    ];

    demoLists.forEach(list => {
        const listColumn = createListColumn(list);
        container.appendChild(listColumn);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    loadBoard();
});
