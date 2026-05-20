import { createNode, createEdge, NODE_TYPES } from './graphData'
import { v4 as uuidv4 } from 'uuid'

export function parseDrawIO(xmlContent) {
  const parser = new DOMParser()
  const xmlDoc = parser.parseFromString(xmlContent, 'text/xml')

  if (xmlDoc.querySelector('parsererror')) {
    throw new Error('Invalid XML format')
  }

  const mxGraphModel = xmlDoc.querySelector('mxGraphModel')
  if (!mxGraphModel) {
    throw new Error('Not a valid Draw.io file')
  }

  const root = mxGraphModel.querySelector('root')
  if (!root) {
    throw new Error('No root element found')
  }

  const cells = root.querySelectorAll('mxCell')
  const nodes = []
  const edges = []
  const cellMap = new Map()

  cells.forEach(cell => {
    const id = cell.getAttribute('id')
    const value = cell.getAttribute('value') || ''
    const style = cell.getAttribute('style') || ''
    const vertex = cell.getAttribute('vertex')
    const edge = cell.getAttribute('edge')
    const parent = cell.getAttribute('parent')
    const source = cell.getAttribute('source')
    const target = cell.getAttribute('target')

    const geometry = cell.querySelector('mxGeometry')
    let x = 0, y = 0, width = 120, height = 60

    if (geometry) {
      x = parseFloat(geometry.getAttribute('x') || 0)
      y = parseFloat(geometry.getAttribute('y') || 0)
      width = parseFloat(geometry.getAttribute('width') || 120)
      height = parseFloat(geometry.getAttribute('height') || 60)
    }

    const cellData = {
      id,
      value,
      style,
      vertex: vertex === '1',
      edge: edge === '1',
      parent,
      source,
      target,
      x,
      y,
      width,
      height,
      geometry
    }

    cellMap.set(id, cellData)

    if (vertex === '1' && parent !== '0' && parent !== '1') {
      const nodeType = getNodeTypeFromStyle(style)
      const node = createNode(nodeType, x + 100, y + 100, sanitizeLabel(value))
      node.width = width || 120
      node.height = height || 60

      const fillColor = getStyleValue(style, 'fillColor')
      const strokeColor = getStyleValue(style, 'strokeColor')
      const fontSize = getStyleValue(style, 'fontSize')

      if (fillColor) node.fill = fillColor
      if (strokeColor) node.stroke = strokeColor
      if (fontSize) node.fontSize = parseInt(fontSize)

      nodes.push(node)
      cellData.nodeId = node.id
    }

    if (edge === '1' && source && target) {
      cellData.edgeId = null
      edges.push(cellData)
    }
  })

  const finalEdges = []
  edges.forEach(edgeData => {
    const sourceCell = cellMap.get(edgeData.source)
    const targetCell = cellMap.get(edgeData.target)

    if (sourceCell?.nodeId && targetCell?.nodeId) {
      const edge = createEdge(sourceCell.nodeId, targetCell.nodeId, sanitizeLabel(edgeData.value))
      finalEdges.push(edge)
    }
  })

  return { nodes, edges }
}

export function parseVSDX(arrayBuffer) {
  return new Promise((resolve, reject) => {
    try {
      import('jszip').then(async ({ default: JSZip }) => {
        const zip = await JSZip.loadAsync(arrayBuffer)
        const visioXml = zip.file('visio/pages/page1.xml')
        
        if (!visioXml) {
          reject(new Error('Not a valid Visio file or no page found'))
          return
        }

        const xmlContent = await visioXml.async('string')
        const result = parseVisioXML(xmlContent)
        resolve(result)
      }).catch(reject)
    } catch (e) {
      reject(e)
    }
  })
}

function parseVisioXML(xmlContent) {
  const parser = new DOMParser()
  const xmlDoc = parser.parseFromString(xmlContent, 'text/xml')

  const shapes = xmlDoc.querySelectorAll('Shape')
  const nodes = []
  const edges = []
  const shapeMap = new Map()

  shapes.forEach(shape => {
    const id = shape.getAttribute('ID')
    const type = shape.getAttribute('Type')
    const name = shape.getAttribute('Name') || ''

    const textEl = shape.querySelector('Text')
    const text = textEl?.textContent || ''

    const xForm = shape.querySelector('XForm')
    let x = 0, y = 0, width = 120, height = 60

    if (xForm) {
      const pinX = xForm.querySelector('PinX')
      const pinY = xForm.querySelector('PinY')
      const w = xForm.querySelector('Width')
      const h = xForm.querySelector('Height')

      x = pinX ? parseFloat(pinX.textContent) : 0
      y = pinY ? parseFloat(pinY.textContent) : 0
      width = w ? parseFloat(w.textContent) : 120
      height = h ? parseFloat(h.textContent) : 60
    }

    const isEdge = type === 'Line' || type === 'Dynamic connector' || name.includes('Connector')

    if (isEdge) {
      const beginX = shape.querySelector('BeginX')
      const beginY = shape.querySelector('BeginY')
      const endX = shape.querySelector('EndX')
      const endY = shape.querySelector('EndY')

      edges.push({
        id,
        label: text,
        beginX: beginX ? parseFloat(beginX.textContent) : 0,
        beginY: beginY ? parseFloat(beginY.textContent) : 0,
        endX: endX ? parseFloat(endX.textContent) : 0,
        endY: endY ? parseFloat(endY.textContent) : 0
      })
    } else {
      const nodeType = getVisioNodeType(shape)
      const node = createNode(nodeType, x + 100, y + 100, sanitizeLabel(text))
      node.width = width
      node.height = height

      const fillForegnd = shape.querySelector('FillForegnd')
      const lineColor = shape.querySelector('LineColor')

      if (fillForegnd) node.fill = rgbToHex(fillForegnd.textContent)
      if (lineColor) node.stroke = rgbToHex(lineColor.textContent)

      nodes.push(node)
      shapeMap.set(id, node.id)
    }
  })

  const finalEdges = edges.map(edge => {
    let sourceId = null
    let targetId = null
    let minDist1 = Infinity
    let minDist2 = Infinity

    nodes.forEach(node => {
      const centerX = node.x + node.width / 2
      const centerY = node.y + node.height / 2

      const dist1 = Math.sqrt((centerX - edge.beginX) ** 2 + (centerY - edge.beginY) ** 2)
      const dist2 = Math.sqrt((centerX - edge.endX) ** 2 + (centerY - edge.endY) ** 2)

      if (dist1 < minDist1) {
        minDist1 = dist1
        sourceId = node.id
      }
      if (dist2 < minDist2) {
        minDist2 = dist2
        targetId = node.id
      }
    })

    if (sourceId && targetId && sourceId !== targetId) {
      return createEdge(sourceId, targetId, edge.label)
    }
    return null
  }).filter(Boolean)

  return { nodes, edges: finalEdges }
}

function getNodeTypeFromStyle(style) {
  const lowerStyle = style.toLowerCase()

  if (lowerStyle.includes('ellipse') || lowerStyle.includes('circle')) {
    return NODE_TYPES.CIRCLE
  }
  if (lowerStyle.includes('diamond') || lowerStyle.includes('rhombus')) {
    return NODE_TYPES.DIAMOND
  }
  if (lowerStyle.includes('parallelogram') || lowerStyle.includes('trapezoid')) {
    return NODE_TYPES.PARALLELOGRAM
  }
  if (lowerStyle.includes('document') || lowerStyle.includes('note')) {
    return NODE_TYPES.DOCUMENT
  }
  if (lowerStyle.includes('group')) {
    return NODE_TYPES.GROUP
  }

  return NODE_TYPES.RECTANGLE
}

function getVisioNodeType(shape) {
  const name = (shape.getAttribute('Name') || '').toLowerCase()

  if (name.includes('circle') || name.includes('ellipse') || name.includes('round')) {
    return NODE_TYPES.CIRCLE
  }
  if (name.includes('diamond') || name.includes('decision')) {
    return NODE_TYPES.DIAMOND
  }
  if (name.includes('parallelogram') || name.includes('data')) {
    return NODE_TYPES.PARALLELOGRAM
  }
  if (name.includes('document') || name.includes('predefined')) {
    return NODE_TYPES.DOCUMENT
  }

  return NODE_TYPES.RECTANGLE
}

function getStyleValue(style, key) {
  const regex = new RegExp(`${key}=([^;]+)`, 'i')
  const match = style.match(regex)
  return match ? match[1].trim() : null
}

function sanitizeLabel(text) {
  if (!text) return ''
  return text
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .trim()
    .substring(0, 50)
}

function rgbToHex(rgb) {
  if (!rgb) return '#ffffff'
  if (rgb.startsWith('#')) return rgb

  const match = rgb.match(/(\d+),\s*(\d+),\s*(\d+)/)
  if (match) {
    const r = parseInt(match[1]).toString(16).padStart(2, '0')
    const g = parseInt(match[2]).toString(16).padStart(2, '0')
    const b = parseInt(match[3]).toString(16).padStart(2, '0')
    return `#${r}${g}${b}`
  }

  return '#ffffff'
}

export function importFile(file) {
  return new Promise((resolve, reject) => {
    const fileName = file.name.toLowerCase()

    if (fileName.endsWith('.drawio') || fileName.endsWith('.xml')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const result = parseDrawIO(e.target.result)
          resolve(result)
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = reject
      reader.readAsText(file)
    } else if (fileName.endsWith('.vsdx')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        parseVSDX(e.target.result).then(resolve).catch(reject)
      }
      reader.onerror = reject
      reader.readAsArrayBuffer(file)
    } else {
      reject(new Error('Unsupported file format. Please use .drawio, .xml, or .vsdx files'))
    }
  })
}
