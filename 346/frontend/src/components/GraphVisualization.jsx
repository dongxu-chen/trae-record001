import { useEffect, useRef, useState, useMemo } from 'react'
import * as d3 from 'd3'
import { Spin, Empty, Tooltip } from 'antd'
import { ZoomInOutlined, ZoomOutOutlined, ReloadOutlined, BgColorsOutlined } from '@ant-design/icons'
import { getCommunityColor, getNodeDegrees, calculateNodeSize, filterGraphByTime, getNodeLabel, filterGraphByRelationshipTypes, getRelationshipColor } from '../utils/graphUtils'

const HIGHLIGHT_COLORS = {
  key: '#faad14',
  infected: '#f5222d',
  recovered: '#52c41a',
  new_infection: '#fa8c16'
}

const GraphVisualization = ({ data, loading, communities = [], timeRange, relationshipTypes = [], selectedNodeId, onNodeClick, highlightedNodes = {} }) => {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const [zoomLevel, setZoomLevel] = useState(1)
  const [showLabels, setShowLabels] = useState(true)
  const [colorByCommunity, setColorByCommunity] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)

  const displayData = useMemo(() => {
    let result = data

    if (timeRange && (timeRange[0] || timeRange[1])) {
      result = filterGraphByTime(result, timeRange[0], timeRange[1])
    }

    if (relationshipTypes && relationshipTypes.length > 0) {
      result = filterGraphByRelationshipTypes(result, relationshipTypes)
    }

    return result
  }, [data, timeRange, relationshipTypes])

  const nodeDegrees = useMemo(() => {
    return getNodeDegrees(displayData)
  }, [displayData])

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  useEffect(() => {
    if (loading || !displayData?.nodes?.length) return

    const { width, height } = dimensions
    const nodes = displayData.nodes.map((d) => ({ ...d }))
    const edges = displayData.edges.map((d) => ({ ...d }))

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg.append('g')

    const zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        setZoomLevel(event.transform.k)
      })

    svg.call(zoom)

    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('class', 'link')
      .attr('stroke-width', (d) => Math.sqrt(d.weight || 1))
      .attr('stroke', (d) => getRelationshipColor(d.type || d.relationship_type))

    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .call(
        d3
          .drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
      )

    node
      .append('circle')
      .attr('r', (d) => {
        const baseSize = calculateNodeSize(nodeDegrees[d.id])
        if (highlightedNodes[d.id] === 'new_infection') return baseSize * 1.5
        if (highlightedNodes[d.id]) return baseSize * 1.2
        if (selectedNodeId === d.id) return baseSize * 1.3
        return baseSize
      })
      .attr('fill', (d) => {
        if (highlightedNodes[d.id]) {
          return HIGHLIGHT_COLORS[highlightedNodes[d.id]] || '#1890ff'
        }
        return colorByCommunity ? getCommunityColor(communities, d.id) : '#1890ff'
      })
      .attr('stroke', (d) => {
        if (selectedNodeId === d.id) return '#722ed1'
        if (highlightedNodes[d.id]) return '#fff'
        return '#fff'
      })
      .attr('stroke-width', (d) => {
        if (selectedNodeId === d.id) return 3
        if (highlightedNodes[d.id]) return 2
        return 1.5
      })
      .style('opacity', (d) => {
        if (Object.keys(highlightedNodes).length > 0 && !highlightedNodes[d.id]) return 0.3
        return 1
      })

    if (showLabels) {
      node
        .append('text')
        .text((d) => getNodeLabel(d))
        .attr('dy', (d) => calculateNodeSize(nodeDegrees[d.id]) + 12)
    }

    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'tooltip')
      .style('opacity', 0)

    node
      .on('click', (event, d) => {
        event.stopPropagation()
        if (onNodeClick) {
          onNodeClick(d.id)
        }
      })
      .on('mouseover', (event, d) => {
        setSelectedNode(d)
        tooltip
          .style('opacity', 1)
          .html(
            `<div class="tooltip-title">${getNodeLabel(d)}</div>
             <div class="tooltip-content">
               ID: ${d.id}<br/>
               标签: ${d.label || 'N/A'}<br/>
               度数: ${nodeDegrees[d.id] || 0}
             </div>`
          )
          .style('left', event.pageX + 10 + 'px')
          .style('top', event.pageY - 10 + 'px')
      })
      .on('mousemove', (event) => {
        tooltip
          .style('left', event.pageX + 10 + 'px')
          .style('top', event.pageY - 10 + 'px')
      })
      .on('mouseout', () => {
        setSelectedNode(null)
        tooltip.style('opacity', 0)
      })

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(60)
          .strength(0.3)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(25))

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)

      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    }

    function dragged(event, d) {
      d.fx = event.x
      d.fy = event.y
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    }

    return () => {
      simulation.stop()
      tooltip.remove()
    }
  }, [displayData, dimensions, communities, colorByCommunity, showLabels, nodeDegrees, loading, selectedNodeId, highlightedNodes, onNodeClick])

  const handleZoomIn = () => {
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(d3.zoom().scaleBy, 1.5)
  }

  const handleZoomOut = () => {
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(d3.zoom().scaleBy, 0.75)
  }

  const handleReset = () => {
    const svg = d3.select(svgRef.current)
    svg.transition().duration(500).call(d3.zoom().transform, d3.zoomIdentity)
  }

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (!displayData?.nodes?.length) {
    return (
      <div className="loading-container">
        <Empty description="暂无图数据，请先导入数据" />
      </div>
    )
  }

  return (
    <div className="graph-container" ref={containerRef}>
      <svg ref={svgRef} width={dimensions.width} height={dimensions.height} />
      <div className="graph-controls">
        <Tooltip title="放大">
          <button onClick={handleZoomIn}>
            <ZoomInOutlined />
          </button>
        </Tooltip>
        <Tooltip title="缩小">
          <button onClick={handleZoomOut}>
            <ZoomOutOutlined />
          </button>
        </Tooltip>
        <Tooltip title="重置视图">
          <button onClick={handleReset}>
            <ReloadOutlined />
          </button>
        </Tooltip>
        <Tooltip title={colorByCommunity ? '按社区着色' : '统一着色'}>
          <button
            onClick={() => setColorByCommunity(!colorByCommunity)}
            style={{
              background: colorByCommunity ? '#1890ff' : '#fff',
              color: colorByCommunity ? '#fff' : '#666',
            }}
          >
            <BgColorsOutlined />
          </button>
        </Tooltip>
      </div>
    </div>
  )
}

export default GraphVisualization
