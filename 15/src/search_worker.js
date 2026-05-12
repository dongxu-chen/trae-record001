let localIndex = {
  notes: [],
  tagsCount: new Map()
};

self.onmessage = function(e) {
  const { type, payload } = e.data;
  
  switch (type) {
    case 'SET_INDEX':
      localIndex.notes = payload.notes || [];
      localIndex.tagsCount = new Map(payload.tagsCount || []);
      self.postMessage({ type: 'INDEX_UPDATED' });
      break;
      
    case 'SEARCH':
      const results = performSearch(
        payload.query,
        payload.selectedTags,
        payload.notes
      );
      self.postMessage({
        type: 'SEARCH_RESULTS',
        results,
        query: payload.query
      });
      break;
      
    case 'GET_ALL_TAGS':
      self.postMessage({
        type: 'TAGS_LIST',
        tags: Array.from(localIndex.tagsCount.entries())
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
      });
      break;
  }
};

function performSearch(query, selectedTags, notes) {
  const searchNotes = notes || localIndex.notes;
  const queryLower = query ? query.toLowerCase().trim() : '';
  const selectedTagsLower = selectedTags ? selectedTags.map(t => t.toLowerCase()) : [];
  
  let results = searchNotes.map(note => {
    let score = 0;
    let matchedFields = [];
    
    if (selectedTagsLower.length > 0) {
      const noteTags = (note.tags || []).map(t => t.toLowerCase());
      const allTagsMatch = selectedTagsLower.every(tag => noteTags.includes(tag));
      if (!allTagsMatch) {
        return null;
      }
      score += 10;
      matchedFields.push('tags');
    }
    
    if (queryLower) {
      const terms = queryLower.split(/\s+/).filter(t => t);
      const title = (note.title || '').toLowerCase();
      const preview = (note.preview || '').toLowerCase();
      const tags = (note.tags || []).join(' ').toLowerCase();
      const searchText = `${title} ${preview} ${tags}`;
      
      for (const term of terms) {
        if (title.includes(term)) {
          score += 5;
          if (!matchedFields.includes('title')) matchedFields.push('title');
        }
        if (tags.includes(term)) {
          score += 3;
          if (!matchedFields.includes('tags')) matchedFields.push('tags');
        }
        if (preview.includes(term)) {
          score += 2;
          if (!matchedFields.includes('content')) matchedFields.push('content');
        }
        
        const regex = new RegExp(escapeRegExp(term), 'gi');
        const titleMatches = (title.match(regex) || []).length;
        const previewMatches = (preview.match(regex) || []).length;
        score += titleMatches * 0.5 + previewMatches * 0.2;
      }
      
      if (score === 0) {
        if (searchText.includes(queryLower)) {
          score += 1;
        } else {
          return null;
        }
      }
    } else if (selectedTagsLower.length === 0) {
      score = 1;
    }
    
    return { note, score, matchedFields };
  }).filter(r => r !== null);
  
  results.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    return (b.note.modified || '0').localeCompare(a.note.modified || '0');
  });
  
  return results.map(r => ({
    ...r.note,
    _searchScore: r.score,
    _matchedFields: r.matchedFields
  }));
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
