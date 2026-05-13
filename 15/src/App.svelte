<script>
  import NoteList from './note_list.svelte';
  import { renderMarkdown } from './markdown_parser.js';
  import 'highlight.js/styles/github.css';

  let notes = [];
  let allTags = [];
  let currentNote = null;
  let editorContent = '';
  let isDirty = false;
  let message = '';
  let messageType = 'info';
  let showTagEditor = false;
  let newTagInput = '';

  const invoke = async (cmd, args) => {
    try {
      return await window.__TAURI__?.invoke?.(cmd, args);
    } catch (e) {
      console.error('Tauri invoke error:', e);
      return null;
    }
  };

  const loadNotes = async () => {
    const result = await invoke('list_notes');
    if (result) {
      notes = result;
    }
    await loadAllTags();
    return notes;
  };

  const loadAllTags = async () => {
    const result = await invoke('get_all_tags');
    if (result) {
      allTags = result;
    }
    return allTags;
  };

  const extractTagsFromContent = (content) => {
    const tags = new Set();
    const regex = /#([a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      tags.add(match[1].toLowerCase());
    }
    return Array.from(tags);
  };

  const parseFrontmatter = (content) => {
    const lines = content.split('\n');
    if (lines.length < 3 || lines[0].trim() !== '---') {
      return { metadata: {}, bodyStart: 0, hasFrontmatter: false };
    }

    let endIdx = -1;
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') {
        endIdx = i;
        break;
      }
    }

    if (endIdx === -1) {
      return { metadata: {}, bodyStart: 0, hasFrontmatter: false };
    }

    const metadata = {};
    for (let i = 1; i < endIdx; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const colonIdx = line.indexOf(':');
      if (colonIdx !== -1) {
        const key = line.slice(0, colonIdx).trim().toLowerCase();
        let value = line.slice(colonIdx + 1).trim();
        if (value.startsWith('[') && value.endsWith(']')) {
          value = value.slice(1, -1);
        }
        metadata[key] = value;
      }
    }

    return { metadata, bodyStart: endIdx + 1, hasFrontmatter: true };
  };

  const updateNoteTags = (content, tags) => {
    const { metadata, bodyStart, hasFrontmatter } = parseFrontmatter(content);
    const lines = content.split('\n');
    
    let bodyLines = lines;
    let newFrontmatter = ['---'];
    
    if (hasFrontmatter) {
      bodyLines = lines.slice(bodyStart);
    }
    
    if (tags && tags.length > 0) {
      metadata.tags = tags.join(', ');
    } else if (metadata.tags) {
      delete metadata.tags;
    }
    
    for (const [key, value] of Object.entries(metadata)) {
      if (value) {
        newFrontmatter.push(`${key}: ${value}`);
      }
    }
    
    if (Object.keys(metadata).length === 0) {
      return bodyLines.join('\n');
    }
    
    newFrontmatter.push('---');
    const result = [...newFrontmatter, ...bodyLines].join('\n');
    return result;
  };

  const getCurrentNoteTags = () => {
    if (!currentNote) return [];
    if (currentNote.tags && currentNote.tags.length > 0) {
      return currentNote.tags;
    }
    return extractTagsFromContent(editorContent);
  };

  const addTagToNote = () => {
    const tag = newTagInput.trim().toLowerCase();
    if (!tag) return;
    
    const cleanTag = tag.replace(/^#+/, '');
    const currentTags = getCurrentNoteTags();
    
    if (!currentTags.includes(cleanTag)) {
      const newTags = [...currentTags, cleanTag];
      editorContent = updateNoteTags(editorContent, newTags);
      currentNote = { ...currentNote, tags: newTags };
      isDirty = true;
    }
    
    newTagInput = '';
  };

  const removeTagFromNote = (tagToRemove) => {
    const currentTags = getCurrentNoteTags();
    const newTags = currentTags.filter(t => t !== tagToRemove);
    editorContent = updateNoteTags(editorContent, newTags);
    currentNote = { ...currentNote, tags: newTags };
    isDirty = true;
  };

  const selectNote = async (note) => {
    if (isDirty && !await confirmSave()) {
      return;
    }

    if (!note.content || note.content.trim() === '') {
      const fullNote = await invoke('read_note', {
        filePath: note.file_path
      });
      if (fullNote) {
        currentNote = fullNote;
        editorContent = fullNote.content;
      }
    } else {
      currentNote = note;
      editorContent = note.content;
    }
    isDirty = false;
    showTagEditor = false;
  };

  const createNewNote = async () => {
    if (isDirty && !await confirmSave()) {
      return;
    }
    const result = await invoke('create_new_note');
    if (result) {
      currentNote = result;
      editorContent = result.content;
      isDirty = false;
      await loadNotes();
    }
  };

  const saveCurrentNote = async () => {
    if (!currentNote) return;

    const title = extractTitle(editorContent);
    const result = await invoke('save_note', {
      title,
      content: editorContent,
      filePath: currentNote.file_path
    });

    if (result) {
      currentNote = result;
      isDirty = false;
      showMessage('保存成功', 'success');
      await loadNotes();
    } else {
      showMessage('保存失败', 'error');
    }
  };

  const deleteCurrentNote = async () => {
    if (!currentNote) return;
    if (!confirm('确定要删除这篇笔记吗？')) return;

    const deletedPath = currentNote.file_path;
    await invoke('delete_note', {
      filePath: deletedPath
    });

    notes = notes.filter(n => n.file_path !== deletedPath);
    currentNote = null;
    editorContent = '';
    isDirty = false;
    showMessage('已删除', 'info');

    await loadNotes();
  };

  const extractTitle = (content) => {
    const firstLine = content.split('\n').find(l => {
      const trimmed = l.trim();
      return trimmed && trimmed !== '---';
    }) || '';
    return firstLine.replace(/^#+\s*/, '').trim() || '未命名笔记';
  };

  const confirmSave = async () => {
    if (!currentNote) return true;
    const answer = confirm('当前笔记尚未保存，是否保存？');
    if (answer) {
      await saveCurrentNote();
    }
    return true;
  };

  const showMessage = (msg, type) => {
    message = msg;
    messageType = type;
    setTimeout(() => {
      message = '';
    }, 2000);
  };

  const handleInput = () => {
    isDirty = true;
  };

  const handleKeydown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveCurrentNote();
    }
  };

  const handleTagInputKeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTagToNote();
    }
  };

  const getTagSuggestions = () => {
    const currentTags = getCurrentNoteTags();
    const inputLower = newTagInput.toLowerCase();
    return allTags
      .filter(t => {
        const tagName = typeof t === 'string' ? t : t[0];
        return !currentTags.includes(tagName) && 
               tagName.toLowerCase().includes(inputLower);
      })
      .slice(0, 5);
  };

  const suggestTag = (tagInfo) => {
    const tagName = typeof tagInfo === 'string' ? tagInfo : tagInfo[0];
    newTagInput = tagName;
  };

  loadNotes();
</script>

<main class="app">
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>笔记</h2>
      <button class="new-btn" on:click={createNewNote}>+ 新建</button>
    </div>
    <NoteList 
      {notes} 
      {currentNote}
      {allTags}
      on:select={(e) => selectNote(e.detail)}
    />
  </aside>

  <section class="editor-section">
    {#if currentNote}
      <div class="editor-header">
        <div class="note-title">
          {currentNote.title}
          {#if isDirty} <span class="dirty-dot">●</span>{/if}
        </div>
        <div class="header-actions">
          <button 
            class="tag-edit-btn" 
            class:active={showTagEditor}
            on:click={() => showTagEditor = !showTagEditor}
          >
            🏷️ 标签
            {#if currentNote.tags && currentNote.tags.length > 0}
              <span class="tag-count">{currentNote.tags.length}</span>
            {/if}
          </button>
          <button class="save-btn" on:click={saveCurrentNote}>保存</button>
          <button class="delete-btn" on:click={deleteCurrentNote}>删除</button>
        </div>
      </div>

      {#if showTagEditor}
        <div class="tag-editor-panel">
          <div class="tag-editor-header">
            <span>当前笔记标签</span>
            <button class="close-btn" on:click={() => showTagEditor = false}>✕</button>
          </div>
          
          {#if getCurrentNoteTags().length > 0}
            <div class="current-tags">
              {#each getCurrentNoteTags() as tag}
                <span class="tag-badge">
                  #{tag}
                  <button class="remove-tag-btn" on:click={() => removeTagFromNote(tag)}>✕</button>
                </span>
              {/each}
            </div>
          {:else}
            <div class="no-tags">暂无标签</div>
          {/if}
          
          <div class="add-tag-section">
            <input
              type="text"
              class="tag-input"
              placeholder="输入标签，按回车添加..."
              bind:value={newTagInput}
              on:keydown={handleTagInputKeydown}
            />
            <button class="add-tag-btn" on:click={addTagToNote}>添加</button>
          </div>
          
          {#if newTagInput && getTagSuggestions().length > 0}
            <div class="tag-suggestions">
              <div class="suggestions-label">建议标签</div>
              {#each getTagSuggestions() as suggestion}
                <button 
                  class="suggestion-item"
                  on:click={() => suggestTag(suggestion)}
                >
                  #{typeof suggestion === 'string' ? suggestion : suggestion[0]}
                  <span class="suggestion-count">
                    ({typeof suggestion === 'string' ? '0' : suggestion[1]})
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <div class="editor-container">
        <div class="editor-pane">
          <textarea
            class="editor"
            bind:value={editorContent}
            on:input={handleInput}
            on:keydown={handleKeydown}
            placeholder="在这里编写 Markdown...
支持 #标签 语法，也可以通过标签按钮管理"
          />
        </div>

        <div class="preview-pane">
          <div class="preview-label">预览</div>
          <div 
            class="preview-content"
            class:markdown-body={true}
            {@html renderMarkdown(editorContent)}
          />
        </div>
      </div>
    {:else}
      <div class="empty-state">
        <h2>欢迎使用 Markdown 笔记</h2>
        <p>从左侧选择一篇笔记，或点击"新建"开始写作</p>
        <p class="tip-tags">提示：在内容中使用 <code>#标签名</code> 可以自动添加标签</p>
        <button class="big-new-btn" on:click={createNewNote}>创建新笔记</button>
      </div>
    {/if}
  </section>

  {#if message}
    <div class="message {messageType}">
      {message}
    </div>
  {/if}
</main>

<style>
  .app {
    display: flex;
    height: 100vh;
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .sidebar {
    width: 280px;
    border-right: 1px solid #e1e4e8;
    display: flex;
    flex-direction: column;
    background: #fafbfc;
  }

  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid #e1e4e8;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sidebar-header h2 {
    margin: 0;
    font-size: 18px;
    color: #24292e;
  }

  .new-btn {
    padding: 6px 12px;
    background: #2ea44f;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
  }

  .new-btn:hover {
    background: #22863a;
  }

  .editor-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .editor-header {
    padding: 12px 24px;
    border-bottom: 1px solid #e1e4e8;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
  }

  .note-title {
    font-size: 16px;
    font-weight: 600;
    color: #24292e;
  }

  .dirty-dot {
    color: #e36209;
    margin-left: 4px;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .tag-edit-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border: 1px solid #d1d5da;
    border-radius: 6px;
    background: white;
    cursor: pointer;
    font-size: 14px;
    color: #586069;
    transition: all 0.2s ease;
  }

  .tag-edit-btn:hover {
    border-color: #0366d6;
    color: #0366d6;
  }

  .tag-edit-btn.active {
    background: #f1f8ff;
    border-color: #0366d6;
    color: #0366d6;
  }

  .tag-count {
    background: #0366d6;
    color: white;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
  }

  .save-btn, .delete-btn {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
  }

  .save-btn {
    background: #0366d6;
    color: white;
  }

  .save-btn:hover {
    background: #0356b3;
  }

  .delete-btn {
    background: #d73a49;
    color: white;
  }

  .delete-btn:hover {
    background: #b31d28;
  }

  .tag-editor-panel {
    padding: 16px 24px;
    background: #f6f8fa;
    border-bottom: 1px solid #e1e4e8;
  }

  .tag-editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    font-size: 13px;
    color: #6a737d;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    color: #6a737d;
    cursor: pointer;
    font-size: 14px;
    padding: 4px;
  }

  .close-btn:hover {
    color: #24292e;
  }

  .current-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  .tag-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: #f1f8ff;
    border: 1px solid #0366d6;
    border-radius: 14px;
    font-size: 13px;
    color: #0366d6;
  }

  .remove-tag-btn {
    background: none;
    border: none;
    color: #0366d6;
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    line-height: 1;
    opacity: 0.7;
  }

  .remove-tag-btn:hover {
    opacity: 1;
  }

  .no-tags {
    color: #959da5;
    font-size: 13px;
    margin-bottom: 16px;
  }

  .add-tag-section {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }

  .tag-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #d1d5da;
    border-radius: 6px;
    font-size: 14px;
  }

  .tag-input:focus {
    outline: none;
    border-color: #0366d6;
    box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.1);
  }

  .add-tag-btn {
    padding: 8px 16px;
    background: #2ea44f;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
  }

  .add-tag-btn:hover {
    background: #22863a;
  }

  .tag-suggestions {
    background: white;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    overflow: hidden;
  }

  .suggestions-label {
    padding: 6px 12px;
    font-size: 12px;
    color: #6a737d;
    background: #fafbfc;
    border-bottom: 1px solid #e1e4e8;
  }

  .suggestion-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    color: #586069;
    text-align: left;
  }

  .suggestion-item:hover {
    background: #f6f8fa;
  }

  .suggestion-count {
    color: #959da5;
    font-size: 12px;
  }

  .editor-container {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .editor-pane, .preview-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .editor-pane {
    border-right: 1px solid #e1e4e8;
  }

  .editor {
    flex: 1;
    padding: 24px;
    border: none;
    outline: none;
    resize: none;
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
    font-size: 14px;
    line-height: 1.6;
    background: white;
  }

  .preview-label {
    padding: 8px 24px;
    border-bottom: 1px solid #e1e4e8;
    font-size: 12px;
    color: #6a737d;
    background: #fafbfc;
  }

  .preview-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .markdown-body :global(h1) { font-size: 2em; margin: 0.67em 0; font-weight: 600; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
  .markdown-body :global(h2) { font-size: 1.5em; margin: 0.83em 0; font-weight: 600; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
  .markdown-body :global(h3) { font-size: 1.17em; margin: 1em 0; font-weight: 600; }
  .markdown-body :global(p) { margin: 1em 0; line-height: 1.6; }
  .markdown-body :global(ul), .markdown-body :global(ol) { padding-left: 2em; margin: 1em 0; }
  .markdown-body :global(li) { margin: 0.25em 0; }
  .markdown-body :global(code) { background: rgba(27, 31, 35, 0.05); padding: 0.2em 0.4em; border-radius: 3px; font-size: 85%; font-family: 'SFMono-Regular', Consolas, monospace; }
  .markdown-body :global(pre) { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }
  .markdown-body :global(pre code) { background: none; padding: 0; }
  .markdown-body :global(blockquote) { border-left: 4px solid #dfe2e5; color: #6a737d; padding: 0 1em; margin: 1em 0; }
  .markdown-body :global(a) { color: #0366d6; text-decoration: none; }
  .markdown-body :global(a:hover) { text-decoration: underline; }
  .markdown-body :global(strong) { font-weight: 600; }
  .markdown-body :global(em) { font-style: italic; }
  .markdown-body :global(hr) { border: none; border-top: 1px solid #e1e4e8; margin: 2em 0; }
  .markdown-body :global(table) { border-collapse: collapse; margin: 1em 0; }
  .markdown-body :global(th), .markdown-body :global(td) { border: 1px solid #dfe2e5; padding: 8px 12px; }
  .markdown-body :global(th) { background: #f6f8fa; font-weight: 600; }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    color: #6a737d;
  }

  .empty-state h2 {
    margin-bottom: 8px;
    color: #24292e;
  }

  .empty-state p {
    margin-bottom: 8px;
  }

  .empty-state .tip-tags {
    font-size: 13px;
    opacity: 0.8;
    margin-bottom: 24px;
  }

  .empty-state .tip-tags code {
    background: rgba(27, 31, 35, 0.05);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'SFMono-Regular', Consolas, monospace;
    font-size: 12px;
  }

  .big-new-btn {
    padding: 12px 24px;
    background: #2ea44f;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
    font-weight: 600;
  }

  .big-new-btn:hover {
    background: #22863a;
  }

  .message {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 24px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: fadeIn 0.2s ease;
  }

  .message.success { background: #2ea44f; }
  .message.error { background: #d73a49; }
  .message.info { background: #0366d6; }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateX(-50%) translateY(10px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
  }

  :global(.hljs) {
    background: #f6f8fa !important;
    border-radius: 6px;
    padding: 16px;
  }
</style>
