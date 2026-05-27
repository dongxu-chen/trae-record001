import React, { useState, useCallback } from 'react';

const SearchFilter = ({
  events = [],
  tracks = [],
  onFilterChange,
  eventTypes = [],
  eventColors = []
}) => {
  const [searchKeywords, setSearchKeywords] = useState('');
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [selectedTracks, setSelectedTracks] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleKeywordsChange = useCallback((e) => {
    const value = e.target.value;
    setSearchKeywords(value);
    onFilterChange && onFilterChange({
      keywords: value,
      types: selectedTypes,
      trackIds: selectedTracks
    });
  }, [selectedTypes, selectedTracks, onFilterChange]);

  const handleTypeToggle = useCallback((type) => {
    setSelectedTypes(prev => {
      const newTypes = prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type];
      onFilterChange && onFilterChange({
        keywords: searchKeywords,
        types: newTypes,
        trackIds: selectedTracks
      });
      return newTypes;
    });
  }, [searchKeywords, selectedTracks, onFilterChange]);

  const handleTrackToggle = useCallback((trackId) => {
    setSelectedTracks(prev => {
      const newTracks = prev.includes(trackId)
        ? prev.filter(t => t !== trackId)
        : [...prev, trackId];
      onFilterChange && onFilterChange({
        keywords: searchKeywords,
        types: selectedTypes,
        trackIds: newTracks
      });
      return newTracks;
    });
  }, [searchKeywords, selectedTypes, onFilterChange]);

  const handleClearFilters = useCallback(() => {
    setSearchKeywords('');
    setSelectedTypes([]);
    setSelectedTracks([]);
    onFilterChange && onFilterChange({
      keywords: '',
      types: [],
      trackIds: []
    });
  }, [onFilterChange]);

  const getTypeColor = (type) => {
    const colorItem = eventColors.find(c => c.type === type);
    return colorItem ? colorItem.color : '#6b7280';
  };

  const hasActiveFilters = searchKeywords || selectedTypes.length > 0 || selectedTracks.length > 0;

  return (
    <div className="search-filter-container">
      <div className="search-filter-header">
        <div className="search-input-wrapper">
          <svg
            className="search-icon"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="搜索事件标题、描述、地点..."
            value={searchKeywords}
            onChange={handleKeywordsChange}
          />
          {searchKeywords && (
            <button
              className="search-clear-btn"
              onClick={() => handleKeywordsChange({ target: { value: '' } })}
            >
              ×
            </button>
          )}
        </div>
        <button
          className={`filter-toggle-btn ${isExpanded ? 'active' : ''}`}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          筛选
          {hasActiveFilters && (
            <span className="filter-badge">
              {selectedTypes.length + selectedTracks.length + (searchKeywords ? 1 : 0)}
            </span>
          )}
        </button>
        {hasActiveFilters && (
          <button className="clear-filters-btn" onClick={handleClearFilters}>
            清除筛选
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="filter-options">
          {eventTypes.length > 0 && (
            <div className="filter-section">
              <label className="filter-section-label">事件类型</label>
              <div className="filter-tags">
                {eventTypes.map(type => (
                  <button
                    key={type}
                    className={`filter-tag ${selectedTypes.includes(type) ? 'active' : ''}`}
                    onClick={() => handleTypeToggle(type)}
                    style={{
                      backgroundColor: selectedTypes.includes(type) ? getTypeColor(type) : 'transparent',
                      borderColor: getTypeColor(type),
                      color: selectedTypes.includes(type) ? 'white' : getTypeColor(type)
                    }}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          )}

          {tracks.length > 0 && (
            <div className="filter-section">
              <label className="filter-section-label">轨道</label>
              <div className="filter-tags">
                {tracks.map(track => (
                  <button
                    key={track.id}
                    className={`filter-tag ${selectedTracks.includes(track.id) ? 'active' : ''}`}
                    onClick={() => handleTrackToggle(track.id)}
                    style={{
                      backgroundColor: selectedTracks.includes(track.id) ? track.color : 'transparent',
                      borderColor: track.color,
                      color: selectedTracks.includes(track.id) ? 'white' : track.color
                    }}
                  >
                    {track.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchFilter;
