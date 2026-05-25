import { useEffect, useRef } from 'react'
import { useEditorStore } from '@/lib/store'
import { animationEngine } from '@/lib/animationEngine'

export function Canvas() {
  const { project, currentTime, selectedLayerId, selectLayer, updateElementTransform } = useEditorStore()
  const svgRef = useRef<SVGSVGElement>(null)
  const elementRefs = useRef<Record<string, SVGElement>>({})

  useEffect(() => {
    if (!project) return

    const getElementState = (id: string) => {
      const el = elementRefs.current[id]
      const element = project.elements[id]
      if (!el || !element) return null

      return {
        x: element.transform.position.x,
        y: element.transform.position.y,
        rotation: element.transform.rotation,
        scaleX: element.transform.scale.x,
        scaleY: element.transform.scale.y,
        opacity: element.transform.opacity,
        setX: (val: number) => updateElementTransform(id, { position: { ...element.transform.position, x: val } }),
        setY: (val: number) => updateElementTransform(id, { position: { ...element.transform.position, y: val } }),
        setRotation: (val: number) => updateElementTransform(id, { rotation: val }),
        setScaleX: (val: number) => updateElementTransform(id, { scale: { ...element.transform.scale, x: val } }),
        setScaleY: (val: number) => updateElementTransform(id, { scale: { ...element.transform.scale, y: val } }),
        setOpacity: (val: number) => updateElementTransform(id, { opacity: val }),
      }
    }

    animationEngine.buildTimeline(project, getElementState)
    animationEngine.seek(currentTime)
  }, [project])

  useEffect(() => {
    animationEngine.seek(currentTime)
  }, [currentTime])

  useEffect(() => {
    animationEngine.setOnUpdate((time) => {
      useEditorStore.getState().setCurrentTime(time)
    })
  }, [])

  if (!project) {
    return (
      <div className="canvas-container">
        <div style={{ textAlign: 'center', color: '#888' }}>
          <p>选择或创建一个项目开始编辑</p>
        </div>
      </div>
    )
  }

  const handleElementClick = (layerId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    selectLayer(layerId)
  }

  const renderElement = (elementId: string) => {
    const element = project.elements[elementId]
    if (!element) return null

    const layer = project.layers.find((l) => l.elementId === elementId)
    const isSelected = layer && selectedLayerId === layer.id

    const transform = `
      translate(${element.transform.position.x}, ${element.transform.position.y})
      rotate(${element.transform.rotation}, ${element.transform.anchor.x}, ${element.transform.anchor.y})
      scale(${element.transform.scale.x}, ${element.transform.scale.y})
    `

    const commonProps: any = {
      ref: (el: any) => {
        if (el) elementRefs.current[elementId] = el
      },
      transform,
      opacity: element.transform.opacity,
      onClick: layer ? (e: any) => handleElementClick(layer.id, e) : undefined,
      style: layer ? { cursor: 'pointer' } : undefined,
    }

    if (isSelected) {
      commonProps.style = { ...commonProps.style, filter: 'drop-shadow(0 0 4px #e94560)' }
    }

    switch (element.type) {
      case 'path':
        return <path key={elementId} {...commonProps} d={element.attributes.d} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'rect':
        return <rect key={elementId} {...commonProps} x={element.attributes.x} y={element.attributes.y} width={element.attributes.width} height={element.attributes.height} rx={element.attributes.rx} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'circle':
        return <circle key={elementId} {...commonProps} cx={element.attributes.cx} cy={element.attributes.cy} r={element.attributes.r} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'ellipse':
        return <ellipse key={elementId} {...commonProps} cx={element.attributes.cx} cy={element.attributes.cy} rx={element.attributes.rx} ry={element.attributes.ry} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'line':
        return <line key={elementId} {...commonProps} x1={element.attributes.x1} y1={element.attributes.y1} x2={element.attributes.x2} y2={element.attributes.y2} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'polyline':
        return <polyline key={elementId} {...commonProps} points={element.attributes.points} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'polygon':
        return <polygon key={elementId} {...commonProps} points={element.attributes.points} fill={element.attributes.fill} stroke={element.attributes.stroke} strokeWidth={element.attributes['stroke-width']} />
      case 'g':
        return <g key={elementId} {...commonProps}>{element.children.map(renderElement)}</g>
      default:
        return null
    }
  }

  return (
    <div className="canvas-container" onClick={() => selectLayer(null)}>
      <div
        className="canvas-wrapper"
        style={{
          width: project.width,
          height: project.height,
        }}
      >
        <svg
          ref={svgRef}
          width={project.width}
          height={project.height}
          viewBox={`0 0 ${project.width} ${project.height}`}
        >
          {Object.keys(project.elements)
            .filter((id) => !project.elements[id].parentId)
            .map(renderElement)}
        </svg>
      </div>
    </div>
  )
}
