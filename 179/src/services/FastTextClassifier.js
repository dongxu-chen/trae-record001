const fs = require('fs');
const path = require('path');
const synonymService = require('./SynonymService');
const logger = require('../utils/logger');

class FastTextClassifier {
  constructor(options = {}) {
    this.learningRate = options.learningRate || 0.1;
    this.epochs = options.epochs || 100;
    this.minCount = options.minCount || 1;
    this.wordNgrams = options.wordNgrams || 2;
    this.dim = options.dim || 100;
    this.loss = options.loss || 'softmax';

    this.word2idx = new Map();
    this.idx2word = [];
    this.label2idx = new Map();
    this.idx2label = [];
    
    this.inputEmbedding = [];
    this.outputEmbedding = [];
    this.bias = [];
    
    this.vocabCount = new Map();
    this.isTrained = false;
  }

  tokenize(text) {
    const cleaned = text.toLowerCase()
      .replace(/[^\w\u4e00-\u9fa5\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const words = [];
    
    const chineseChars = cleaned.match(/[\u4e00-\u9fa5]/g) || [];
    for (let i = 0; i < chineseChars.length - 1; i++) {
      words.push(chineseChars[i] + chineseChars[i + 1]);
    }

    const englishWords = cleaned.match(/[a-zA-Z]+/g) || [];
    words.push(...englishWords);

    return words;
  }

  getNgrams(words) {
    const ngrams = [...words];
    
    for (let n = 2; n <= this.wordNgrams; n++) {
      for (let i = 0; i <= words.length - n; i++) {
        const ngram = words.slice(i, i + n).join(' ');
        ngrams.push(ngram);
      }
    }

    return ngrams;
  }

  buildVocab(sentences) {
    for (const sentence of sentences) {
      const words = this.tokenize(sentence.text);
      const expandedText = synonymService.expandText(sentence.text);
      const expandedWords = this.tokenize(expandedText);
      const allWords = [...new Set([...words, ...expandedWords])];
      
      for (const word of allWords) {
        this.vocabCount.set(word, (this.vocabCount.get(word) || 0) + 1);
      }

      if (!this.label2idx.has(sentence.label)) {
        this.label2idx.set(sentence.label, this.idx2label.length);
        this.idx2label.push(sentence.label);
      }
    }

    for (const [word, count] of this.vocabCount.entries()) {
      if (count >= this.minCount) {
        this.word2idx.set(word, this.idx2word.length);
        this.idx2word.push(word);
      }
    }

    logger.info(`Vocabulary built: ${this.idx2word.length} words, ${this.idx2label.length} labels`);
  }

  initWeights() {
    const vocabSize = this.idx2word.length;
    const numLabels = this.idx2label.length;

    this.inputEmbedding = [];
    for (let i = 0; i < vocabSize; i++) {
      const vec = new Array(this.dim).fill(0);
      for (let j = 0; j < this.dim; j++) {
        vec[j] = (Math.random() - 0.5) / this.dim;
      }
      this.inputEmbedding.push(vec);
    }

    this.outputEmbedding = [];
    this.bias = new Array(numLabels).fill(0);
    for (let i = 0; i < numLabels; i++) {
      const vec = new Array(this.dim).fill(0);
      this.outputEmbedding.push(vec);
    }
  }

  getSentenceVector(words) {
    const ngrams = this.getNgrams(words);
    const indices = [];
    
    for (const gram of ngrams) {
      const idx = this.word2idx.get(gram);
      if (idx !== undefined) {
        indices.push(idx);
      }
    }

    if (indices.length === 0) {
      return new Array(this.dim).fill(0);
    }

    const vec = new Array(this.dim).fill(0);
    for (const idx of indices) {
      for (let j = 0; j < this.dim; j++) {
        vec[j] += this.inputEmbedding[idx][j];
      }
    }

    for (let j = 0; j < this.dim; j++) {
      vec[j] /= indices.length;
    }

    return vec;
  }

  softmax(scores) {
    const maxScore = Math.max(...scores);
    const expScores = scores.map(s => Math.exp(s - maxScore));
    const sum = expScores.reduce((a, b) => a + b, 0);
    return expScores.map(s => s / sum);
  }

  computeScores(sentenceVec) {
    const scores = [];
    const numLabels = this.idx2label.length;
    
    for (let i = 0; i < numLabels; i++) {
      let score = this.bias[i];
      for (let j = 0; j < this.dim; j++) {
        score += sentenceVec[j] * this.outputEmbedding[i][j];
      }
      scores.push(score);
    }

    return scores;
  }

  async train(trainingData) {
    await synonymService.loadSynonyms();

    logger.info(`Training FastText classifier with ${trainingData.length} samples...`);

    this.buildVocab(trainingData);
    this.initWeights();

    const numLabels = this.idx2label.length;

    for (let epoch = 0; epoch < this.epochs; epoch++) {
      let totalLoss = 0;
      let correct = 0;

      for (const sample of trainingData) {
        const words = this.tokenize(sample.text);
        const expandedText = synonymService.expandText(sample.text);
        const expandedWords = this.tokenize(expandedText);
        const allWords = [...new Set([...words, ...expandedWords])];
        
        const sentenceVec = this.getSentenceVector(allWords);
        const scores = this.computeScores(sentenceVec);
        const probs = this.softmax(scores);

        const trueLabelIdx = this.label2idx.get(sample.label);
        const predictedIdx = probs.indexOf(Math.max(...probs));
        
        if (predictedIdx === trueLabelIdx) {
          correct++;
        }

        totalLoss += -Math.log(probs[trueLabelIdx] + 1e-10);

        for (let i = 0; i < numLabels; i++) {
          const grad = (i === trueLabelIdx ? 1 : 0) - probs[i];
          
          for (let j = 0; j < this.dim; j++) {
            this.outputEmbedding[i][j] += this.learningRate * grad * sentenceVec[j];
          }
          this.bias[i] += this.learningRate * grad;
        }

        const wordIndices = [];
        const ngrams = this.getNgrams(allWords);
        for (const gram of ngrams) {
          const idx = this.word2idx.get(gram);
          if (idx !== undefined) {
            wordIndices.push(idx);
          }
        }

        if (wordIndices.length > 0) {
          for (const idx of wordIndices) {
            for (let j = 0; j < this.dim; j++) {
              let gradSum = 0;
              for (let i = 0; i < numLabels; i++) {
                const grad = (i === trueLabelIdx ? 1 : 0) - probs[i];
                gradSum += grad * this.outputEmbedding[i][j];
              }
              this.inputEmbedding[idx][j] += this.learningRate * gradSum / wordIndices.length;
            }
          }
        }
      }

      const accuracy = correct / trainingData.length;
      const avgLoss = totalLoss / trainingData.length;

      if ((epoch + 1) % 10 === 0) {
        logger.debug(`Epoch ${epoch + 1}/${this.epochs}: loss=${avgLoss.toFixed(4)}, acc=${accuracy.toFixed(4)}`);
      }
    }

    this.isTrained = true;
    logger.info('FastText classifier training completed');
  }

  async predict(text, k = 1) {
    if (!this.isTrained) {
      throw new Error('Classifier not trained. Call train() first.');
    }

    await synonymService.loadSynonyms();

    const words = this.tokenize(text);
    const expandedText = synonymService.expandText(text);
    const expandedWords = this.tokenize(expandedText);
    const allWords = [...new Set([...words, ...expandedWords])];

    const sentenceVec = this.getSentenceVector(allWords);
    const scores = this.computeScores(sentenceVec);
    const probs = this.softmax(scores);

    const results = probs.map((prob, idx) => ({
      label: this.idx2label[idx],
      probability: prob
    }));

    results.sort((a, b) => b.probability - a.probability);

    return results.slice(0, k);
  }

  async predictLabel(text) {
    const predictions = await this.predict(text, 1);
    return predictions[0];
  }

  loadTrainingData(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n').filter(line => line.trim());
    
    const data = [];
    for (const line of lines) {
      const match = line.match(/^(__label__\S+)\s+(.*)$/);
      if (match) {
        const label = match[1].replace('__label__', '');
        const text = match[2].trim();
        data.push({ text, label });
      }
    }

    return data;
  }

  async trainFromFile(filePath) {
    const trainingData = this.loadTrainingData(filePath);
    await this.train(trainingData);
  }

  saveModel(filePath) {
    const model = {
      word2idx: Object.fromEntries(this.word2idx),
      idx2word: this.idx2word,
      label2idx: Object.fromEntries(this.label2idx),
      idx2label: this.idx2label,
      inputEmbedding: this.inputEmbedding,
      outputEmbedding: this.outputEmbedding,
      bias: this.bias,
      dim: this.dim,
      wordNgrams: this.wordNgrams
    };

    fs.writeFileSync(filePath, JSON.stringify(model));
    logger.info(`Model saved to ${filePath}`);
  }

  loadModel(filePath) {
    const model = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    this.word2idx = new Map(Object.entries(model.word2idx));
    this.idx2word = model.idx2word;
    this.label2idx = new Map(Object.entries(model.label2idx));
    this.idx2label = model.idx2label;
    this.inputEmbedding = model.inputEmbedding;
    this.outputEmbedding = model.outputEmbedding;
    this.bias = model.bias;
    this.dim = model.dim;
    this.wordNgrams = model.wordNgrams;
    this.isTrained = true;

    logger.info(`Model loaded from ${filePath}`);
  }

  getVocabSize() {
    return this.idx2word.length;
  }

  getNumLabels() {
    return this.idx2label.length;
  }
}

const defaultClassifier = new FastTextClassifier({
  learningRate: 0.05,
  epochs: 150,
  dim: 128,
  wordNgrams: 2
});

module.exports = {
  FastTextClassifier,
  classifier: defaultClassifier,
  trainDefault: async () => {
    const trainingDataPath = path.join(__dirname, '../data/training_data.txt');
    if (fs.existsSync(trainingDataPath)) {
      await defaultClassifier.trainFromFile(trainingDataPath);
    } else {
      logger.warn('Training data file not found');
    }
  }
};
