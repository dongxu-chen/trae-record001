const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

let testCases = [
  {
    id: uuidv4(),
    name: '邮箱验证示例',
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    testText: 'test@example.com, invalid-email, user.name@domain.org',
    createdAt: Date.now()
  },
  {
    id: uuidv4(),
    name: '手机号验证',
    pattern: '1[3-9]\\d{9}',
    testText: '13812345678, 12345678901, 15900001111',
    createdAt: Date.now()
  }
];

app.get('/api/test-cases', (req, res) => {
  res.json(testCases);
});

app.post('/api/test-cases', (req, res) => {
  const { name, pattern, testText } = req.body;
  const newTestCase = {
    id: uuidv4(),
    name,
    pattern,
    testText,
    createdAt: Date.now()
  };
  testCases.unshift(newTestCase);
  res.status(201).json(newTestCase);
});

app.put('/api/test-cases/:id', (req, res) => {
  const { id } = req.params;
  const { name, pattern, testText } = req.body;
  const index = testCases.findIndex(tc => tc.id === id);
  
  if (index === -1) {
    return res.status(404).json({ error: '测试用例不存在' });
  }
  
  testCases[index] = {
    ...testCases[index],
    name,
    pattern,
    testText,
    updatedAt: Date.now()
  };
  
  res.json(testCases[index]);
});

app.delete('/api/test-cases/:id', (req, res) => {
  const { id } = req.params;
  const index = testCases.findIndex(tc => tc.id === id);
  
  if (index === -1) {
    return res.status(404).json({ error: '测试用例不存在' });
  }
  
  testCases.splice(index, 1);
  res.json({ message: '删除成功' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
