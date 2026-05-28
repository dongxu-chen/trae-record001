import { create } from 'zustand';

const useStore = create((set, get) => ({
  documents: [],
  currentDocument: null,
  revisions: [],
  comments: [],
  activeUsers: [],
  cursors: new Map(),

  setDocuments: (documents) => set({ documents }),
  
  setCurrentDocument: (document) => set({ currentDocument: document }),
  
  addDocument: (document) => set((state) => ({
    documents: [document, ...state.documents]
  })),
  
  updateDocument: (docId, updates) => set((state) => ({
    documents: state.documents.map(d => 
      d.docId === docId ? { ...d, ...updates } : d
    ),
    currentDocument: state.currentDocument?.docId === docId 
      ? { ...state.currentDocument, ...updates }
      : state.currentDocument
  })),
  
  setRevisions: (revisions) => set({ revisions }),
  
  addRevision: (revision) => set((state) => ({
    revisions: [revision, ...state.revisions]
  })),
  
  updateRevision: (revisionId, updates) => set((state) => ({
    revisions: state.revisions.map(r => 
      r._id === revisionId ? { ...r, ...updates } : r
    )
  })),
  
  setComments: (comments) => set({ comments }),
  
  addComment: (comment) => set((state) => ({
    comments: [comment, ...state.comments]
  })),
  
  updateComment: (commentId, updates) => set((state) => ({
    comments: state.comments.map(c => 
      c._id === commentId ? { ...c, ...updates } : c
    )
  })),
  
  setActiveUsers: (users) => set({ activeUsers: users }),
  
  setCursor: (socketId, cursor) => set((state) => {
    const newCursors = new Map(state.cursors);
    if (cursor) {
      newCursors.set(socketId, cursor);
    } else {
      newCursors.delete(socketId);
    }
    return { cursors: newCursors };
  }),
  
  clearCursors: () => set({ cursors: new Map() }),
}));

export default useStore;
