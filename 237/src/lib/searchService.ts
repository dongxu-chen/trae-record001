import InvertedIndex from '@/models/InvertedIndex'
import Note from '@/models/Note'
import { initJieba, tokenize, tokenizeWithWeight } from './jieba'
import { Types } from 'mongoose'

export interface SearchHit {
  noteId: string
  title: string
  content: string
  score: number
  highlight?: {
    title?: string[]
    content?: string[]
    ocrText?: string[]
  }
}

export async function indexDocument(noteId: string, title: string, content: string, ocrText: string = '') {
  await initJieba()
  
  const noteObjectId = new Types.ObjectId(noteId)
  
  await InvertedIndex.deleteMany({ 'postings.noteId': noteObjectId })
  
  const titleTokens = tokenizeWithWeight(title)
  const contentTokens = tokenizeWithWeight(content)
  const ocrTokens = tokenizeWithWeight(ocrText)
  
  const allTokens = new Set([...titleTokens.keys(), ...contentTokens.keys(), ...ocrTokens.keys()])
  
  const bulkOps: any[] = []
  
  for (const term of allTokens) {
    const titleFreq = titleTokens.get(term) || 0
    const contentFreq = contentTokens.get(term) || 0
    const ocrFreq = ocrTokens.get(term) || 0
    const totalFreq = titleFreq * 2 + contentFreq + ocrFreq * 0.5
    
    const titlePositions = getTokenPositions(title, term)
    const contentPositions = getTokenPositions(content, term)
    const ocrPositions = getTokenPositions(ocrText, term)
    
    const fieldWeight = titleFreq > 0 ? 2 : (contentFreq > 0 ? 1 : 0.5)
    
    bulkOps.push({
      updateOne: {
        filter: { term },
        update: {
          $push: {
            postings: {
              noteId: noteObjectId,
              positions: [...titlePositions, ...contentPositions, ...ocrPositions],
              frequency: totalFreq,
              fieldWeight,
            },
          },
          $inc: { documentFrequency: 1 },
        },
        upsert: true,
      },
    })
  }
  
  if (bulkOps.length > 0) {
    await InvertedIndex.bulkWrite(bulkOps)
  }
}

export async function removeDocumentFromIndex(noteId: string) {
  const noteObjectId = new Types.ObjectId(noteId)
  
  await InvertedIndex.updateMany(
    { 'postings.noteId': noteObjectId },
    {
      $pull: { postings: { noteId: noteObjectId } },
      $inc: { documentFrequency: -1 },
    }
  )
  
  await InvertedIndex.deleteMany({ postings: { $size: 0 } })
}

export async function search(
  query: string,
  options: {
    tags?: string[]
    folderId?: string
    limit?: number
  } = {}
): Promise<SearchHit[]> {
  await initJieba()
  
  const { tags, folderId, limit = 50 } = options
  
  const queryTokens = tokenize(query, true)
  if (queryTokens.length === 0) {
    return []
  }
  
  const indexEntries = await InvertedIndex.find({
    term: { $in: queryTokens },
  })
  
  if (indexEntries.length === 0) {
    return []
  }
  
  const docScores = new Map<string, number>()
  const docTerms = new Map<string, Set<string>>()
  
  const totalDocs = await Note.countDocuments()
  
  for (const entry of indexEntries) {
    const idf = Math.log((totalDocs - entry.documentFrequency + 0.5) / (entry.documentFrequency + 0.5) + 1)
    
    for (const posting of entry.postings) {
      const noteId = posting.noteId.toString()
      const tf = 1 + Math.log(posting.frequency)
      const score = tf * idf * posting.fieldWeight
      
      const currentScore = docScores.get(noteId) || 0
      docScores.set(noteId, currentScore + score)
      
      if (!docTerms.has(noteId)) {
        docTerms.set(noteId, new Set())
      }
      docTerms.get(noteId)!.add(entry.term)
    }
  }
  
  const scoredDocs = Array.from(docScores.entries())
    .map(([noteId, score]) => ({
      noteId,
      score,
      matchedTerms: docTerms.get(noteId) || new Set(),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
  
  const noteIds = scoredDocs.map(d => new Types.ObjectId(d.noteId))
  
  let noteQuery: any = { _id: { $in: noteIds } }
  if (tags && tags.length > 0) {
    noteQuery.tags = { $in: tags.map(t => new Types.ObjectId(t)) }
  }
  if (folderId) {
    noteQuery.folderId = new Types.ObjectId(folderId)
  }
  
  const notes = await Note.find(noteQuery).lean()
  const noteMap = new Map(notes.map(n => [n._id.toString(), n]))
  
  const results: SearchHit[] = []
  for (const { noteId, score, matchedTerms } of scoredDocs) {
    const note = noteMap.get(noteId)
    if (note) {
      results.push({
        noteId,
        title: note.title,
        content: note.content,
        score,
        highlight: generateHighlight(note.title, note.content, note.ocrText || '', matchedTerms),
      })
    }
  }
  
  return results
}

function getTokenPositions(text: string, term: string): number[] {
  const positions: number[] = []
  let pos = text.indexOf(term)
  while (pos !== -1) {
    positions.push(pos)
    pos = text.indexOf(term, pos + 1)
  }
  return positions
}

function generateHighlight(
  title: string,
  content: string,
  ocrText: string,
  matchedTerms: Set<string>
): { title?: string[]; content?: string[]; ocrText?: string[] } {
  const highlight: { title?: string[]; content?: string[]; ocrText?: string[] } = {}
  
  const titleHighlights: string[] = []
  for (const term of matchedTerms) {
    if (title.toLowerCase().includes(term.toLowerCase())) {
      const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi')
      const highlighted = title.replace(regex, '<em>$1</em>')
      if (highlighted !== title) {
        titleHighlights.push(highlighted)
      }
    }
  }
  if (titleHighlights.length > 0) {
    highlight.title = titleHighlights
  }
  
  const contentHighlights: string[] = []
  const contentLower = content.toLowerCase()
  for (const term of matchedTerms) {
    const termLower = term.toLowerCase()
    let pos = contentLower.indexOf(termLower)
    while (pos !== -1 && contentHighlights.length < 5) {
      const start = Math.max(0, pos - 50)
      const end = Math.min(content.length, pos + term.length + 50)
      const snippet = content.substring(start, end)
      const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi')
      const highlighted = snippet.replace(regex, '<em>$1</em>')
      if (highlighted !== snippet) {
        contentHighlights.push(`...${highlighted}...`)
      }
      pos = contentLower.indexOf(termLower, pos + 1)
    }
  }
  if (contentHighlights.length > 0) {
    highlight.content = contentHighlights
  }

  if (ocrText) {
    const ocrHighlights: string[] = []
    const ocrLower = ocrText.toLowerCase()
    for (const term of matchedTerms) {
      const termLower = term.toLowerCase()
      let pos = ocrLower.indexOf(termLower)
      while (pos !== -1 && ocrHighlights.length < 3) {
        const start = Math.max(0, pos - 30)
        const end = Math.min(ocrText.length, pos + term.length + 30)
        const snippet = ocrText.substring(start, end)
        const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi')
        const highlighted = snippet.replace(regex, '<em>$1</em>')
        if (highlighted !== snippet) {
          ocrHighlights.push(`📷 ...${highlighted}...`)
        }
        pos = ocrLower.indexOf(termLower, pos + 1)
      }
    }
    if (ocrHighlights.length > 0) {
      highlight.ocrText = ocrHighlights
    }
  }
  
  return highlight
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
