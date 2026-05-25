import mammoth from 'mammoth'
import * as pdfjsLib from 'pdfjs-dist'
import { Document, Packer, Paragraph, TextRun } from 'docx'
import { saveAs } from 'file-saver'
import { LanguageCode, DocumentTranslation, FileType } from '../types'
import { translateWithEnhancements } from './translationService'
import { TranslateApiConfig } from '../types'
import { documentDB } from './database'

pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.6.82/pdf.worker.min.mjs`

export interface FormatSegment {
  id: string
  text: string
  formatTags: string[]
  prefix: string
  suffix: string
  isTranslatable: boolean
}

export interface ParsedDocument {
  segments: FormatSegment[]
  rawText: string
  htmlContent?: string
}

const FORMAT_TAG_REGEX = /<[^>]+>/g
const PLACEHOLDER_PREFIX = '__FORMAT_'
const PLACEHOLDER_SUFFIX = '__'

const getFileType = (fileName: string): FileType => {
  const ext = fileName.toLowerCase().split('.').pop()
  if (ext === 'docx') return 'docx'
  if (ext === 'pdf') return 'pdf'
  return 'txt'
}

const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result as string)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

const readFileAsArrayBuffer = (file: File): Promise<ArrayBuffer> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result as ArrayBuffer)
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

const generateSegmentId = (index: number): string => {
  return `${PLACEHOLDER_PREFIX}${index}${PLACEHOLDER_SUFFIX}`
}

export const parseDocumentWithFormat = async (file: File): Promise<ParsedDocument> => {
  const fileType = getFileType(file.name)
  let htmlContent = ''
  let rawText = ''

  switch (fileType) {
    case 'docx': {
      const arrayBuffer = await readFileAsArrayBuffer(file)
      const result = await mammoth.convertToHtml({ arrayBuffer })
      htmlContent = result.value
      rawText = (await mammoth.extractRawText({ arrayBuffer })).value
      break
    }
    case 'pdf': {
      const arrayBuffer = await readFileAsArrayBuffer(file)
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
      let fullHtml = ''
      let fullText = ''
      
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i)
        const textContent = await page.getTextContent()
        const pageText = textContent.items
          .map((item: any) => item.str)
          .join(' ')
        fullText += pageText + '\n\n'
        fullHtml += `<p>${pageText}</p>\n\n`
      }
      htmlContent = fullHtml
      rawText = fullText
      break
    }
    case 'txt':
    default: {
      rawText = await readFileAsText(file)
      htmlContent = rawText.split('\n').map(line => `<p>${line}</p>`).join('\n')
      break
    }
  }

  const segments = parseHtmlToSegments(htmlContent)
  
  return {
    segments,
    rawText,
    htmlContent,
  }
}

export const parseHtmlToSegments = (html: string): FormatSegment[] => {
  const segments: FormatSegment[] = []
  
  const blockElements = html.split(/(?<=<\/(p|h[1-6]|div|li|br)>)|(?=<(p|h[1-6]|div|li)>)|(?<=<br\s*\/?>)/)
    .filter(s => s.trim())
  
  let segmentIndex = 0
  
  for (const block of blockElements) {
    if (!block.trim()) continue
    
    if (!block.includes('<') || FORMAT_TAG_REGEX.test(block)) {
      const textParts = extractTextWithInlineTags(block)
      for (const part of textParts) {
        if (part.text.trim()) {
          segments.push({
            id: generateSegmentId(segmentIndex++),
            text: part.text,
            formatTags: part.tags,
            prefix: part.prefix,
            suffix: part.suffix,
            isTranslatable: true,
          })
        }
      }
    } else {
      segments.push({
        id: generateSegmentId(segmentIndex++),
        text: block,
        formatTags: [],
        prefix: '',
        suffix: '',
        isTranslatable: true,
      })
    }
  }
  
  return segments
}

const extractTextWithInlineTags = (html: string): Array<{ text: string; tags: string[]; prefix: string; suffix: string }> => {
  const results: Array<{ text: string; tags: string[]; prefix: string; suffix: string }> = []
  let currentText = ''
  let currentTags: string[] = []
  let currentPrefix = ''
  let currentSuffix = ''
  
  let i = 0
  while (i < html.length) {
    if (html[i] === '<') {
      const tagEnd = html.indexOf('>', i)
      if (tagEnd === -1) {
        currentText += html.slice(i)
        break
      }
      
      const tag = html.slice(i, tagEnd + 1)
      const isClosingTag = tag.startsWith('</')
      const isSelfClosing = tag.endsWith('/>') || tag === '<br>'
      
      if (isSelfClosing) {
        if (currentText.trim()) {
          results.push({
            text: currentText.trim(),
            tags: [...currentTags],
            prefix: currentPrefix,
            suffix: currentSuffix + tag,
          })
          currentText = ''
          currentTags = []
          currentPrefix = ''
          currentSuffix = ''
        } else {
          currentPrefix += tag
        }
      } else if (isClosingTag) {
        const tagName = tag.slice(2, -1).toLowerCase()
        if (['b', 'strong', 'i', 'em', 'u', 'span', 'a', 'code', 'sup', 'sub'].includes(tagName)) {
          currentSuffix = tag + currentSuffix
        } else {
          if (currentText.trim()) {
            results.push({
              text: currentText.trim(),
              tags: [...currentTags],
              prefix: currentPrefix,
              suffix: currentSuffix + tag,
            })
            currentText = ''
            currentTags = []
            currentPrefix = ''
            currentSuffix = ''
          } else {
            currentSuffix += tag
          }
        }
      } else {
        const tagName = tag.slice(1, -1).split(' ')[0].toLowerCase()
        if (['b', 'strong', 'i', 'em', 'u', 'span', 'a', 'code', 'sup', 'sub'].includes(tagName)) {
          currentPrefix += tag
          currentTags.push(tag)
        } else if (['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'].includes(tagName)) {
          if (currentText.trim()) {
            results.push({
              text: currentText.trim(),
              tags: [...currentTags],
              prefix: currentPrefix,
              suffix: currentSuffix,
            })
          }
          currentPrefix = tag
          currentText = ''
          currentTags = []
          currentSuffix = ''
        }
      }
      i = tagEnd + 1
    } else {
      currentText += html[i]
      i++
    }
  }
  
  if (currentText.trim()) {
    results.push({
      text: currentText.trim(),
      tags: currentTags,
      prefix: currentPrefix,
      suffix: currentSuffix,
    })
  }
  
  return results
}

export const restoreFormatToTranslatedText = (
  translatedText: string,
  segment: FormatSegment
): string => {
  let result = translatedText
  
  for (let i = segment.formatTags.length - 1; i >= 0; i--) {
    const openingTag = segment.formatTags[i]
    const tagName = openingTag.slice(1, -1).split(' ')[0].toLowerCase()
    const closingTag = `</${tagName}>`
    result = closingTag + result + openingTag
  }
  
  result = segment.prefix + result + segment.suffix
  
  return result
}

export const extractTextFromFile = async (file: File): Promise<string> => {
  const parsed = await parseDocumentWithFormat(file)
  return parsed.rawText
}

const splitTextIntoChunks = (text: string, maxChunkSize: number = 500): string[] => {
  const sentences = text.split(/(?<=[.!?。！？])\s+/)
  const chunks: string[] = []
  let currentChunk = ''
  
  for (const sentence of sentences) {
    if (currentChunk.length + sentence.length <= maxChunkSize) {
      currentChunk += (currentChunk ? ' ' : '') + sentence
    } else {
      if (currentChunk) {
        chunks.push(currentChunk)
      }
      currentChunk = sentence
    }
  }
  
  if (currentChunk) {
    chunks.push(currentChunk)
  }
  
  return chunks.length > 0 ? chunks : [text]
}

export const translateDocument = async (
  file: File,
  source: LanguageCode,
  target: LanguageCode,
  config: TranslateApiConfig,
  onProgress?: (progress: number, currentChunk: number, totalChunks: number) => void
): Promise<DocumentTranslation & { translatedHtml?: string }> => {
  const parsed = await parseDocumentWithFormat(file)
  const fileType = getFileType(file.name)
  
  const translatableSegments = parsed.segments.filter(s => s.isTranslatable && s.text.trim())
  const translatedSegments: Map<string, string> = new Map()
  
  const totalSegments = translatableSegments.length
  let completedSegments = 0
  
  for (const segment of translatableSegments) {
    try {
      const result = await translateWithEnhancements(segment.text, source, target, config, {
        useTerms: true,
        useMemory: true,
        saveToHistory: false,
        saveToMemory: true,
      })
      
      const restoredText = restoreFormatToTranslatedText(result.translatedText, segment)
      translatedSegments.set(segment.id, restoredText)
    } catch (err) {
      console.error(`Failed to translate segment ${segment.id}:`, err)
      translatedSegments.set(segment.id, segment.prefix + segment.text + segment.suffix)
    }
    
    completedSegments++
    if (onProgress) {
      onProgress(completedSegments / totalSegments, completedSegments, totalSegments)
    }
  }
  
  let translatedContent = ''
  let translatedHtml = ''
  
  for (const segment of parsed.segments) {
    const translated = translatedSegments.get(segment.id) || segment.prefix + segment.text + segment.suffix
    translatedHtml += translated
    translatedContent += segment.text + '\n'
  }
  
  const translatedPlainText = parsed.segments
    .map(segment => translatedSegments.get(segment.id) || segment.text)
    .join('\n')
    .replace(/<[^>]+>/g, '')
  
  const doc: DocumentTranslation & { translatedHtml?: string } = {
    fileName: file.name,
    fileType,
    sourceLang: source,
    targetLang: target,
    originalContent: parsed.rawText,
    translatedContent: translatedPlainText,
    translatedHtml,
    createdAt: Date.now(),
  }
  
  const id = await documentDB.add(doc)
  return { ...doc, id }
}

export const downloadTranslatedDocument = async (
  doc: DocumentTranslation & { translatedHtml?: string },
  format?: FileType
): Promise<void> => {
  const fileType = format || doc.fileType
  const baseName = doc.fileName.replace(/\.[^/.]+$/, '')
  
  switch (fileType) {
    case 'docx': {
      const content = doc.translatedHtml || doc.translatedContent
      const paragraphs = content
        .split(/<\/p>|<br\s*\/?>|\n/)
        .filter(line => line.trim())
        .map(line => {
          const plainText = line.replace(/<[^>]+>/g, '').trim()
          return new Paragraph({
            children: [new TextRun(plainText)],
          })
        })
      
      const docxDoc = new Document({
        sections: [{ properties: {}, children: paragraphs }],
      })
      
      const blob = await Packer.toBlob(docxDoc)
      saveAs(blob, `${baseName}_translated.docx`)
      break
    }
    case 'pdf':
    case 'txt':
    default: {
      if (doc.translatedHtml) {
        const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${baseName}_translated</title>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }
    p { margin-bottom: 1em; }
    h1, h2, h3, h4, h5, h6 { margin-top: 1.5em; margin-bottom: 0.5em; }
    strong, b { font-weight: bold; }
    em, i { font-style: italic; }
    u { text-decoration: underline; }
    code { background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
  </style>
</head>
<body>
${doc.translatedHtml}
</body>
</html>`
        const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' })
        saveAs(blob, `${baseName}_translated.html`)
      } else {
        const blob = new Blob([doc.translatedContent], { type: 'text/plain;charset=utf-8' })
        saveAs(blob, `${baseName}_translated.txt`)
      }
      break
    }
  }
}

export const exportTerms = (terms: any[]): void => {
  const csvContent = [
    ['Source Text', 'Translated Text', 'Source Language', 'Target Language', 'Domain'].join(','),
    ...terms.map(term => [
      `"${term.sourceText.replace(/"/g, '""')}"`,
      `"${term.translatedText.replace(/"/g, '""')}"`,
      term.sourceLang,
      term.targetLang,
      term.domain || '',
    ].join(',')),
  ].join('\n')
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  saveAs(blob, 'terms_export.csv')
}

export const importTerms = async (file: File): Promise<any[]> => {
  const content = await readFileAsText(file)
  const lines = content.split('\n').filter(line => line.trim())
  
  const terms: any[] = []
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  
  const sourceTextIdx = headers.findIndex(h => h.includes('source') && h.includes('text'))
  const translatedTextIdx = headers.findIndex(h => h.includes('translated') || h.includes('target'))
  const sourceLangIdx = headers.findIndex(h => h.includes('source') && h.includes('lang'))
  const targetLangIdx = headers.findIndex(h => h.includes('target') && h.includes('lang'))
  const domainIdx = headers.findIndex(h => h.includes('domain'))
  
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i])
    if (values.length >= 2) {
      terms.push({
        sourceText: values[sourceTextIdx >= 0 ? sourceTextIdx : 0],
        translatedText: values[translatedTextIdx >= 0 ? translatedTextIdx : 1],
        sourceLang: (values[sourceLangIdx >= 0 ? sourceLangIdx : 2] as LanguageCode) || 'en',
        targetLang: (values[targetLangIdx >= 0 ? targetLangIdx : 3] as LanguageCode) || 'zh',
        domain: domainIdx >= 0 ? values[domainIdx] : undefined,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      })
    }
  }
  
  return terms
}

const parseCSVLine = (line: string): string[] => {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += char
    }
  }
  
  result.push(current)
  return result.map(v => v.trim())
}
