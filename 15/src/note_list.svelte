<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let notes = [];
  export let currentNote = null;
  export let allTags = [];

  const dispatch = createEventDispatcher();

  let searchQuery = '';
  let selectedTags = [];
  let showTagPanel = false;
  let debounceTimer = null;
  let searchWorker = null;
  let displayedNotes = [];
  let isSearching = false;

  onMount(() => {
    $: if (notes) {
      displayedNotes = notes;
    }
  });

  $: if (searchWorker && notes) {
    scheduleSearch();
  }

  const selectNote = (note) => {
    dispatch('select', note);
  };

  const toggleTag = (tagName) => {
    const index = selectedTags.indexOf(tagName);
    if (index > -1) {
      selectedTags = selectedTags.filter(t => t !== tagName);
    } else {
      selectedTags = [...selectedTags, tagName];
    }
    scheduleSearch();
  };

  const clearSearch = () => {
    searchQuery = '';
    selectedTags = [];
    displayedNotes = notes;
  };

  const scheduleSearch = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    if (!searchQuery && selectedTags.length === 0) {
      displayedNotes = notes;
      return;
    }

    isSearching = true;
    debounceTimer = setTimeout(() => {
      performSearch();
    }, 150);
  };

  const performSearch = async () => {
    try {
      const result = await window.__TAURI__?.invoke?.('search_notes', {
        query: searchQuery,
        tagsFilter: selectedTags
      });
      
      if (result) {
        displayedNotes = result;
      }
    } catch (e) {
      console.error('Search error:', e);
      displayedNotes = clientSideSearch();
    } finally {
      isSearching = false;
    }
  };

  const clientSideSearch = () => {
    const query = searchQuery.toLowerCase().trim();
    const tags = selectedTags.map(t => t.toLowerCase());
    
    return notes.filter(note => {
      if (tags.length > 0) {
        const noteTags = (note.tags || []).map(t => t.toLowerCase());
        const allMatch = tags.every(tag => noteTags.includes(tag));
        if (!allMatch) return false;
      }
      
      if (!query) return true;
      
      const title = (note.title || '').toLowerCase();
      const preview = (note.preview || '').toLowerCase();
      const noteTags = (note.tags || []).join(' ').toLowerCase();
      
      return title.includes(query) || preview.includes(query) || noteTags.includes(query);
    });
  };

  const handleSearchInput = () => {
    scheduleSearch();
  };

  const clearTagFilter = (tag) => {
    selectedTags = selectedTags.filter(t => t !== tag);
    scheduleSearch();
  };

  const formatDate = (timestamp) => {
    if (!timestamp || timestamp === '0') return '';
    const date = new Date(parseInt(timestamp) * 1000);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;

    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric'
    });
  };

  const getPreview = (note) => {
    if (note.preview && note.preview.trim()) {
      return note.preview;
    }
    if (note.content) {
      const text = note.content.replace(/^#+\s*/, '').split('\n');
      for (let i = 1; i < text.length; i++) {
        const line = text[i].trim();
        if (line && !line.startsWith('#')) {
          return line.length > 60 ? line.slice(0, 60) + '...' : line;
        }
      }
    }
    return '暂无内容';
  };

  const hasFilters = searchQuery || selectedTags.length > 0;
</script>

<div class="note-list-container">
  <div class="search-section">
    <div class="search-box">
      <input
        type="text"
        class="search-input"
        placeholder="搜索笔记..."
        bind:value={searchQuery}
        on:input={handleSearchInput}
      />
      {#if searchQuery}
        <button class="clear-search" on:click={() => { searchQuery = ''; scheduleSearch(); }}>
          ✕
        </button>
      {/if}
      {#if isSearching}
        <span class="search-spinner">...</span>
      {/if}
    </div>
    
    <div class="tag-toggle-row">
      <button 
        class="tag-toggle-btn"
        class:active={showTagPanel}
        on:click={() => showTagPanel = !showTagPanel}
      >
        <span class="tag-icon">#</span>
        标签过滤
        {#if selectedTags.length > 0}
          <span class="tag-badge">{selectedTags.length}</span>
        {/if}
      </button>
      
      {#if hasFilters}
        <button class="clear-all-btn" on:click={clearSearch}>
          清除过滤
        </button>
      {/if}
    </div>
    
    {#if showTagPanel && allTags.length > 0}
      <div class="tag-panel">
        <div class="tag-panel-title">所有标签</div>
        <div class="tag-cloud">
          {#each allTags as tagInfo}
            <button
              class="tag-chip"
              class:selected={selectedTags.includes(tagInfo[0])}
              on:click={() => toggleTag(tagInfo[0])}
            >
              #{tagInfo[0]}
              <span class="tag-count">({tagInfo[1]})</span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
    
    {#if selectedTags.length > 0}
      <div class="active-tags">
        <span class="active-tags-label">已选:</span>
        {#each selectedTags as tag}
          <span class="active-tag-chip">
            #{tag}
            <button class="remove-tag" on:click={() => clearTagFilter(tag)}>✕</button>
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="note-list">
    {#if displayedNotes.length === 0}
      <div class="empty-list">
        {#if hasFilters}
          <p>没有匹配的笔记</p>
          <button class="clear-all-btn" on:click={clearSearch}>清除搜索条件</button>
        {:else}
          <p>还没有笔记</p>
          <p class="hint">点击上方"新建"开始</p>
        {/if}
      </div>
    {:else}
      {#each displayedNotes as note (note.file_path)}
        <div 
          class="note-item"
          class:active={currentNote?.file_path === note.file_path}
          on:click={() => selectNote(note)}
        >
          <div class="note-item-header">
            <span class="note-item-title">{note.title || '未命名'}</span>
            <span class="note-item-date">{formatDate(note.modified)}</span>
          </div>
          <div class="note-item-preview">{getPreview(note)}</div>
          {#if note.tags && note.tags.length > 0}
            <div class="note-item-tags">
              {#each note.tags.slice(0, 3) as tag}
                <span class="mini-tag">#{tag}</span>
              {/each}
              {#if note.tags.length > 3}
                <span class="mini-tag more">+{note.tags.length - 3}</span>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .note-list-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .search-section {
    padding: 12px 16px;
    border-bottom: 1px solid #e1e4e8;
    background: #f6f8fa;
  }

  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-input {
    width: 100%;
    padding: 8px 32px 8px 12px;
    border: 1px solid #d1d5da;
    border-radius: 6px;
    font-size: 14px;
    background: white;
    transition: border-color 0.2s ease;
  }

  .search-input:focus {
    outline: none;
    border-color: #0366d6;
    box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.1);
  }

  .clear-search {
    position: absolute;
    right: 8px;
    background: none;
    border: none;
    color: #6a737d;
    cursor: pointer;
    padding: 4px 8px;
    font-size: 14px;
  }

  .clear-search:hover {
    color: #24292e;
  }

  .search-spinner {
    position: absolute;
    right: 8px;
    color: #6a737d;
    font-size: 14px;
  }

  .tag-toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
  }

  .tag-toggle-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid #d1d5da;
    border-radius: 6px;
    background: white;
    cursor: pointer;
    font-size: 13px;
    color: #586069;
    transition: all 0.2s ease;
  }

  .tag-toggle-btn:hover {
    border-color: #0366d6;
    color: #0366d6;
  }

  .tag-toggle-btn.active {
    background: #f1f8ff;
    border-color: #0366d6;
    color: #0366d6;
  }

  .tag-icon {
    font-weight: bold;
  }

  .tag-badge {
    background: #0366d6;
    color: white;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
  }

  .clear-all-btn {
    background: none;
    border: none;
    color: #6a737d;
    font-size: 12px;
    cursor: pointer;
    padding: 4px 8px;
    text-decoration: underline;
  }

  .clear-all-btn:hover {
    color: #0366d6;
  }

  .tag-panel {
    margin-top: 10px;
    padding: 12px;
    background: white;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
  }

  .tag-panel-title {
    font-size: 12px;
    color: #6a737d;
    margin-bottom: 8px;
  }

  .tag-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .tag-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 14px;
    font-size: 12px;
    color: #586069;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .tag-chip:hover {
    border-color: #0366d6;
    background: #f1f8ff;
  }

  .tag-chip.selected {
    background: #0366d6;
    border-color: #0366d6;
    color: white;
  }

  .tag-count {
    opacity: 0.7;
    font-size: 11px;
  }

  .active-tags {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #e1e4e8;
  }

  .active-tags-label {
    font-size: 12px;
    color: #6a737d;
  }

  .active-tag-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: #f1f8ff;
    border: 1px solid #0366d6;
    border-radius: 12px;
    font-size: 12px;
    color: #0366d6;
  }

  .remove-tag {
    background: none;
    border: none;
    color: #0366d6;
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    line-height: 1;
  }

  .remove-tag:hover {
    opacity: 0.7;
  }

  .note-list {
    flex: 1;
    overflow-y: auto;
  }

  .empty-list {
    padding: 48px 16px;
    text-align: center;
    color: #6a737d;
  }

  .empty-list p {
    margin: 0;
  }

  .empty-list .hint {
    font-size: 12px;
    margin-top: 8px;
    opacity: 0.7;
  }

  .note-item {
    padding: 16px;
    border-bottom: 1px solid #e1e4e8;
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .note-item:hover {
    background: #f6f8fa;
  }

  .note-item.active {
    background: #f1f8ff;
    border-left: 3px solid #0366d6;
  }

  .note-item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 6px;
  }

  .note-item-title {
    font-size: 15px;
    font-weight: 600;
    color: #24292e;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .note-item-date {
    font-size: 12px;
    color: #6a737d;
    flex-shrink: 0;
  }

  .note-item-preview {
    font-size: 13px;
    color: #586069;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 6px;
  }

  .note-item-tags {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .mini-tag {
    font-size: 11px;
    color: #6a737d;
    background: #f1f8ff;
    padding: 2px 6px;
    border-radius: 10px;
  }

  .mini-tag.more {
    background: #f6f8fa;
    color: #959da5;
  }
</style>
