import moment from 'moment';

export const TIME_UNITS = {
  DAY: 'day',
  WEEK: 'week',
  MONTH: 'month',
  YEAR: 'year'
};

export const ANIMATION_DURATION = 300;
export const EASING_FACTOR = 0.15;

export const getTimeUnitFormatter = (timeUnit) => {
  switch (timeUnit) {
    case TIME_UNITS.DAY:
      return {
        major: (d) => moment(d).format('YYYY年MM月'),
        minor: (d) => moment(d).format('DD')
      };
    case TIME_UNITS.WEEK:
      return {
        major: (d) => moment(d).format('YYYY年MM月'),
        minor: (d) => `${moment(d).format('W')}周`
      };
    case TIME_UNITS.MONTH:
      return {
        major: (d) => moment(d).format('YYYY年'),
        minor: (d) => moment(d).format('MM月')
      };
    case TIME_UNITS.YEAR:
      return {
        major: (d) => '',
        minor: (d) => moment(d).format('YYYY年')
      };
    default:
      return {
        major: (d) => moment(d).format('YYYY年MM月'),
        minor: (d) => moment(d).format('DD')
      };
  }
};

export const getTimeUnitStep = (timeUnit) => {
  switch (timeUnit) {
    case TIME_UNITS.DAY:
      return { major: { unit: 'month', step: 1 }, minor: { unit: 'day', step: 1 } };
    case TIME_UNITS.WEEK:
      return { major: { unit: 'month', step: 1 }, minor: { unit: 'week', step: 1 } };
    case TIME_UNITS.MONTH:
      return { major: { unit: 'year', step: 1 }, minor: { unit: 'month', step: 1 } };
    case TIME_UNITS.YEAR:
      return { major: { unit: 'year', step: 1 }, minor: { unit: 'year', step: 1 } };
    default:
      return { major: { unit: 'month', step: 1 }, minor: { unit: 'day', step: 1 } };
  }
};

export const generateTicks = (startTime, endTime, timeUnit) => {
  const step = getTimeUnitStep(timeUnit);
  const majorTicks = [];
  const minorTicks = [];

  const currentMajor = moment(startTime).startOf(step.major.unit);
  while (currentMajor.valueOf() <= endTime) {
    majorTicks.push(currentMajor.valueOf());
    currentMajor.add(step.major.step, step.major.unit);
  }

  const currentMinor = moment(startTime).startOf(step.minor.unit);
  while (currentMinor.valueOf() <= endTime) {
    minorTicks.push(currentMinor.valueOf());
    currentMinor.add(step.minor.step, step.minor.unit);
  }

  return { majorTicks, minorTicks };
};

export const formatTimeRange = (startTime, endTime, timeUnit) => {
  const format = (time) => {
    switch (timeUnit) {
      case TIME_UNITS.DAY:
        return moment(time).format('YYYY-MM-DD');
      case TIME_UNITS.WEEK:
        return `${moment(time).format('YYYY')}年${moment(time).format('W')}周`;
      case TIME_UNITS.MONTH:
        return moment(time).format('YYYY年MM月');
      case TIME_UNITS.YEAR:
        return moment(time).format('YYYY年');
      default:
        return moment(time).format('YYYY-MM-DD');
    }
  };
  return `${format(startTime)} - ${format(endTime)}`;
};

export const getDefaultTimeRange = (events, timeUnit) => {
  if (events.length === 0) {
    const now = moment();
    return {
      startTime: now.startOf('month').valueOf(),
      endTime: now.endOf('month').valueOf()
    };
  }

  const minTime = Math.min(...events.map(e => e.startTime));
  const maxTime = Math.max(...events.map(e => e.endTime));

  let startTime = moment(minTime);
  let endTime = moment(maxTime);

  const padding = {
    day: 7,
    week: 2,
    month: 1,
    year: 1
  };

  startTime = startTime.subtract(padding[timeUnit] || 1, timeUnit);
  endTime = endTime.add(padding[timeUnit] || 1, timeUnit);

  return {
    startTime: startTime.valueOf(),
    endTime: endTime.valueOf()
  };
};

export const getZoomRange = (currentStart, currentEnd, zoomFactor) => {
  const center = (currentStart + currentEnd) / 2;
  const range = (currentEnd - currentStart) * zoomFactor;
  return {
    startTime: Math.round(center - range / 2),
    endTime: Math.round(center + range / 2)
  };
};

export const getPanRange = (currentStart, currentEnd, panDistance, containerWidth) => {
  const timeRange = currentEnd - currentStart;
  const timePerPixel = timeRange / containerWidth;
  const timeDelta = panDistance * timePerPixel;

  return {
    startTime: Math.round(currentStart + timeDelta),
    endTime: Math.round(currentEnd + timeDelta)
  };
};

export const aggregateEvents = (events, xScale, threshold = 30) => {
  const aggregated = [];
  const clusters = [];
  const sortedEvents = [...events].sort((a, b) => a.startTime - b.startTime);

  let currentCluster = null;

  for (const event of sortedEvents) {
    const eventX = xScale(event.startTime);

    if (!currentCluster) {
      currentCluster = {
        events: [event],
        startTime: event.startTime,
        endTime: event.endTime,
        x: eventX
      };
    } else {
      const clusterX = xScale((currentCluster.startTime + currentCluster.endTime) / 2);
      if (Math.abs(eventX - clusterX) < threshold) {
        currentCluster.events.push(event);
        currentCluster.startTime = Math.min(currentCluster.startTime, event.startTime);
        currentCluster.endTime = Math.max(currentCluster.endTime, event.endTime);
      } else {
        clusters.push(currentCluster);
        currentCluster = {
          events: [event],
          startTime: event.startTime,
          endTime: event.endTime,
          x: eventX
        };
      }
    }
  }

  if (currentCluster) {
    clusters.push(currentCluster);
  }

  for (const cluster of clusters) {
    if (cluster.events.length === 1) {
      aggregated.push({
        ...cluster.events[0],
        aggregated: false,
        clusterX: xScale((cluster.startTime + cluster.endTime) / 2)
      });
    } else {
      aggregated.push({
        id: `cluster-${cluster.startTime}-${cluster.endTime}`,
        title: `${cluster.events.length}个事件`,
        startTime: cluster.startTime,
        endTime: cluster.endTime,
        trackId: cluster.events[0].trackId,
        type: 'aggregate',
        color: '#6b7280',
        description: `包含${cluster.events.length}个事件`,
        events: cluster.events,
        aggregated: true,
        clusterX: xScale((cluster.startTime + cluster.endTime) / 2)
      });
    }
  }

  return aggregated;
};

export const aggregateEventsForViewport = (events, xScale, viewportStart, viewportEnd, threshold = 30) => {
  const visibleEvents = events.filter(event =>
    event.endTime >= viewportStart && event.startTime <= viewportEnd
  );
  return aggregateEvents(visibleEvents, xScale, threshold);
};

export const getTrackPositions = (tracks, trackHeight, headerHeight) => {
  return tracks.map((track, index) => ({
    ...track,
    y: headerHeight + index * trackHeight,
    height: trackHeight
  }));
};

export const getEventPosition = (event, xScale, trackPositions, eventHeight) => {
  const track = trackPositions.find(t => t.id === event.trackId);
  if (!track) return null;

  const startTime = event.startTime;
  const endTime = event.endTime;

  const x = xScale(startTime);
  const endX = xScale(endTime);
  const width = Math.max(endX - x, 4);
  const y = track.y + (track.height - eventHeight) / 2;

  return { x, y, width, height: eventHeight, startTime, endTime };
};

export const getEventPositionAbsolute = (event, trackPositions, eventHeight) => {
  const track = trackPositions.find(t => t.id === event.trackId);
  if (!track) return null;

  const y = track.y + (track.height - eventHeight) / 2;

  return {
    startTime: event.startTime,
    endTime: event.endTime,
    y,
    height: eventHeight
  };
};

export const isEventVisible = (event, xScale, containerWidth) => {
  const eventStartX = xScale(event.startTime);
  const eventEndX = xScale(event.endTime);
  return eventEndX >= 0 && eventStartX <= containerWidth;
};

export const isEventInViewport = (event, viewportStart, viewportEnd) => {
  return event.endTime >= viewportStart && event.startTime <= viewportEnd;
};

export const findEventAtPosition = (events, xScale, trackPositions, x, y, eventHeight) => {
  for (let i = events.length - 1; i >= 0; i--) {
    const event = events[i];
    const pos = getEventPosition(event, xScale, trackPositions, eventHeight);
    if (pos && x >= pos.x && x <= pos.x + pos.width && y >= pos.y && y <= pos.y + pos.height) {
      return event;
    }
  }
  return null;
};

export const easeOutCubic = (t) => {
  return 1 - Math.pow(1 - t, 3);
};

export const interpolateValue = (start, end, progress) => {
  return start + (end - start) * progress;
};

export const interpolateEventPosition = (event, fromXScale, toXScale, trackPositions, eventHeight, progress) => {
  const track = trackPositions.find(t => t.id === event.trackId);
  if (!track) return null;

  const fromX = fromXScale(event.startTime);
  const fromEndX = fromXScale(event.endTime);
  const fromWidth = Math.max(fromEndX - fromX, 4);

  const toX = toXScale(event.startTime);
  const toEndX = toXScale(event.endTime);
  const toWidth = Math.max(toEndX - toX, 4);

  const x = interpolateValue(fromX, toX, progress);
  const width = interpolateValue(fromWidth, toWidth, progress);
  const y = track.y + (track.height - eventHeight) / 2;

  return { x, y, width, height: eventHeight };
};

export const expandCluster = (cluster, targetTrackId) => {
  const centerTime = (cluster.startTime + cluster.endTime) / 2;
  const sortedEvents = [...cluster.events].sort((a, b) => a.startTime - b.startTime);
  
  return sortedEvents.map((event, index) => ({
    ...event,
    expanded: true,
    originalClusterId: cluster.id,
    expandedIndex: index,
    expandedTotal: sortedEvents.length
  }));
};

export const calculateExpandedPositions = (events, trackHeight, eventHeight) => {
  return events.map((event, index) => ({
    ...event,
    expandedY: (index + 0.5) * (eventHeight + 4)
  }));
};

export const lerp = (start, end, factor) => {
  return start + (end - start) * factor;
};

export const clamp = (value, min, max) => {
  return Math.min(Math.max(value, min), max);
};

export const getViewportEvents = (events, viewportStart, viewportEnd) => {
  return events.filter(event =>
    event.endTime >= viewportStart && event.startTime <= viewportEnd
  );
};

export const createAnimatedScale = (fromScale, toScale, duration = ANIMATION_DURATION) => {
  const startTime = Date.now();
  
  return (time) => {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeOutCubic(progress);
    
    return {
      scale: (t) => {
        const fromValue = fromScale(t);
        const toValue = toScale(t);
        return lerp(fromValue, toValue, eased);
      },
      invert: (x) => {
        const fromDomain = fromScale.domain();
        const toDomain = toScale.domain();
        const fromValue = fromScale.invert(x);
        const toValue = toScale.invert(x);
        return lerp(fromValue, toValue, eased);
      },
      progress: eased,
      isComplete: progress >= 1
    };
  };
};

export const interpolateTimeRange = (fromRange, toRange, progress) => {
  return {
    startTime: Math.round(lerp(fromRange.startTime, toRange.startTime, progress)),
    endTime: Math.round(lerp(fromRange.endTime, toRange.endTime, progress))
  };
};

export const encodeSnapshot = (state) => {
  const data = {
    v: 1,
    s: state.timeRange?.startTime,
    e: state.timeRange?.endTime,
    u: state.timeUnit,
    f: state.filterKeywords,
    t: state.filterTypes,
    ts: Date.now()
  };
  const json = JSON.stringify(data);
  const base64 = btoa(encodeURIComponent(json));
  return base64;
};

export const decodeSnapshot = (encoded) => {
  try {
    const json = decodeURIComponent(atob(encoded));
    const data = JSON.parse(json);
    if (data.v !== 1) return null;
    return {
      timeRange: data.s && data.e ? { startTime: data.s, endTime: data.e } : null,
      timeUnit: data.u || null,
      filterKeywords: data.f || '',
      filterTypes: data.t || [],
      timestamp: data.ts
    };
  } catch (e) {
    return null;
  }
};

export const generateShareLink = (state, baseUrl = window.location.origin + window.location.pathname) => {
  const snapshot = encodeSnapshot(state);
  return `${baseUrl}?snapshot=${snapshot}`;
};

export const parseShareLink = (url) => {
  try {
    const urlObj = new URL(url);
    const snapshot = urlObj.searchParams.get('snapshot');
    if (snapshot) {
      return decodeSnapshot(snapshot);
    }
    return null;
  } catch (e) {
    return null;
  }
};

export const getSnapshotFromUrl = () => {
  return parseShareLink(window.location.href);
};

export const filterEvents = (events, options = {}) => {
  const { keywords = '', types = [], trackIds = [], dateRange = null } = options;
  let filtered = [...events];

  if (keywords && keywords.trim()) {
    const lowerKeywords = keywords.toLowerCase().trim();
    filtered = filtered.filter(event =>
      event.title?.toLowerCase().includes(lowerKeywords) ||
      event.description?.toLowerCase().includes(lowerKeywords) ||
      event.details?.location?.toLowerCase().includes(lowerKeywords)
    );
  }

  if (types && types.length > 0) {
    filtered = filtered.filter(event =>
      types.includes(event.type) || types.includes(event.details?.category)
    );
  }

  if (trackIds && trackIds.length > 0) {
    filtered = filtered.filter(event => trackIds.includes(event.trackId));
  }

  if (dateRange) {
    filtered = filtered.filter(event =>
      event.endTime >= dateRange.startTime && event.startTime <= dateRange.endTime
    );
  }

  return filtered;
};

export const getEventTypes = (events) => {
  const types = new Set();
  events.forEach(event => {
    if (event.details?.category) {
      types.add(event.details.category);
    } else if (event.type && event.type !== 'event' && event.type !== 'aggregate') {
      types.add(event.type);
    }
  });
  return Array.from(types);
};

export const getEventColors = () => {
  return [
    { type: '会议', color: '#3b82f6' },
    { type: '培训', color: '#10b981' },
    { type: '评审', color: '#8b5cf6' },
    { type: '发布', color: '#22c55e' },
    { type: '团建', color: '#ec4899' },
    { type: '调研', color: '#f97316' },
    { type: '维护', color: '#06b6d4' }
  ];
};

export const compareTimelines = (timelineA, timelineB) => {
  const eventsA = new Set(timelineA.events.map(e => e.id));
  const eventsB = new Set(timelineB.events.map(e => e.id));

  const onlyInA = timelineA.events.filter(e => !eventsB.has(e.id));
  const onlyInB = timelineB.events.filter(e => !eventsA.has(e.id));
  const inBoth = timelineA.events.filter(e => eventsB.has(e.id));

  return { onlyInA, onlyInB, inBoth };
};
