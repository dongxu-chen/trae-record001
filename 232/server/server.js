const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

const PORT = process.env.PORT || 8080;
const wss = new WebSocket.Server({ port: PORT });

console.log(`WebSocket server running on port ${PORT}`);

const sessions = new Map();

function getOrCreateSession(sessionId) {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, {
      clients: new Map(),
      state: {
        layers: [],
        commandQueue: [],
        commandIndex: -1
      },
      comments: [],
      pendingLayers: new Map()
    });
  }
  return sessions.get(sessionId);
}

function broadcastToSession(sessionId, message, excludeClient = null) {
  const session = sessions.get(sessionId);
  if (!session) return;
  
  session.clients.forEach((info, client) => {
    if (client !== excludeClient && client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

function executeCommand(session, command) {
  command.id = command.id || uuidv4();
  session.state.commandQueue = session.state.commandQueue.slice(0, session.state.commandIndex + 1);
  session.state.commandQueue.push(command);
  session.state.commandIndex++;
  
  applyCommand(session.state, command);
}

function applyCommand(state, command) {
  switch (command.type) {
    case 'addLayer':
      state.layers.push(command.layer);
      break;
    case 'updateLayer': {
        const index = state.layers.findIndex(l => l.id === command.layer.id);
        if (index !== -1) {
          state.layers[index] = command.layer;
        }
        break;
      }
    case 'appendPoints': {
        const layer = state.layers.find(l => l.id === command.layerId);
        if (layer && layer.points) {
          layer.points.push(...command.points);
        }
        break;
      }
    case 'deleteLayer':
      state.layers = state.layers.filter(l => l.id !== command.layerId);
      break;
    case 'moveLayer': {
        const { layerId, direction } = command;
        const index = state.layers.findIndex(l => l.id === layerId);
        if (index !== -1) {
          const newIndex = index + direction;
          if (newIndex >= 0 && newIndex < state.layers.length) {
            const temp = state.layers[index];
            state.layers[index] = state.layers[newIndex];
            state.layers[newIndex] = temp;
          }
        }
        break;
      }
    case 'clear':
      state.layers = [];
      break;
  }
}

function undoCommand(state) {
  if (state.commandIndex < 0) return false;
  
  const command = state.commandQueue[state.commandIndex];
  undoCommandImpl(state, command);
  state.commandIndex--;
  return true;
}

function undoCommandImpl(state, command) {
  switch (command.type) {
    case 'addLayer':
    case 'appendPoints':
    case 'updateLayer':
      state.layers = state.layers.filter(l => l.id !== command.layerId || command.type === 'addLayer');
      if (command.type === 'addLayer' && command.originalLayer) {
        state.layers.push(command.originalLayer);
      }
      break;
    case 'deleteLayer':
      if (command.layer) {
        state.layers.push(command.layer);
      }
      break;
    case 'moveLayer': {
        const { layerId, direction } = command;
        const index = state.layers.findIndex(l => l.id === layerId);
        if (index !== -1) {
          const newIndex = index - direction;
          if (newIndex >= 0 && newIndex < state.layers.length) {
            const temp = state.layers[index];
            state.layers[index] = state.layers[newIndex];
            state.layers[newIndex] = temp;
          }
        }
        break;
      }
    case 'clear':
      if (command.originalLayers) {
        state.layers = command.originalLayers;
      }
      break;
  }
}

function redoCommand(state) {
  if (state.commandIndex >= state.commandQueue.length - 1) return false;
  
  state.commandIndex++;
  const command = state.commandQueue[state.commandIndex];
  applyCommand(state, command);
  return true;
}

wss.on('connection', (ws) => {
  const clientId = uuidv4();
  let currentSessionId = null;
  
  console.log(`Client connected: ${clientId}`);

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      
      switch (message.type) {
        case 'join': {
          const sessionId = message.sessionId || 'default';
          currentSessionId = sessionId;
          const session = getOrCreateSession(sessionId);
          session.clients.set(ws, {
            id: clientId,
            name: message.userName || '匿名用户'
          });
          
          const onlineUsers = Array.from(session.clients.values());
          
          ws.send(JSON.stringify({
            type: 'init',
            clientId,
            sessionId,
            state: session.state,
            comments: session.comments,
            onlineUsers
          }));
          
          broadcastToSession(sessionId, {
            type: 'userJoined',
            clientId,
            userName: message.userName || '匿名用户',
            userCount: session.clients.size
          }, ws);
          
          console.log(`Client ${clientId} joined session ${sessionId}`);
          break;
        }
        
        case 'startDraw': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          session.pendingLayers.set(message.layer.id, message.layer);
          
          broadcastToSession(currentSessionId, {
            type: 'startDraw',
            layer: message.layer,
            clientId
          }, ws);
          break;
        }
        
        case 'appendPoints': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const layer = session.pendingLayers.get(message.layerId);
          if (layer && layer.points) {
            layer.points.push(...message.points);
          }
          
          broadcastToSession(currentSessionId, {
            type: 'appendPoints',
            layerId: message.layerId,
            points: message.points,
            clientId
          }, ws);
          break;
        }
        
        case 'endDraw': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const layer = session.pendingLayers.get(message.layerId);
          if (layer) {
            session.pendingLayers.delete(message.layerId);
            
            const command = {
              type: 'addLayer',
              layerId: message.layerId,
              layer: JSON.parse(JSON.stringify(layer))
            };
            executeCommand(session, command);
          }
          
          broadcastToSession(currentSessionId, {
            type: 'endDraw',
            layerId: message.layerId,
            clientId
          }, ws);
          break;
        }
        
        case 'addShape': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const command = {
            type: 'addLayer',
            layerId: message.layer.id,
            layer: JSON.parse(JSON.stringify(message.layer))
          };
          executeCommand(session, command);
          
          broadcastToSession(currentSessionId, {
            type: 'addShape',
            layer: message.layer,
            clientId
          }, ws);
          break;
        }
        
        case 'updateLayer': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const originalLayer = session.state.layers.find(l => l.id === message.layer.id);
          
          const command = {
            type: 'updateLayer',
            layerId: message.layer.id,
            layer: JSON.parse(JSON.stringify(message.layer)),
            originalLayer: originalLayer ? JSON.parse(JSON.stringify(originalLayer)) : null
          };
          executeCommand(session, command);
          
          broadcastToSession(currentSessionId, {
            type: 'updateLayer',
            layer: message.layer,
            clientId
          }, ws);
          break;
        }
        
        case 'deleteLayer': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const layer = session.state.layers.find(l => l.id === message.layerId);
          
          const command = {
            type: 'deleteLayer',
            layerId: message.layerId,
            layer: layer ? JSON.parse(JSON.stringify(layer)) : null
          };
          executeCommand(session, command);
          
          broadcastToSession(currentSessionId, {
            type: 'deleteLayer',
            layerId: message.layerId,
            clientId
          }, ws);
          break;
        }
        
        case 'moveLayer': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const command = {
            type: 'moveLayer',
            layerId: message.layerId,
            direction: message.direction
          };
          executeCommand(session, command);
          
          broadcastToSession(currentSessionId, {
            type: 'moveLayer',
            layerId: message.layerId,
            direction: message.direction,
            clientId
          }, ws);
          break;
        }
        
        case 'undo': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          if (undoCommand(session.state)) {
            broadcastToSession(currentSessionId, {
              type: 'undo',
              commandId: session.state.commandQueue[session.state.commandIndex + 1]?.id,
              clientId
            }, ws);
          }
          break;
        }
        
        case 'redo': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          if (redoCommand(session.state)) {
            broadcastToSession(currentSessionId, {
              type: 'redo',
              commandId: session.state.commandQueue[session.state.commandIndex]?.id,
              clientId
            }, ws);
          }
          break;
        }
        
        case 'clear': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const command = {
            type: 'clear',
            originalLayers: JSON.parse(JSON.stringify(session.state.layers))
          };
          executeCommand(session, command);
          
          broadcastToSession(currentSessionId, {
            type: 'clear',
            clientId
          }, ws);
          break;
        }
        
        case 'syncState': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          session.state = message.state;
          
          broadcastToSession(currentSessionId, {
            type: 'stateSync',
            state: message.state,
            clientId
          }, ws);
          break;
        }
        
        case 'cursor': {
          if (!currentSessionId) return;
          broadcastToSession(currentSessionId, {
            type: 'cursor',
            clientId,
            x: message.x,
            y: message.y,
            screenX: message.screenX,
            screenY: message.screenY
          }, ws);
          break;
        }
        
        case 'addComment': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          if (message.comment) {
            session.comments.push(message.comment);
          }
          
          broadcastToSession(currentSessionId, {
            type: 'addComment',
            comment: message.comment,
            clientId
          }, ws);
          break;
        }
        
        case 'replyComment': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const comment = session.comments.find(c => c.id === message.commentId);
          if (comment) {
            comment.replies = comment.replies || [];
            comment.replies.push(message.reply);
          }
          
          broadcastToSession(currentSessionId, {
            type: 'replyComment',
            commentId: message.commentId,
            reply: message.reply,
            clientId
          }, ws);
          break;
        }
        
        case 'resolveComment': {
          if (!currentSessionId) return;
          const session = sessions.get(currentSessionId);
          if (!session) return;
          
          const comment = session.comments.find(c => c.id === message.commentId);
          if (comment) {
            comment.resolved = message.resolved;
          }
          
          broadcastToSession(currentSessionId, {
            type: 'resolveComment',
            commentId: message.commentId,
            resolved: message.resolved,
            clientId
          }, ws);
          break;
        }
      }
    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('close', () => {
    if (currentSessionId) {
      const session = sessions.get(currentSessionId);
      if (session) {
        const clientInfo = session.clients.get(ws);
        session.clients.delete(ws);
        console.log(`Client ${clientId} disconnected from session ${currentSessionId}`);
        
        broadcastToSession(currentSessionId, {
          type: 'userLeft',
          clientId,
          userName: clientInfo?.name || '匿名用户',
          userCount: session.clients.size
        });
        
        if (session.clients.size === 0) {
          setTimeout(() => {
            if (session.clients.size === 0) {
              sessions.delete(currentSessionId);
              console.log(`Session ${currentSessionId} cleaned up`);
            }
          }, 60000);
        }
      }
    }
  });
});
