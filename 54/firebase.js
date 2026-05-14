import { initializeApp } from 'firebase/app'
import { getFirestore } from 'firebase/firestore'
import { getStorage } from 'firebase/storage'

const firebaseConfig = {
  apiKey: 'YOUR_API_KEY',
  authDomain: 'YOUR_PROJECT.firebaseapp.com',
  projectId: 'YOUR_PROJECT_ID',
  storageBucket: 'YOUR_PROJECT.appspot.com',
  messagingSenderId: 'YOUR_SENDER_ID',
  appId: 'YOUR_APP_ID'
}

let app = null
let db = null
let storage = null
const listeners = new Map()

function getOrInitializeApp() {
  if (!app) {
    app = initializeApp(firebaseConfig)
  }
  return app
}

function getDB() {
  if (!db) {
    const firebaseApp = getOrInitializeApp()
    db = getFirestore(firebaseApp)
  }
  return db
}

function getStorageRef() {
  if (!storage) {
    const firebaseApp = getOrInitializeApp()
    storage = getStorage(firebaseApp)
  }
  return storage
}

function addListener(key, unsubscribeFn) {
  if (listeners.has(key)) {
    listeners.get(key)()
    listeners.delete(key)
  }
  listeners.set(key, unsubscribeFn)
}

function removeListener(key) {
  if (listeners.has(key)) {
    listeners.get(key)()
    listeners.delete(key)
  }
}

function clearAllListeners() {
  listeners.forEach((unsubscribeFn) => {
    unsubscribeFn()
  })
  listeners.clear()
}

function hasListener(key) {
  return listeners.has(key)
}

const initializedApp = getOrInitializeApp()
const initializedDB = getDB()
const initializedStorage = getStorageRef()

export {
  initializedApp as app,
  initializedDB as db,
  initializedStorage as storage,
  addListener,
  removeListener,
  clearAllListeners,
  hasListener
}
