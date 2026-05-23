import { createStore } from 'vuex'

const STORAGE_KEY = 'code-snippets'
const SHARE_KEY = 'shared-snippets'
const THEME_KEY = 'app-theme'

function loadFromStorage(key) {
  try {
    const data = localStorage.getItem(key)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveToStorage(key, data) {
  localStorage.setItem(key, JSON.stringify(data))
}

export default createStore({
  state: {
    snippets: loadFromStorage(STORAGE_KEY),
    sharedSnippets: loadFromStorage(SHARE_KEY),
    currentSnippetId: null,
    theme: localStorage.getItem(THEME_KEY) || 'dark',
    searchQuery: '',
    selectedTags: [],
    showVersionHistory: false,
    showShareModal: false
  },
  getters: {
    tagStats: (state) => {
      const stats = {}
      state.snippets.forEach(s => {
        s.tags.forEach(t => {
          stats[t] = (stats[t] || 0) + 1
        })
      })
      return Object.entries(stats)
        .map(([tag, count]) => ({ tag, count }))
        .sort((a, b) => b.count - a.count)
    },
    filteredSnippets: (state) => {
      let result = state.snippets
      if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase()
        result = result.filter(s => 
          s.title.toLowerCase().includes(query) ||
          s.code.toLowerCase().includes(query) ||
          s.tags.some(t => t.toLowerCase().includes(query)) ||
          (s.description && s.description.toLowerCase().includes(query))
        )
      }
      if (state.selectedTags.length > 0) {
        result = result.filter(s => 
          state.selectedTags.some(tag => s.tags.includes(tag))
        )
      }
      return result.sort((a, b) => b.updatedAt - a.updatedAt)
    },
    currentSnippet: (state) => {
      return state.snippets.find(s => s.id === state.currentSnippetId) || null
    },
    getSharedSnippet: (state) => (shareId) => {
      const shared = state.sharedSnippets.find(s => s.shareId === shareId)
      if (!shared) return null
      if (shared.expiresAt && shared.expiresAt < Date.now()) {
        return null
      }
      return state.snippets.find(s => s.id === shared.snippetId) || null
    }
  },
  mutations: {
    SET_THEME(state, theme) {
      state.theme = theme
      localStorage.setItem(THEME_KEY, theme)
      document.documentElement.setAttribute('data-theme', theme)
    },
    SET_SEARCH_QUERY(state, query) {
      state.searchQuery = query
    },
    TOGGLE_TAG(state, tag) {
      const index = state.selectedTags.indexOf(tag)
      if (index === -1) {
        state.selectedTags.push(tag)
      } else {
        state.selectedTags.splice(index, 1)
      }
    },
    CLEAR_TAGS(state) {
      state.selectedTags = []
    },
    SET_CURRENT_SNIPPET(state, id) {
      state.currentSnippetId = id
    },
    ADD_SNIPPET(state, snippet) {
      const fullSnippet = {
        ...snippet,
        versions: [],
        description: ''
      }
      state.snippets.push(fullSnippet)
      saveToStorage(STORAGE_KEY, state.snippets)
    },
    UPDATE_SNIPPET(state, { id, data, createVersion = true }) {
      const index = state.snippets.findIndex(s => s.id === id)
      if (index !== -1) {
        const oldSnippet = state.snippets[index]
        
        if (createVersion && oldSnippet.code !== data.code) {
          const version = {
            id: Date.now().toString(),
            title: oldSnippet.title,
            code: oldSnippet.code,
            language: oldSnippet.language,
            tags: [...oldSnippet.tags],
            description: oldSnippet.description || '',
            createdAt: Date.now()
          }
          if (!oldSnippet.versions) {
            oldSnippet.versions = []
          }
          oldSnippet.versions.unshift(version)
          if (oldSnippet.versions.length > 20) {
            oldSnippet.versions = oldSnippet.versions.slice(0, 20)
          }
        }
        
        state.snippets[index] = { 
          ...oldSnippet, 
          ...data, 
          updatedAt: Date.now() 
        }
        saveToStorage(STORAGE_KEY, state.snippets)
      }
    },
    DELETE_SNIPPET(state, id) {
      state.snippets = state.snippets.filter(s => s.id !== id)
      state.sharedSnippets = state.sharedSnippets.filter(s => s.snippetId !== id)
      if (state.currentSnippetId === id) {
        state.currentSnippetId = null
      }
      saveToStorage(STORAGE_KEY, state.snippets)
      saveToStorage(SHARE_KEY, state.sharedSnippets)
    },
    ROLLBACK_VERSION(state, { snippetId, versionId }) {
      const snippet = state.snippets.find(s => s.id === snippetId)
      if (snippet && snippet.versions) {
        const version = snippet.versions.find(v => v.id === versionId)
        if (version) {
          snippet.versions.unshift({
            id: Date.now().toString(),
            title: snippet.title,
            code: snippet.code,
            language: snippet.language,
            tags: [...snippet.tags],
            description: snippet.description || '',
            createdAt: Date.now()
          })
          
          snippet.title = version.title
          snippet.code = version.code
          snippet.language = version.language
          snippet.tags = [...version.tags]
          snippet.description = version.description || ''
          snippet.updatedAt = Date.now()
          
          saveToStorage(STORAGE_KEY, state.snippets)
        }
      }
    },
    DELETE_VERSION(state, { snippetId, versionId }) {
      const snippet = state.snippets.find(s => s.id === snippetId)
      if (snippet && snippet.versions) {
        snippet.versions = snippet.versions.filter(v => v.id !== versionId)
        saveToStorage(STORAGE_KEY, state.snippets)
      }
    },
    CREATE_SHARE_LINK(state, { snippetId, expiresAt }) {
      const shareId = Math.random().toString(36).substring(2, 15)
      const shareData = {
        shareId,
        snippetId,
        createdAt: Date.now(),
        expiresAt: expiresAt || null
      }
      state.sharedSnippets.push(shareData)
      saveToStorage(SHARE_KEY, state.sharedSnippets)
      return shareId
    },
    SET_SHOW_VERSION_HISTORY(state, show) {
      state.showVersionHistory = show
    },
    SET_SHOW_SHARE_MODAL(state, show) {
      state.showShareModal = show
    }
  },
  actions: {
    createSnippet({ commit }, snippetData) {
      const snippet = {
        id: Date.now().toString(),
        title: snippetData.title || '未命名片段',
        code: snippetData.code || '',
        language: snippetData.language || 'javascript',
        tags: snippetData.tags || [],
        description: snippetData.description || '',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        versions: []
      }
      commit('ADD_SNIPPET', snippet)
      commit('SET_CURRENT_SNIPPET', snippet.id)
      return snippet
    },
    updateSnippet({ commit }, { id, data, createVersion = true }) {
      commit('UPDATE_SNIPPET', { id, data, createVersion })
    },
    deleteSnippet({ commit }, id) {
      commit('DELETE_SNIPPET', id)
    },
    rollbackVersion({ commit }, { snippetId, versionId }) {
      commit('ROLLBACK_VERSION', { snippetId, versionId })
    },
    deleteVersion({ commit }, { snippetId, versionId }) {
      commit('DELETE_VERSION', { snippetId, versionId })
    },
    createShareLink({ commit }, { snippetId, expiresIn }) {
      let expiresAt = null
      if (expiresIn) {
        expiresAt = Date.now() + expiresIn
      }
      const shareId = commit('CREATE_SHARE_LINK', { snippetId, expiresAt })
      return shareId
    },
    exportSnippets({ state }) {
      const dataStr = JSON.stringify(state.snippets, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `code-snippets-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }
})
