const Note = require('./models/Note');

function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightText(text, searchTerm, caseSensitive = false) {
  if (!searchTerm || !text) return text;

  const flags = caseSensitive ? 'g' : 'gi';
  const regex = new RegExp(`(${escapeRegex(searchTerm)})`, flags);
  const matches = [];
  let match;

  while ((match = regex.exec(text)) !== null) {
    matches.push({
      start: match.index,
      end: match.index + match[0].length,
      text: match[0],
    });
  }

  return matches;
}

function findSegmentsByKeyword(segments, keyword) {
  if (!segments || segments.length === 0) return [];

  const results = [];
  const lowerKeyword = keyword.toLowerCase();

  segments.forEach(segment => {
    const text = segment.text?.toLowerCase() || '';
    if (text.includes(lowerKeyword)) {
      results.push({
        ...segment,
        matchIndex: text.indexOf(lowerKeyword),
      });
    }

    if (segment.words && segment.words.length > 0) {
      segment.words.forEach(word => {
        if (word.word?.toLowerCase().includes(lowerKeyword)) {
          if (!results.find(r => r.id === segment.id)) {
            results.push({
              ...segment,
              matchIndex: segment.text?.toLowerCase().indexOf(lowerKeyword),
            });
          }
        }
      });
    }
  });

  return results.sort((a, b) => a.start - b.start;
}

async function searchNotes(keyword, options = {}) {
  const {
    limit = 50,
    skip = 0,
    searchInSegments = true,
  } = options;

  if (!keyword || keyword.trim() === '') {
    return {
      notes: [],
      total: 0,
      keyword: '',
    };
  }

  const escapedKeyword = keyword.trim();
  const query = {
    $or: [
      { transcript: { $regex: escapedKeyword, $options: 'i' } },
      { whisperTranscript: { $regex: escapedKeyword, $options: 'i' } },
    ],
  };

  const [notes, total] = await Promise.all([
    Note.find(query)
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit),
    Note.countDocuments(query),
  ]);

  const notesWithMatches = notes.map(note => {
    const noteObj = note.toObject();
    const transcriptMatches = highlightText(noteObj.transcript, escapedKeyword);
    const whisperMatches = highlightText(noteObj.whisperTranscript, escapedKeyword);

    let segmentMatches = [];
    if (searchInSegments && noteObj.transcriptionData?.segments) {
      segmentMatches = findSegmentsByKeyword(
        noteObj.transcriptionData.segments,
        escapedKeyword
      );
    }

    return {
      ...noteObj,
      matches: {
        transcript: transcriptMatches,
        whisper: whisperMatches,
        segments: segmentMatches,
      },
      matchCount: transcriptMatches.length + whisperMatches.length + segmentMatches.length,
    };
  });

  return {
    notes: notesWithMatches,
    total,
    keyword: escapedKeyword,
    limit,
    skip,
  };
}

async function searchWithinNote(noteId, keyword) {
  if (!keyword || keyword.trim() === '') {
    return { segments: [], keyword: '' };
  }

  const note = await Note.findById(noteId);
  if (!note) {
    throw new Error('笔记不存在');
  }

  const noteObj = note.toObject();
  const escapedKeyword = keyword.trim();

  const transcriptMatches = highlightText(noteObj.transcript, escapedKeyword);
  const whisperMatches = highlightText(noteObj.whisperTranscript, escapedKeyword);

  let segmentMatches = [];
  if (noteObj.transcriptionData?.segments) {
    segmentMatches = findSegmentsByKeyword(
      noteObj.transcriptionData.segments,
      escapedKeyword
    );
  }

  return {
    segments: segmentMatches,
    transcriptMatches,
    whisperMatches,
    keyword: escapedKeyword,
  };
}

function getSegmentsInRange(segments, startTime, endTime) {
  if (!segments || segments.length === 0) return [];

  return segments.filter(segment => {
    const segStart = segment.start || 0;
    const segEnd = segment.end || 0;
    return segStart <= endTime && segEnd >= startTime;
  });
}

function filterSegmentsByTime(segments, startTime, endTime) {
  return getSegmentsInRange(segments, startTime, endTime);
}

module.exports = {
  searchNotes,
  searchWithinNote,
  highlightText,
  findSegmentsByKeyword,
  filterSegmentsByTime,
  getSegmentsInRange,
};