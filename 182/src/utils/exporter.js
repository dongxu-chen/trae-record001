function generateSVG(nodes, edges, edgePaths, options = {}) {
  const {
    width = 1200, height = 800, padding = 50, scale = 1 } = options

  const visibleNodes = nodes.filter(n => !n.collapsed)

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  visibleNodes.forEach(node => {
    minX = Math.min(minX, node.x)
    minY = Math.min(minY, node.y)
    maxX = Math.max(maxX, node.x + node.width)
    maxY = Math.max(maxY, node.y + node.height)
  })

  const contentWidth = (maxX - minX + padding * 2) * scale
  const contentHeight = (maxY - minY + padding * 2) * scale

  const offsetX = -minX + padding
  const offsetY = -minY + padding

  let svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${contentWidth}" height="${contentHeight}" viewBox="0 0 ${contentWidth} ${contentHeight}">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#666"/>
    </marker>
  </defs>
  <g transform="translate(${offsetX * scale}, ${offsetY * scale}) scale(${scale})">
`

  const renderNode = (node) => {
    const x = node.x
    const y = node.y
    const w = node.width
    const h = node.height

    let shape = ''

    if (node.type === 'rectangle' || node.type === 'group') {
      shape = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" ry="8" fill="${node.fill}" stroke="${node.stroke}" stroke-width="${node.strokeWidth}" ${node.strokeDashArray ? `stroke-dasharray="${node.strokeDashArray.join(',')}"` : ''}/>`
    } else if (node.type === 'circle') {
      shape = `<ellipse cx="${x + w / 2}" cy="${y + h / 2}" rx="${w / 2}" ry="${h / 2}" fill="${node.fill}" stroke="${node.stroke}" stroke-width="${node.strokeWidth}"/>`
    } else if (node.type === 'diamond') {
      const cx = x + w / 2
      const cy = y + h / 2
      shape = `<polygon points="${cx},${y} ${x + w},${cy} ${cx},${y + h} ${x},${cy}" fill="${node.fill}" stroke="${node.stroke}" stroke-width="${node.strokeWidth}"/>`
    } else if (node.type === 'parallelogram') {
      const skew = 20
      shape = `<polygon points="${x + skew},${y} ${x + w},${y} ${x + w - skew},${y + h} ${x},${y + h}" fill="${node.fill}" stroke="${node.stroke}" stroke-width="${node.strokeWidth}"/>`
    } else if (node.type === 'document') {
      shape = `
        <path d="M${x},${y + 10} L${x},${y + h} L${x + w},${y + h} L${x + w},${y + 10} Q${x + w},${y} ${x + w - 10},${y} L${x + 10},${y} Q${x},${y} ${x},${y + 10}" fill="${node.fill}" stroke="${node.stroke}" stroke-width="${node.strokeWidth}"/>
        <path d="M${x + w - 10},${y} L${x + w - 10},${y + 10} L${x + w},${y + 10}" fill="none" stroke="${node.stroke}" stroke-width="${node.strokeWidth}"/>
      `
    }

    const textY = node.type === 'group' && !node.collapsed ? y + 20 : y + h / 2 + 5
    const text = `<text x="${x + w / 2}" y="${textY}" text-anchor="middle" font-size="${node.fontSize}" fill="${node.fontColor}" font-family="Arial, sans-serif">${node.label}</text>`

    let collapseButton = ''
    if (node.isGroup) {
      const btnX = x + w - 20
      const btnY = y + 8
      collapseButton = `
        <circle cx="${btnX}" cy="${btnY}" r="8" fill="#fff" stroke="#1890ff" stroke-width="1" style="cursor: pointer;"/>
        <text x="${btnX}" y="${btnY + 4}" text-anchor="middle" font-size="12" fill="#1890ff" font-family="Arial, sans-serif">${node.collapsed ? '+' : '-'}</text>
      `
    }

    return shape + text + collapseButton
  }

  visibleNodes.forEach(node => {
    svgContent += `    ${renderNode(node)}\n`
  })

  edges.forEach(edge => {
    const path = edgePaths[edge.id]
    if (!path || path.length < 2) return

    const sourceNode = nodes.find(n => n.id === edge.sourceId)
    const targetNode = nodes.find(n => n.id === edge.targetId)
    if (!sourceNode || !targetNode) return
    if (sourceNode.collapsed || targetNode.collapsed) return

    let pathD = `M ${path[0].x} ${path[0].y}`
    for (let i = 1; i < path.length; i++) {
      pathD += ` L ${path[i].x} ${path[i].y}`
    }

    svgContent += `    <path d="${pathD}" fill="none" stroke="${edge.stroke}" stroke-width="${edge.strokeWidth}" marker-end="url(#arrowhead)"/>`

    if (edge.label) {
      const midIndex = Math.floor(path.length / 2)
      const midPoint = path[midIndex]
      svgContent += `
    <rect x="${midPoint.x - 30}" y="${midPoint.y - 10}" width="60" height="20" fill="#fff" stroke="#ccc" stroke-width="1" rx="3"/>
    <text x="${midPoint.x}" y="${midPoint.y + 4}" text-anchor="middle" font-size="${edge.fontSize}" fill="${edge.fontColor}" font-family="Arial, sans-serif">${edge.label}</text>`
    }
    svgContent += '\n'
  })

  svgContent += `  </g>\n</svg>`

  return svgContent
}

export function exportSVG(nodes, edges, edgePaths, filename = 'flowchart.svg') {
  const svgContent = generateSVG(nodes, edges, edgePaths)
  
  const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function exportPNG(nodes, edges, edgePaths, filename = 'flowchart.png', scale = 2) {
  const svgContent = generateSVG(nodes, edges, edgePaths, { scale })
  
  const svgBlob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  
  const img = new Image()
  
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = img.width
    canvas.height = img.height
    
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0)
    
    canvas.toBlob((blob) => {
      const pngUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = pngUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(pngUrl)
      URL.revokeObjectURL(url)
    }, 'image/png')
  }
  
  img.src = url
}

export function exportJSON(nodes, edges, filename = 'flowchart.json') {
  const data = {
    version: '1.0',
    nodes: nodes.map(n => ({ ...n })),
    edges: edges.map(e => ({ ...e }))
  }
  
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
