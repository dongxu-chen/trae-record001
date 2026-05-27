import React, { useState, useCallback, useMemo } from 'react';
import Timeline from './Timeline.jsx';
import { compareTimelines } from '../utils/timelineUtils';

const TimelineCompare = ({
  events,
  tracks,
  defaultTimeUnit = 'month',
  onEventClick,
  onEventViewDetails,
  onExitCompare
}) => {
  const [compareMode, setCompareMode] = useState(true);
  const [linkViews, setLinkViews] = useState(true);
  const [highlightDiff, setHighlightDiff] = useState(true);

  const [timeRangeA, setTimeRangeA] = useState(null);
  const [timeRangeB, setTimeRangeB] = useState(null);
  const [timeUnitA, setTimeUnitA] = useState(defaultTimeUnit);
  const [timeUnitB, setTimeUnitB] = useState(defaultTimeUnit);
  const [filterA, setFilterA] = useState({ keywords: '', types: [], trackIds: [] });
  const [filterB, setFilterB] = useState({ keywords: '', types: [], trackIds: [] });

  const comparison = useMemo(() => {
    if (!compareMode) return null;
    return compareTimelines(
      { events: getFilteredEvents(events, filterA) },
      { events: getFilteredEvents(events, filterB) }
    );
  }, [compareMode, events, filterA, filterB]);

  function getFilteredEvents(allEvents, filter) {
    let filtered = [...allEvents];
    if (filter.keywords) {
      const lower = filter.keywords.toLowerCase();
      filtered = filtered.filter(e =>
        e.title?.toLowerCase().includes(lower) ||
        e.description?.toLowerCase().includes(lower)
      );
    }
    if (filter.types?.length) {
      filtered = filtered.filter(e => filter.types.includes(e.details?.category));
    }
    if (filter.trackIds?.length) {
      filtered = filtered.filter(e => filter.trackIds.includes(e.trackId));
    }
    return filtered;
  }

  const handleSyncRange = useCallback((source, range) => {
    if (!linkViews) return;
    if (source === 'A') {
      setTimeRangeB(range);
    } else {
      setTimeRangeA(range);
    }
  }, [linkViews]);

  const handleSyncTimeUnit = useCallback((source, unit) => {
    if (!linkViews) return;
    if (source === 'A') {
      setTimeUnitB(unit);
    } else {
      setTimeUnitA(unit);
    }
  }, [linkViews]);

  if (!compareMode) {
    return (
      <div className="compare-mode-toggle">
        <button
          className="compare-toggle-btn"
          onClick={() => setCompareMode(true)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          开启对比模式
        </button>
      </div>
    );
  }

  return (
    <div className="timeline-compare-container">
      <div className="compare-toolbar">
        <div className="compare-toolbar-left">
          <button
            className="compare-toggle-btn active"
            onClick={() => setCompareMode(false)}
          >
            关闭对比模式
          </button>
          <label className="compare-checkbox">
            <input
              type="checkbox"
              checked={linkViews}
              onChange={(e) => setLinkViews(e.target.checked)}
            />
            联动视图
          </label>
          <label className="compare-checkbox">
            <input
              type="checkbox"
              checked={highlightDiff}
              onChange={(e) => setHighlightDiff(e.target.checked)}
            />
            高亮差异
          </label>
        </div>
        {comparison && (
          <div className="compare-stats">
            <span className="compare-stat">
              <span className="compare-stat-label">A独有:</span>
              <span className="compare-stat-value">{comparison.onlyInA.length}</span>
            </span>
            <span className="compare-stat">
              <span className="compare-stat-label">B独有:</span>
              <span className="compare-stat-value">{comparison.onlyInB.length}</span>
            </span>
            <span className="compare-stat">
              <span className="compare-stat-label">共有:</span>
              <span className="compare-stat-value">{comparison.inBoth.length}</span>
            </span>
          </div>
        )}
      </div>

      <div className="compare-timelines">
        <div className="compare-timeline-panel">
          <div className="compare-panel-header">
            <span className="compare-panel-label">时间轴 A</span>
            {highlightDiff && (
              <span className="compare-panel-badge">
                {comparison?.onlyInA.length || 0} 项独有
              </span>
            )}
          </div>
          <div className="compare-panel-content">
            <Timeline
              events={events}
              tracks={tracks}
              defaultTimeUnit={timeUnitA}
              initialTimeRange={timeRangeA}
              onEventClick={onEventClick}
              onEventViewDetails={onEventViewDetails}
              onTimeRangeChange={(range) => {
                setTimeRangeA(range);
                handleSyncRange('A', range);
              }}
              onTimeUnitChange={(unit) => {
                setTimeUnitA(unit);
                handleSyncTimeUnit('A', unit);
              }}
              highlightEvents={highlightDiff ? comparison?.onlyInA?.map(e => e.id) : null}
              highlightColor="#3b82f6"
            />
          </div>
        </div>

        <div className="compare-timeline-panel">
          <div className="compare-panel-header">
            <span className="compare-panel-label">时间轴 B</span>
            {highlightDiff && (
              <span className="compare-panel-badge">
                {comparison?.onlyInB.length || 0} 项独有
              </span>
            )}
          </div>
          <div className="compare-panel-content">
            <Timeline
              events={events}
              tracks={tracks}
              defaultTimeUnit={timeUnitB}
              initialTimeRange={timeRangeB}
              onEventClick={onEventClick}
              onEventViewDetails={onEventViewDetails}
              onTimeRangeChange={(range) => {
                setTimeRangeB(range);
                handleSyncRange('B', range);
              }}
              onTimeUnitChange={(unit) => {
                setTimeUnitB(unit);
                handleSyncTimeUnit('B', unit);
              }}
              highlightEvents={highlightDiff ? comparison?.onlyInB?.map(e => e.id) : null}
              highlightColor="#ef4444"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineCompare;
