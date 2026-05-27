export interface HistoryItem {
  id?: number;
  expression: string;
  result: string;
  timestamp: number;
}

const DB_NAME = 'scientific_calculator';
const STORE_NAME = 'history';
const DB_VERSION = 2;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (db.objectStoreNames.contains(STORE_NAME)) {
        db.deleteObjectStore(STORE_NAME);
      }
      const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      store.createIndex('timestamp', 'timestamp', { unique: false });
      store.createIndex('expression', 'expression', { unique: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T> | Promise<T>,
): Promise<T> {
  const db = await openDB();
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode);
    const store = tx.objectStore(STORE_NAME);
    const result = fn(store);
    tx.oncomplete = () => {
      if (result instanceof IDBRequest) resolve(result.result);
    };
    tx.onerror = () => reject(tx.error);
    if (result instanceof IDBRequest) {
      result.onerror = () => reject(result.error);
    } else if (result instanceof Promise) {
      result.then(resolve).catch(reject);
    }
  });
}

export async function upsertHistory(item: Omit<HistoryItem, 'id'>): Promise<HistoryItem> {
  const db = await openDB();
  return new Promise<HistoryItem>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const exprIndex = store.index('expression');
    const getReq = exprIndex.get(item.expression);
    getReq.onsuccess = () => {
      const existing = getReq.result as HistoryItem | undefined;
      if (existing) {
        existing.result = item.result;
        existing.timestamp = item.timestamp;
        const putReq = store.put(existing);
        putReq.onsuccess = () => resolve(existing);
        putReq.onerror = () => reject(putReq.error);
      } else {
        const addReq = store.add(item);
        addReq.onsuccess = () => {
          resolve({ ...item, id: addReq.result as number });
        };
        addReq.onerror = () => reject(addReq.error);
      }
    };
    getReq.onerror = () => reject(getReq.error);
    tx.onerror = () => reject(tx.error);
  });
}

export async function getAllHistory(): Promise<HistoryItem[]> {
  return new Promise((resolve, reject) => {
    openDB()
      .then((db) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const index = store.index('timestamp');
        const req = index.openCursor(null, 'prev');
        const items: HistoryItem[] = [];
        req.onsuccess = () => {
          const cursor = req.result;
          if (cursor) {
            items.push(cursor.value as HistoryItem);
            cursor.continue();
          } else {
            resolve(items);
          }
        };
        req.onerror = () => reject(req.error);
      })
      .catch(reject);
  });
}

export async function deleteHistory(id: number): Promise<void> {
  return withStore<void>('readwrite', (store) => store.delete(id) as IDBRequest<void>);
}

export async function clearHistory(): Promise<void> {
  return withStore<void>('readwrite', (store) => store.clear() as IDBRequest<void>);
}
