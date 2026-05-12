import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { MonacoBinding } from 'y-monaco';

const CollabContext = createContext(null);

const COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#00CED1'
];

function generateColor(index) {
  return COLORS[index % COLORS.length];
}

function generateUserName(id) {
  const adjectives = ['快速', '聪明', '勇敢', '友善', '创意', '热情', '冷静', '专注'];
  const nouns = ['狐狸', '熊猫', '狮子', '兔子', '老虎', '海豚', '猫头鹰', '蝴蝶'];
  
  const hash = id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const adj = adjectives[hash % adjectives.length];
  const noun = nouns[(hash * 7) % nouns.length];
  
  return `${adj}${noun}`;
}

function CollabProvider({ roomId, userId, children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [users, setUsers] = useState(new Map());
  const [error, setError] = useState(null);
  
  const ydocRef = useRef(null);
  const providerRef = useRef(null);
  const awarenessRef = useRef(null);
  const ytextRef = useRef(null);
  const bindingRef = useRef(null);
  const colorIndexRef = useRef(userId ? (userId.charCodeAt(0) + userId.charCodeAt(userId.length - 1)) % COLORS.length : Math.floor(Math.random() * COLORS.length));
  const userNameRef = useRef(userId ? generateUserName(userId) : generateUserName(Math.random().toString(36)));

  const init = useCallback(() => {
    if (ytextRef.current || !roomId) return;

    const ydoc = new Y.Doc();
    ydocRef.current = ydoc;

    const ytext = ydoc.getText('code');
    ytextRef.current = ytext;

    const ylang = ydoc.getText('language');
    const youtput = ydoc.getArray('output');

    const provider = new WebsocketProvider(
      window.location.origin.replace(/^https?:\/\//, 'ws://'),
      `room-${roomId}`,
      ydoc,
      {
        connect: true,
        params: {
          userId,
          userName: userNameRef.current
        }
      }
    );
    providerRef.current = provider;

    const awareness = provider.awareness;
    awarenessRef.current = awareness;

    awareness.setLocalStateField('user', {
      id: userId || `user-${Date.now()}`,
      name: userNameRef.current,
      color: generateColor(colorIndexRef.current),
      joinedAt: Date.now()
    });

    provider.on('status', (event) => {
      setIsConnected(event.status === 'connected');
      if (event.status === 'connected') {
        setError(null);
      }
    });

    provider.on('connection-error', (err) => {
      console.error('WebSocket 连接错误:', err);
      setError('连接协同服务器失败');
      setIsConnected(false);
    });

    awareness.on('change', (changes) => {
      const states = awareness.getStates();
      const userMap = new Map();
      
      states.forEach((state, clientId) => {
        if (state && state.user) {
          userMap.set(clientId, {
            ...state.user,
            clientId
          });
        }
      });
      
      setUsers(userMap);
    });

    ydoc.on('destroy', () => {
      provider.disconnect();
    });
  }, [roomId, userId]);

  useEffect(() => {
    if (roomId) {
      init();
    }

    return () => {
      if (bindingRef.current) {
        bindingRef.current.destroy();
        bindingRef.current = null;
      }
      if (providerRef.current) {
        providerRef.current.disconnect();
        providerRef.current = null;
      }
      if (ydocRef.current) {
        ydocRef.current.destroy();
        ydocRef.current = null;
      }
      ytextRef.current = null;
      awarenessRef.current = null;
    };
  }, [roomId, init]);

  const bindEditor = useCallback((editor) => {
    if (!ytextRef.current || !editor) return;
    if (bindingRef.current) {
      bindingRef.current.destroy();
    }

    const binding = new MonacoBinding(
      ytextRef.current,
      editor.getModel(),
      new Set([editor]),
      awarenessRef.current
    );
    bindingRef.current = binding;

    return () => {
      if (bindingRef.current === binding) {
        binding.destroy();
        bindingRef.current = null;
      }
    };
  }, []);

  const getCode = useCallback(() => {
    return ytextRef.current ? ytextRef.current.toString() : '';
  }, []);

  const setCode = useCallback((newCode) => {
    if (ytextRef.current) {
      ytextRef.current.delete(0, ytextRef.current.length);
      ytextRef.current.insert(0, newCode);
    }
  }, []);

  const sendOutput = useCallback((outputItem) => {
    if (!ydocRef.current) return;
    const youtput = ydocRef.current.getArray('output');
    youtput.push([outputItem]);
  }, []);

  const clearOutput = useCallback(() => {
    if (!ydocRef.current) return;
    const youtput = ydocRef.current.getArray('output');
    youtput.delete(0, youtput.length);
  }, []);

  const value = {
    isConnected,
    users,
    error,
    ydoc: ydocRef.current,
    ytext: ytextRef.current,
    awareness: awarenessRef.current,
    userName: userNameRef.current,
    userColor: generateColor(colorIndexRef.current),
    bindEditor,
    getCode,
    setCode,
    sendOutput,
    clearOutput
  };

  return (
    <CollabContext.Provider value={value}>
      {children}
    </CollabContext.Provider>
  );
}

function useCollab() {
  const context = useContext(CollabContext);
  if (!context) {
    return null;
  }
  return context;
}

export { CollabProvider, useCollab, generateColor, generateUserName };
