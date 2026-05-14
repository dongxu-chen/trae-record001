import { initializeApp } from 'firebase/app'
import { 
  getAuth, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup
} from 'firebase/auth'
import { 
  getFirestore, 
  doc, 
  setDoc, 
  getDoc, 
  collection,
  query,
  where,
  getDocs,
  addDoc,
  onSnapshot,
  serverTimestamp,
  writeBatch
} from 'firebase/firestore'

const DEFAULT_FIREBASE_CONFIG = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
}

let app = null
let auth = null
let db = null
let unsubscribeSync = null
let currentUser = null

const LOCAL_STORAGE_KEYS = {
  SETTINGS: 'pomodoro_settings',
  STATS: 'pomodoro_stats',
  TASKS: 'pomodoro_tasks',
  SESSIONS: 'pomodoro_sessions',
  FIREBASE_CONFIG: 'pomodoro_firebase_config'
}

export const isFirebaseConfigured = () => {
  const savedConfig = localStorage.getItem(LOCAL_STORAGE_KEYS.FIREBASE_CONFIG)
  if (savedConfig) {
    try {
      const config = JSON.parse(savedConfig)
      return config.apiKey && config.apiKey !== 'YOUR_API_KEY'
    } catch {
      return false
    }
  }
  return false
}

export const configureFirebase = (config) => {
  localStorage.setItem(LOCAL_STORAGE_KEYS.FIREBASE_CONFIG, JSON.stringify(config))
  
  if (app) {
    return { app, auth, db }
  }
  
  app = initializeApp(config)
  auth = getAuth(app)
  db = getFirestore(app)
  
  return { app, auth, db }
}

export const getFirebaseConfigFromStorage = () => {
  const savedConfig = localStorage.getItem(LOCAL_STORAGE_KEYS.FIREBASE_CONFIG)
  if (savedConfig) {
    try {
      return JSON.parse(savedConfig)
    } catch {
      return null
    }
  }
  return null
}

const initFirebase = () => {
  const savedConfig = getFirebaseConfigFromStorage()
  if (savedConfig && savedConfig.apiKey !== 'YOUR_API_KEY') {
    return configureFirebase(savedConfig)
  }
  return null
}

initFirebase()

export const signUp = async (email, password) => {
  if (!auth) throw new Error('Firebase not configured')
  const result = await createUserWithEmailAndPassword(auth, email, password)
  currentUser = result.user
  return result.user
}

export const signIn = async (email, password) => {
  if (!auth) throw new Error('Firebase not configured')
  const result = await signInWithEmailAndPassword(auth, email, password)
  currentUser = result.user
  return result.user
}

export const signInWithGoogle = async () => {
  if (!auth) throw new Error('Firebase not configured')
  const provider = new GoogleAuthProvider()
  const result = await signInWithPopup(auth, provider)
  currentUser = result.user
  return result.user
}

export const signOut = async () => {
  if (!auth) return
  if (unsubscribeSync) {
    unsubscribeSync()
    unsubscribeSync = null
  }
  await firebaseSignOut(auth)
  currentUser = null
}

export const getCurrentUser = () => {
  return currentUser || auth?.currentUser
}

export const onAuthChange = (callback) => {
  if (!auth) {
    callback(null)
    return () => {}
  }
  return onAuthStateChanged(auth, (user) => {
    currentUser = user
    callback(user)
  })
}

export const syncToCloud = async () => {
  const user = getCurrentUser()
  if (!user || !db) return false

  try {
    const userDocRef = doc(db, 'users', user.uid)
    
    const settings = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.SETTINGS) || '{}')
    const stats = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.STATS) || '{}')
    const tasks = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.TASKS) || '[]')
    const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.SESSIONS) || '[]')

    await setDoc(userDocRef, {
      settings,
      stats,
      tasks,
      lastSync: serverTimestamp()
    }, { merge: true })

    if (sessions.length > 0) {
      const sessionsCol = collection(db, 'users', user.uid, 'sessions')
      const batch = writeBatch(db)
      
      sessions.slice(0, 500).forEach(session => {
        if (!session.synced) {
          const sessionRef = doc(sessionsCol, session.id || Date.now().toString())
          batch.set(sessionRef, { ...session, synced: true })
        }
      })
      
      await batch.commit()
      
      const updatedSessions = sessions.map(s => ({ ...s, synced: true }))
      localStorage.setItem(LOCAL_STORAGE_KEYS.SESSIONS, JSON.stringify(updatedSessions))
    }

    return true
  } catch (error) {
    console.error('Sync to cloud failed:', error)
    return false
  }
}

export const syncFromCloud = async () => {
  const user = getCurrentUser()
  if (!user || !db) return false

  try {
    const userDocRef = doc(db, 'users', user.uid)
    const docSnap = await getDoc(userDocRef)

    if (docSnap.exists()) {
      const data = docSnap.data()
      
      if (data.settings && Object.keys(data.settings).length > 0) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.SETTINGS, JSON.stringify(data.settings))
      }
      if (data.stats && Object.keys(data.stats).length > 0) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.STATS, JSON.stringify(data.stats))
      }
      if (data.tasks && data.tasks.length > 0) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.TASKS, JSON.stringify(data.tasks))
      }

      const sessionsCol = collection(db, 'users', user.uid, 'sessions')
      const sessionsSnap = await getDocs(sessionsCol)
      const cloudSessions = sessionsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))
      
      if (cloudSessions.length > 0) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.SESSIONS, JSON.stringify(cloudSessions))
      }
    }

    return true
  } catch (error) {
    console.error('Sync from cloud failed:', error)
    return false
  }
}

export const startRealtimeSync = () => {
  const user = getCurrentUser()
  if (!user || !db) return () => {}

  if (unsubscribeSync) {
    unsubscribeSync()
  }

  const userDocRef = doc(db, 'users', user.uid)
  unsubscribeSync = onSnapshot(userDocRef, (docSnap) => {
    if (docSnap.exists()) {
      const data = docSnap.data()
      if (data.settings) localStorage.setItem(LOCAL_STORAGE_KEYS.SETTINGS, JSON.stringify(data.settings))
      if (data.stats) localStorage.setItem(LOCAL_STORAGE_KEYS.STATS, JSON.stringify(data.stats))
      if (data.tasks) localStorage.setItem(LOCAL_STORAGE_KEYS.TASKS, JSON.stringify(data.tasks))
    }
  }, (error) => {
    console.error('Realtime sync error:', error)
  })

  return () => {
    if (unsubscribeSync) {
      unsubscribeSync()
      unsubscribeSync = null
    }
  }
}

export const addSession = async (session) => {
  const newSession = {
    id: Date.now().toString(36) + Math.random().toString(36).substr(2),
    ...session,
    createdAt: new Date().toISOString(),
    synced: false
  }

  const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.SESSIONS) || '[]')
  sessions.push(newSession)
  localStorage.setItem(LOCAL_STORAGE_KEYS.SESSIONS, JSON.stringify(sessions))

  const user = getCurrentUser()
  if (user && db) {
    try {
      const sessionsCol = collection(db, 'users', user.uid, 'sessions')
      await setDoc(doc(sessionsCol, newSession.id), { ...newSession, synced: true })
      
      const updatedSessions = sessions.map(s => 
        s.id === newSession.id ? { ...s, synced: true } : s
      )
      localStorage.setItem(LOCAL_STORAGE_KEYS.SESSIONS, JSON.stringify(updatedSessions))
    } catch (error) {
      console.error('Failed to sync session to cloud:', error)
    }
  }

  return newSession
}

export const getSessions = (startDate, endDate) => {
  const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.SESSIONS) || '[]')
  
  if (!startDate && !endDate) {
    return sessions
  }

  const start = startDate ? new Date(startDate).getTime() : 0
  const end = endDate ? new Date(endDate).getTime() : Date.now()

  return sessions.filter(session => {
    const sessionTime = new Date(session.createdAt).getTime()
    return sessionTime >= start && sessionTime <= end
  })
}

export const getSessionsFromCloud = async (startDate, endDate) => {
  const user = getCurrentUser()
  if (!user || !db) return []

  try {
    let sessionsQuery = collection(db, 'users', user.uid, 'sessions')
    
    if (startDate) {
      sessionsQuery = query(sessionsQuery, where('createdAt', '>=', startDate.toISOString()))
    }
    if (endDate) {
      sessionsQuery = query(sessionsQuery, where('createdAt', '<=', endDate.toISOString()))
    }

    const snapshot = await getDocs(sessionsQuery)
    return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
  } catch (error) {
    console.error('Failed to get sessions from cloud:', error)
    return []
  }
}
