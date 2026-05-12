const express = require('express');
const fs = require('fs');
const path = require('path');
const router = express.Router();

const SNAPSHOT_DIR = path.join(__dirname, '..', 'snapshots');
const LOG_DIR = path.join(__dirname, '..', 'logs');

if (!fs.existsSync(SNAPSHOT_DIR)) {
  fs.mkdirSync(SNAPSHOT_DIR, { recursive: true });
}

if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

const ANTI_CHEAT_LOG_FILE = path.join(LOG_DIR, 'anti_cheat.log');
const PROCTOR_LOG_FILE = path.join(LOG_DIR, 'proctor.log');

function getTimestamp() {
  return new Date().toISOString();
}

function formatLogEntry(entry) {
  return `${getTimestamp()} | ${JSON.stringify(entry)}\n`;
}

function appendLog(filePath, entry) {
  const logLine = formatLogEntry(entry);
  fs.appendFileSync(filePath, logLine);
}

function base64ToImage(base64Data, filePath) {
  const base64Image = base64Data.split(';base64,').pop();
  fs.writeFileSync(filePath, base64Image, { encoding: 'base64' });
}

function getStudentDir(examId, studentName) {
  const dir = path.join(
    SNAPSHOT_DIR, 
    `exam_${examId}`, 
    studentName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_')
  );
  
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  
  return dir;
}

router.post('/snapshot', (req, res) => {
  const { examId, studentName, imageData, timestamp } = req.body;

  if (!examId || !studentName || !imageData) {
    return res.status(400).json({ error: '缺少必要参数' });
  }

  try {
    const studentDir = getStudentDir(examId, studentName);
    const safeTimestamp = (timestamp || getTimestamp()).replace(/[:.]/g, '-');
    const fileName = `snapshot_${safeTimestamp}.jpg`;
    const filePath = path.join(studentDir, fileName);

    base64ToImage(imageData, filePath);

    const logEntry = {
      type: 'snapshot',
      examId,
      studentName,
      fileName,
      timestamp: timestamp || getTimestamp(),
      size: fs.statSync(filePath).size
    };

    appendLog(PROCTOR_LOG_FILE, logEntry);

    res.json({ 
      success: true, 
      message: '快照已保存',
      fileName
    });
  } catch (err) {
    console.error('快照保存失败:', err);
    appendLog(PROCTOR_LOG_FILE, {
      type: 'error',
      error: 'snapshot_save_failed',
      message: err.message,
      timestamp: getTimestamp()
    });
    res.status(500).json({ error: '快照保存失败' });
  }
});

router.post('/event', (req, res) => {
  const { examId, studentName, eventType, eventData, severity, timestamp } = req.body;

  if (!examId || !studentName || !eventType) {
    return res.status(400).json({ error: '缺少必要参数' });
  }

  try {
    const logEntry = {
      examId,
      studentName,
      eventType,
      eventData: eventData || null,
      severity: severity || 'info',
      timestamp: timestamp || getTimestamp()
    };

    appendLog(ANTI_CHEAT_LOG_FILE, logEntry);

    const isViolation = ['warning', 'danger'].includes(severity) || 
      eventType.includes('violation') ||
      eventType.includes('attempt') ||
      eventType.includes('switch');

    if (isViolation) {
      appendLog(PROCTOR_LOG_FILE, {
        type: 'violation',
        ...logEntry
      });
    }

    res.json({ success: true, message: '事件已记录' });
  } catch (err) {
    console.error('事件记录失败:', err);
    res.status(500).json({ error: '事件记录失败' });
  }
});

function analyzeAntiCheatLog(examId, studentName) {
  if (!fs.existsSync(ANTI_CHEAT_LOG_FILE)) {
    return { totalEvents: 0, violations: 0, events: [] };
  }

  const logContent = fs.readFileSync(ANTI_CHEAT_LOG_FILE, 'utf-8');
  const lines = logContent.trim().split('\n').filter(line => line.trim());

  const events = [];
  let violationCount = 0;

  lines.forEach(line => {
    try {
      const pipeIndex = line.indexOf('|');
      if (pipeIndex === -1) return;

      const jsonPart = line.substring(pipeIndex + 1).trim();
      const entry = JSON.parse(jsonPart);

      if (examId && entry.examId !== examId) return;
      if (studentName && entry.studentName !== studentName) return;

      events.push(entry);

      if (['warning', 'danger'].includes(entry.severity)) {
        violationCount++;
      }
    } catch (e) {
      console.warn('解析日志行失败:', e.message);
    }
  });

  events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const eventTypeCounts = {};
  events.forEach(e => {
    eventTypeCounts[e.eventType] = (eventTypeCounts[e.eventType] || 0) + 1;
  });

  return {
    totalEvents: events.length,
    violations: violationCount,
    eventTypeCounts,
    events
  };
}

router.get('/analytics', (req, res) => {
  const { examId, studentName } = req.query;

  try {
    const analysis = analyzeAntiCheatLog(examId, studentName);

    res.json({
      success: true,
      examId,
      studentName,
      analysis
    });
  } catch (err) {
    console.error('日志分析失败:', err);
    res.status(500).json({ error: '日志分析失败' });
  }
});

router.get('/analysis/:examId/:studentName', (req, res) => {
  const { examId, studentName } = req.params;

  try {
    const analysis = analyzeAntiCheatLog(examId, studentName);

    const violationThreshold = 5;
    const riskLevel = analysis.violations >= violationThreshold ? 'high' :
                      analysis.violations >= 2 ? 'medium' : 'low';

    const recommendations = [];
    if (analysis.eventTypeCounts['tab_switch']) {
      recommendations.push(`检测到 ${analysis.eventTypeCounts['tab_switch']} 次标签页切换`);
    }
    if (analysis.eventTypeCounts['copy_attempt'] || analysis.eventTypeCounts['paste_attempt']) {
      recommendations.push('检测到复制/粘贴操作尝试');
    }
    if (analysis.eventTypeCounts['devtools_attempt']) {
      recommendations.push('检测到开发者工具打开尝试');
    }

    res.json({
      success: true,
      examId,
      studentName,
      summary: {
        totalEvents: analysis.totalEvents,
        totalViolations: analysis.violations,
        riskLevel,
        violationThreshold
      },
      eventBreakdown: analysis.eventTypeCounts,
      recommendations,
      timeline: analysis.events.slice(-50)
    });
  } catch (err) {
    console.error('考生分析失败:', err);
    res.status(500).json({ error: '考生分析失败' });
  }
});

router.get('/logs', (req, res) => {
  const { type = 'anti_cheat', limit = 100 } = req.query;

  try {
    const logFile = type === 'proctor' ? PROCTOR_LOG_FILE : ANTI_CHEAT_LOG_FILE;
    
    if (!fs.existsSync(logFile)) {
      return res.json({ logs: [] });
    }

    const logContent = fs.readFileSync(logFile, 'utf-8');
    const lines = logContent.trim().split('\n').filter(line => line.trim());
    const recentLines = lines.slice(-parseInt(limit));

    const logs = recentLines.map(line => {
      try {
        const pipeIndex = line.indexOf('|');
        if (pipeIndex === -1) return null;

        const timestamp = line.substring(0, pipeIndex).trim();
        const jsonPart = line.substring(pipeIndex + 1).trim();
        const entry = JSON.parse(jsonPart);

        return {
          timestamp,
          ...entry
        };
      } catch (e) {
        return null;
      }
    }).filter(Boolean);

    res.json({ logs });
  } catch (err) {
    console.error('日志读取失败:', err);
    res.status(500).json({ error: '日志读取失败' });
  }
});

module.exports = router;
