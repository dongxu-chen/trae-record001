import { SvgElement, Layer } from '@/types'
import { nanoid } from 'nanoid'

export function parseSvg(svgContent: string): {
  elements: Record<string, SvgElement>
  layers: Layer[]
  viewBox: { width: number; height: number }
} {
  const parser = new DOMParser()
  const doc = parser.parseFromString(svgContent, 'image/svg+xml')
  const svg = doc.querySelector('svg')

  if (!svg) {
    throw new Error('Invalid SVG content')
  }

  const viewBox = svg.getAttribute('viewBox')
  let width = parseInt(svg.getAttribute('width') || '400')
  let height = parseInt(svg.getAttribute('height') || '400')

  if (viewBox) {
    const parts = viewBox.split(/\s+/)
    if (parts.length === 4) {
      width = parseInt(parts[2]) || width
      height = parseInt(parts[3]) || height
    }
  }

  const elements: Record<string, SvgElement> = {}
  const layers: Layer[] = []

  function parseElement(el: Element, parentId: string | null): string | null {
    const tagName = el.tagName.toLowerCase()
    
    const supportedTypes = ['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'g']
    if (!supportedTypes.includes(tagName)) {
      return null
    }

    const id = nanoid()
    const name = el.getAttribute('id') || `${tagName}-${Object.keys(elements).length + 1}`

    const attributes: Record<string, string> = {}
    for (const attr of el.attributes) {
      attributes[attr.name] = attr.value
    }

    const element: SvgElement = {
      id,
      name,
      type: tagName as SvgElement['type'],
      attributes,
      transform: {
        position: { x: 0, y: 0 },
        rotation: 0,
        scale: { x: 1, y: 1 },
        anchor: { x: width / 2, y: height / 2 },
        opacity: 1,
      },
      parentId,
      children: [],
    }

    elements[id] = element

    if (tagName !== 'g') {
      layers.push({
        id: nanoid(),
        name,
        elementId: id,
        visible: true,
        locked: false,
        tracks: [],
      })
    }

    for (const child of el.children) {
      const childId = parseElement(child, id)
      if (childId) {
        element.children.push(childId)
      }
    }

    return id
  }

  for (const child of svg.children) {
    parseElement(child, null)
  }

  return { elements, layers, viewBox: { width, height } }
}

export function serializeSvg(
  elements: Record<string, SvgElement>,
  width: number,
  height: number
): string {
  const rootIds = Object.values(elements)
    .filter((el) => el.parentId === null)
    .map((el) => el.id)

  function buildElement(id: string): string {
    const el = elements[id]
    if (!el) return ''

    const attrs = Object.entries(el.attributes)
      .map(([k, v]) => `${k}="${v}"`)
      .join(' ')

    const transform = `translate(${el.transform.position.x}, ${el.transform.position.y}) rotate(${el.transform.rotation}) scale(${el.transform.scale.x}, ${el.transform.scale.y})`

    if (el.type === 'g') {
      const children = el.children.map(buildElement).join('')
      return `<g id="${el.name}" ${attrs} transform="${transform}">${children}</g>`
    }

    return `<${el.type} id="${el.name}" ${attrs} transform="${transform}" opacity="${el.transform.opacity}" />`
  }

  const content = rootIds.map(buildElement).join('')

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">${content}</svg>`
}
