import express from 'express';
import cors from 'cors';
import multer from 'multer';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

const storage = multer.memoryStorage();
const upload = multer({ storage });

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: '数据映射工具API服务运行中' });
});

app.post('/api/convert', upload.single('file'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '未上传文件' });
    }

    res.json({
      success: true,
      message: '文件接收成功',
      fileName: req.file.originalname,
      fileSize: req.file.size,
    });
  } catch (error) {
    res.status(500).json({ error: '处理文件时出错' });
  }
});

app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
});
