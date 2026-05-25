import { ref } from 'vue';
import { WS_MESSAGE_TYPES, CONNECTION_STATUS } from '../constants';
import ot from './ot';
class WebSocketClient {
 constructor() {
 this.ws = null;
 this.url = null;
 this.status = ref(CONNECTION_STATUS.OFFLINE);
 this.users = ref([]);
 this.currentUser = ref(null);
 this.roomId = null;
 this.messageQueue = [];
 this.reconnectAttempts = 0;
 this.maxReconnectAttempts = 5;
 this.reconnectDelay = 2000;
 this.heartbeatInterval = null;
 this.listeners = new Map();
 this.userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
 this.userName = `用户${Math.floor(Math.random() * 1000)}`;
 this.userColor = this.generateRandomColor();
 this.ot = ot;
 this.pendingOperations = [];
 this.lastAckVersion = 0;
 this.remoteOperations = [];
 }
 generateRandomColor() {
 const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#409eff', '#909399', '#9c27b0', '#00bcd4', '#ff9800'];
 return colors[Math.floor(Math.random() * colors.length)];
 }
 connect(url, roomId = 'default') {
 return new Promise((resolve, reject) => {
 this.url = url;
 this.roomId = roomId;
 this.status.value = CONNECTION_STATUS.CONNECTING;
 try {
 this.ws = new WebSocket(url);
 this.ws.onopen = () => this.onOpen(resolve);
 this.ws.onmessage = (event) => this.onMessage(event);
 this.ws.onclose = (event) => this.onClose(event);
 this.ws.onerror = (error) => this.onError(error, reject);
 }
 catch (error) {
 this.status.value = CONNECTION_STATUS.OFFLINE;
 reject(error);
 }
 });
 }
 onOpen(resolve) {
 this.status.value = CONNECTION_STATUS.ONLINE;
 this.reconnectAttempts = 0;
 this.currentUser.value = {
 id: this.userId,
 name: this.userName,
 color: this.userColor,
 roomId: this.roomId
 };
 this.sendMessage(WS_MESSAGE_TYPES.JOIN, {
 user: this.currentUser.value,
 roomId: this.roomId
 });
 this.startHeartbeat();
 this.flushMessageQueue();
 resolve(this.currentUser.value);
 }
 onMessage(event) {
 try {
 const message = JSON.parse(event.data);
 this.handleMessage(message);
 }
 catch (error) {
 console.error('WebSocket 消息解析失败:', error);
 }
 }
 handleMessage(message) {
 const { type, data, senderId } = message;
 if (senderId === this.userId)
 return;
 this.emit(type, data, senderId);
 switch (type) {
 case WS_MESSAGE_TYPES.USERS_UPDATE:
 this.users.value = data.users || [];
 break;
 case WS_MESSAGE_TYPES.ANNOTATION_ADD:
 case WS_MESSAGE_TYPES.ANNOTATION_UPDATE:
 case WS_MESSAGE_TYPES.ANNOTATION_DELETE:
 case WS_MESSAGE_TYPES.CURSOR_MOVE:
 case WS_MESSAGE_TYPES.IMAGE_LOAD:
 case WS_MESSAGE_TYPES.UNDO:
 case WS_MESSAGE_TYPES.REDO:
 break;
 case WS_MESSAGE_TYPES.OT_OPERATION:
 this.handleRemoteOperation(data.operation, senderId);
 break;
 case WS_MESSAGE_TYPES.OT_ACK:
 this.handleOperationAck(data);
 break;
 case WS_MESSAGE_TYPES.OT_SYNC:
 this.handleSync(data);
 break;
 }
 }
 handleRemoteOperation(operation, senderId) {
 if (!operation || !operation.id) return;
 const existingOp = this.remoteOperations.find(op => op.id === operation.id);
 if (existingOp) return;
 this.remoteOperations.push(operation);
 if (this.pendingOperations.length > 0) {
 const transformed = this.ot.transformAgainst(operation, this.pendingOperations[0]);
 for (let i = 1; i < this.pendingOperations.length; i++) {
 const { right } = this.ot.transform(this.pendingOperations[i - 1], transformed);
 operation.transformed = right;
 }
 }
 this.emit('ot_operation', operation, senderId);
 this.sendOperationAck(operation.id, operation.version);
 }
 handleOperationAck(data) {
 const { operationId, version } = data;
 const index = this.pendingOperations.findIndex(op => op.id === operationId);
 if (index !== -1) {
 this.pendingOperations.splice(index, 1);
 this.lastAckVersion = Math.max(this.lastAckVersion, version);
 }
 }
 handleSync(data) {
 const { operations, version } = data;
 if (version > this.ot.version) {
 operations.forEach(op => {
 if (!this.remoteOperations.find(o => o.id === op.id)) {
 this.remoteOperations.push(op);
 this.emit('ot_operation', op, op.userId);
 }
 });
 this.ot.version = version;
 }
 }
 onClose(event) {
 this.status.value = CONNECTION_STATUS.OFFLINE;
 this.stopHeartbeat();
 if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
 this.reconnectAttempts++;
 console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
 setTimeout(() => {
 if (this.url && this.roomId) {
 this.connect(this.url, this.roomId).catch(() => { });
 }
 }, this.reconnectDelay * this.reconnectAttempts);
 }
 }
 onError(error, reject) {
 console.error('WebSocket 错误:', error);
 if (reject) {
 reject(error);
 }
 }
 startHeartbeat() {
 this.stopHeartbeat();
 this.heartbeatInterval = setInterval(() => {
 if (this.ws && this.ws.readyState === WebSocket.OPEN) {
 this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
 }
 }, 30000);
 }
 stopHeartbeat() {
 if (this.heartbeatInterval) {
 clearInterval(this.heartbeatInterval);
 this.heartbeatInterval = null;
 }
 }
 sendMessage(type, data) {
 const message = {
 type,
 data,
 senderId: this.userId,
 roomId: this.roomId,
 timestamp: Date.now()
 };
 if (this.ws && this.ws.readyState === WebSocket.OPEN) {
 this.ws.send(JSON.stringify(message));
 }
 else {
 this.messageQueue.push(message);
 }
 }
 flushMessageQueue() {
 while (this.messageQueue.length > 0) {
 const message = this.messageQueue.shift();
 if (this.ws && this.ws.readyState === WebSocket.OPEN) {
 this.ws.send(JSON.stringify(message));
 }
 else {
 this.messageQueue.unshift(message);
 break;
 }
 }
 }
 on(eventType, callback) {
 if (!this.listeners.has(eventType)) {
 this.listeners.set(eventType, new Set());
 }
 this.listeners.get(eventType).add(callback);
 return () => this.off(eventType, callback);
 }
 off(eventType, callback) {
 if (this.listeners.has(eventType)) {
 this.listeners.get(eventType).delete(callback);
 }
 }
 emit(eventType, data, senderId) {
 if (this.listeners.has(eventType)) {
 this.listeners.get(eventType).forEach(callback => {
 try {
 callback(data, senderId);
 }
 catch (error) {
 console.error(`事件监听器错误 [${eventType}]:`, error);
 }
 });
 }
 }
 sendAnnotationAdd(annotation) {
 this.sendMessage(WS_MESSAGE_TYPES.ANNOTATION_ADD, { annotation });
 }
 sendAnnotationUpdate(annotation) {
 this.sendMessage(WS_MESSAGE_TYPES.ANNOTATION_UPDATE, { annotation });
 }
 sendAnnotationDelete(annotationId) {
 this.sendMessage(WS_MESSAGE_TYPES.ANNOTATION_DELETE, { annotationId });
 }
 sendCursorMove(position, imageId) {
 this.sendMessage(WS_MESSAGE_TYPES.CURSOR_MOVE, {
 position,
 imageId,
 user: this.currentUser.value
 });
 }
 sendImageLoad(imageData) {
 this.sendMessage(WS_MESSAGE_TYPES.IMAGE_LOAD, { image: imageData });
 }
 sendUndo(imageId) {
 this.sendMessage(WS_MESSAGE_TYPES.UNDO, { imageId });
 }
 sendRedo(imageId) {
 this.sendMessage(WS_MESSAGE_TYPES.REDO, { imageId });
 }
 sendOperation(operation) {
 operation.userId = this.userId;
 this.pendingOperations.push(operation);
 this.sendMessage(WS_MESSAGE_TYPES.OT_OPERATION, { operation });
 }
 sendOperationAck(operationId, version) {
 this.sendMessage(WS_MESSAGE_TYPES.OT_ACK, { operationId, version });
 }
 requestSync() {
 this.sendMessage(WS_MESSAGE_TYPES.OT_SYNC, {
 requestSync: true,
 currentVersion: this.ot.version
 });
 }
 setUserName(name) {
 this.userName = name;
 if (this.currentUser.value) {
 this.currentUser.value.name = name;
 }
 }
 disconnect() {
 this.stopHeartbeat();
 if (this.ws) {
 if (this.status.value === CONNECTION_STATUS.ONLINE) {
 this.sendMessage(WS_MESSAGE_TYPES.LEAVE, {
 userId: this.userId,
 roomId: this.roomId
 });
 }
 this.ws.close();
 this.ws = null;
 }
 this.status.value = CONNECTION_STATUS.OFFLINE;
 this.users.value = [];
 this.messageQueue = [];
 this.reconnectAttempts = 0;
 }
 isOnline() {
 return this.status.value === CONNECTION_STATUS.ONLINE;
 }
}
export const wsClient = new WebSocketClient();
export default wsClient;

