export const GRID_CONFIG = {
  COLUMNS: 12,
  ROW_HEIGHT: 100,
  GAP: 16,
  MIN_WIDTH: 3,
  MIN_HEIGHT: 2,
  DEFAULT_WIDTH: 6,
  DEFAULT_HEIGHT: 4,
}

export function snapToGrid(value, gridSize) {
  return Math.round(value / gridSize) * gridSize
}

export function calculateGridPosition(
  clientX,
  clientY,
  containerRect,
  itemWidth,
  itemHeight
) {
  const relativeX = clientX - containerRect.left
  const relativeY = clientY - containerRect.top

  const colWidth = (containerRect.width - (GRID_CONFIG.COLUMNS - 1) * GRID_CONFIG.GAP) / GRID_CONFIG.COLUMNS

  const col = Math.max(0, Math.min(
    GRID_CONFIG.COLUMNS - 1,
    Math.floor(relativeX / (colWidth + GRID_CONFIG.GAP))
  ))

  const row = Math.max(0, Math.floor(relativeY / (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP)))

  const width = Math.max(GRID_CONFIG.MIN_WIDTH, Math.min(
    GRID_CONFIG.COLUMNS - col,
    itemWidth || GRID_CONFIG.DEFAULT_WIDTH
  ))

  const height = Math.max(GRID_CONFIG.MIN_HEIGHT, itemHeight || GRID_CONFIG.DEFAULT_HEIGHT)

  return {
    col,
    row,
    width,
    height,
    x: col * (colWidth + GRID_CONFIG.GAP),
    y: row * (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP),
  }
}

export function getGridStyle(position) {
  return {
    gridColumn: `${position.col + 1} / span ${position.width}`,
    gridRow: `${position.row + 1} / span ${position.height}`,
  }
}

export function createGridLines(containerWidth, containerHeight) {
  const colWidth = (containerWidth - (GRID_CONFIG.COLUMNS - 1) * GRID_CONFIG.GAP) / GRID_CONFIG.COLUMNS
  const lines = []

  for (let i = 0; i <= GRID_CONFIG.COLUMNS; i++) {
    lines.push({
      type: 'vertical',
      x: i * (colWidth + GRID_CONFIG.GAP),
    })
  }

  const rowCount = Math.ceil(containerHeight / (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP))
  for (let i = 0; i <= rowCount; i++) {
    lines.push({
      type: 'horizontal',
      y: i * (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP),
    })
  }

  return lines
}

export function findDropZone(clientX, clientY, containerRect, existingItems, itemId) {
  const colWidth = (containerRect.width - (GRID_CONFIG.COLUMNS - 1) * GRID_CONFIG.GAP) / GRID_CONFIG.COLUMNS
  const col = Math.max(0, Math.min(
    GRID_CONFIG.COLUMNS - GRID_CONFIG.MIN_WIDTH,
    Math.floor((clientX - containerRect.left) / (colWidth + GRID_CONFIG.GAP))
  ))
  const row = Math.max(0, Math.floor((clientY - containerRect.top) / (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP)))

  const width = GRID_CONFIG.DEFAULT_WIDTH
  const height = GRID_CONFIG.DEFAULT_HEIGHT

  const adjustedWidth = Math.min(width, GRID_CONFIG.COLUMNS - col)

  return {
    col,
    row,
    width: adjustedWidth,
    height,
    isValid: true,
  }
}

export function checkCollision(position, existingItems, excludeId = null) {
  const { col, row, width, height } = position

  for (const item of existingItems) {
    if (item.id === excludeId) continue
    if (!item.position) continue

    const itemPos = item.position
    const itemCol = itemPos.col || 0
    const itemRow = itemPos.row || 0
    const itemWidth = itemPos.width || GRID_CONFIG.DEFAULT_WIDTH
    const itemHeight = itemPos.height || GRID_CONFIG.DEFAULT_HEIGHT

    const overlapX = col < itemCol + itemWidth && col + width > itemCol
    const overlapY = row < itemRow + itemHeight && row + height > itemRow

    if (overlapX && overlapY) {
      return true
    }
  }

  return false
}

export function findNextAvailablePosition(existingItems, width, height) {
  let row = 0
  const maxAttempts = 100

  while (row < maxAttempts) {
    for (let col = 0; col <= GRID_CONFIG.COLUMNS - width; col++) {
      const position = { col, row, width, height }
      if (!checkCollision(position, existingItems)) {
        return position
      }
    }
    row++
  }

  return { col: 0, row, width, height }
}
