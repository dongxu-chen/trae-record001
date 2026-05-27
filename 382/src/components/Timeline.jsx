import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import moment from 'moment';
import EventPopup from './EventPopup.jsx';
import { drawTimeline, handleCanvasInteraction, aggregateEventsIncremental } from '../utils/canvasRenderer';
import {
  TIME_UNITS,
  ANIMATION_DURATION,
  getDefaultTimeRange,
  getZoomRange,
  getPanRange,
  aggregateEvents,
  aggregateEventsForViewport,
  formatTimeRange,
  findEventAtPosition,
  getTrackPositions,
  getEventPosition,
  getEventPositionAbsolute,
  isEventInViewport,
  getViewportEvents,
  interpolateTimeRange,
  easeOutCubic,
  lerp,
  expandCluster,
  filterEvents
} from '../utils/timelineUtils';

const Timeline = ({
  events = [],
  tracks = [],
  defaultTimeUnit = TIME_UNITS.MONTH,
  initialTimeRange = null,
  onEventClick,
  onEventViewDetails,
  onTimeRangeChange,
  onTimeUnitChange,
  trackHeight = 50,
  eventHeight = 28,
  headerHeight = 80,
  minWidth = 800,
  minHeight = 400,
  aggregationThreshold = 30,
  highlightEvents = null,
  highlightColor = '#3b82f6',
  filterOptions = null,
  showControls = true
}) => {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const animationStateRef = useRef({
    type: null,
    startTime: 0,
    duration: ANIMATION_DURATION,
    fromRange: null,
    toRange: null,
    fromXScale: null,
    toXScale: null,
    cluster: null
  });

  const [timeUnit, setTimeUnit] = useState(defaultTimeUnit);
  const [timeRange, setTimeRange] = useState(() => {
    return initialTimeRange || getDefaultTimeRange(events, defaultTimeUnit);
  });
  const [dimensions, setDimensions] = useState({ width: minWidth, height: minHeight });
  const [hoveredEvent, setHoveredEvent] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [currentTime, setCurrentTime] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [expandedClusters, setExpandedClusters] = useState({});
  const [animationProgress, setAnimationProgress] = useState(1);
  const [previousXScale, setPreviousXScale] = useState(null);
  const [animationType, setAnimationType] = useState(null);
  const [expandedCluster, setExpandedCluster] = useState(null);
  const [viewportEvents, setViewportEvents] = useState([]);

  const filteredEvents = useMemo(() => {
    if (!filterOptions) return events;
    return filterEvents(events, filterOptions);
  }, [events, filterOptions]);

  const xScale = useMemo(() => {
    return d3.scaleTime()
      .domain([timeRange.startTime, timeRange.endTime])
      .range([0, dimensions.width]);
  }, [timeRange, dimensions.width]);

  const aggregatedEvents = useMemo(() => {
    return aggregateEventsForViewport(filteredEvents, xScale, timeRange.startTime, timeRange.endTime, aggregationThreshold);
  }, [filteredEvents, xScale, timeRange.startTime, timeRange.endTime, aggregationThreshold]);

  const trackPositions = useMemo(() => {
    return getTrackPositions(tracks, trackHeight, headerHeight);
  }, [tracks, trackHeight, headerHeight]);

  const totalHeight = headerHeight + tracks.length * trackHeight + 20;

  const updateViewportEvents = useCallback(() => {
    const visibleEvents = getViewportEvents(filteredEvents, timeRange.startTime, timeRange.endTime);
    setViewportEvents(visibleEvents);
  }, [filteredEvents, timeRange.startTime, timeRange.endTime]);

  useEffect(() => {
    updateViewportEvents();
  }, [updateViewportEvents]);

  useEffect(() => {
    onTimeRangeChange && onTimeRangeChange(timeRange);
  }, [timeRange, onTimeRangeChange]);

  useEffect(() => {
    onTimeUnitChange && onTimeUnitChange(timeUnit);
  }, [timeUnit, onTimeUnitChange]);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const width = Math.max(containerRef.current.clientWidth, minWidth);
        const height = Math.max(totalHeight, minHeight);
        setDimensions({ width, height });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [minWidth, minHeight, totalHeight]);

  useEffect(() => {
    if (canvasRef.current) {
      canvasRef.current.width = dimensions.width;
      canvasRef.current.height = totalHeight;
    }
  }, [dimensions, totalHeight]);

  const animate = useCallback(() => {
    const state = animationStateRef.current;
    if (!state.type) return;

    const elapsed = Date.now() - state.startTime;
    const progress = Math.min(elapsed / state.duration, 1);
    const eased = easeOutCubic(progress);

    setAnimationProgress(eased);

    if (state.type === 'timeUnitChange') {
      const interpolatedRange = interpolateTimeRange(state.fromRange, state.toRange, eased);
      setTimeRange(interpolatedRange);
    }

    if (progress >= 1) {
      animationFrameRef.current = null;
      state.type = null;
      setAnimationType(null);
      setExpandedCluster(null);
      setPreviousXScale(null);
      setAnimationProgress(1);

      if (state.type === 'expand' && state.cluster) {
        setExpandedClusters(prev => ({
          ...prev,
          [state.cluster.id]: true
        }));
      }
      return;
    }

    animationFrameRef.current = requestAnimationFrame(animate);
  }, []);

  const startAnimation = useCallback((type, options = {}) => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    const state = animationStateRef.current;
    state.type = type;
    state.startTime = Date.now();
    state.duration = options.duration || ANIMATION_DURATION;

    if (type === 'timeUnitChange') {
      state.fromRange = options.fromRange;
      state.toRange = options.toRange;
    } else if (type === 'expand' || type === 'collapse') {
      state.cluster = options.cluster;
      setExpandedCluster(options.cluster);
    }

    setAnimationType(type);
    setAnimationProgress(0);
    animationFrameRef.current = requestAnimationFrame(animate);
  }, [animate]);

  useEffect(() => {
    if (canvasRef.current) {
      drawTimeline(canvasRef.current, {
        events: viewportEvents,
        tracks,
        timeRange,
        timeUnit,
        width: dimensions.width,
        height: totalHeight,
        xScale,
        eventHeight,
        trackHeight,
        headerHeight,
        aggregatedEvents,
        hoveredEvent,
        selectedEvent,
        expandedCluster,
        animationProgress,
        previousXScale,
        isDragging,
        dragStart,
        currentTime,
        animationType,
        highlightEvents,
        highlightColor
      });
    }
  }, [viewportEvents, tracks, timeRange, timeUnit, dimensions, xScale, trackHeight, eventHeight,
      aggregatedEvents, hoveredEvent, selectedEvent, isDragging, dragStart,
      currentTime, totalHeight, animationProgress, previousXScale, animationType,
      expandedCluster, headerHeight, highlightEvents, highlightColor]);

  useEffect(() => {
    if (canvasRef.current) {
      const cleanup = handleCanvasInteraction(canvasRef.current, {
        events: viewportEvents,
        tracks,
        timeRange,
        xScale,
        eventHeight,
        trackHeight,
        headerHeight,
        aggregatedEvents,
        expandedClusters,
        onEventClick: (event, pos) => {
          setSelectedEvent(event);
          setPopupPosition(pos);
          onEventClick && onEventClick(event, pos);
        },
        onEventHover: (event, pos) => {
          setHoveredEvent(event);
          if (pos) {
            setTooltip(event);
          } else {
            setTooltip(null);
          }
        },
        onClusterClick: (cluster, pos) => {
          if (expandedClusters[cluster.id]) {
            startAnimation('collapse', { cluster, duration: 300 });
            setExpandedClusters(prev => {
              const newState = { ...prev };
              delete newState[cluster.id];
              return newState;
            });
          } else {
            startAnimation('expand', { cluster, duration: 300 });
          }
        },
        onDragStart: (pos) => {
          setIsDragging(true);
          setDragStart(pos);
        },
        onDrag: (dx, startPos) => {
          const newRange = getPanRange(
            timeRange.startTime,
            timeRange.endTime,
            -dx,
            dimensions.width
          );
          setTimeRange(newRange);
          setCurrentTime(xScale.invert(startPos.x + dx));
        },
        onDragEnd: () => {
          setIsDragging(false);
          setDragStart(null);
          setCurrentTime(null);
        },
        onCanvasClick: (pos) => {
          setSelectedEvent(null);
          onEventClick && onEventClick(null, pos);
        }
      });

      return cleanup;
    }
  }, [viewportEvents, tracks, timeRange, xScale, eventHeight, trackHeight,
      headerHeight, aggregatedEvents, expandedClusters, dimensions.width, startAnimation, onEventClick]);

  const handleTimeUnitChange = useCallback((unit) => {
    if (unit === timeUnit) return;

    const newRange = getDefaultTimeRange(filteredEvents, unit);

    setPreviousXScale(xScale.copy());
    startAnimation('timeUnitChange', {
      fromRange: timeRange,
      toRange: newRange,
      duration: 400
    });

    setTimeUnit(unit);
    setSelectedEvent(null);
  }, [timeUnit, filteredEvents, timeRange, xScale, startAnimation]);

  const handleZoom = useCallback((direction) => {
    const zoomFactor = direction === 'in' ? 0.8 : 1.2;
    const newRange = getZoomRange(
      timeRange.startTime,
      timeRange.endTime,
      zoomFactor
    );

    setPreviousXScale(xScale.copy());
    startAnimation('timeUnitChange', {
      fromRange: timeRange,
      toRange: newRange,
      duration: 300
    });
  }, [timeRange, xScale, startAnimation]);

  const handleWheel = useCallback((e) => {
    if (e.deltaY < 0) {
      handleZoom('in');
    } else {
      handleZoom('out');
    }
  }, [handleZoom]);

  const handleResetView = useCallback(() => {
    const newRange = getDefaultTimeRange(filteredEvents, timeUnit);
    setPreviousXScale(xScale.copy());
    startAnimation('timeUnitChange', {
      fromRange: timeRange,
      toRange: newRange,
      duration: 400
    });
    setSelectedEvent(null);
  }, [filteredEvents, timeUnit, timeRange, xScale, startAnimation]);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <div className="timeline-container" ref={containerRef}>
      {showControls && (
        <div className="timeline-controls">
          <div className="time-unit-buttons">
            <button
              className={`time-unit-btn ${timeUnit === TIME_UNITS.DAY ? 'active' : ''}`}
              onClick={() => handleTimeUnitChange(TIME_UNITS.DAY)}
            >
              日
            </button>
            <button
              className={`time-unit-btn ${timeUnit === TIME_UNITS.WEEK ? 'active' : ''}`}
              onClick={() => handleTimeUnitChange(TIME_UNITS.WEEK)}
            >
              周
            </button>
            <button
              className={`time-unit-btn ${timeUnit === TIME_UNITS.MONTH ? 'active' : ''}`}
              onClick={() => handleTimeUnitChange(TIME_UNITS.MONTH)}
            >
              月
            </button>
            <button
              className={`time-unit-btn ${timeUnit === TIME_UNITS.YEAR ? 'active' : ''}`}
              onClick={() => handleTimeUnitChange(TIME_UNITS.YEAR)}
            >
              年
            </button>
          </div>
          <div className="timeline-info">
            <span style={{ fontSize: '13px', color: '#6b7280' }}>
              {formatTimeRange(timeRange.startTime, timeRange.endTime, timeUnit)}
            </span>
          </div>
          <div className="zoom-controls">
            <button className="zoom-btn" onClick={() => handleZoom('out')} title="缩小">
              −
            </button>
            <button className="zoom-btn" onClick={handleResetView} title="重置视图">
              ⟳
            </button>
            <button className="zoom-btn" onClick={() => handleZoom('in')} title="放大">
              +
            </button>
          </div>
        </div>
      )}
      <div
        className="timeline-canvas-wrapper"
        onWheel={handleWheel}
        style={{ height: totalHeight }}
      >
        <div className="timeline-canvas-container">
          <div className="timeline-track-labels" style={{ width: 80, position: 'absolute', left: 0, top: 0 }}>
            {trackPositions.map((track, index) => (
              <div
                key={track.id}
                className="timeline-track-label"
                style={{
                  height: trackHeight,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: '#f9fafb',
                  borderBottom: '1px solid #e5e7eb',
                  marginTop: index === 0 ? headerHeight : 0
                }}
              >
                <div style={{ width: 4, height: '100%', backgroundColor: track.color, marginRight: 8 }} />
                <span style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>
                  {track.name}
                </span>
              </div>
            ))}
          </div>
          <canvas
            ref={canvasRef}
            width={dimensions.width}
            height={totalHeight}
            style={{ width: dimensions.width, height: totalHeight, display: 'block' }}
          />
        </div>
      </div>
      {tooltip && (
        <div className="timeline-tooltip">
          <div>{tooltip.title}</div>
          <div style={{ fontSize: '11px', opacity: 0.8 }}>
            {moment(tooltip.startTime).format('YYYY-MM-DD')}
          </div>
        </div>
      )}
      {selectedEvent && !selectedEvent.aggregated && (
        <EventPopup
          event={selectedEvent}
          position={popupPosition}
          onClose={() => setSelectedEvent(null)}
          onViewDetails={onEventViewDetails}
        />
      )}
    </div>
  );
};

export default Timeline;
