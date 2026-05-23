import { Note } from '@/types'

export interface WikiLink {
  sourceId: string
  sourceTitle: string
  targetId: string
  targetTitle: string
}

export interface LinkInfo {
  noteId?: string
  title: string
  raw: string
  exists: boolean
}

export function parseWikiLinks(content: string): LinkInfo[] {
  const wikiLinkRegex = /\[\[([^\]]+)\]\]/g
  const links: LinkInfo[] = []
  let match

  while ((match = wikiLinkRegex.exec(content)) !== null) {
    const raw = match[0]
    const fullText = match[1]
    
    let title = fullText
    let alias: string | undefined
    
    if (fullText.includes('|')) {
      const parts = fullText.split('|')
      title = parts[0].trim()
      alias = parts[1].trim()
    }
    
    links.push({
      title: title.trim(),
      raw,
      exists: false,
    })
  }
  
  return links
}

export function resolveWikiLinks(
  content: string,
  allNotes: Note[]
): { content: string; links: WikiLink[] } {
  const noteMap = new Map(allNotes.map(n => [n.title.toLowerCase(), n]))
  
  const links: WikiLink[] = []
  let resolvedContent = content
  
  const wikiLinkRegex = /\[\[([^\]]+)\]\]/g
  
  resolvedContent = resolvedContent.replace(wikiLinkRegex, (match, fullText) => {
    const title = fullText.includes('|') 
      ? fullText.split('|')[0].trim() 
      : fullText.trim()
    
    const displayText = fullText.includes('|') 
      ? fullText.split('|')[1].trim() 
      : title
    
    const note = noteMap.get(title.toLowerCase())
    
    if (note) {
      links.push({
        sourceId: '',
        sourceTitle: '',
        targetId: note._id,
        targetTitle: note.title,
      })
      return `<a href="/note/${note._id}" class="wiki-link wiki-link-exists" data-note-id="${note._id}">${displayText}</a>`
    } else {
      return `<span class="wiki-link wiki-link-missing" data-title="${title}">${displayText}</span>`
    }
  })
  
  return { content: resolvedContent, links }
}

export function getBacklinks(
  noteId: string,
  allNotes: Note[]
): { noteId: string; title: string; snippet: string }[] {
  const currentNote = allNotes.find(n => n._id === noteId)
  if (!currentNote) return []
  
  const backlinks: { noteId: string; title: string; snippet: string }[] = []
  
  for (const note of allNotes) {
    if (note._id === noteId) continue
    
    const links = parseWikiLinks(note.content)
    const hasLink = links.some(
      link => link.title.toLowerCase() === currentNote.title.toLowerCase()
    )
    
    if (hasLink) {
      const snippet = getContextSnippet(note.content, currentNote.title)
      backlinks.push({
        noteId: note._id,
        title: note.title,
        snippet,
      })
    }
  }
  
  return backlinks
}

function getContextSnippet(content: string, keyword: string, chars: number = 50): string {
  const index = content.toLowerCase().indexOf(keyword.toLowerCase())
  if (index === -1) return ''
  
  const start = Math.max(0, index - chars)
  const end = Math.min(content.length, index + keyword.length + chars)
  
  let snippet = content.substring(start, end)
  if (start > 0) snippet = '...' + snippet
  if (end < content.length) snippet = snippet + '...'
  
  return snippet
}

export function extractLinkTitles(content: string): string[] {
  const links = parseWikiLinks(content)
  return [...new Set(links.map(l => l.title.toLowerCase()))]
}

export function buildKnowledgeGraph(notes: Note[]): {
  nodes: { id: string; name: string; val: number }[]
  links: { source: string; target: string; value: number }[]
} {
  const nodes = notes.map(note => ({
    id: note._id,
    name: note.title,
    val: 1,
  }))
  
  const links: { source: string; target: string; value: number }[] = []
  const noteTitleMap = new Map(notes.map(n => [n.title.toLowerCase(), n._id]))
  
  for (const note of notes) {
    const linkTitles = extractLinkTitles(note.content)
    
    for (const title of linkTitles) {
      const targetId = noteTitleMap.get(title)
      if (targetId && targetId !== note._id) {
        links.push({
          source: note._id,
          target: targetId,
          value: 1,
        })
      }
    }
  }
  
  return { nodes, links }
}

export function getOrphanedNotes(notes: Note[]): Note[] {
  const { links } = buildKnowledgeGraph(notes)
  const linkedNotes = new Set([
    ...links.map(l => l.source),
    ...links.map(l => l.target),
  ])
  
  return notes.filter(n => !linkedNotes.has(n._id))
}

export function getMostConnectedNotes(notes: Note[], limit: number = 10): Note[] {
  const { links } = buildKnowledgeGraph(notes)
  const connectionCount = new Map<string, number>()
  
  for (const link of links) {
    connectionCount.set(
      link.source,
      (connectionCount.get(link.source) || 0) + 1
    )
    connectionCount.set(
      link.target,
      (connectionCount.get(link.target) || 0) + 1
    )
  }
  
  return notes
    .map(note => ({ note, count: connectionCount.get(note._id) || 0 }))
    .filter(n => n.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
    .map(n => n.note)
}
