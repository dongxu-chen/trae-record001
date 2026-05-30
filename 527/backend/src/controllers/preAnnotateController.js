const Document = require('../models/Document');
const Annotation = require('../models/Annotation');

const BASE_ENTITY_PATTERNS = {
  PERSON: [
    /(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?/g,
    /[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?/g
  ],
  ORGANIZATION: [
    /[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc\.|Corp\.|Ltd\.|Company|Corporation|Group|University|Institute|Association)/g,
    /(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Bank|Hospital|School|College)/g
  ],
  LOCATION: [
    /(?:in|at|from|to)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:,|\s|$)/g,
    /[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:City|Town|Village|Province|State|Country)/g
  ],
  DATE: [
    /\d{4}-\d{2}-\d{2}/g,
    /\d{2}\/\d{2}\/\d{4}/g,
    /(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}/g
  ],
  EMAIL: [
    /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g
  ],
  PHONE: [
    /(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g
  ]
};

const BASE_KEYWORDS = {
  PERSON: ['John', 'Mary', 'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Zhang', 'Li', 'Wang', 'Zhao', 'Liu', 'Chen', 'Yang', 'Huang', 'Zhou', 'Wu'],
  ORGANIZATION: ['Google', 'Microsoft', 'Apple', 'Amazon', 'Facebook', 'IBM', 'Intel', 'Oracle', 'Salesforce', 'Adobe', 'Alibaba', 'Tencent', 'Baidu', 'Huawei', 'Xiaomi'],
  LOCATION: ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'New York', 'London', 'Paris', 'Tokyo', 'Sydney', 'Hong Kong']
};

const LABEL_COLORS = {
  PERSON: '#FF6B6B',
  ORGANIZATION: '#4ECDC4',
  LOCATION: '#45B7D1',
  DATE: '#96CEB4',
  EMAIL: '#FFEAA7',
  PHONE: '#DDA0DD'
};

let modelState = {
  version: '1.0.0',
  trainedAt: null,
  learnedPatterns: {},
  learnedKeywords: {},
  labelWeights: {},
  totalAnnotations: 0,
  lastUpdated: null
};

let uncertaintyCache = {};

function getColorForLabel(label) {
  return LABEL_COLORS[label] || '#CCCCCC';
}

function getDynamicPatterns(taskId) {
  const taskPatterns = modelState.learnedPatterns[taskId] || {};
  const merged = {};
  
  Object.keys(BASE_ENTITY_PATTERNS).forEach(label => {
    merged[label] = [
      ...BASE_ENTITY_PATTERNS[label],
      ...(taskPatterns[label] || [])
    ];
  });
  
  Object.keys(taskPatterns).forEach(label => {
    if (!merged[label]) {
      merged[label] = taskPatterns[label];
    }
  });
  
  return merged;
}

function getDynamicKeywords(taskId) {
  const taskKeywords = modelState.learnedKeywords[taskId] || {};
  const merged = {};
  
  Object.keys(BASE_KEYWORDS).forEach(label => {
    merged[label] = [
      ...BASE_KEYWORDS[label],
      ...(taskKeywords[label] || [])
    ];
  });
  
  Object.keys(taskKeywords).forEach(label => {
    if (!merged[label]) {
      merged[label] = taskKeywords[label];
    }
  });
  
  return merged;
}

function getLabelWeights(taskId) {
  return modelState.labelWeights[taskId] || {};
}

function calculateConfidence(entity, taskId) {
  let baseConfidence = 0.7;
  
  if (entity.fromPattern) {
    baseConfidence = 0.7;
  } else if (entity.fromKeyword) {
    baseConfidence = 0.85;
  }
  
  const weights = getLabelWeights(taskId);
  const labelWeight = weights[entity.label] || 1.0;
  baseConfidence *= labelWeight;
  
  if (entity.isLearned) {
    baseConfidence *= 0.9;
  }
  
  if (entity.text.length < 2) {
    baseConfidence *= 0.5;
  } else if (entity.text.length > 20) {
    baseConfidence *= 0.8;
  }
  
  return Math.min(0.99, Math.max(0.1, baseConfidence));
}

function calculateUncertainty(entities, text, taskId) {
  if (entities.length === 0) return 0.5;
  
  let totalUncertainty = 0;
  
  entities.forEach(entity => {
    const confidence = entity.confidence || calculateConfidence(entity, taskId);
    totalUncertainty += (1 - confidence);
  });
  
  const avgUncertainty = totalUncertainty / entities.length;
  
  const textLength = text.length;
  const entityDensity = entities.length / (textLength / 100);
  const densityPenalty = entityDensity > 5 ? 0.2 : entityDensity < 1 ? 0.1 : 0;
  
  const hasOverlap = entities.some((e1, i) => 
    entities.some((e2, j) => i !== j && 
      (e1.start < e2.end && e1.end > e2.start))
  );
  const overlapPenalty = hasOverlap ? 0.15 : 0;
  
  return Math.min(1.0, avgUncertainty + densityPenalty + overlapPenalty);
}

async function fineTuneModel(taskId) {
  try {
    const annotations = await Annotation.find({ taskId })
      .populate('documentId', 'text');
    
    if (annotations.length === 0) {
      return { success: false, message: 'No annotations to learn from' };
    }
    
    const newPatterns = {};
    const newKeywords = {};
    const labelCounts = {};
    const labelCorrect = {};
    
    annotations.forEach(ann => {
      ann.entities.forEach(entity => {
        if (entity.isPreAnnotated) return;
        
        const label = entity.label;
        const text = entity.text.trim();
        
        if (!newKeywords[label]) {
          newKeywords[label] = new Set();
        }
        newKeywords[label].add(text);
        
        if (!labelCounts[label]) {
          labelCounts[label] = 0;
          labelCorrect[label] = 0;
        }
        labelCounts[label]++;
        
        if (text.length > 2 && text.length < 15 && !text.match(/\d/)) {
          if (!newPatterns[label]) {
            newPatterns[label] = [];
          }
          
          const escapedText = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const pattern = new RegExp(`\\b${escapedText}\\b`, 'gi');
          
          const exists = newPatterns[label].some(p => 
            p.toString() === pattern.toString()
          );
          
          if (!exists && newPatterns[label].length < 50) {
            newPatterns[label].push(pattern);
          }
        }
      });
    });
    
    modelState.learnedPatterns[taskId] = {};
    Object.entries(newPatterns).forEach(([label, patterns]) => {
      modelState.learnedPatterns[taskId][label] = patterns;
    });
    
    modelState.learnedKeywords[taskId] = {};
    Object.entries(newKeywords).forEach(([label, keywords]) => {
      modelState.learnedKeywords[taskId][label] = Array.from(keywords).slice(0, 200);
    });
    
    modelState.labelWeights[taskId] = {};
    Object.entries(labelCounts).forEach(([label, count]) => {
      modelState.labelWeights[taskId][label] = Math.min(1.2, 0.8 + (count / 100) * 0.4);
    });
    
    modelState.version = `1.${annotations.length}.0`;
    modelState.trainedAt = new Date();
    modelState.totalAnnotations = annotations.length;
    modelState.lastUpdated = new Date();
    
    return {
      success: true,
      version: modelState.version,
      learnedLabels: Object.keys(newKeywords),
      totalAnnotations: annotations.length,
      newPatternsCount: Object.values(newPatterns).reduce((a, b) => a + b.length, 0),
      newKeywordsCount: Object.values(newKeywords).reduce((a, b) => a + b.size, 0)
    };
  } catch (error) {
    console.error('Fine-tuning error:', error);
    return { success: false, error: error.message };
  }
}

function preAnnotateEntities(text, taskId) {
  const entities = [];
  let entityId = 0;
  
  const patterns = getDynamicPatterns(taskId);
  const keywords = getDynamicKeywords(taskId);
  
  Object.entries(patterns).forEach(([label, patternList]) => {
    patternList.forEach(pattern => {
      try {
        const matches = text.matchAll(pattern);
        for (const match of matches) {
          const entityText = match[0].trim();
          const start = match.index;
          const end = start + entityText.length;
          
          if (entityText.length > 2 && !entities.some(e => 
            (start >= e.start && start < e.end) || 
            (end > e.start && end <= e.end) ||
            (start < e.start && end > e.end)
          )) {
            const entity = {
              id: `pre-entity-${entityId++}`,
              start,
              end,
              text: entityText,
              label,
              color: getColorForLabel(label),
              isPreAnnotated: true,
              fromPattern: true,
              isLearned: Object.keys(modelState.learnedPatterns[taskId] || {}).includes(label)
            };
            entity.confidence = calculateConfidence(entity, taskId);
            entities.push(entity);
          }
        }
      } catch (e) {
        console.log('Pattern error:', e.message);
      }
    });
  });
  
  Object.entries(keywords).forEach(([label, keywordList]) => {
    keywordList.forEach(keyword => {
      try {
        const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
        const matches = text.matchAll(regex);
        for (const match of matches) {
          const start = match.index;
          const end = start + match[0].length;
          
          if (!entities.some(e => 
            (start >= e.start && start < e.end) || 
            (end > e.start && end <= e.end) ||
            (start < e.start && end > e.end)
          )) {
            const entity = {
              id: `pre-entity-${entityId++}`,
              start,
              end,
              text: match[0],
              label,
              color: getColorForLabel(label),
              isPreAnnotated: true,
              fromKeyword: true,
              isLearned: (modelState.learnedKeywords[taskId]?.[label] || []).includes(keyword)
            };
            entity.confidence = calculateConfidence(entity, taskId);
            entities.push(entity);
          }
        }
      } catch (e) {
        console.log('Keyword error:', e.message);
      }
    });
  });
  
  return entities;
}

exports.preAnnotateDocument = async (req, res) => {
  try {
    const { documentId } = req.params;
    const { useActiveLearning = true, confidenceThreshold = 0.3 } = req.body || {};
    
    const document = await Document.findById(documentId);
    
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    
    const taskId = document.taskId.toString();
    let entities = preAnnotateEntities(document.text, taskId);
    
    if (useActiveLearning && confidenceThreshold > 0) {
      entities = entities.filter(e => e.confidence >= confidenceThreshold);
    }
    
    const uncertainty = calculateUncertainty(entities, document.text, taskId);
    uncertaintyCache[documentId] = uncertainty;
    
    await Document.findByIdAndUpdate(documentId, {
      isPreAnnotated: true,
      updatedAt: Date.now()
    });
    
    res.json({
      documentId,
      entities,
      relations: [],
      events: [],
      modelInfo: {
        version: modelState.version,
        lastTrained: modelState.trainedAt,
        totalAnnotations: modelState.totalAnnotations
      },
      uncertainty,
      suggestion: uncertainty > 0.7 
        ? 'HIGH_UNCERTAINTY' 
        : uncertainty > 0.4 
          ? 'MEDIUM_UNCERTAINTY' 
          : 'LOW_UNCERTAINTY'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.fineTune = async (req, res) => {
  try {
    const { taskId } = req.params;
    
    const result = await fineTuneModel(taskId);
    
    if (!result.success) {
      return res.status(400).json(result);
    }
    
    res.json({
      message: 'Model fine-tuned successfully',
      ...result
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getNextUncertainDocument = async (req, res) => {
  try {
    const { taskId } = req.params;
    const { sampleSize = 20, strategy = 'uncertainty' } = req.query;
    
    const documents = await Document.find({ 
      taskId, 
      status: 'pending' 
    }).limit(parseInt(sampleSize) * 3);
    
    if (documents.length === 0) {
      return res.json(null);
    }
    
    const scoredDocs = [];
    
    for (const doc of documents) {
      let uncertainty = uncertaintyCache[doc._id.toString()];
      
      if (uncertainty === undefined) {
        const entities = preAnnotateEntities(doc.text, taskId);
        uncertainty = calculateUncertainty(entities, doc.text, taskId);
        uncertaintyCache[doc._id.toString()] = uncertainty;
      }
      
      let score = uncertainty;
      
      if (strategy === 'diversity') {
        const textLength = doc.text.length;
        const lengthScore = Math.min(1, textLength / 500);
        score = (score + lengthScore) / 2;
      } else if (strategy === 'hybrid') {
        const entities = preAnnotateEntities(doc.text, taskId);
        const diversityScore = 1 - (entities.filter(e => e.confidence > 0.8).length / Math.max(1, entities.length));
        score = (uncertainty * 0.7 + diversityScore * 0.3);
      }
      
      scoredDocs.push({ document: doc, score, uncertainty });
    }
    
    scoredDocs.sort((a, b) => b.score - a.score);
    const selected = scoredDocs[0];
    
    res.json({
      ...selected.document.toObject(),
      activeLearningScore: selected.score,
      uncertainty: selected.uncertainty,
      strategy,
      poolSize: documents.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getModelInfo = async (req, res) => {
  try {
    const { taskId } = req.params;
    
    const annotations = await Annotation.countDocuments({ taskId });
    
    res.json({
      version: modelState.version,
      trainedAt: modelState.trainedAt,
      lastUpdated: modelState.lastUpdated,
      totalAnnotations: annotations,
      learnedPatterns: modelState.learnedPatterns[taskId] 
        ? Object.keys(modelState.learnedPatterns[taskId]).map(label => ({
            label,
            count: modelState.learnedPatterns[taskId][label].length
          }))
        : [],
      learnedKeywords: modelState.learnedKeywords[taskId]
        ? Object.keys(modelState.learnedKeywords[taskId]).map(label => ({
            label,
            count: modelState.learnedKeywords[taskId][label].length,
            samples: modelState.learnedKeywords[taskId][label].slice(0, 10)
          }))
        : [],
      labelWeights: modelState.labelWeights[taskId] || {}
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.checkConsistency = async (req, res) => {
  try {
    const { taskId } = req.params;
    const { sampleSize = 50, sampleStrategy = 'random' } = req.query;
    
    const allAnnotations = await Annotation.find({ taskId })
      .populate('documentId', 'text');
    
    const totalCount = allAnnotations.length;
    
    let sampledAnnotations = allAnnotations;
    
    if (totalCount > parseInt(sampleSize)) {
      if (sampleStrategy === 'random') {
        const shuffled = [...allAnnotations].sort(() => 0.5 - Math.random());
        sampledAnnotations = shuffled.slice(0, parseInt(sampleSize));
      } else if (sampleStrategy === 'recent') {
        sampledAnnotations = allAnnotations
          .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
          .slice(0, parseInt(sampleSize));
      } else if (sampleStrategy === 'stratified') {
        const byLabel = {};
        allAnnotations.forEach(ann => {
          ann.entities.forEach(e => {
            if (!byLabel[e.label]) byLabel[e.label] = [];
            byLabel[e.label].push(ann);
          });
        });
        
        const perLabel = Math.ceil(parseInt(sampleSize) / Math.max(1, Object.keys(byLabel).length));
        const selected = new Set();
        
        Object.values(byLabel).forEach(anns => {
          const shuffled = [...anns].sort(() => 0.5 - Math.random());
          shuffled.slice(0, perLabel).forEach(a => selected.add(a._id.toString()));
        });
        
        sampledAnnotations = allAnnotations.filter(a => selected.has(a._id.toString()));
      }
    }
    
    const entityMentions = {};
    const overlappingEntities = [];
    
    sampledAnnotations.forEach(ann => {
      ann.entities.forEach(entity => {
        const key = entity.text.toLowerCase();
        if (!entityMentions[key]) {
          entityMentions[key] = [];
        }
        entityMentions[key].push({
          label: entity.label,
          documentId: ann.documentId._id,
          entityId: entity.id
        });
      });
      
      const sortedEntities = [...ann.entities].sort((a, b) => a.start - b.start);
      for (let i = 0; i < sortedEntities.length - 1; i++) {
        for (let j = i + 1; j < sortedEntities.length; j++) {
          if (sortedEntities[j].start < sortedEntities[i].end) {
            overlappingEntities.push({
              documentId: ann.documentId._id,
              text: ann.documentId.text,
              entity1: sortedEntities[i],
              entity2: sortedEntities[j]
            });
          } else {
            break;
          }
        }
      }
    });
    
    const inconsistentIssues = [];
    Object.entries(entityMentions).forEach(([text, mentions]) => {
      const labels = new Set(mentions.map(m => m.label));
      if (labels.size > 1) {
        inconsistentIssues.push({
          type: 'inconsistent_label',
          text,
          labels: Array.from(labels),
          occurrences: mentions.length,
          details: mentions.slice(0, 20)
        });
      }
    });
    
    const inconsistencyRate = totalCount > 0 
      ? (inconsistentIssues.length / totalCount * 100).toFixed(2)
      : 0;
    
    const overlapRate = totalCount > 0
      ? (overlappingEntities.length / totalCount * 100).toFixed(2)
      : 0;
    
    const issues = [];
    if (inconsistentIssues.length > 0) {
      issues.push(...inconsistentIssues);
    }
    if (overlappingEntities.length > 0) {
      issues.push({
        type: 'overlapping_entities',
        count: overlappingEntities.length,
        details: overlappingEntities.slice(0, 10)
      });
    }
    
    res.json({
      totalAnnotations: totalCount,
      sampledCount: sampledAnnotations.length,
      sampleSize: parseInt(sampleSize),
      sampleStrategy,
      inconsistentCount: inconsistentIssues.length,
      overlappingCount: overlappingEntities.length,
      inconsistencyRate: `${inconsistencyRate}%`,
      overlapRate: `${overlapRate}%`,
      isSampled: totalCount > parseInt(sampleSize),
      estimatedTotalIssues: {
        inconsistent: Math.round(inconsistentIssues.length * (totalCount / sampledAnnotations.length)),
        overlapping: Math.round(overlappingEntities.length * (totalCount / sampledAnnotations.length))
      },
      issues
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
