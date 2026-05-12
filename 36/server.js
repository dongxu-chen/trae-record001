const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = 3000;
const JWT_SECRET = 'offline-diary-secret-key-change-in-production';

app.use(cors());
app.use(express.json());
app.use(express.static('./'));

const users = new Map();
const diaries = new Map();
const chunkBuffer = new Map();

users.set('demo@example.com', {
  id: 'user-demo-001',
  email: 'demo@example.com',
  name: '演示用户',
  password: bcrypt.hashSync('password123', 10),
  createdAt: new Date().toISOString()
});

function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email },
    JWT_SECRET,
    { expiresIn: '7d' }
  );
}

function verifyToken(req, res, next) {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ message: '未授权' });
  }

  const token = authHeader.split(' ')[1];

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ message: 'Token 无效' });
  }
}

app.post('/api/auth/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ message: '请填写完整信息' });
    }

    if (password.length < 6) {
      return res.status(400).json({ message: '密码至少6位' });
    }

    if (users.has(email)) {
      return res.status(400).json({ message: '邮箱已被注册' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = `user-${uuidv4()}`;

    const user = {
      id: userId,
      email,
      name,
      password: hashedPassword,
      createdAt: new Date().toISOString()
    };

    users.set(email, user);

    const token = generateToken(user);

    res.status(201).json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        token
      },
      message: '注册成功'
    });
  } catch (error) {
    console.error('注册错误:', error);
    res.status(500).json({ message: '服务器错误' });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ message: '请填写邮箱和密码' });
    }

    const user = users.get(email);
    
    if (!user) {
      return res.status(401).json({ message: '邮箱或密码错误' });
    }

    const isValid = await bcrypt.compare(password, user.password);
    
    if (!isValid) {
      return res.status(401).json({ message: '邮箱或密码错误' });
    }

    const token = generateToken(user);

    res.json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        token
      },
      message: '登录成功'
    });
  } catch (error) {
    console.error('登录错误:', error);
    res.status(500).json({ message: '服务器错误' });
  }
});

app.get('/api/auth/me', verifyToken, (req, res) => {
  const user = Array.from(users.values()).find(u => u.id === req.user.id);
  
  if (!user) {
    return res.status(404).json({ message: '用户不存在' });
  }

  res.json({
    id: user.id,
    email: user.email,
    name: user.name
  });
});

app.get('/api/diaries', verifyToken, (req, res) => {
  const userDiaries = Array.from(diaries.values())
    .filter(d => d.userId === req.user.id)
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

  res.json(userDiaries);
});

app.post('/api/diaries', verifyToken, (req, res) => {
  try {
    const { id, title, content, createdAt, updatedAt } = req.body;

    if (!title && !content) {
      return res.status(400).json({ message: '日记内容不能为空' });
    }

    const now = new Date().toISOString();
    const diaryId = id || `diary-${uuidv4()}`;

    const existingDiary = diaries.get(diaryId);
    
    if (existingDiary && existingDiary.userId !== req.user.id) {
      return res.status(403).json({ message: '无权限' });
    }

    const diary = {
      id: diaryId,
      userId: req.user.id,
      title: title || '无标题',
      content: content || '',
      createdAt: existingDiary?.createdAt || createdAt || now,
      updatedAt: updatedAt || now,
      synced: true
    };

    diaries.set(diaryId, diary);

    res.status(201).json(diary);
  } catch (error) {
    console.error('保存日记错误:', error);
    res.status(500).json({ message: '服务器错误' });
  }
});

app.delete('/api/diaries/:id', verifyToken, (req, res) => {
  try {
    const diaryId = req.params.id;
    const diary = diaries.get(diaryId);

    if (!diary) {
      return res.status(404).json({ message: '日记不存在' });
    }

    if (diary.userId !== req.user.id) {
      return res.status(403).json({ message: '无权限' });
    }

    diaries.delete(diaryId);
    res.json({ message: '删除成功' });
  } catch (error) {
    console.error('删除日记错误:', error);
    res.status(500).json({ message: '服务器错误' });
  }
});

app.post('/api/diaries/chunk', verifyToken, async (req, res) => {
  try {
    const { chunkId, chunkIndex, chunkCount, diaryId, data, action } = req.body;

    if (!chunkId || chunkIndex === undefined || !chunkCount || !data) {
      return res.status(400).json({ message: '缺少必要参数' });
    }

    const bufferKey = `${req.user.id}_${chunkId}`;
    
    if (!chunkBuffer.has(bufferKey)) {
      chunkBuffer.set(bufferKey, {
        chunks: [],
        chunkCount,
        diaryId,
        action,
        userId: req.user.id,
        createdAt: Date.now()
      });
    }

    const buffer = chunkBuffer.get(bufferKey);
    buffer.chunks[chunkIndex] = data;

    const receivedCount = buffer.chunks.filter(Boolean).length;
    
    if (receivedCount === chunkCount) {
      try {
        const fullData = buffer.chunks.join('');
        const diary = JSON.parse(fullData);
        
        const now = new Date().toISOString();
        const finalDiaryId = diary.id || diaryId || `diary-${uuidv4()}`;
        
        const existingDiary = diaries.get(finalDiaryId);
        
        if (existingDiary && existingDiary.userId !== req.user.id) {
          chunkBuffer.delete(bufferKey);
          return res.status(403).json({ message: '无权限' });
        }

        const finalDiary = {
          ...diary,
          id: finalDiaryId,
          userId: req.user.id,
          updatedAt: now,
          synced: true,
          createdAt: existingDiary?.createdAt || diary.createdAt || now
        };

        diaries.set(finalDiaryId, finalDiary);
        chunkBuffer.delete(bufferKey);

        console.log(`[Chunk] 日记组装完成: ${finalDiaryId}`);
        res.json({ 
          message: '分块上传完成',
          diaryId: finalDiaryId
        });
      } catch (parseError) {
        chunkBuffer.delete(bufferKey);
        console.error('[Chunk] 解析失败:', parseError);
        res.status(500).json({ message: '数据解析失败' });
      }
    } else {
      res.json({
        message: '分块已接收',
        received: receivedCount,
        total: chunkCount
      });
    }
  } catch (error) {
    console.error('分块上传错误:', error);
    res.status(500).json({ message: '服务器错误' });
  }
});

setInterval(() => {
  const now = Date.now();
  const timeout = 30 * 60 * 1000;
  
  for (const [key, buffer] of chunkBuffer.entries()) {
    if (now - buffer.createdAt > timeout) {
      console.log(`[Chunk] 清理超时的分块: ${key}`);
      chunkBuffer.delete(key);
    }
  }
}, 5 * 60 * 1000);

app.listen(PORT, () => {
  console.log(`\n========================================`);
  console.log(`  离线日记本服务器已启动`);
  console.log(`========================================`);
  console.log(`  访问地址: http://localhost:${PORT}`);
  console.log(`  API 地址: http://localhost:${PORT}/api`);
  console.log(`\n  演示账户:`);
  console.log(`    邮箱: demo@example.com`);
  console.log(`    密码: password123`);
  console.log(`\n  提示: 首次访问请在浏览器中注册新账户`);
  console.log(`========================================\n`);
});
