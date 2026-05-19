const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

class SynonymService {
  constructor() {
    this.synonymMap = new Map();
    this.wordToCategory = new Map();
    this.isLoaded = false;
  }

  async loadSynonyms() {
    if (this.isLoaded) return;

    try {
      const filePath = path.join(__dirname, '../data/synonyms.json');
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      for (const [category, words] of Object.entries(data)) {
        for (const [mainWord, synonyms] of Object.entries(words)) {
          this.synonymMap.set(mainWord.toLowerCase(), new Set([mainWord, ...synonyms.map(s => s.toLowerCase())]));
          this.wordToCategory.set(mainWord.toLowerCase(), category);
          
          for (const syn of synonyms) {
            this.wordToCategory.set(syn.toLowerCase(), category);
          }
        }
      }

      this.isLoaded = true;
      logger.info(`Synonyms loaded: ${this.synonymMap.size} main words`);
    } catch (error) {
      logger.error('Failed to load synonyms:', error);
    }
  }

  getSynonyms(word) {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    const lowerWord = word.toLowerCase();
    const synonyms = this.synonymMap.get(lowerWord);
    return synonyms ? Array.from(synonyms) : [word];
  }

  getCategory(word) {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    return this.wordToCategory.get(word.toLowerCase()) || null;
  }

  expandText(text) {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    const words = text.toLowerCase().split(/\s+/);
    const expandedWords = [];

    for (const word of words) {
      expandedWords.push(word);
      const synonyms = this.synonymMap.get(word);
      if (synonyms) {
        expandedWords.push(...synonyms);
      }
    }

    return expandedWords.join(' ');
  }

  expandWithWeights(text) {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    const words = text.toLowerCase().split(/\s+/);
    const weightedWords = [];

    for (const word of words) {
      weightedWords.push({ word, weight: 2 });
      
      const synonyms = this.synonymMap.get(word);
      if (synonyms) {
        for (const syn of synonyms) {
          if (syn !== word) {
            weightedWords.push({ word: syn, weight: 1 });
          }
        }
      }
    }

    return weightedWords;
  }

  addSynonym(word, synonym, category = 'general') {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    const lowerWord = word.toLowerCase();
    const lowerSyn = synonym.toLowerCase();

    if (!this.synonymMap.has(lowerWord)) {
      this.synonymMap.set(lowerWord, new Set([lowerWord]));
    }

    this.synonymMap.get(lowerWord).add(lowerSyn);
    this.wordToCategory.set(lowerSyn, category);

    logger.info(`Added synonym: ${synonym} -> ${word} (${category})`);
  }

  getSynonymMap() {
    if (!this.isLoaded) {
      this.loadSynonyms();
    }

    const result = {};
    for (const [word, synonyms] of this.synonymMap.entries()) {
      result[word] = Array.from(synonyms);
    }
    return result;
  }
}

module.exports = new SynonymService();
module.exports.SynonymService = SynonymService;
