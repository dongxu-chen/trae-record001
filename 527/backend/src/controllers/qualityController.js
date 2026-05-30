const QualityScore = require('../models/QualityScore');
const Annotation = require('../models/Annotation');
const Document = require('../models/Document');
const { checkConsistency } = require('./preAnnotateController');

exports.getQualityScores = async (req, res) => {
  try {
    const { taskId, period = 'all_time', sortBy = 'overallScore', limit = 100 } = req.query;
    
    const query = taskId ? { taskId } : {};
    
    let scores = await QualityScore.find(query)
      .sort({ [sortBy]: -1 })
      .limit(parseInt(limit));
    
    scores = scores.map((score, index) => ({
      ...score.toObject(),
      rank: index + 1
    }));
    
    res.json(scores);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getPersonalQuality = async (req, res) => {
  try {
    const { annotator, taskId } = req.query;
    
    const query = { annotator };
    if (taskId) query.taskId = taskId;
    
    const score = await QualityScore.findOne(query);
    
    if (!score) {
      return res.status(404).json({ error: 'Quality score not found' });
    }
    
    const allScores = await QualityScore.find({ taskId: score.taskId })
      .sort({ overallScore: -1 });
    
    const rank = allScores.findIndex(s => s.annotator === annotator) + 1;
    const totalAnnotators = allScores.length;
    
    const percentile = totalAnnotators > 0 
      ? Math.round((1 - (rank - 1) / totalAnnotators) * 100) 
      : 100;
    
    res.json({
      ...score.toObject(),
      rank,
      totalAnnotators,
      percentile
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.updateQualityScore = async (req, res) => {
  try {
    const { annotator, taskId, annotationStats, timeSpent, preAnnotateActions } = req.body;
    
    let score = await QualityScore.findOne({ annotator, taskId });
    
    if (!score) {
      score = new QualityScore({ annotator, taskId });
    }
    
    if (annotationStats) {
      score.entitiesAnnotated += annotationStats.entities || 0;
      score.relationsAnnotated += annotationStats.relations || 0;
      score.eventsAnnotated += annotationStats.events || 0;
      score.totalAnnotations += (annotationStats.entities || 0) + 
                                (annotationStats.relations || 0) + 
                                (annotationStats.events || 0);
    }
    
    if (timeSpent) {
      score.totalTimeSpent += timeSpent;
      const totalDocs = await countAnnotatedDocuments(annotator, taskId);
      if (totalDocs > 0) {
        score.avgTimePerDocument = Math.round(score.totalTimeSpent / totalDocs);
      }
    }
    
    if (preAnnotateActions) {
      const total = (preAnnotateActions.accepted || 0) + 
                    (preAnnotateActions.modified || 0) + 
                    (preAnnotateActions.rejected || 0);
      
      if (total > 0) {
        score.preAnnotateAcceptRate = Math.round((preAnnotateActions.accepted || 0) / total * 100);
        score.preAnnotateModifyRate = Math.round((preAnnotateActions.modified || 0) / total * 100);
        score.preAnnotateRejectRate = Math.round((preAnnotateActions.rejected || 0) / total * 100);
      }
    }
    
    score.accuracyScore = await calculateAccuracy(annotator, taskId);
    score.consistencyScore = await calculateConsistency(annotator, taskId);
    score.speedScore = calculateSpeedScore(score.avgTimePerDocument);
    score.overallScore = Math.round(
      score.accuracyScore * 0.4 + 
      score.consistencyScore * 0.3 + 
      score.speedScore * 0.3
    );
    
    score.lastActiveAt = Date.now();
    score.updatedAt = Date.now();
    
    await updateDailyWeeklyStats(score);
    await score.save();
    
    res.json(score);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getAnnotatorRankings = async (req, res) => {
  try {
    const { taskId, limit = 20 } = req.query;
    
    const scores = await QualityScore.find({ taskId })
      .sort({ overallScore: -1 })
      .limit(parseInt(limit));
    
    const rankings = scores.map((score, index) => ({
      rank: index + 1,
      annotator: score.annotator,
      overallScore: score.overallScore,
      accuracyScore: score.accuracyScore,
      consistencyScore: score.consistencyScore,
      totalAnnotations: score.totalAnnotations,
      previousRank: score.previousRank || index + 1
    }));
    
    res.json({
      rankings,
      totalAnnotators: await QualityScore.countDocuments({ taskId }),
      lastUpdated: new Date()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getQualityTrends = async (req, res) => {
  try {
    const { annotator, taskId, type = 'daily' } = req.query;
    
    const score = await QualityScore.findOne({ annotator, taskId });
    
    if (!score) {
      return res.json({ trends: [], labels: [] });
    }
    
    const stats = type === 'weekly' ? score.weeklyStats : score.dailyStats;
    const trends = stats.slice(-30);
    
    res.json({
      labels: trends.map(s => type === 'weekly' ? s.week : s.date),
      annotations: trends.map(s => s.annotations),
      scores: trends.map(s => s.avgScore)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

async function countAnnotatedDocuments(annotator, taskId) {
  const docs = await Document.find({ taskId, status: 'annotated', annotatedBy: annotator });
  return docs.length;
}

async function calculateAccuracy(annotator, taskId) {
  const annotations = await Annotation.find({ taskId, annotatedBy: annotator })
    .populate('documentId', 'text');
  
  if (annotations.length === 0) return 0;
  
  let score = 0;
  annotations.forEach(ann => {
    const entityCount = ann.entities?.length || 0;
    const relationCount = ann.relations?.length || 0;
    const eventCount = ann.events?.length || 0;
    const total = entityCount + relationCount + eventCount;
    
    if (total > 0) {
      const hasOverlapping = checkOverlappingEntities(ann.entities || []);
      if (!hasOverlapping) score += 10;
      
      const validRelations = validateRelations(ann.relations || [], ann.entities || []);
      score += validRelations * 5;
    }
    
    score += Math.min(20, total * 0.5);
  });
  
  return Math.min(100, Math.round(score / annotations.length * 5));
}

async function calculateConsistency(annotator, taskId) {
  try {
    const consistencyCheck = await checkConsistency({
      query: { taskId, sampleSize: 20, annotator, sampleStrategy: 'recent' }
    }, {}, true);
    
    if (consistencyCheck && consistencyCheck.issues) {
      const totalChecked = consistencyCheck.totalDocuments || 1;
      const issues = consistencyCheck.issues.length || 0;
      return Math.max(0, Math.round((1 - issues / totalChecked) * 100));
    }
    return 75;
  } catch (error) {
    return 75;
  }
}

function calculateSpeedScore(avgTimePerDocument) {
  if (!avgTimePerDocument || avgTimePerDocument === 0) return 50;
  
  if (avgTimePerDocument < 30) return 100;
  if (avgTimePerDocument < 60) return 90;
  if (avgTimePerDocument < 120) return 80;
  if (avgTimePerDocument < 180) return 70;
  if (avgTimePerDocument < 300) return 60;
  return 50;
}

function checkOverlappingEntities(entities) {
  for (let i = 0; i < entities.length; i++) {
    for (let j = i + 1; j < entities.length; j++) {
      const a = entities[i];
      const b = entities[j];
      if ((a.start <= b.start && b.start < a.end) || 
          (b.start <= a.start && a.start < b.end)) {
        return true;
      }
    }
  }
  return false;
}

function validateRelations(relations, entities) {
  let validCount = 0;
  const entityIds = new Set(entities.map(e => e.id));
  
  relations.forEach(rel => {
    if (entityIds.has(rel.sourceId) && entityIds.has(rel.targetId)) {
      validCount++;
    }
  });
  
  return validCount;
}

async function updateDailyWeeklyStats(score) {
  const today = new Date().toISOString().split('T')[0];
  const weekKey = getWeekKey(new Date());
  
  const dailyIndex = score.dailyStats.findIndex(s => s.date === today);
  if (dailyIndex >= 0) {
    score.dailyStats[dailyIndex].annotations = score.totalAnnotations;
    score.dailyStats[dailyIndex].avgScore = score.overallScore;
  } else {
    score.dailyStats.push({
      date: today,
      annotations: score.totalAnnotations,
      avgScore: score.overallScore
    });
  }
  
  const weeklyIndex = score.weeklyStats.findIndex(s => s.week === weekKey);
  if (weeklyIndex >= 0) {
    score.weeklyStats[weeklyIndex].annotations = score.totalAnnotations;
    score.weeklyStats[weeklyIndex].avgScore = score.overallScore;
  } else {
    score.weeklyStats.push({
      week: weekKey,
      annotations: score.totalAnnotations,
      avgScore: score.overallScore
    });
  }
  
  if (score.dailyStats.length > 90) {
    score.dailyStats = score.dailyStats.slice(-90);
  }
  if (score.weeklyStats.length > 52) {
    score.weeklyStats = score.weeklyStats.slice(-52);
  }
}

function getWeekKey(date) {
  const d = new Date(date);
  const year = d.getFullYear();
  const weekNum = Math.ceil((((d - new Date(year, 0, 1)) / 86400000) + new Date(year, 0, 1).getDay() + 1) / 7);
  return `${year}-W${weekNum.toString().padStart(2, '0')}`;
}
