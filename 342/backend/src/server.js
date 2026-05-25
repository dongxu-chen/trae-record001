const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');
const {
  generatePseudocode,
  generatePlantUML,
  generateStateMachine,
  generatePython,
  generateJava,
  generateGo,
  generateJavaScript,
  generateCode,
  generateAllLanguages,
  generateUnitTests,
} = require('./codeGenerator');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

const UPLOAD_DIR = path.join(__dirname, '..', 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, _file, cb) => cb(null, `${uuidv4()}.png`),
});

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowed = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/webp'];
    if (allowed.includes(file.mimetype)) cb(null, true);
    else cb(new Error('不支持的文件类型，仅支持 PNG/JPEG/BMP/WebP'));
  },
});

function runPythonScript(imagePath) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, '..', 'python', 'process_flowchart.py');
    const pythonExe = process.env.PYTHON_PATH || 'D:\\Software\\Python\\Install\\python.exe';

    execFile(pythonExe, [scriptPath, imagePath], { maxBuffer: 50 * 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) {
        console.error('Python script error:', err.message);
        console.error('Stderr:', stderr);
        return reject(new Error('图像处理失败：' + (stderr || err.message)));
      }
      try {
        const result = JSON.parse(stdout);
        resolve(result);
      } catch (parseErr) {
        console.error('JSON parse error:', parseErr.message);
        console.error('Raw stdout:', stdout.slice(0, 500));
        reject(new Error('解析处理结果失败'));
      }
    });
  });
}

function generateAllCode(flowchartData) {
  return {
    pseudocode: generatePseudocode(flowchartData),
    plantuml: generatePlantUML(flowchartData),
    stateMachine: generateStateMachine(flowchartData),
    python: generatePython(flowchartData),
    java: generateJava(flowchartData),
    go: generateGo(flowchartData),
    javascript: generateJavaScript(flowchartData),
    tests: {
      python: generateUnitTests(flowchartData, 'python'),
      java: generateUnitTests(flowchartData, 'java'),
      go: generateUnitTests(flowchartData, 'go'),
      javascript: generateUnitTests(flowchartData, 'javascript'),
    },
  };
}

app.post('/api/process', upload.single('image'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: '请上传图片文件' });
  }

  const imagePath = req.file.path;
  console.log('Processing image:', imagePath);

  try {
    const flowchartData = await runPythonScript(imagePath);

    if (!flowchartData.nodes || flowchartData.nodes.length === 0) {
      return res.status(200).json({
        warning: '未检测到有效的流程图节点，请确保图片清晰且包含标准流程图符号',
        nodes: [],
        edges: [],
        pseudocode: '',
        plantuml: '',
        stateMachine: '',
        python: '',
        java: '',
        go: '',
        javascript: '',
        tests: {},
      });
    }

    const allCode = generateAllCode(flowchartData);

    res.json({
      nodes: flowchartData.nodes,
      edges: flowchartData.edges,
      ...allCode,
    });
  } catch (error) {
    console.error('Processing failed:', error);
    res.status(500).json({ error: error.message });
  } finally {
    setTimeout(() => {
      fs.unlink(imagePath, (err) => {
        if (err) console.error('Failed to delete temp file:', err);
      });
    }, 5000);
  }
});

app.post('/api/regenerate', async (req, res) => {
  try {
    const { nodes, edges, language } = req.body;

    if (!nodes || !Array.isArray(nodes) || nodes.length === 0) {
      return res.status(400).json({ error: '请提供有效的节点数据' });
    }

    const flowchartData = {
      nodes,
      edges: edges || [],
    };

    console.log(`Regenerating code for ${nodes.length} nodes, language: ${language || 'all'}`);

    if (language && language !== 'all') {
      const code = generateCode(flowchartData, language);
      const tests = language !== 'pseudocode' && language !== 'plantuml'
        ? generateUnitTests(flowchartData, language)
        : '';
      return res.json({
        code,
        tests,
        language,
      });
    }

    const allCode = generateAllCode(flowchartData);
    res.json({
      nodes,
      edges: edges || [],
      ...allCode,
    });
  } catch (error) {
    console.error('Regenerate failed:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/generate-test', async (req, res) => {
  try {
    const { nodes, edges, language } = req.body;

    if (!nodes || !Array.isArray(nodes)) {
      return res.status(400).json({ error: '请提供有效的节点数据' });
    }

    const flowchartData = {
      nodes,
      edges: edges || [],
    };

    const testCode = generateUnitTests(flowchartData, language || 'javascript');
    res.json({
      tests: testCode,
      language: language || 'javascript',
    });
  } catch (error) {
    console.error('Generate test failed:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Flowchart2Code backend running on http://localhost:${PORT}`);
});
