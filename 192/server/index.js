const http = require('http');
const WebSocket = require('ws');
const ShareDB = require('sharedb');
const richText = require('rich-text');

ShareDB.types.register(richText.type);

const backend = new ShareDB({
  presence: false,
});

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Collaborative Editor Server Running');
});

const wss = new WebSocket.Server({ server });

const connectedClients = new Map();
const oplogStore = new Map();
const snapshotStore = new Map();

const DOC_ID = 'default-doc';

function initDocument() {
  if (!oplogStore.has(DOC_ID)) {
    oplogStore.set(DOC_ID, []);
  }
  if (!snapshotStore.has(DOC_ID)) {
    const initialContent = [
      {
        insert: '欢迎使用协同富文本编辑器\n',
        attributes: { bold: true, size: 'large' }
      },
      {
        insert: '这是一个支持多人实时编辑的富文本编辑器。\n'
      },
      {
        insert: '功能特性：\n',
        attributes: { underline: true }
      },
      {
        insert: '• 多人实时协同编辑\n'
      },
      {
        insert: '• 操作转换(OT)解决冲突\n'
      },
      {
        insert: '• 光标位置实时同步\n'
      },
      {
        insert: '• Markdown快捷输入\n'
      },
      {
        insert: '• 评论批注\n'
      },
      {
        insert: '• Oplog版本历史，按需重放\n'
      }
    ];
    snapshotStore.set(DOC_ID, {
      v: 0,
      content: initialContent,
      timestamp: Date.now()
    });
  }
}

initDocument();

wss.on('connection', (ws, req) => {
  const clientId = req.headers['sec-websocket-key'] || Math.random().toString(36).substr(2, 9);
  
  const shareDBConnection = backend.connect();
  const doc = shareDBConnection.get('documents', DOC_ID);
  
  if (!doc.type) {
    const snapshot = snapshotStore.get(DOC_ID);
    doc.create(snapshot.content, 'rich-text');
  }

  const oplog = oplogStore.get(DOC_ID);
  
  doc.subscribe((err) => {
    if (err) throw err;
    const snapshot = snapshotStore.get(DOC_ID);
    ws.send(JSON.stringify({
      type: 'init',
      content: doc.data,
      clientId,
      version: doc.version,
      snapshotVersion: snapshot.v,
      oplogLength: oplog.length
    }));
  });

  doc.on('op', (op, source) => {
    if (source !== shareDBConnection.id) {
      ws.send(JSON.stringify({
        type: 'op',
        op,
        version: doc.version
      }));
    }
  });

  connectedClients.set(clientId, { ws, shareDBConnection, doc });
  
  broadcastUserList();
  broadcastAllPresence();

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      
      switch (data.type) {
        case 'op':
          handleOp(data.op, clientId, doc, shareDBConnection);
          break;
          
        case 'presence':
          handlePresence(data.range, clientId);
          break;
          
        case 'comment':
          broadcastComment(data.comment, clientId);
          break;
          
        case 'resolveComment':
          broadcastResolveComment(data.commentId, clientId);
          break;
          
        case 'getOplog':
          handleGetOplog(ws, data.fromVersion, data.toVersion);
          break;
          
        case 'getSnapshot':
          handleGetSnapshot(ws, data.version);
          break;
          
        case 'revertToVersion':
          handleRevertToVersion(data.version, clientId, doc, shareDBConnection);
          break;
          
        case 'createCheckpoint':
          handleCreateCheckpoint(doc);
          break;
      }
    } catch (e) {
      console.error('Error parsing message:', e);
    }
  });

  ws.on('close', () => {
    connectedClients.delete(clientId);
    shareDBConnection.close();
    broadcastUserList();
    broadcastAllPresence();
  });
});

function handleOp(op, clientId, doc, connection) {
  const oplog = oplogStore.get(DOC_ID);
  
  oplog.push({
    v: doc.version + 1,
    op,
    timestamp: Date.now(),
    clientId,
    type: 'op'
  });

  doc.submitOp(op, { source: connection.id });

  if (oplog.length > 1000) {
    createCheckpoint(doc);
  }
}

function handlePresence(range, fromClientId) {
  const client = connectedClients.get(fromClientId);
  if (client) {
    client.presence = range;
    client.lastPresenceUpdate = Date.now();
  }

  connectedClients.forEach(({ ws }, clientId) => {
    if (clientId !== fromClientId && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'presence',
        clientId: fromClientId,
        range,
        timestamp: Date.now()
      }));
    }
  });
}

function broadcastAllPresence() {
  const allPresence = {};
  connectedClients.forEach((client, id) => {
    if (client.presence) {
      allPresence[id] = client.presence;
    }
  });

  connectedClients.forEach(({ ws }) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'presenceBatch',
        presence: allPresence
      }));
    }
  });
}

function broadcastUserList() {
  const userList = Array.from(connectedClients.keys());
  connectedClients.forEach(({ ws }) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'users',
        users: userList
      }));
    }
  });
}

function broadcastComment(comment, fromClientId) {
  connectedClients.forEach(({ ws }, clientId) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'comment',
        comment,
        fromClientId
      }));
    }
  });
}

function broadcastResolveComment(commentId, fromClientId) {
  connectedClients.forEach(({ ws }, clientId) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'resolveComment',
        commentId,
        fromClientId
      }));
    }
  });
}

function handleGetOplog(ws, fromVersion = 0, toVersion) {
  const oplog = oplogStore.get(DOC_ID);
  let result = oplog;
  
  if (fromVersion > 0) {
    result = result.filter(entry => entry.v > fromVersion);
  }
  if (toVersion) {
    result = result.filter(entry => entry.v <= toVersion);
  }

  ws.send(JSON.stringify({
    type: 'oplog',
    entries: result.slice(-100),
    total: result.length
  }));
}

function handleGetSnapshot(ws, targetVersion) {
  const snapshot = snapshotStore.get(DOC_ID);
  const oplog = oplogStore.get(DOC_ID);
  
  if (targetVersion === undefined || targetVersion === snapshot.v) {
    ws.send(JSON.stringify({
      type: 'snapshot',
      snapshot: snapshot
    }));
    return;
  }

  if (targetVersion < snapshot.v) {
    const content = replayOplogBackward(snapshot.content, snapshot.v, targetVersion, oplog);
    ws.send(JSON.stringify({
      type: 'snapshot',
      snapshot: {
        v: targetVersion,
        content,
        timestamp: Date.now(),
        generated: true
      }
    }));
  } else {
    const opsToApply = oplog.filter(e => e.v > snapshot.v && e.v <= targetVersion);
    let content = [...snapshot.content];
    for (const entry of opsToApply) {
      content = applyOpToContent(content, entry.op);
    }
    ws.send(JSON.stringify({
      type: 'snapshot',
      snapshot: {
        v: targetVersion,
        content,
        timestamp: Date.now(),
        generated: true
      }
    }));
  }
}

function handleRevertToVersion(targetVersion, clientId, doc, connection) {
  const snapshot = snapshotStore.get(DOC_ID);
  const oplog = oplogStore.get(DOC_ID);

  const targetSnapshot = replayOplogBackward(
    snapshot.content,
    snapshot.v,
    targetVersion,
    oplog
  );

  const currentContent = doc.data;
  const revertOp = generateRevertOp(currentContent, targetSnapshot);

  if (revertOp.length > 0) {
    oplog.push({
      v: doc.version + 1,
      op: revertOp,
      timestamp: Date.now(),
      clientId,
      type: 'revert',
      targetVersion
    });
    doc.submitOp(revertOp, { source: connection.id });
  }
}

function handleCreateCheckpoint(doc) {
  createCheckpoint(doc);
}

function createCheckpoint(doc) {
  const snapshot = {
    v: doc.version,
    content: JSON.parse(JSON.stringify(doc.data)),
    timestamp: Date.now(),
    isCheckpoint: true
  };
  snapshotStore.set(DOC_ID, snapshot);

  const oplog = oplogStore.get(DOC_ID);
  const recentOplog = oplog.filter(e => e.v > doc.version - 100);
  oplogStore.set(DOC_ID, recentOplog);

  console.log(`Checkpoint created at version ${doc.version}`);
}

function replayOplogBackward(content, fromVersion, toVersion, oplog) {
  const opsToRevert = oplog
    .filter(e => e.v > toVersion && e.v <= fromVersion)
    .sort((a, b) => b.v - a.v);

  let result = JSON.parse(JSON.stringify(content));
  
  for (const entry of opsToRevert) {
    result = invertAndApplyOp(result, entry.op);
  }

  return result;
}

function applyOpToContent(content, op) {
  let result = [];
  let contentIndex = 0;
  let opIndex = 0;

  const flatContent = flattenContent(content);
  
  for (const component of op) {
    if (typeof component === 'number') {
      result.push(...flatContent.slice(contentIndex, contentIndex + component));
      contentIndex += component;
    } else if (component.insert !== undefined) {
      result.push({ insert: component.insert, attributes: component.attributes || {} });
    } else if (component.delete !== undefined) {
      contentIndex += component.delete;
    } else if (component.retain !== undefined) {
      const attrs = component.attributes || {};
      const slice = flatContent.slice(contentIndex, contentIndex + component.retain);
      if (Object.keys(attrs).length > 0) {
        result.push(...slice.map(item => ({
          ...item,
          attributes: { ...item.attributes, ...attrs }
        })));
      } else {
        result.push(...slice);
      }
      contentIndex += component.retain;
    }
  }

  if (contentIndex < flatContent.length) {
    result.push(...flatContent.slice(contentIndex));
  }

  return unflattenContent(result);
}

function invertAndApplyOp(content, op) {
  const flatContent = flattenContent(content);
  const invertedOp = invertOpForContent(op, flatContent);
  return applyOpToContent(content, invertedOp);
}

function invertOpForContent(op, flatContent) {
  const inverted = [];
  let pos = 0;

  for (const component of op) {
    if (typeof component === 'number') {
      inverted.push(component);
      pos += component;
    } else if (component.insert !== undefined) {
      inverted.push({ delete: component.insert.length });
    } else if (component.delete !== undefined) {
      const deletedText = flatContent.slice(pos, pos + component.delete);
      for (const item of deletedText) {
        inverted.push({ insert: item.insert, attributes: item.attributes });
      }
      pos += component.delete;
    } else if (component.retain !== undefined) {
      inverted.push({ retain: component.retain });
      pos += component.retain;
    }
  }

  return inverted;
}

function generateRevertOp(currentContent, targetContent) {
  const currentFlat = flattenContent(currentContent);
  const targetFlat = flattenContent(targetContent);
  
  const diffResult = computeDiff(currentFlat, targetFlat);
  return diffResult;
}

function computeDiff(current, target) {
  const op = [];
  let i = 0;
  let j = 0;

  while (i < current.length && j < target.length) {
    if (current[i].insert === target[j].insert && 
        JSON.stringify(current[i].attributes) === JSON.stringify(target[j].attributes)) {
      op.push(current[i].insert.length);
      i++;
      j++;
    } else {
      let matchI = i;
      let matchJ = j;
      let found = false;
      
      for (let lookAhead = 0; lookAhead < 20 && i + lookAhead < current.length; lookAhead++) {
        const currentItem = current[i + lookAhead];
        for (let targetLook = 0; targetLook < 20 && j + targetLook < target.length; targetLook++) {
          if (currentItem.insert === target[j + targetLook].insert &&
              JSON.stringify(currentItem.attributes) === JSON.stringify(target[j + targetLook].attributes)) {
            matchI = i + lookAhead;
            matchJ = j + targetLook;
            found = true;
            break;
          }
        }
        if (found) break;
      }

      if (found && matchI > i) {
        op.push({ delete: current.slice(i, matchI).reduce((sum, item) => sum + item.insert.length, 0) });
        i = matchI;
      } else if (found && matchJ > j) {
        for (let k = j; k < matchJ; k++) {
          op.push({ insert: target[k].insert, attributes: target[k].attributes });
        }
        j = matchJ;
      } else {
        op.push({ delete: current[i].insert.length });
        op.push({ insert: target[j].insert, attributes: target[j].attributes });
        i++;
        j++;
      }
    }
  }

  if (i < current.length) {
    op.push({ delete: current.slice(i).reduce((sum, item) => sum + item.insert.length, 0) });
  }

  while (j < target.length) {
    op.push({ insert: target[j].insert, attributes: target[j].attributes });
    j++;
  }

  return op;
}

function flattenContent(content) {
  const result = [];
  if (Array.isArray(content)) {
    for (const item of content) {
      if (typeof item === 'object' && item.insert !== undefined) {
        result.push({
          insert: item.insert,
          attributes: item.attributes || {}
        });
      }
    }
  }
  return result;
}

function unflattenContent(flat) {
  return flat;
}

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Document initialized with snapshot version ${snapshotStore.get(DOC_ID).v}`);
});
