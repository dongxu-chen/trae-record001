import Version from '@/models/Version'
import Note from '@/models/Note'
import { diff_match_patch } from 'diff-match-patch'

const dmp = new diff_match_patch()

export interface VersionData {
  _id: string
  noteId: string
  versionNumber: number
  title: string
  content: string
  createdAt: string
  isDelta?: boolean
}

export async function createInitialVersion(noteId: string, title: string, content: string) {
  await Version.create({
    noteId,
    title,
    content,
    versionNumber: 1,
    isFullVersion: true,
  })
}

export async function createVersion(noteId: string, newTitle: string, newContent: string) {
  const lastVersion = await Version.findOne({ noteId }).sort({ versionNumber: -1 })
  
  if (!lastVersion) {
    return createInitialVersion(noteId, newTitle, newContent)
  }
  
  const lastFullVersion = await Version.findOne({ 
    noteId, 
    isFullVersion: true 
  }).sort({ versionNumber: -1 })
  
  if (!lastFullVersion) {
    return createInitialVersion(noteId, newTitle, newContent)
  }
  
  const newVersionNumber = lastVersion.versionNumber + 1
  
  const shouldCreateFullVersion = 
    newVersionNumber % 10 === 0 || 
    lastVersion.versionNumber - lastFullVersion.versionNumber >= 9
  
  if (shouldCreateFullVersion) {
    await Version.create({
      noteId,
      title: newTitle,
      content: newContent,
      versionNumber: newVersionNumber,
      isFullVersion: true,
    })
  } else {
    const titleDelta = dmp.patch_toText(
      dmp.patch_make(lastVersion.title, newTitle)
    )
    const contentDelta = dmp.patch_toText(
      dmp.patch_make(lastVersion.content, newContent)
    )
    
    await Version.create({
      noteId,
      title: titleDelta,
      content: contentDelta,
      versionNumber: newVersionNumber,
      isFullVersion: false,
      baseVersion: lastVersion.versionNumber,
    })
  }
}

export async function getVersions(noteId: string): Promise<VersionData[]> {
  const versions = await Version.find({ noteId })
    .sort({ versionNumber: -1 })
    .lean()
  
  const fullVersions: VersionData[] = []
  let fullVersion: any = null
  
  for (const version of versions) {
    if (version.isFullVersion && !fullVersion) {
      fullVersion = {
        title: version.title,
        content: version.content,
      }
    }
  }
  
  if (!fullVersion) {
    const note = await Note.findById(noteId)
    if (note) {
      fullVersion = {
        title: note.title,
        content: note.content,
      }
    }
  }
  
  const result: VersionData[] = []
  
  for (let i = versions.length - 1; i >= 0; i--) {
    const version = versions[i]
    
    if (version.isFullVersion) {
      fullVersion = {
        title: version.title,
        content: version.content,
      }
    } else {
      try {
        const titlePatches = dmp.patch_fromText(version.title)
        const contentPatches = dmp.patch_fromText(version.content)
        
        const [newTitle] = dmp.patch_apply(titlePatches, fullVersion.title)
        const [newContent] = dmp.patch_apply(contentPatches, fullVersion.content)
        
        fullVersion = {
          title: newTitle,
          content: newContent,
        }
      } catch (error) {
        console.error('Failed to apply patch:', error)
      }
    }
    
    result.push({
      _id: version._id.toString(),
      noteId: version.noteId.toString(),
      versionNumber: version.versionNumber,
      title: fullVersion.title,
      content: fullVersion.content,
      createdAt: version.createdAt.toISOString(),
      isDelta: !version.isFullVersion,
    })
  }
  
  return result.reverse()
}

export async function getVersionByNumber(noteId: string, versionNumber: number): Promise<VersionData | null> {
  const versions = await getVersions(noteId)
  return versions.find(v => v.versionNumber === versionNumber) || null
}

export async function reconstructVersion(noteId: string, targetVersion: number): Promise<{ title: string; content: string } | null> {
  const versions = await Version.find({ 
    noteId, 
    versionNumber: { $lte: targetVersion } 
  }).sort({ versionNumber: 1 }).lean()
  
  if (versions.length === 0) {
    return null
  }
  
  let lastFullIndex = -1
  for (let i = versions.length - 1; i >= 0; i--) {
    if (versions[i].isFullVersion) {
      lastFullIndex = i
      break
    }
  }
  
  if (lastFullIndex === -1) {
    const note = await Note.findById(noteId)
    return note ? { title: note.title, content: note.content } : null
  }
  
  let result = {
    title: versions[lastFullIndex].title,
    content: versions[lastFullIndex].content,
  }
  
  for (let i = lastFullIndex + 1; i < versions.length; i++) {
    const version = versions[i]
    if (!version.isFullVersion) {
      try {
        const titlePatches = dmp.patch_fromText(version.title)
        const contentPatches = dmp.patch_fromText(version.content)
        
        const [newTitle] = dmp.patch_apply(titlePatches, result.title)
        const [newContent] = dmp.patch_apply(contentPatches, result.content)
        
        result = { title: newTitle, content: newContent }
      } catch (error) {
        console.error('Failed to apply patch:', error)
      }
    } else {
      result = {
        title: version.title,
        content: version.content,
      }
    }
  }
  
  return result
}

export async function getVersionDiff(
  noteId: string, 
  version1: number, 
  version2: number
): Promise<{ titleDiff: any[]; contentDiff: any[] } | null> {
  const v1 = await reconstructVersion(noteId, version1)
  const v2 = await reconstructVersion(noteId, version2)
  
  if (!v1 || !v2) {
    return null
  }
  
  return {
    titleDiff: dmp.diff_main(v1.title, v2.title),
    contentDiff: dmp.diff_main(v1.content, v2.content),
  }
}

export async function deleteVersionsByNoteId(noteId: string) {
  await Version.deleteMany({ noteId })
}
