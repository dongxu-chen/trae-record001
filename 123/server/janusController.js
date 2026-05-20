const express = require('express');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const router = express.Router();

const RECORDINGS_DIR = path.join(__dirname, '..', 'janus', 'recordings');
const JANUS_API_URL = 'http://localhost:8088/janus';

if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

const recordingsMetadata = new Map();

function parseFilename(filename) {
  const match = filename.match(/exam_(\d+)_(\d+)_(\d+)_(webcam|screen)\.(mjr|webm)/);
  if (match) {
    return {
      examId: match[1],
      userId: match[2],
      timestamp: parseInt(match[3]),
      streamType: match[4] === 'webcam' ? 'camera' : 'screen'
    };
  }
  return null;
}

function getFileInfo(filePath) {
  try {
    const stats = fs.statSync(filePath);
    return {
      size: stats.size,
      createdAt: stats.birthtime,
      modifiedAt: stats.mtime
    };
  } catch (error) {
    return null;
  }
}

router.get('/recordings', (req, res) => {
  try {
    const files = fs.readdirSync(RECORDINGS_DIR);
    const recordings = [];
    
    files.forEach((file, index) => {
      const filePath = path.join(RECORDINGS_DIR, file);
      const fileInfo = getFileInfo(filePath);
      const parsed = parseFilename(file);
      
      if (fileInfo && (file.endsWith('.mjr') || file.endsWith('.webm'))) {
        const recording = {
          id: `rec_${index}_${Date.now()}`,
          filename: file,
          size: fileInfo.size,
          createdAt: fileInfo.createdAt,
          duration: recordingsMetadata.get(file)?.duration || 0,
          examId: parsed?.examId || '',
          userId: parsed?.userId || '',
          userName: recordingsMetadata.get(file)?.userName || '',
          streamType: parsed?.streamType || 'unknown'
        };
        recordings.push(recording);
      }
    });
    
    recordings.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    
    res.json({
      success: true,
      recordings,
      total: recordings.length
    });
  } catch (error) {
    console.error('获取录制列表失败:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

router.get('/recordings/:id/play', (req, res) => {
  try {
    const { id } = req.params;
    const files = fs.readdirSync(RECORDINGS_DIR);
    
    let targetFile = null;
    for (const file of files) {
      if (file.includes(id.split('_')[1])) {
        targetFile = file;
        break;
      }
    }
    
    if (!targetFile) {
      return res.status(404).json({
        success: false,
        error: '录制文件不存在'
      });
    }
    
    const filePath = path.join(RECORDINGS_DIR, targetFile);
    
    if (targetFile.endsWith('.mjr')) {
      const webmFile = targetFile.replace('.mjr', '.webm');
      const webmPath = path.join(RECORDINGS_DIR, webmFile);
      
      if (!fs.existsSync(webmPath)) {
        const convertCmd = `janus-pp-rec ${filePath} ${webmPath}`;
        exec(convertCmd, (error) => {
          if (error) {
            console.error('转换录制文件失败:', error);
          }
          if (fs.existsSync(webmPath)) {
            res.sendFile(webmPath);
          } else {
            res.sendFile(filePath);
          }
        });
        return;
      }
      res.sendFile(webmPath);
    } else {
      res.sendFile(filePath);
    }
  } catch (error) {
    console.error('播放录制失败:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

router.get('/recordings/:id/download', (req, res) => {
  try {
    const { id } = req.params;
    const files = fs.readdirSync(RECORDINGS_DIR);
    
    let targetFile = null;
    for (const file of files) {
      if (file.includes(id.split('_')[1])) {
        targetFile = file;
        break;
      }
    }
    
    if (!targetFile) {
      return res.status(404).json({
        success: false,
        error: '录制文件不存在'
      });
    }
    
    const filePath = path.join(RECORDINGS_DIR, targetFile);
    res.download(filePath);
  } catch (error) {
    console.error('下载录制失败:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

router.delete('/recordings/:id', (req, res) => {
  try {
    const { id } = req.params;
    const files = fs.readdirSync(RECORDINGS_DIR);
    
    let deleted = false;
    files.forEach(file => {
      if (file.includes(id.split('_')[1])) {
        const filePath = path.join(RECORDINGS_DIR, file);
        fs.unlinkSync(filePath);
        deleted = true;
      }
    });
    
    if (deleted) {
      res.json({
        success: true,
        message: '删除成功'
      });
    } else {
      res.status(404).json({
        success: false,
        error: '录制文件不存在'
      });
    }
  } catch (error) {
    console.error('删除录制失败:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

router.get('/status', async (req, res) => {
  try {
    const fetch = await import('node-fetch').then(mod => mod.default);
    const response = await fetch(`${JANUS_API_URL}/info`);
    const data = await response.json();
    
    const files = fs.readdirSync(RECORDINGS_DIR);
    const totalSize = files.reduce((acc, file) => {
      const filePath = path.join(RECORDINGS_DIR, file);
      try {
        return acc + fs.statSync(filePath).size;
      } catch {
        return acc;
      }
    }, 0);
    
    res.json({
      success: true,
      janus: {
        version: data.version,
        name: data.name,
        author: data.author
      },
      recordings: {
        count: files.length,
        totalSize
      }
    });
  } catch (error) {
    console.error('获取Janus状态失败:', error);
    res.status(500).json({
      success: false,
      error: 'Janus服务未连接',
      janus: { connected: false },
      recordings: { count: 0, totalSize: 0 }
    });
  }
});

router.post('/room/create', async (req, res) => {
  try {
    const { roomId, description, secret, publishers } = req.body;
    
    const fetch = await import('node-fetch').then(mod => mod.default);
    
    const janusSession = await fetch(JANUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'create',
        transaction: `create_${Date.now()}`
      })
    }).then(r => r.json());
    
    if (janusSession.janus !== 'success') {
      throw new Error('创建Janus会话失败');
    }
    
    const sessionId = janusSession.data.id;
    
    const attachResponse = await fetch(`${JANUS_API_URL}/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'attach',
        plugin: 'janus.plugin.videoroom',
        transaction: `attach_${Date.now()}`
      })
    }).then(r => r.json());
    
    if (attachResponse.janus !== 'success') {
      throw new Error('附加插件失败');
    }
    
    const handleId = attachResponse.data.id;
    
    const createRoomResponse = await fetch(`${JANUS_API_URL}/${sessionId}/${handleId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'message',
        body: {
          request: 'create',
          room: roomId || 1234567890,
          description: description || '在线考试监控房间',
          secret: secret || 'exam-room-secret-2024',
          publishers: publishers || 10000,
          bitrate: 512000,
          record: true,
          rec_dir: '/usr/local/share/janus/recordings',
          allow_multiple_publishers_per_user: true,
          max_publishers_per_user: 2
        },
        transaction: `create_room_${Date.now()}`
      })
    }).then(r => r.json());
    
    res.json({
      success: true,
      room: createRoomResponse.plugindata.data
    });
  } catch (error) {
    console.error('创建房间失败:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

router.get('/room/:roomId/list', async (req, res) => {
  try {
    const { roomId } = req.params;
    const fetch = await import('node-fetch').then(mod => mod.default);
    
    const janusSession = await fetch(JANUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'create',
        transaction: `list_${Date.now()}`
      })
    }).then(r => r.json());
    
    const sessionId = janusSession.data.id;
    
    const attachResponse = await fetch(`${JANUS_API_URL}/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'attach',
        plugin: 'janus.plugin.videoroom',
        transaction: `attach_${Date.now()}`
      })
    }).then(r => r.json());
    
    const handleId = attachResponse.data.id;
    
    const listResponse = await fetch(`${JANUS_API_URL}/${sessionId}/${handleId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        janus: 'message',
        body: {
          request: 'listparticipants',
          room: parseInt(roomId)
        },
        transaction: `list_participants_${Date.now()}`
      })
    }).then(r => r.json());
    
    res.json({
      success: true,
      participants: listResponse.plugindata.data.participants || []
    });
  } catch (error) {
    console.error('获取参与者列表失败:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      participants: []
    });
  }
});

module.exports = router;
