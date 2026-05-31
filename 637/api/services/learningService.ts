import type { NamingStyle, HistoryItem, LearningData } from '../../shared/types';

const DEFAULT_LEARNING_DATA: LearningData = {
  stylePreferences: {
    'camelCase': 0,
    'snake_case': 0,
    'PascalCase': 0,
    'kebab-case': 0,
    'SCREAMING_SNAKE_CASE': 0
  },
  wordFrequency: {},
  patternFrequency: {},
  nameFrequency: {},
  totalUsage: 0,
  minFrequencyThreshold: 2
};

let inMemoryLearningData: LearningData = { ...DEFAULT_LEARNING_DATA };
let inMemoryHistory: HistoryItem[] = [];

export function loadLearningData(): LearningData {
  return inMemoryLearningData;
}

export function saveLearningData(data: LearningData): void {
  inMemoryLearningData = data;
}

export function loadHistory(): HistoryItem[] {
  return inMemoryHistory;
}

export function saveHistory(history: HistoryItem[]): void {
  inMemoryHistory = history;
}

export function setMinFrequencyThreshold(threshold: number): void {
  const data = loadLearningData();
  data.minFrequencyThreshold = threshold;
  saveLearningData(data);
}

export function addToHistory(item: Omit<HistoryItem, 'id' | 'timestamp' | 'isFavorite'>): HistoryItem {
  const historyItem: HistoryItem = {
    ...item,
    id: `hist-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: Date.now(),
    isFavorite: false
  };
  
  const history = loadHistory();
  history.unshift(historyItem);
  
  const recentHistory = history.slice(0, 200);
  saveHistory(recentHistory);
  updateLearningFromHistory(historyItem);
  
  return historyItem;
}

function updateLearningFromHistory(item: HistoryItem): void {
  const data = loadLearningData();
  
  const styleBonus = item.feedback === 'like' ? 2 : item.feedback === 'dislike' ? 0 : 1;
  data.stylePreferences[item.style] = (data.stylePreferences[item.style] || 0) + styleBonus;
  
  const words = item.selectedName.split(/[-_]/).filter(w => w.length > 0);
  for (const word of words) {
    const lowerWord = word.toLowerCase();
    data.wordFrequency[lowerWord] = (data.wordFrequency[lowerWord] || 0) + styleBonus;
  }
  
  const nameKey = `${item.selectedName.toLowerCase()}:${item.style}`;
  data.nameFrequency[nameKey] = (data.nameFrequency[nameKey] || 0) + styleBonus;
  
  data.patternFrequency[item.style] = (data.patternFrequency[item.style] || 0) + styleBonus;
  data.totalUsage += styleBonus;
  
  saveLearningData(data);
}

export function getWordWeight(word: string): number {
  const data = loadLearningData();
  const lowerWord = word.toLowerCase();
  const frequency = data.wordFrequency[lowerWord] || 0;
  
  if (frequency === 0) return 1;
  if (frequency < data.minFrequencyThreshold) return 0.5;
  
  return 1 + Math.log10(frequency) * 0.1;
}

export function getNameFrequency(name: string, style: NamingStyle): number {
  const data = loadLearningData();
  const nameKey = `${name.toLowerCase()}:${style}`;
  return data.nameFrequency[nameKey] || 0;
}

export function filterLowFrequencyWords(words: string[]): string[] {
  const data = loadLearningData();
  return words.filter(word => {
    const lowerWord = word.toLowerCase();
    const frequency = data.wordFrequency[lowerWord] || 0;
    return frequency === 0 || frequency >= data.minFrequencyThreshold;
  });
}

export function getHighFrequencyWords(minCount: number = 3): string[] {
  const data = loadLearningData();
  return Object.entries(data.wordFrequency)
    .filter(([, count]) => count >= minCount)
    .sort(([, a], [, b]) => b - a)
    .map(([word]) => word);
}

export function getPreferredStyle(): NamingStyle {
  const data = loadLearningData();
  
  if (data.totalUsage === 0) {
    return 'camelCase';
  }
  
  let maxCount = 0;
  let preferred: NamingStyle = 'camelCase';
  
  for (const [style, count] of Object.entries(data.stylePreferences)) {
    if (count > maxCount) {
      maxCount = count;
      preferred = style as NamingStyle;
    }
  }
  
  return preferred;
}

export function getSuggestions(): { 
  preferredStyle: NamingStyle;
  frequentWords: string[];
  usageStats: Record<NamingStyle, number>;
  highFrequencyNames: Array<{ name: string; style: NamingStyle; count: number }>;
} {
  const data = loadLearningData();
  
  const sortedWords = Object.entries(data.wordFrequency)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([word]) => word);
  
  const highFrequencyNames = Object.entries(data.nameFrequency)
    .filter(([, count]) => count >= data.minFrequencyThreshold)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([key, count]) => {
      const [name, style] = key.split(':');
      return { name, style: style as NamingStyle, count };
    });
  
  return {
    preferredStyle: getPreferredStyle(),
    frequentWords: sortedWords,
    usageStats: { ...data.stylePreferences },
    highFrequencyNames
  };
}

export function calculateFrequencyBoost(name: string, style: NamingStyle): number {
  const frequency = getNameFrequency(name, style);
  if (frequency === 0) return 0;
  return Math.min(0.15, Math.log10(frequency + 1) * 0.05);
}

export function toggleFavorite(id: string): HistoryItem | null {
  const history = loadHistory();
  const item = history.find(h => h.id === id);
  
  if (item) {
    item.isFavorite = !item.isFavorite;
    saveHistory(history);
    return item;
  }
  
  return null;
}

export function deleteHistoryItem(id: string): boolean {
  const history = loadHistory();
  const index = history.findIndex(h => h.id === id);
  
  if (index !== -1) {
    history.splice(index, 1);
    saveHistory(history);
    return true;
  }
  
  return false;
}

export function clearHistory(): void {
  saveHistory([]);
  saveLearningData({ ...DEFAULT_LEARNING_DATA });
}

export function submitFeedback(id: string, feedback: 'like' | 'dislike'): void {
  const history = loadHistory();
  const item = history.find(h => h.id === id);
  
  if (item) {
    const oldFeedback = item.feedback;
    item.feedback = feedback;
    saveHistory(history);
    
    if (oldFeedback) {
      recalculateLearningData();
    } else {
      updateLearningFromHistory(item);
    }
  }
}

function recalculateLearningData(): void {
  const history = loadHistory();
  const data = { ...DEFAULT_LEARNING_DATA };
  
  for (const item of history) {
    const styleBonus = item.feedback === 'like' ? 2 : item.feedback === 'dislike' ? 0 : 1;
    data.stylePreferences[item.style] = (data.stylePreferences[item.style] || 0) + styleBonus;
    
    const words = item.selectedName.split(/[-_]/).filter(w => w.length > 0);
    for (const word of words) {
      const lowerWord = word.toLowerCase();
      data.wordFrequency[lowerWord] = (data.wordFrequency[lowerWord] || 0) + styleBonus;
    }
    
    const nameKey = `${item.selectedName.toLowerCase()}:${item.style}`;
    data.nameFrequency[nameKey] = (data.nameFrequency[nameKey] || 0) + styleBonus;
    
    data.patternFrequency[item.style] = (data.patternFrequency[item.style] || 0) + styleBonus;
    data.totalUsage += styleBonus;
  }
  
  saveLearningData(data);
}
