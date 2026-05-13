require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const Note = require('./models/Note');
const transcribeAudio = require('./transcribe');
const { trimAudio } = require('./transcribe');
const searchService = require('./search');

const app = express();
const PORT = process.env.PORT || 5000;

const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
    const ext = path.extname(file.originalname);
    cb(null, `audio-${uniqueSuffix}${ext}`);
  }
});

const upload = multer({ storage, limits: { fileSize: 100 * 1024 * 1024 } });

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use('/uploads', express.static(uploadsDir));

mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('MongoDB 连接成功'))
  .catch(err => console.error('MongoDB 连接失败:', err));

app.get('/api/notes', async (req, res) => {
  try {
    const { keyword, limit = 20, skip = 0 } = req.query;

    if (keyword) {
      const results = await searchService.searchNotes(keyword, {
        limit: parseInt(limit),
        skip: parseInt(skip),
      });
      return res.json(results);
    }

    const notes = await Note.find().sort({ createdAt: -1 }).skip(parseInt(skip)).limit(parseInt(limit));
    const total = await Note.countDocuments();
    res.json({ notes, total, limit: parseInt(limit), skip: parseInt(skip) });
  } catch (error) {
    console.error('获取笔记失败:', error);
    res.status(500).json({ error: '获取笔记失败' });
  }
});

app.get('/api/notes/:id', async (req, res) => {
  try {
    const note = await Note.findById(req.params.id);
    if (!note) {
      return res.status(404).json({ error: '笔记不存在' });
    }
    res.json(note);
  } catch (error) {
    console.error('获取笔记失败:', error);
    res.status(500).json({ error: '获取笔记失败' });
  }
});

app.get('/api/notes/:id/search', async (req, res) => {
  try {
    const { keyword } = req.query;
    const results = await searchService.searchWithinNote(req.params.id, keyword);
    res.json(results);
  } catch (error) {
    console.error('搜索失败:', error);
    res.status(500).json({ error: error.message || '搜索失败' });
  }
});

app.post('/api/notes', upload.single('audio'), async (req, res) => {
  try {
    const { transcript } = req.body;
    let audioPath = null;
    let whisperTranscript = '';
    let transcriptionData = null;
    let duration = 0;

    if (req.file) {
      audioPath = `/uploads/${req.file.filename}`;

      if (process.env.OPENAI_API_KEY) {
        try {
          transcriptionData = await transcribeAudio(req.file.path, true);
          whisperTranscript = transcriptionData.text || '';
          duration = transcriptionData.duration || 0;
        } catch (error) {
          console.error('Whisper 转写失败:', error);
        }
      }
    }

    const note = new Note({
      transcript: transcript || '',
      whisperTranscript,
      audioPath,
      transcriptionData,
      duration,
    });

    const savedNote = await note.save();
    res.status(201).json(savedNote);
  } catch (error) {
    console.error('创建笔记失败:', error);
    res.status(500).json({ error: '创建笔记失败: ' + error.message });
  }
});

app.put('/api/notes/:id', async (req, res) => {
  try {
    const { transcript } = req.body;
    const note = await Note.findByIdAndUpdate(
      req.params.id,
      { transcript, updatedAt: Date.now() },
      { new: true }
    );

    if (!note) {
      return res.status(404).json({ error: '笔记不存在' });
    }

    res.json(note);
  } catch (error) {
    console.error('更新笔记失败:', error);
    res.status(500).json({ error: '更新笔记失败' });
  }
});

app.post('/api/notes/:id/trim', async (req, res) => {
  try {
    const { startTime, endTime } = req.body;
    const note = await Note.findById(req.params.id);

    if (!note) {
      return res.status(404).json({ error: '笔记不存在' });
    }

    if (!note.audioPath) {
      return res.status(400).json({ error: '笔记没有音频文件' });
    }

    const inputPath = path.join(__dirname, note.audioPath);
    if (!fs.existsSync(inputPath)) {
      return res.status(404).json({ error: '音频文件不存在' });
    }

    const ext = path.extname(note.audioPath);
    const trimmedFilename = `trimmed-${Date.now()}-${path.basename(note.audioPath, ext)}${ext}`;
    const outputPath = path.join(uploadsDir, trimmedFilename);

    await trimAudio(inputPath, outputPath, parseFloat(startTime), parseFloat(endTime));

    let newTranscriptionData = null;
    let newWhisperTranscript = '';
    let newDuration = parseFloat(endTime) - parseFloat(startTime);

    if (note.transcriptionData?.segments) {
      const filteredSegments = searchService.getSegmentsInRange(
        note.transcriptionData.segments,
        parseFloat(startTime),
        parseFloat(endTime)
      );

      const adjustedSegments = filteredSegments.map(seg => ({
        ...seg,
        start: seg.start - parseFloat(startTime),
        end: seg.end - parseFloat(startTime),
        words: (seg.words || []).map(w => ({
          ...w,
          start: w.start - parseFloat(startTime),
          end: w.end - parseFloat(startTime),
        })),
      }));

      newTranscriptionData = {
        text: adjustedSegments.map(s => s.text).join(' '),
        segments: adjustedSegments,
        duration: newDuration,
        language: note.transcriptionData.language,
      };
      newWhisperTranscript = newTranscriptionData.text;
    }

    const trimmedNote = new Note({
      transcript: newWhisperTranscript || note.transcript,
      whisperTranscript: newWhisperTranscript,
      audioPath: `/uploads/${trimmedFilename}`,
      transcriptionData: newTranscriptionData,
      duration: newDuration,
    });

    const savedTrimmedNote = await trimmedNote.save();
    res.status(201).json(savedTrimmedNote);
  } catch (error) {
    console.error('裁剪音频失败:', error);
    res.status(500).json({ error: '裁剪音频失败: ' + error.message });
  }
});

app.delete('/api/notes/:id', async (req, res) => {
  try {
    const note = await Note.findById(req.params.id);
    if (!note) {
      return res.status(404).json({ error: '笔记不存在' });
    }

    if (note.audioPath) {
      const fullPath = path.join(__dirname, note.audioPath);
      if (fs.existsSync(fullPath)) {
        try {
          fs.unlinkSync(fullPath);
        } catch (e) {
          console.warn('删除音频文件失败:', e);
        }
      }
    }

    await note.deleteOne();
    res.json({ message: '笔记已删除' });
  } catch (error) {
    console.error('删除笔记失败:', error);
    res.status(500).json({ error: '删除笔记失败' });
  }
});

app.post('/api/transcribe', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '请提供音频文件' });
    }

    if (!process.env.OPENAI_API_KEY) {
      return res.status(400).json({ error: '未配置 OpenAI API Key' });
    }

    const withTimestamps = req.query.timestamps === 'true';
    const result = await transcribeAudio(req.file.path, withTimestamps);

    if (withTimestamps) {
      res.json(result);
    } else {
      res.json({ transcript: result });
    }
  } catch (error) {
    console.error('转写失败:', error);
    res.status(500).json({ error: '转写失败: ' + error.message });
  }
});

app.get('/api/search', async (req, res) => {
  try {
    const { keyword, limit = 20, skip = 0 } = req.query;
    const results = await searchService.searchNotes(keyword, {
      limit: parseInt(limit),
      skip: parseInt(skip),
    });
    res.json(results);
  } catch (error) {
    console.error('搜索失败:', error);
    res.status(500).json({ error: '搜索失败' });
  }
});

app.listen(PORT, () => {
  console.log(`服务器运行在端口 ${PORT}`);
});