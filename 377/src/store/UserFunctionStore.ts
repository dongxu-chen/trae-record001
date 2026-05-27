export interface UserFunctionDef {
  id?: number;
  name: string;
  params: string[];
  expression: string;
  timestamp: number;
}

const DB_NAME = 'scientific_calculator';
const STORE_NAME = 'user_functions';
const DB_VERSION = 3;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('history')) {
        const historyStore = db.createObjectStore('history', { keyPath: 'id', autoIncrement: true });
        historyStore.createIndex('timestamp', 'timestamp', { unique: false });
        historyStore.createIndex('expression', 'expression', { unique: true });
      }
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        store.createIndex('name', 'name', { unique: true });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
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

export async function addUserFunction(
  fn: Omit<UserFunctionDef, 'id' | 'timestamp'>,
): Promise<UserFunctionDef> {
  const item: UserFunctionDef = { ...fn, timestamp: Date.now() };
  const db = await openDB();
  return new Promise<UserFunctionDef>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const nameIndex = store.index('name');
    const getReq = nameIndex.get(fn.name);
    getReq.onsuccess = () => {
      const existing = getReq.result as UserFunctionDef | undefined;
      if (existing) {
        reject(new Error(`函数名 '${fn.name}' 已存在`));
        return;
      }
      const addReq = store.add(item);
      addReq.onsuccess = () => {
        resolve({ ...item, id: addReq.result as number });
      };
      addReq.onerror = () => reject(addReq.error);
    };
    getReq.onerror = () => reject(getReq.error);
    tx.onerror = () => reject(tx.error);
  });
}

export async function updateUserFunction(
  id: number,
  fn: Partial<Omit<UserFunctionDef, 'id'>>,
): Promise<UserFunctionDef> {
  const db = await openDB();
  return new Promise<UserFunctionDef>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const getReq = store.get(id);
    getReq.onsuccess = () => {
      const existing = getReq.result as UserFunctionDef | undefined;
      if (!existing) {
        reject(new Error(`函数不存在`));
        return;
      }
      const updated: UserFunctionDef = { ...existing, ...fn, timestamp: Date.now() };
      const putReq = store.put(updated);
      putReq.onsuccess = () => resolve(updated);
      putReq.onerror = () => reject(putReq.error);
    };
    getReq.onerror = () => reject(getReq.error);
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteUserFunction(id: number): Promise<void> {
  return withStore<void>('readwrite', (store) => store.delete(id) as IDBRequest<void>);
}

export async function getAllUserFunctions(): Promise<UserFunctionDef[]> {
  return new Promise((resolve, reject) => {
    openDB()
      .then((db) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const index = store.index('timestamp');
        const req = index.openCursor(null, 'prev');
        const items: UserFunctionDef[] = [];
        req.onsuccess = () => {
          const cursor = req.result;
          if (cursor) {
            items.push(cursor.value as UserFunctionDef);
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
