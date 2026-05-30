const { AchievementDefinition, UserAchievement, Leaderboard } = require('../models/Achievement');
const QualityScore = require('../models/QualityScore');

const DEFAULT_ACHIEVEMENTS = [
  { id: 'first_annotation', name: '初次标注', description: '完成第一条标注', category: 'annotation', icon: '✨', points: 10, rarity: 'common', requirement: { type: 'annotations', value: 1 } },
  { id: 'annotations_10', name: '新手起步', description: '完成10条标注', category: 'annotation', icon: '🌱', points: 20, rarity: 'common', requirement: { type: 'annotations', value: 10 } },
  { id: 'annotations_50', name: '渐入佳境', description: '完成50条标注', category: 'annotation', icon: '📝', points: 50, rarity: 'common', requirement: { type: 'annotations', value: 50 } },
  { id: 'annotations_100', name: '标注达人', description: '完成100条标注', category: 'annotation', icon: '🏅', points: 100, rarity: 'rare', requirement: { type: 'annotations', value: 100 } },
  { id: 'annotations_500', name: '标注大师', description: '完成500条标注', category: 'annotation', icon: '🎖️', points: 250, rarity: 'epic', requirement: { type: 'annotations', value: 500 } },
  { id: 'annotations_1000', name: '标注传奇', description: '完成1000条标注', category: 'annotation', icon: '👑', points: 500, rarity: 'legendary', requirement: { type: 'annotations', value: 1000 } },
  
  { id: 'entities_10', name: '实体捕手', description: '标注10个实体', category: 'annotation', icon: '🎯', points: 15, rarity: 'common', requirement: { type: 'entities', value: 10 } },
  { id: 'entities_100', name: '实体猎手', description: '标注100个实体', category: 'annotation', icon: '🏹', points: 80, rarity: 'rare', requirement: { type: 'entities', value: 100 } },
  { id: 'relations_10', name: '关系探索者', description: '标注10条关系', category: 'annotation', icon: '🔗', points: 20, rarity: 'common', requirement: { type: 'relations', value: 10 } },
  { id: 'relations_50', name: '关系专家', description: '标注50条关系', category: 'annotation', icon: '🕸️', points: 60, rarity: 'rare', requirement: { type: 'relations', value: 50 } },
  
  { id: 'accuracy_80', name: '准确达人', description: '准确率达到80%', category: 'quality', icon: '🎯', points: 50, rarity: 'rare', requirement: { type: 'accuracy', value: 80 } },
  { id: 'accuracy_90', name: '精准大师', description: '准确率达到90%', category: 'quality', icon: '💎', points: 100, rarity: 'epic', requirement: { type: 'accuracy', value: 90 } },
  { id: 'accuracy_95', name: '完美主义', description: '准确率达到95%', category: 'quality', icon: '🏆', points: 200, rarity: 'legendary', requirement: { type: 'accuracy', value: 95 } },
  
  { id: 'consistency_80', name: '始终如一', description: '一致性得分达到80%', category: 'quality', icon: '⚖️', points: 50, rarity: 'rare', requirement: { type: 'consistency', value: 80 } },
  { id: 'consistency_95', name: '稳如磐石', description: '一致性得分达到95%', category: 'quality', icon: '🗿', points: 150, rarity: 'epic', requirement: { type: 'consistency', value: 95 } },
  
  { id: 'streak_3', name: '三天坚持', description: '连续3天标注', category: 'streak', icon: '🔥', points: 30, rarity: 'common', requirement: { type: 'streak', value: 3 } },
  { id: 'streak_7', name: '一周达人', description: '连续7天标注', category: 'streak', icon: '⚡', points: 70, rarity: 'rare', requirement: { type: 'streak', value: 7 } },
  { id: 'streak_30', name: '月度冠军', description: '连续30天标注', category: 'streak', icon: '🌟', points: 300, rarity: 'epic', requirement: { type: 'streak', value: 30 } },
  
  { id: 'template_5', name: '模板新手', description: '使用5次标注模板', category: 'special', icon: '📋', points: 25, rarity: 'common', requirement: { type: 'templates_used', value: 5 } },
  { id: 'template_20', name: '模板达人', description: '使用20次标注模板', category: 'special', icon: '📚', points: 80, rarity: 'rare', requirement: { type: 'templates_used', value: 20 } },
  
  { id: 'speed_30s', name: '闪电手速', description: '平均每篇文档标注时间少于30秒', category: 'speed', icon: '⚡', points: 60, rarity: 'rare', requirement: { type: 'speed', value: 30 } },
  { id: 'speed_1min', name: '手速达人', description: '平均每篇文档标注时间少于1分钟', category: 'speed', icon: '🚀', points: 40, rarity: 'common', requirement: { type: 'speed', value: 60 } }
];

exports.initializeDefaultAchievements = async () => {
  try {
    const existing = await AchievementDefinition.countDocuments();
    if (existing === 0) {
      await AchievementDefinition.insertMany(DEFAULT_ACHIEVEMENTS);
      console.log('Default achievements initialized');
    }
  } catch (error) {
    console.error('Error initializing achievements:', error);
  }
};

exports.getAllAchievements = async (req, res) => {
  try {
    const { category, isGlobal } = req.query;
    
    const query = {};
    if (category) query.category = category;
    if (isGlobal !== undefined) query.isGlobal = isGlobal === 'true';
    
    const achievements = await AchievementDefinition.find(query)
      .sort({ points: 1 });
    
    res.json(achievements);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getUserAchievements = async (req, res) => {
  try {
    const { annotator, taskId } = req.query;
    
    const query = { annotator };
    if (taskId) query.taskId = taskId;
    
    const userAchievements = await UserAchievement.find(query);
    const achievementDefs = await AchievementDefinition.find();
    
    const achievementsWithProgress = achievementDefs.map(def => {
      const userProgress = userAchievements.find(ua => ua.achievementId === def.id);
      const progress = userProgress?.progress || 0;
      const unlocked = userProgress?.unlocked || false;
      const progressPercent = Math.min(100, Math.round((progress / def.requirement.value) * 100));
      
      return {
        ...def.toObject(),
        progress,
        progressPercent,
        unlocked,
        unlockedAt: userProgress?.unlockedAt
      };
    }).sort((a, b) => {
      if (a.unlocked && !b.unlocked) return -1;
      if (!a.unlocked && b.unlocked) return 1;
      if (a.progressPercent !== b.progressPercent) return b.progressPercent - a.progressPercent;
      return a.points - b.points;
    });
    
    const totalPoints = achievementsWithProgress
      .filter(a => a.unlocked)
      .reduce((sum, a) => sum + a.points, 0);
    
    res.json({
      achievements: achievementsWithProgress,
      totalPoints,
      unlockedCount: achievementsWithProgress.filter(a => a.unlocked).length,
      totalCount: achievementsWithProgress.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.updateAchievementProgress = async (req, res) => {
  try {
    const { annotator, taskId, updates } = req.body;
    
    const newlyUnlocked = [];
    
    for (const update of updates) {
      const { type, value } = update;
      
      const achievements = await AchievementDefinition.find({
        'requirement.type': type,
        'requirement.taskId': { $in: [null, taskId] }
      });
      
      for (const def of achievements) {
        let userAch = await UserAchievement.findOne({
          achievementId: def.id,
          annotator,
          taskId
        });
        
        if (!userAch) {
          userAch = new UserAchievement({
            achievementId: def.id,
            annotator,
            taskId,
            progress: 0,
            unlocked: false
          });
        }
        
        if (!userAch.unlocked) {
          userAch.progress = value;
          userAch.updatedAt = Date.now();
          
          if (userAch.progress >= def.requirement.value) {
            userAch.unlocked = true;
            userAch.unlockedAt = Date.now();
            newlyUnlocked.push({
              achievement: def,
              unlockedAt: userAch.unlockedAt
            });
          }
          
          await userAch.save();
        }
      }
    }
    
    res.json({
      message: 'Progress updated',
      newlyUnlocked,
      updatedCount: updates.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getLeaderboard = async (req, res) => {
  try {
    const { taskId, period = 'all_time', limit = 20 } = req.query;
    
    let leaderboard = await Leaderboard.findOne({ taskId, period });
    
    const shouldRefresh = !leaderboard || 
      (Date.now() - leaderboard.createdAt.getTime()) > 3600000;
    
    if (shouldRefresh) {
      leaderboard = await generateLeaderboard(taskId, period, parseInt(limit));
    }
    
    const rankings = leaderboard.rankings.slice(0, parseInt(limit)).map((r, index) => ({
      ...r,
      rank: index + 1,
      previousRank: r.previousRank || index + 1,
      rankChange: (r.previousRank || index + 1) - (index + 1)
    }));
    
    res.json({
      period,
      rankings,
      totalParticipants: leaderboard.rankings.length,
      lastUpdated: leaderboard.createdAt
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

async function generateLeaderboard(taskId, period, limit) {
  const scores = await QualityScore.find({ taskId })
    .sort({ overallScore: -1 });
  
  const { startDate, endDate } = getPeriodDates(period);
  
  const rankings = await Promise.all(
    scores.slice(0, limit * 2).map(async (score, index) => {
      const periodStats = getPeriodStats(score, startDate, endDate);
      
      let totalPoints = 0;
      const userAchievements = await UserAchievement.find({
        annotator: score.annotator,
        taskId,
        unlocked: true
      });
      
      for (const ua of userAchievements) {
        const def = await AchievementDefinition.findOne({ id: ua.achievementId });
        if (def) totalPoints += def.points;
      }
      
      return {
        annotator: score.annotator,
        score: score.overallScore,
        annotations: periodStats.annotations || score.totalAnnotations,
        accuracy: score.accuracyScore,
        consistency: score.consistencyScore,
        totalPoints,
        rank: index + 1,
        previousRank: index + 1
      };
    })
  );
  
  rankings.sort((a, b) => {
    if (b.totalPoints !== a.totalPoints) return b.totalPoints - a.totalPoints;
    if (b.score !== a.score) return b.score - a.score;
    return b.annotations - a.annotations;
  });
  
  rankings.forEach((r, i) => r.rank = i + 1);
  
  let leaderboard = await Leaderboard.findOne({ taskId, period });
  
  if (leaderboard) {
    const previousRankings = leaderboard.rankings.reduce((acc, r) => {
      acc[r.annotator] = r.rank;
      return acc;
    }, {});
    
    rankings.forEach(r => {
      r.previousRank = previousRankings[r.annotator] || r.rank;
    });
    
    leaderboard.rankings = rankings;
    leaderboard.startDate = startDate;
    leaderboard.endDate = endDate;
    leaderboard.createdAt = new Date();
  } else {
    leaderboard = new Leaderboard({
      taskId,
      period,
      rankings,
      startDate,
      endDate
    });
  }
  
  await leaderboard.save();
  return leaderboard;
}

function getPeriodDates(period) {
  const now = new Date();
  const endDate = new Date(now);
  
  let startDate;
  switch (period) {
    case 'daily':
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      break;
    case 'weekly':
      startDate = new Date(now);
      startDate.setDate(now.getDate() - 7);
      break;
    case 'monthly':
      startDate = new Date(now.getFullYear(), now.getMonth(), 1);
      break;
    case 'all_time':
    default:
      startDate = new Date(0);
      break;
  }
  
  return { startDate, endDate };
}

function getPeriodStats(score, startDate, endDate) {
  const dailyStats = score.dailyStats?.filter(s => {
    const d = new Date(s.date);
    return d >= startDate && d <= endDate;
  }) || [];
  
  return {
    annotations: dailyStats.reduce((sum, s) => sum + s.annotations, 0),
    avgScore: dailyStats.length > 0
      ? dailyStats.reduce((sum, s) => sum + s.avgScore, 0) / dailyStats.length
      : 0
  };
}

exports.checkAchievements = async (annotator, taskId, annotationStats) => {
  const updates = [];
  
  const score = await QualityScore.findOne({ annotator, taskId });
  if (!score) return [];
  
  const totalAnnotations = score.totalAnnotations;
  if (totalAnnotations > 0) {
    updates.push({ type: 'annotations', value: totalAnnotations });
    updates.push({ type: 'entities', value: score.entitiesAnnotated });
    updates.push({ type: 'relations', value: score.relationsAnnotated });
  }
  
  if (score.accuracyScore > 0) {
    updates.push({ type: 'accuracy', value: score.accuracyScore });
  }
  
  if (score.consistencyScore > 0) {
    updates.push({ type: 'consistency', value: score.consistencyScore });
  }
  
  if (score.avgTimePerDocument > 0) {
    updates.push({ type: 'speed', value: Math.max(0, 300 - score.avgTimePerDocument) });
  }
  
  const req = { body: { annotator, taskId, updates } };
  const res = { json: () => {} };
  
  try {
    await exports.updateAchievementProgress(req, res);
  } catch (error) {
    console.error('Error checking achievements:', error);
  }
  
  return [];
};

exports.getAnnotatorSummary = async (req, res) => {
  try {
    const { annotator, taskId } = req.query;
    
    const score = await QualityScore.findOne({ annotator, taskId });
    const userAchievements = await UserAchievement.find({ annotator, taskId, unlocked: true });
    const allAchievements = await AchievementDefinition.find();
    
    const totalPoints = userAchievements.reduce((sum, ua) => {
      const def = allAchievements.find(a => a.id === ua.achievementId);
      return sum + (def?.points || 0);
    }, 0);
    
    const allScores = await QualityScore.find({ taskId }).sort({ overallScore: -1 });
    const rank = allScores.findIndex(s => s.annotator === annotator) + 1;
    
    res.json({
      annotator,
      overallScore: score?.overallScore || 0,
      totalAnnotations: score?.totalAnnotations || 0,
      totalPoints,
      rank,
      totalAnnotators: allScores.length,
      achievementsCount: userAchievements.length,
      totalAchievementsCount: allAchievements.length,
      recentAchievements: userAchievements
        .sort((a, b) => (b.unlockedAt || b.createdAt) - (a.unlockedAt || a.createdAt))
        .slice(0, 5)
        .map(ua => {
          const def = allAchievements.find(a => a.id === ua.achievementId);
          return def ? {
            ...def.toObject(),
            unlockedAt: ua.unlockedAt
          } : null;
        })
        .filter(Boolean)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
