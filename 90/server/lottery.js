const express = require('express');
const cors = require('cors');
const path = require('path');
const Database = require('better-sqlite3');

const app = express();
const PORT = 3000;
const DAILY_LIMIT = 3;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'client')));

const dbPath = path.join(__dirname, 'prize.db');
const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('busy_timeout = 5000');
db.pragma('synchronous = NORMAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS prizes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    probability REAL NOT NULL,
    color TEXT NOT NULL,
    total_count INTEGER DEFAULT 0,
    remaining_count INTEGER DEFAULT 0,
    user_max INTEGER DEFAULT -1
  );

  CREATE TABLE IF NOT EXISTS lottery_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    draw_uuid TEXT UNIQUE,
    prize_id INTEGER,
    prize_name TEXT,
    prize_color TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prize_id) REFERENCES prizes(id)
  );

  CREATE INDEX IF NOT EXISTS idx_user_date ON lottery_records(user_id, DATE(created_at));
  CREATE INDEX IF NOT EXISTS idx_uuid ON lottery_records(draw_uuid);
  CREATE INDEX IF NOT EXISTS idx_user_prize ON lottery_records(user_id, prize_id);
  CREATE INDEX IF NOT EXISTS idx_created_at ON lottery_records(created_at DESC);
`);

const prizes = [
  { id: 1, name: '一等奖', probability: 0.01, color: '#FF6B6B', total_count: 1, remaining_count: 1, user_max: 1 },
  { id: 2, name: '二等奖', probability: 0.05, color: '#4ECDC4', total_count: 5, remaining_count: 5, user_max: 1 },
  { id: 3, name: '三等奖', probability: 0.1, color: '#45B7D1', total_count: 10, remaining_count: 10, user_max: 2 },
  { id: 4, name: '四等奖', probability: 0.15, color: '#96CEB4', total_count: 20, remaining_count: 20, user_max: -1 },
  { id: 5, name: '五等奖', probability: 0.2, color: '#FFEAA7', total_count: 50, remaining_count: 50, user_max: -1 },
  { id: 6, name: '谢谢参与', probability: 0.49, color: '#DFE6E9', total_count: -1, remaining_count: -1, user_max: -1 }
];

const insertPrizeStmt = db.prepare(
  'INSERT INTO prizes (id, name, probability, color, total_count, remaining_count, user_max) VALUES (?, ?, ?, ?, ?, ?, ?)'
);
const checkColsStmt = db.prepare('PRAGMA table_info(prizes)');
const cols = checkColsStmt.all();
const hasUserMax = cols.some(c => c.name === 'user_max');
if (!hasUserMax) {
  db.exec('ALTER TABLE prizes ADD COLUMN user_max INTEGER DEFAULT -1');
}

const initPrizesStmt = db.prepare('SELECT COUNT(*) as count FROM prizes');
if (initPrizesStmt.get().count === 0) {
  prizes.forEach(p => insertPrizeStmt.run(p.id, p.name, p.probability, p.color, p.total_count, p.remaining_count, p.user_max));
}

const getPrizesForUserStmt = db.prepare(`
  SELECT p.* FROM prizes p
  WHERE (p.remaining_count > 0 OR p.remaining_count = -1)
  AND (
    p.user_max = -1
    OR (
      SELECT COUNT(*) FROM lottery_records r
      WHERE r.user_id = ? AND r.prize_id = p.id
    ) < p.user_max
  )
  ORDER BY p.id
`);

const getAllPrizesStmt = db.prepare('SELECT id, name, probability, color, total_count, remaining_count, user_max FROM prizes ORDER BY id');

function drawPrize(userId) {
  const availablePrizes = getPrizesForUserStmt.all(userId);

  if (availablePrizes.length === 0) {
    return null;
  }

  const totalProbability = availablePrizes.reduce((sum, p) => sum + p.probability, 0);
  const random = Math.random() * totalProbability;

  let cumulative = 0;
  for (const prize of availablePrizes) {
    cumulative += prize.probability;
    if (random <= cumulative) {
      return prize;
    }
  }

  return availablePrizes[availablePrizes.length - 1];
}

app.get('/api/prizes', (req, res) => {
  const allPrizes = getAllPrizesStmt.all();
  res.json(allPrizes);
});

const decrementStmt = db.prepare(
  'UPDATE prizes SET remaining_count = remaining_count - 1 WHERE id = ? AND (remaining_count > 0 OR remaining_count = -1)'
);

const insertRecordStmt = db.prepare(
  'INSERT INTO lottery_records (user_id, draw_uuid, prize_id, prize_name, prize_color) VALUES (?, ?, ?, ?, ?)'
);

const countUserTodayStmt = db.prepare(
  'SELECT COUNT(*) as count FROM lottery_records WHERE user_id = ? AND DATE(created_at) = DATE("now")'
);

const countByUuidStmt = db.prepare(
  'SELECT * FROM lottery_records WHERE draw_uuid = ?'
);

const getPrizeIndexStmt = db.prepare(
  'SELECT COUNT(*) as count FROM prizes WHERE id < ?'
);

const getPrizeByIdStmt = db.prepare(
  'SELECT id, name, color FROM prizes WHERE id = ?'
);

app.post('/api/draw', (req, res) => {
  const { userId, drawUuid } = req.body;
  const user_id = userId || 'anonymous';
  const uuid = drawUuid || null;

  if (uuid) {
    const existing = countByUuidStmt.get(uuid);
    if (existing) {
      const prize = getPrizeByIdStmt.get(existing.prize_id);
      const prizeIndex = getPrizeIndexStmt.get(existing.prize_id).count;
      const todayCount = countUserTodayStmt.get(user_id).count;
      return res.json({
        prize: { id: prize.id, name: prize.name, color: prize.color, index: prizeIndex },
        remainingDraws: Math.max(0, DAILY_LIMIT - todayCount),
        isDuplicate: true
      });
    }
  }

  try {
    db.exec('BEGIN IMMEDIATE TRANSACTION');

    const todayRecords = countUserTodayStmt.get(user_id);
    if (todayRecords.count >= DAILY_LIMIT) {
      db.exec('ROLLBACK');
      return res.status(429).json({ error: `今日抽奖次数已用完（每天最多${DAILY_LIMIT}次）` });
    }

    const prize = drawPrize(user_id);
    if (!prize) {
      db.exec('ROLLBACK');
      return res.status(404).json({ error: '奖品已全部抽完，或您已达到可获奖上限' });
    }

    let updateResult;
    if (prize.remaining_count !== -1) {
      updateResult = decrementStmt.run(prize.id);
      if (updateResult.changes === 0) {
        db.exec('ROLLBACK');
        return res.status(404).json({ error: '该奖品已抽完，请重试' });
      }
    }

    insertRecordStmt.run(user_id, uuid, prize.id, prize.name, prize.color);

    const prizeIndex = getPrizeIndexStmt.get(prize.id).count;
    const remainingDraws = DAILY_LIMIT - todayRecords.count - 1;

    db.exec('COMMIT');

    res.json({
      prize: {
        id: prize.id,
        name: prize.name,
        color: prize.color,
        index: prizeIndex
      },
      remainingDraws
    });
  } catch (error) {
    try { db.exec('ROLLBACK'); } catch (e) {}
    console.error('抽奖失败:', error);
    res.status(500).json({ error: '系统繁忙，请稍后重试' });
  }
});

app.get('/api/records', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit) || 50, 200);
  const records = db.prepare(
    'SELECT id, user_id, prize_id, prize_name, prize_color, created_at FROM lottery_records ORDER BY created_at DESC LIMIT ?'
  ).all(limit);
  res.json(records);
});

app.get('/api/records/wins', (req, res) => {
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const records = db.prepare(`
    SELECT id, user_id, prize_id, prize_name, prize_color, created_at
    FROM lottery_records
    WHERE prize_name != '谢谢参与'
    ORDER BY created_at DESC
    LIMIT ?
  `).all(limit);
  res.json(records);
});

app.post('/api/admin/reset-inventory', (req, res) => {
  const { password, prizeId } = req.body;
  const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

  if (password !== ADMIN_PASSWORD) {
    return res.status(403).json({ error: '密码错误' });
  }

  try {
    db.exec('BEGIN IMMEDIATE TRANSACTION');

    if (prizeId) {
      const prize = db.prepare('SELECT total_count FROM prizes WHERE id = ?').get(prizeId);
      if (!prize) {
        db.exec('ROLLBACK');
        return res.status(404).json({ error: '奖品不存在' });
      }
      db.prepare('UPDATE prizes SET remaining_count = total_count WHERE id = ?').run(prizeId);
    } else {
      db.prepare('UPDATE prizes SET remaining_count = total_count WHERE total_count != -1').run();
    }

    db.exec('COMMIT');
    res.json({ success: true, message: prizeId ? `奖品 ${prizeId} 库存已重置` : '所有奖品库存已重置' });
  } catch (error) {
    try { db.exec('ROLLBACK'); } catch (e) {}
    console.error('重置库存失败:', error);
    res.status(500).json({ error: '重置库存失败' });
  }
});

app.get('/api/admin/stats', (req, res) => {
  const prizes = getAllPrizesStmt.all();
  const totalDraws = db.prepare('SELECT COUNT(*) as count FROM lottery_records').get().count;
  const todayDraws = db.prepare("SELECT COUNT(*) as count FROM lottery_records WHERE DATE(created_at) = DATE('now')").get().count;

  res.json({
    prizes,
    totalDraws,
    todayDraws
  });
});

app.listen(PORT, () => {
  console.log(`抽奖转盘服务已启动: http://localhost:${PORT}`);
  console.log(`管理页面: http://localhost:${PORT}/admin.html`);
  console.log(`数据库路径: ${dbPath}`);
  console.log(`默认管理密码: admin123`);
});
