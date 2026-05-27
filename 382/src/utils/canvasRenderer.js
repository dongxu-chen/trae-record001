import moment from 'moment';
import {
  getTimeUnitFormatter,
  generateTicks,
  getTrackPositions,
  getEventPosition,
  getEventPositionAbsolute,
  aggregateEvents,
  aggregateEventsForViewport,
  findEventAtPosition,
  easeOutCubic,
  interpolateEventPosition,
  isEventInViewport
} from '../utils/timelineUtils';

export const drawTimeline = (canvas, options) => {
  const {
    events,
    tracks,
    timeRange,
    timeUnit,
    width,
    height,
    xScale,
    eventHeight = 28,
    trackHeight = 50,
    headerHeight = 80,
    colors = {},
    aggregatedEvents = null,
    hoveredEvent = null,
    selectedEvent = null,
    expandedCluster = null,
    animationProgress = 1,
    previousXScale = null,
    isDragging = false,
    dragStart = null,
    currentTime = null,
    animationType = null,
    highlightEvents = null,
    highlightColor = '#3b82f6'
  } = options;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, width, height);

  const formatter = getTimeUnitFormatter(timeUnit);
  const { majorTicks, minorTicks } = generateTicks(timeRange.startTime, timeRange.endTime, timeUnit);
  const trackPositions = getTrackPositions(tracks, trackHeight, headerHeight);

  drawBackground(ctx, width, height);
  drawHeader(ctx, majorTicks, minorTicks, formatter, xScale, headerHeight, width);
  drawGrid(ctx, majorTicks, xScale, headerHeight, height, width);
  drawTracks(ctx, trackPositions, width, trackHeight, headerHeight);

  const displayEvents = aggregatedEvents || events;
  const visibleEvents = displayEvents.filter(event =>
    isEventInViewport(event, timeRange.startTime, timeRange.endTime)
  );

  if (expandedCluster && animationType === 'expand') {
    drawExpandingCluster(ctx, expandedCluster, xScale, trackPositions, eventHeight, animationProgress);
  } else if (expandedCluster && animationType === 'collapse') {
    drawCollapsingCluster(ctx, expandedCluster, xScale, trackPositions, eventHeight, animationProgress);
  } else {
    drawEvents(ctx, visibleEvents, xScale, trackPositions, eventHeight, hoveredEvent, selectedEvent, animationProgress, previousXScale, highlightEvents, highlightColor);
  }

  if (isDragging && dragStart && currentTime) {
    drawDragLine(ctx, currentTime, xScale, headerHeight, height);
  }
};

const drawBackground = (ctx, width, height) => {
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
};

const drawHeader = (ctx, majorTicks, minorTicks, formatter, xScale, headerHeight, width) => {
  const minorTickHeight = 30;
  const majorTickHeight = 50;

  ctx.fillStyle = '#f9fafb';
  ctx.fillRect(0, 0, width, headerHeight);

  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, minorTickHeight);
  ctx.lineTo(width, minorTickHeight);
  ctx.stroke();

  ctx.fillStyle = '#9ca3af';
  ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (const tick of minorTicks) {
    const x = xScale(tick);
    if (x >= 0 && x <= width) {
      ctx.fillText(formatter.minor(tick), x, minorTickHeight / 2);
    }
  }

  ctx.fillStyle = '#374151';
  ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif';

  for (const tick of majorTicks) {
    const x = xScale(tick);
    if (x >= 0 && x <= width) {
      ctx.fillText(formatter.major(tick), x, majorTickHeight - 10);
    }
  }

  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, headerHeight);
  ctx.lineTo(width, headerHeight);
  ctx.stroke();
};

const drawGrid = (ctx, ticks, xScale, headerHeight, height, width) => {
  ctx.strokeStyle = '#f3f4f6';
  ctx.lineWidth = 1;

  for (const tick of ticks) {
    const x = xScale(tick);
    if (x >= 0 && x <= width) {
      ctx.beginPath();
      ctx.moveTo(x, headerHeight);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
  }
};

const drawTracks = (ctx, trackPositions, width, trackHeight, headerHeight) => {
  for (const track of trackPositions) {
    ctx.fillStyle = track.color + '10';
    ctx.fillRect(0, track.y, width, track.height);

    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, track.y);
    ctx.lineTo(width, track.y);
    ctx.stroke();
  }

  for (const track of trackPositions) {
    ctx.fillStyle = track.color;
    ctx.fillRect(0, track.y, 4, track.height);
  }
};

const drawEvents = (ctx, events, xScale, trackPositions, eventHeight, hoveredEvent, selectedEvent, animationProgress = 1, previousXScale = null, highlightEvents = null, highlightColor = '#3b82f6') => {
  const highlightSet = highlightEvents ? new Set(highlightEvents) : null;
  for (const event of events) {
    let pos;
    
    if (previousXScale && animationProgress < 1) {
      pos = interpolateEventPosition(event, previousXScale, xScale, trackPositions, eventHeight, animationProgress);
    } else {
      pos = getEventPosition(event, xScale, trackPositions, eventHeight);
    }
    
    if (!pos) continue;

    const isHovered = hoveredEvent && hoveredEvent.id === event.id;
    const isSelected = selectedEvent && selectedEvent.id === event.id;
    const isHighlighted = highlightSet && highlightSet.has(event.id);

    ctx.save();
    ctx.globalAlpha = animationProgress;

    if (event.aggregated) {
      drawAggregatedEvent(ctx, pos, event, isHovered, isSelected, isHighlighted, highlightColor);
    } else {
      drawSingleEvent(ctx, pos, event, isHovered, isSelected, isHighlighted, highlightColor);
    }

    ctx.restore();
  }
};

const drawSingleEvent = (ctx, pos, event, isHovered, isSelected, isHighlighted, highlightColor) => {
  const radius = 4;
  const { x, y, width, height } = pos;

  if (isSelected) {
    ctx.shadowColor = event.color;
    ctx.shadowBlur = 10;
  } else if (isHovered) {
    ctx.shadowColor = event.color;
    ctx.shadowBlur = 6;
  } else if (isHighlighted) {
    ctx.shadowColor = highlightColor;
    ctx.shadowBlur = 8;
  }

  ctx.fillStyle = event.color;
  roundRect(ctx, x, y, width, height, radius);
  ctx.fill();

  if (isHighlighted && !isHovered && !isSelected) {
    ctx.strokeStyle = highlightColor;
    ctx.lineWidth = 2;
    roundRect(ctx, x - 1, y - 1, width + 2, height + 2, radius + 1);
    ctx.stroke();
  }

  if (isHovered || isSelected) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    roundRect(ctx, x + 2, y + 2, width - 4, height - 4, radius - 1);
    ctx.fill();

    ctx.fillStyle = event.color;
    ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(event.title, x + width / 2, y + height / 2);
  }
};

const drawAggregatedEvent = (ctx, pos, event, isHovered, isSelected, isHighlighted, highlightColor) => {
  const radius = 8;
  const { x, y, width, height } = pos;

  if (isSelected) {
    ctx.shadowColor = '#6b7280';
    ctx.shadowBlur = 12;
  } else if (isHovered) {
    ctx.shadowColor = '#6b7280';
    ctx.shadowBlur = 8;
  } else if (isHighlighted) {
    ctx.shadowColor = highlightColor;
    ctx.shadowBlur = 8;
  }

  ctx.fillStyle = '#6b7280';
  roundRect(ctx, x, y, width, height, radius);
  ctx.fill();

  ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
  roundRect(ctx, x + 2, y + 2, width - 4, height - 4, radius - 1);
  ctx.fill();

  ctx.fillStyle = '#6b7280';
  ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(`+${event.events.length}`, x + width / 2, y + height / 2);
};

const drawExpandingCluster = (ctx, cluster, xScale, trackPositions, eventHeight, progress) => {
  const clusterPos = getEventPosition(cluster, xScale, trackPositions, eventHeight);
  if (!clusterPos) return;

  const track = trackPositions.find(t => t.id === cluster.trackId);
  if (!track) return;

  const clusterCenterX = clusterPos.x + clusterPos.width / 2;
  const clusterCenterY = clusterPos.y + clusterPos.height / 2;

  const sortedEvents = [...cluster.events].sort((a, b) => a.startTime - b.startTime);

  for (let i = 0; i < sortedEvents.length; i++) {
    const event = sortedEvents[i];
    const targetPos = getEventPosition(event, xScale, trackPositions, eventHeight);
    if (!targetPos) continue;

    const targetX = targetPos.x + targetPos.width / 2;
    const targetY = targetPos.y + targetPos.height / 2;

    const easedProgress = easeOutCubic(progress);
    const currentX = clusterCenterX + (targetX - clusterCenterX) * easedProgress;
    const currentY = clusterCenterY + (targetY - clusterCenterY) * easedProgress;
    const currentWidth = Math.max(4, targetPos.width * easedProgress + 20 * (1 - easedProgress));
    const currentHeight = eventHeight;

    const eventPos = {
      x: currentX - currentWidth / 2,
      y: currentY - currentHeight / 2,
      width: currentWidth,
      height: currentHeight
    };

    ctx.save();
    ctx.globalAlpha = Math.max(0.3, easedProgress);

    if (progress > 0.7) {
      drawSingleEvent(ctx, eventPos, event, false, false);
    } else {
      const radius = 8 * (1 - easedProgress) + 4 * easedProgress;
      ctx.fillStyle = event.color;
      roundRect(ctx, eventPos.x, eventPos.y, eventPos.width, eventPos.height, radius);
      ctx.fill();
    }

    ctx.restore();
  }

  ctx.save();
  ctx.globalAlpha = 1 - progress;
  drawAggregatedEvent(ctx, clusterPos, cluster, false, false);
  ctx.restore();
};

const drawCollapsingCluster = (ctx, cluster, xScale, trackPositions, eventHeight, progress) => {
  const clusterPos = getEventPosition(cluster, xScale, trackPositions, eventHeight);
  if (!clusterPos) return;

  const track = trackPositions.find(t => t.id === cluster.trackId);
  if (!track) return;

  const clusterCenterX = clusterPos.x + clusterPos.width / 2;
  const clusterCenterY = clusterPos.y + clusterPos.height / 2;

  const sortedEvents = [...cluster.events].sort((a, b) => a.startTime - b.startTime);

  for (let i = 0; i < sortedEvents.length; i++) {
    const event = sortedEvents[i];
    const startPos = getEventPosition(event, xScale, trackPositions, eventHeight);
    if (!startPos) continue;

    const startX = startPos.x + startPos.width / 2;
    const startY = startPos.y + startPos.height / 2;

    const easedProgress = easeOutCubic(progress);
    const currentX = startX + (clusterCenterX - startX) * easedProgress;
    const currentY = startY + (clusterCenterY - startY) * easedProgress;
    const currentWidth = Math.max(4, startPos.width * (1 - easedProgress) + 20 * easedProgress);
    const currentHeight = eventHeight;

    const eventPos = {
      x: currentX - currentWidth / 2,
      y: currentY - currentHeight / 2,
      width: currentWidth,
      height: currentHeight
    };

    ctx.save();
    ctx.globalAlpha = Math.max(0.3, 1 - easedProgress);

    if (progress < 0.3) {
      drawSingleEvent(ctx, eventPos, event, false, false);
    } else {
      const radius = 4 * (1 - easedProgress) + 8 * easedProgress;
      ctx.fillStyle = '#6b7280';
      roundRect(ctx, eventPos.x, eventPos.y, eventPos.width, eventPos.height, radius);
      ctx.fill();
    }

    ctx.restore();
  }

  ctx.save();
  ctx.globalAlpha = progress;
  drawAggregatedEvent(ctx, clusterPos, cluster, false, false);
  ctx.restore();
};

const drawDragLine = (ctx, time, xScale, headerHeight, height) => {
  const x = xScale(time);

  ctx.strokeStyle = '#3b82f6';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.moveTo(x, headerHeight);
  ctx.lineTo(x, height);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#3b82f6';
  ctx.beginPath();
  ctx.arc(x, headerHeight - 10, 5, 0, Math.PI * 2);
  ctx.fill();
};

const roundRect = (ctx, x, y, width, height, radius) => {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
};

export const handleCanvasInteraction = (canvas, options) => {
  const {
    events,
    tracks,
    timeRange,
    xScale,
    eventHeight = 28,
    trackHeight = 50,
    headerHeight = 80,
    aggregatedEvents = null,
    expandedClusters = {},
    onEventClick,
    onEventHover,
    onClusterClick,
    onDragStart,
    onDrag,
    onDragEnd,
    onCanvasClick
  } = options;

  const trackPositions = getTrackPositions(tracks, trackHeight, headerHeight);
  const displayEvents = aggregatedEvents || events;

  let isDragging = false;
  let dragStartPos = null;
  let lastMousePos = null;

  const getMousePosition = (e) => {
    const rect = canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  };

  const handleMouseMove = (e) => {
    const pos = getMousePosition(e);
    const event = findEventAtPosition(displayEvents, xScale, trackPositions, pos.x, pos.y, eventHeight);

    if (event) {
      canvas.style.cursor = 'pointer';
      onEventHover && onEventHover(event, pos);
    } else {
      canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
      onEventHover && onEventHover(null, null);
    }

    if (isDragging && dragStartPos && lastMousePos) {
      const dx = pos.x - lastMousePos.x;
      onDrag && onDrag(dx, dragStartPos);
      lastMousePos = pos;
    }
  };

  const handleMouseDown = (e) => {
    const pos = getMousePosition(e);
    const event = findEventAtPosition(displayEvents, xScale, trackPositions, pos.x, pos.y, eventHeight);

    if (event) {
      if (event.aggregated && onClusterClick) {
        onClusterClick(event, pos);
      } else {
        onEventClick && onEventClick(event, pos);
      }
    } else {
      isDragging = true;
      dragStartPos = pos;
      lastMousePos = pos;
      canvas.style.cursor = 'grabbing';
      onDragStart && onDragStart(pos);
    }
  };

  const handleMouseUp = (e) => {
    if (isDragging) {
      isDragging = false;
      dragStartPos = null;
      lastMousePos = null;
      canvas.style.cursor = 'grab';
      onDragEnd && onDragEnd();
    }
  };

  const handleMouseLeave = (e) => {
    if (isDragging) {
      isDragging = false;
      dragStartPos = null;
      lastMousePos = null;
      canvas.style.cursor = 'grab';
      onDragEnd && onDragEnd();
    }
    onEventHover && onEventHover(null, null);
  };

  const handleClick = (e) => {
    const pos = getMousePosition(e);
    const event = findEventAtPosition(displayEvents, xScale, trackPositions, pos.x, pos.y, eventHeight);
    if (!event && !isDragging) {
      onCanvasClick && onCanvasClick(pos);
    }
  };

  canvas.addEventListener('mousemove', handleMouseMove);
  canvas.addEventListener('mousedown', handleMouseDown);
  canvas.addEventListener('mouseup', handleMouseUp);
  canvas.addEventListener('mouseleave', handleMouseLeave);
  canvas.addEventListener('click', handleClick);

  return () => {
    canvas.removeEventListener('mousemove', handleMouseMove);
    canvas.removeEventListener('mousedown', handleMouseDown);
    canvas.removeEventListener('mouseup', handleMouseUp);
    canvas.removeEventListener('mouseleave', handleMouseLeave);
    canvas.removeEventListener('click', handleClick);
  };
};

export const aggregateEventsIncremental = (allEvents, xScale, viewportStart, viewportEnd, threshold = 30, existingAggregation = null) => {
  return aggregateEventsForViewport(allEvents, xScale, viewportStart, viewportEnd, threshold);
};
