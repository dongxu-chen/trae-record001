import { LanguageCode, CollaborativeSession, CollaborativeSegment, Collaborator, MergeResult } from '../types'
import { calculateSimilarity } from './database'

const generateId = (): string => `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

const mockCollaborators: Omit<Collaborator, 'id' | 'lastActive'>[] = [
  { name: '张三', color: '#3B82F6', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=zhangsan', isOnline: true },
  { name: '李四', color: '#10B981', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=lisi', isOnline: true },
  { name: '王五', color: '#F59E0B', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=wangwu', isOnline: false },
  { name: 'John', color: '#EF4444', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=john', isOnline: true },
]

class CollaborationService {
  private sessions: Map<string, CollaborativeSession> = new Map()
  private listeners: Map<string, Set<(session: CollaborativeSession) => void>> = new Map()
  private currentUser: Collaborator
  private broadcastInterval?: number

  constructor() {
    this.currentUser = {
      id: generateId(),
      name: '我',
      color: '#8B5CF6',
      isOnline: true,
      lastActive: Date.now(),
    }
  }

  getCurrentUser(): Collaborator {
    return this.currentUser
  }

  createSession(
    title: string,
    sourceLang: LanguageCode,
    targetLang: LanguageCode,
    segments: string[],
    documentId?: number
  ): CollaborativeSession {
    const sessionId = generateId()
    
    const collaborativeSegments: CollaborativeSegment[] = segments.map((text, index) => ({
      id: `seg_${index}_${generateId()}`,
      sourceText: text,
      translatedText: '',
      status: 'pending',
      lastModified: Date.now(),
      versions: [],
    }))

    const session: CollaborativeSession = {
      id: sessionId,
      documentId,
      title,
      sourceLang,
      targetLang,
      segments: collaborativeSegments,
      collaborators: [this.currentUser],
      status: 'active',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      createdBy: this.currentUser.id,
    }

    this.sessions.set(sessionId, session)
    this.startMockCollaboration(sessionId)
    
    return session
  }

  joinSession(sessionId: string): CollaborativeSession | null {
    const session = this.sessions.get(sessionId)
    if (!session) return null

    if (!session.collaborators.find(c => c.id === this.currentUser.id)) {
      session.collaborators.push(this.currentUser)
      session.updatedAt = Date.now()
    }

    this.currentUser.lastActive = Date.now()
    this.notifyListeners(sessionId)
    
    return session
  }

  leaveSession(sessionId: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    session.collaborators = session.collaborators.filter(c => c.id !== this.currentUser.id)
    session.segments.forEach(seg => {
      if (seg.assignee === this.currentUser.id) {
        seg.assignee = undefined
        seg.status = 'pending'
      }
    })
    session.updatedAt = Date.now()
    
    this.notifyListeners(sessionId)
    return true
  }

  getSession(sessionId: string): CollaborativeSession | null {
    return this.sessions.get(sessionId) || null
  }

  getAllSessions(): CollaborativeSession[] {
    return Array.from(this.sessions.values())
  }

  claimSegment(sessionId: string, segmentId: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    const segment = session.segments.find(s => s.id === segmentId)
    if (!segment || segment.assignee) return false

    segment.assignee = this.currentUser.id
    segment.status = 'in_progress'
    segment.lastModified = Date.now()
    session.updatedAt = Date.now()

    this.currentUser.currentSegment = segmentId
    this.currentUser.lastActive = Date.now()
    
    this.notifyListeners(sessionId)
    return true
  }

  releaseSegment(sessionId: string, segmentId: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    const segment = session.segments.find(s => s.id === segmentId)
    if (!segment || segment.assignee !== this.currentUser.id) return false

    segment.assignee = undefined
    segment.status = segment.translatedText ? 'translated' : 'pending'
    segment.lastModified = Date.now()
    session.updatedAt = Date.now()

    if (this.currentUser.currentSegment === segmentId) {
      this.currentUser.currentSegment = undefined
    }
    this.currentUser.lastActive = Date.now()
    
    this.notifyListeners(sessionId)
    return true
  }

  updateTranslation(
    sessionId: string,
    segmentId: string,
    translatedText: string,
    status?: 'translated' | 'reviewed'
  ): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    const segment = session.segments.find(s => s.id === segmentId)
    if (!segment) return false

    if (segment.assignee && segment.assignee !== this.currentUser.id) {
      const existingVersion = segment.versions.find(v => v.by === this.currentUser.id)
      if (existingVersion) {
        existingVersion.text = translatedText
        existingVersion.timestamp = Date.now()
      } else {
        segment.versions.push({
          text: translatedText,
          by: this.currentUser.id,
          timestamp: Date.now(),
        })
      }
      segment.status = 'conflict'
    } else {
      if (segment.translatedText && segment.translatedText !== translatedText) {
        segment.versions.push({
          text: segment.translatedText,
          by: segment.modifiedBy || this.currentUser.id,
          timestamp: segment.lastModified,
        })
      }
      
      segment.translatedText = translatedText
      segment.modifiedBy = this.currentUser.id
      segment.lastModified = Date.now()
      segment.status = status || 'translated'

      segment.versions.push({
        text: translatedText,
        by: this.currentUser.id,
        timestamp: Date.now(),
      })
    }

    session.updatedAt = Date.now()
    this.currentUser.lastActive = Date.now()
    
    this.notifyListeners(sessionId)
    return true
  }

  addComment(sessionId: string, segmentId: string, comment: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    const segment = session.segments.find(s => s.id === segmentId)
    if (!segment) return false

    if (!segment.comments) {
      segment.comments = []
    }
    
    segment.comments.push(`${this.currentUser.name}: ${comment}`)
    segment.lastModified = Date.now()
    session.updatedAt = Date.now()
    
    this.notifyListeners(sessionId)
    return true
  }

  resolveConflict(
    sessionId: string,
    segmentId: string,
    chosenVersionIndex: number
  ): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) return false

    const segment = session.segments.find(s => s.id === segmentId)
    if (!segment || segment.status !== 'conflict') return false

    const version = segment.versions[chosenVersionIndex]
    if (!version) return false

    segment.translatedText = version.text
    segment.modifiedBy = this.currentUser.id
    segment.assignee = this.currentUser.id
    segment.status = 'translated'
    segment.lastModified = Date.now()
    segment.versions.push({
      text: version.text,
      by: this.currentUser.id,
      timestamp: Date.now(),
    })

    session.updatedAt = Date.now()
    this.notifyListeners(sessionId)
    return true
  }

  mergeSegments(sessionId: string): MergeResult {
    const session = this.sessions.get(sessionId)
    if (!session) {
      return { merged: [], conflicts: [], autoMerged: 0, manualRequired: 0 }
    }

    const merged: CollaborativeSegment[] = []
    const conflicts: MergeResult['conflicts'] = []
    let autoMerged = 0
    let manualRequired = 0

    for (const segment of session.segments) {
      if (segment.status === 'conflict' && segment.versions.length > 1) {
        const uniqueVersions = this.deduplicateVersions(segment.versions)
        
        if (uniqueVersions.length === 1) {
          segment.translatedText = uniqueVersions[0].text
          segment.status = 'translated'
          autoMerged++
          merged.push(segment)
        } else {
          const bestVersion = this.selectBestVersion(uniqueVersions, segment.sourceText)
          if (bestVersion) {
            segment.translatedText = bestVersion.text
            segment.status = 'translated'
            autoMerged++
            merged.push(segment)
          } else {
            conflicts.push({
              segmentId: segment.id,
              versions: uniqueVersions,
            })
            manualRequired++
          }
        }
      } else {
        merged.push(segment)
        if (segment.translatedText) autoMerged++
      }
    }

    session.segments = merged.concat(
      conflicts.map(c => {
        const seg = session.segments.find(s => s.id === c.segmentId)!
        return { ...seg, status: 'conflict' as const }
      })
    )
    session.updatedAt = Date.now()
    this.notifyListeners(sessionId)

    return { merged, conflicts, autoMerged, manualRequired }
  }

  private deduplicateVersions(versions: CollaborativeSegment['versions']): CollaborativeSegment['versions'] {
    const seen = new Map<string, typeof versions[0]>()
    
    for (const version of versions) {
      const key = version.text.trim().toLowerCase()
      const existing = seen.get(key)
      
      if (!existing || version.timestamp > existing.timestamp) {
        seen.set(key, version)
      }
    }
    
    return Array.from(seen.values()).sort((a, b) => b.timestamp - a.timestamp)
  }

  private selectBestVersion(
    versions: CollaborativeSegment['versions'],
    sourceText: string
  ): typeof versions[0] | null {
    if (versions.length === 0) return null
    if (versions.length === 1) return versions[0]

    let bestScore = -1
    let bestVersion = versions[0]

    for (const version of versions) {
      let score = 0
      
      if (version.text.length > 0) {
        const lengthRatio = version.text.length / Math.max(sourceText.length, 1)
        if (lengthRatio > 0.3 && lengthRatio < 3.0) {
          score += 0.3
        }
      }

      const hasPunctuation = /[.!?。！？]$/.test(version.text.trim())
      if (hasPunctuation) score += 0.1

      const similarity = calculateSimilarity(sourceText, version.text)
      if (similarity < 0.8) score += 0.2

      score += (version.timestamp / Date.now()) * 0.4

      if (score > bestScore) {
        bestScore = score
        bestVersion = version
      }
    }

    return bestScore >= 0.5 ? bestVersion : null
  }

  subscribe(sessionId: string, callback: (session: CollaborativeSession) => void): () => void {
    if (!this.listeners.has(sessionId)) {
      this.listeners.set(sessionId, new Set())
    }
    this.listeners.get(sessionId)!.add(callback)

    return () => {
      this.listeners.get(sessionId)?.delete(callback)
    }
  }

  private notifyListeners(sessionId: string): void {
    const session = this.sessions.get(sessionId)
    if (!session) return

    const listeners = this.listeners.get(sessionId)
    if (listeners) {
      listeners.forEach(callback => callback(session))
    }
  }

  private startMockCollaboration(sessionId: string): void {
    if (this.broadcastInterval) {
      clearInterval(this.broadcastInterval)
    }

    let mockUserIndex = 0
    
    this.broadcastInterval = window.setInterval(() => {
      const session = this.sessions.get(sessionId)
      if (!session || session.status !== 'active') {
        if (this.broadcastInterval) {
          clearInterval(this.broadcastInterval)
        }
        return
      }

      if (Math.random() < 0.3) {
        const mockUserData = mockCollaborators[mockUserIndex % mockCollaborators.length]
        mockUserIndex++
        
        const existingCollaborator = session.collaborators.find(c => c.name === mockUserData.name)
        
        if (!existingCollaborator && Math.random() < 0.2) {
          session.collaborators.push({
            ...mockUserData,
            id: generateId(),
            lastActive: Date.now(),
          })
          session.updatedAt = Date.now()
          this.notifyListeners(sessionId)
        } else if (existingCollaborator) {
          existingCollaborator.isOnline = Math.random() > 0.2
          existingCollaborator.lastActive = Date.now()
          
          if (existingCollaborator.isOnline && Math.random() < 0.4) {
            const pendingSegments = session.segments.filter(
              s => s.status === 'pending' && !s.assignee
            )
            
            if (pendingSegments.length > 0) {
              const targetSegment = pendingSegments[Math.floor(Math.random() * pendingSegments.length)]
              targetSegment.assignee = existingCollaborator.id
              targetSegment.status = 'in_progress'
              targetSegment.lastModified = Date.now()
              existingCollaborator.currentSegment = targetSegment.id
              session.updatedAt = Date.now()
              
              setTimeout(() => {
                const currentSession = this.sessions.get(sessionId)
                const seg = currentSession?.segments.find(s => s.id === targetSegment.id)
                if (seg && seg.assignee === existingCollaborator.id) {
                  seg.translatedText = `[${mockUserData.name}翻译] ${seg.sourceText.substring(0, 5)}...`
                  seg.status = 'translated'
                  seg.modifiedBy = existingCollaborator.id
                  seg.lastModified = Date.now()
                  seg.versions.push({
                    text: seg.translatedText,
                    by: existingCollaborator.id,
                    timestamp: Date.now(),
                  })
                  if (currentSession) {
                    currentSession.updatedAt = Date.now()
                    this.notifyListeners(sessionId)
                  }
                }
              }, 2000 + Math.random() * 3000)
              
              this.notifyListeners(sessionId)
            }
          }
          this.notifyListeners(sessionId)
        }
      }
    }, 5000)
  }

  destroy(): void {
    if (this.broadcastInterval) {
      clearInterval(this.broadcastInterval)
    }
    this.listeners.clear()
    this.sessions.clear()
  }
}

export const collaborationService = new CollaborationService()

export const splitTextIntoSegments = (
  text: string,
  maxSegmentLength: number = 200
): string[] => {
  const sentences = text.match(/[^.!?。！？]+[.!?。！？]?\s*/g) || [text]
  const segments: string[] = []
  let currentSegment = ''

  for (const sentence of sentences) {
    if (currentSegment.length + sentence.length > maxSegmentLength && currentSegment) {
      segments.push(currentSegment.trim())
      currentSegment = sentence
    } else {
      currentSegment += sentence
    }
  }

  if (currentSegment.trim()) {
    segments.push(currentSegment.trim())
  }

  return segments.length > 0 ? segments : [text]
}
