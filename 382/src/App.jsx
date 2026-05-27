import React, { useState, useCallback, useMemo, useEffect } from 'react';
import Timeline from './components/Timeline.jsx';
import SearchFilter from './components/SearchFilter.jsx';
import SnapshotShare from './components/SnapshotShare.jsx';
import TimelineCompare from './components/TimelineCompare.jsx';
import { generateMockEvents, tracks } from './data/mockData.js';
import {
  filterEvents,
  getEventTypes,
  getEventColors,
  getSnapshotFromUrl,
  decodeSnapshot
} from './utils/timelineUtils';

const App = () => {
  const [events] = useState(() => generateMockEvents());
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [filterOptions, setFilterOptions] = useState({ keywords: '', types: [], trackIds: [] });
  const [savedSnapshots, setSavedSnapshots] = useState([]);
  const [currentSnapshot, setCurrentSnapshot] = useState(null);

  const eventTypes = useMemo(() => getEventTypes(events), [events]);
  const eventColors = useMemo(() => getEventColors(), []);

  const filteredEvents = useMemo(() => {
    if (!filterOptions.keywords && filterOptions.types.length === 0 && filterOptions.trackIds.length === 0) {
      return events;
    }
    return filterEvents(events, filterOptions);
  }, [events, filterOptions]);

  useEffect(() => {
    const snapshot = getSnapshotFromUrl();
    if (snapshot) {
      setCurrentSnapshot(snapshot);
      if (snapshot.timeRange || snapshot.filterKeywords || snapshot.filterTypes) {
        setFilterOptions(prev => ({
          keywords: snapshot.filterKeywords || prev.keywords,
          types: snapshot.filterTypes || prev.types,
          trackIds: prev.trackIds
        }));
      }
    }
  }, []);

  const handleEventClick = useCallback((event, position) => {
    setSelectedEvent(event);
    console.log('Event clicked:', event);
  }, []);

  const handleViewDetails = useCallback((event) => {
    console.log('View details for:', event);
    alert(`查看事件详情：${event.title}\n时间：${new Date(event.startTime).toLocaleString()}`);
  }, []);

  const handleFilterChange = useCallback((options) => {
    setFilterOptions(options);
  }, []);

  const handleSaveSnapshot = useCallback((snapshot) => {
    setSavedSnapshots(prev => [snapshot, ...prev.slice(0, 9)]);
  }, []);

  const handleRestoreSnapshot = useCallback((snapshot) => {
    setCurrentSnapshot(snapshot);
    if (snapshot.filterKeywords || snapshot.filterTypes) {
      setFilterOptions(prev => ({
        keywords: snapshot.filterKeywords || prev.keywords,
        types: snapshot.filterTypes || prev.types,
        trackIds: prev.trackIds
      }));
    }
  }, []);

  if (compareMode) {
    return (
      <div className="app-container">
        <div className="app-header">
          <h1 className="app-title">时间轴图表组件 - 对比模式</h1>
          <button
            className="compare-toggle-btn"
            onClick={() => setCompareMode(false)}
          >
            返回单视图
          </button>
        </div>
        <div className="app-content">
          <div className="timeline-wrapper">
            <TimelineCompare
              events={events}
              tracks={tracks}
              defaultTimeUnit="month"
              onEventClick={handleEventClick}
              onEventViewDetails={handleViewDetails}
              onExitCompare={() => setCompareMode(false)}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="app-header">
        <h1 className="app-title">时间轴图表组件</h1>
        <div className="header-actions">
          <button
            className="compare-toggle-btn"
            onClick={() => setCompareMode(true)}
          >
            对比模式
          </button>
        </div>
      </div>
      <div className="app-content">
        <div className="timeline-wrapper">
          <div className="timeline-toolbar">
            <SearchFilter
              events={events}
              tracks={tracks}
              eventTypes={eventTypes}
              eventColors={eventColors}
              onFilterChange={handleFilterChange}
            />
            <SnapshotShare
              timeRange={currentSnapshot?.timeRange}
              timeUnit="month"
              filterKeywords={filterOptions.keywords}
              filterTypes={filterOptions.types}
              savedSnapshots={savedSnapshots}
              onSaveSnapshot={handleSaveSnapshot}
              onRestoreSnapshot={handleRestoreSnapshot}
            />
          </div>
          <Timeline
            events={filteredEvents}
            tracks={tracks}
            defaultTimeUnit="month"
            initialTimeRange={currentSnapshot?.timeRange}
            onEventClick={handleEventClick}
            onEventViewDetails={handleViewDetails}
            filterOptions={filterOptions}
          />
        </div>
      </div>
    </div>
  );
};

export default App;
