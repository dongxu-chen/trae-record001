export interface LineMapping {
  oldToNew: Map<number, number>
  newToOld: Map<number, number>
  oldVisibleToActual: Map<number, number>
  newVisibleToActual: Map<number, number>
  actualToOldVisible: Map<number, number>
  actualToNewVisible: Map<number, number>
}

export function buildLineMappingFromHunks(hunks: any[]): LineMapping {
  const oldToNew = new Map<number, number>()
  const newToOld = new Map<number, number>()
  const oldVisibleToActual = new Map<number, number>()
  const newVisibleToActual = new Map<number, number>()
  const actualToOldVisible = new Map<number, number>()
  const actualToNewVisible = new Map<number, number>()

  let oldActual = 1
  let newActual = 1

  for (const hunk of hunks) {
    const gapOld = hunk.oldStart - oldActual
    const gapNew = hunk.newStart - newActual

    for (let i = 0; i < Math.max(gapOld, gapNew); i++) {
      if (i < gapOld && i < gapNew) {
        oldToNew.set(oldActual + i, newActual + i)
        newToOld.set(newActual + i, oldActual + i)
      }
    }

    oldActual = hunk.oldStart
    newActual = hunk.newStart

    for (const change of hunk.changes) {
      if (change.type === 'normal') {
        oldToNew.set(change.oldLineNumber, change.newLineNumber)
        newToOld.set(change.newLineNumber, change.oldLineNumber)
        oldActual++
        newActual++
      } else if (change.type === 'delete') {
        oldActual++
      } else if (change.type === 'add') {
        newActual++
      }
    }
  }

  return {
    oldToNew,
    newToOld,
    oldVisibleToActual,
    newVisibleToActual,
    actualToOldVisible,
    actualToNewVisible,
  }
}

export interface FoldRegion {
  startLineNumber: number
  endLineNumber: number
}

export function calculateVisibleLineNumber(
  actualLine: number,
  hiddenRegions: FoldRegion[]
): number {
  if (!hiddenRegions || hiddenRegions.length === 0) return actualLine

  let offset = 0
  for (const region of hiddenRegions) {
    if (region.endLineNumber < actualLine) {
      offset += region.endLineNumber - region.startLineNumber
    } else if (region.startLineNumber <= actualLine) {
      offset += Math.max(0, actualLine - region.startLineNumber)
      break
    }
  }

  return Math.max(1, actualLine - offset)
}

export function calculateActualLineNumber(
  visibleLine: number,
  hiddenRegions: FoldRegion[]
): number {
  if (!hiddenRegions || hiddenRegions.length === 0) return visibleLine

  let actual = visibleLine
  for (const region of hiddenRegions) {
    const visibleEnd = calculateVisibleLineNumber(region.endLineNumber, hiddenRegions)
    const visibleStart = calculateVisibleLineNumber(region.startLineNumber, hiddenRegions)
    const hiddenCount = region.endLineNumber - region.startLineNumber

    if (visibleStart < visibleLine) {
      actual += hiddenCount
    } else {
      break
    }
  }

  return actual
}

export function getClosestVisibleLine(
  targetLine: number,
  hiddenRegions: FoldRegion[]
): number {
  if (!hiddenRegions || hiddenRegions.length === 0) return targetLine

  for (const region of hiddenRegions) {
    if (region.startLineNumber <= targetLine && targetLine <= region.endLineNumber) {
      return region.startLineNumber
    }
  }

  return targetLine
}

export function alignDiffScroll(
  sourceLine: number,
  isSourceOld: boolean,
  mapping: LineMapping
): { oldLine: number; newLine: number } {
  if (isSourceOld) {
    const mappedNew = mapping.oldToNew.get(sourceLine) || sourceLine
    return { oldLine: sourceLine, newLine: mappedNew }
  } else {
    const mappedOld = mapping.newToOld.get(sourceLine) || sourceLine
    return { oldLine: mappedOld, newLine: sourceLine }
  }
}

export interface DiffLineChange {
  originalStartLineNumber: number
  originalEndLineNumber: number
  modifiedStartLineNumber: number
  modifiedEndLineNumber: number
}

export function getDiffLineRanges(
  changes: DiffLineChange[],
  index: number
): {
  oldStart: number
  oldEnd: number
  newStart: number
  newEnd: number
  centerOld: number
  centerNew: number
} {
  const change = changes[index]
  if (!change) {
    return { oldStart: 1, oldEnd: 1, newStart: 1, newEnd: 1, centerOld: 1, centerNew: 1 }
  }

  const oldStart = change.originalStartLineNumber > 0 ? change.originalStartLineNumber : change.originalEndLineNumber
  const oldEnd = change.originalEndLineNumber > 0 ? change.originalEndLineNumber : change.originalStartLineNumber
  const newStart = change.modifiedStartLineNumber > 0 ? change.modifiedStartLineNumber : change.modifiedEndLineNumber
  const newEnd = change.modifiedEndLineNumber > 0 ? change.modifiedEndLineNumber : change.modifiedStartLineNumber

  const centerOld = Math.round((oldStart + oldEnd) / 2) || 1
  const centerNew = Math.round((newStart + newEnd) / 2) || 1

  return { oldStart, oldEnd, newStart, newEnd, centerOld, centerNew }
}
