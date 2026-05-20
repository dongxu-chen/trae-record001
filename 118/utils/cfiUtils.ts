export interface CFIPath {
  spineIndex: number
  path: string
  offset: number
}

export class CFIUtils {
  static parse(cfi: string): CFIPath | null {
    try {
      const match = cfi.match(/epubcfi\((\/\d+\/?)?(\d+\[(?:[^\]]|\[[^\]]*\])+\])(:(\d+))?\)/)
      if (!match) return null

      const path = match[2]
      const offset = match[5] ? parseInt(match[5], 10) : 0

      const spineMatch = path.match(/(\d+)\[/)
      const spineIndex = spineMatch ? parseInt(spineMatch[1], 10) - 2 : 0

      return { spineIndex, path, offset }
    } catch {
      return null
    }
  }

  static normalize(cfi: string): string {
    return cfi
      .replace(/:\d+/g, '')
      .replace(/\[.*?\]/g, '')
  }

  static isSameLocation(cfi1: string, cfi2: string): boolean {
    return this.normalize(cfi1) === this.normalize(cfi2)
  }

  static compare(cfi1: string, cfi2: string): number {
    const path1 = this.normalize(cfi1)
    const path2 = this.normalize(cfi2)

    const parts1 = path1.split('/').filter(p => p)
    const parts2 = path2.split('/').filter(p => p)

    const maxLen = Math.max(parts1.length, parts2.length)

    for (let i = 0; i < maxLen; i++) {
      const p1 = parts1[i] || ''
      const p2 = parts2[i] || ''

      const num1 = parseInt(p1.match(/(\d+)/)?.[1] || '0')
      const num2 = parseInt(p2.match(/(\d+)/)?.[1] || '0')

      if (num1 !== num2) {
        return num1 - num2
      }
    }

    return 0
  }

  static getChapterIndex(cfi: string): number {
    const parsed = this.parse(cfi)
    return parsed ? parsed.spineIndex : -1
  }

  static serializeCFI(spineIndex: number, contentPath: string, offset: number = 0): string {
    return `epubcfi(/6/${(spineIndex + 2)}[${contentPath}]!:${offset})`
  }

  static validate(cfi: string): boolean {
    return /^epubcfi\(.*\)$/.test(cfi)
  }
}

export function calculateProgressByCFI(cfi: string, spineLength: number): number {
  const parsed = CFIUtils.parse(cfi)
  if (!parsed) return 0

  const chapterProgress = parsed.spineIndex / Math.max(spineLength - 1, 1)
  return Math.min(100, Math.round(chapterProgress * 100))
}

export function getPageByCFI(cfi: string, chapterPages: number[]): number {
  const parsed = CFIUtils.parse(cfi)
  if (!parsed) return 1

  let page = 0
  for (let i = 0; i < parsed.spineIndex && i < chapterPages.length; i++) {
    page += chapterPages[i]
  }

  const chapterProgress = parsed.offset / 1000
  const currentChapterPages = chapterPages[parsed.spineIndex] || 1

  return page + Math.round(chapterProgress * currentChapterPages) + 1
}
