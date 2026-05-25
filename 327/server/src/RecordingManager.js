import { spawn } from 'child_process';
import { WebSocketServer } from 'ws';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const RECORDINGS_DIR = path.join(__dirname, '../recordings');

if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

class RecordingSession {
  constructor(roomId, layout = 'grid') {
    this.roomId = roomId;
    this.id = uuidv4();
    this.layout = layout;
    this.startTime = null;
    this.endTime = null;
    this.isActive = false;
    this.streams = new Map();
    this.ffmpegProcess = null;
    this.outputPath = null;
    this.wsServer = null;
    this.wsPort = 0;
    this.compositionCanvas = null;
    this.compositionSize = { width: 1920, height: 1080 };
  }

  async start() {
    if (this.isActive) return false;

    this.startTime = Date.now();
    this.isActive = true;
    this.outputPath = path.join(
      RECORDINGS_DIR,
      `${this.roomId}-${Date.now()}.mp4`
    );

    this.wsServer = new WebSocketServer({ port: 0 });
    
    await new Promise((resolve) => {
      this.wsServer.on('listening', () => {
        this.wsPort = this.wsServer.address().port;
        resolve();
      });
    });

    this.wsServer.on('connection', (ws, req) => {
      const url = new URL(req.url, 'http://localhost');
      const participantId = url.searchParams.get('participantId');
      
      if (participantId) {
        this.streams.set(participantId, {
          ws,
          buffer: [],
          isReady: false,
          lastData: null
        });

        ws.on('message', (data) => {
          const stream = this.streams.get(participantId);
          if (stream) {
            stream.buffer.push(data);
            stream.lastData = data;
            if (stream.buffer.length > 60) {
              stream.buffer.shift();
            }
            if (!stream.isReady) {
              stream.isReady = true;
            }
          }
        });

        ws.on('close', () => {
          this.streams.delete(participantId);
        });

        ws.on('error', (err) => {
          console.error(`WebSocket error for ${participantId}:`, err);
        });
      }
    });

    await this._startFFmpeg();
    
    console.log(`Recording started for room ${this.roomId}, WS port: ${this.wsPort}`);
    return {
      recordingId: this.id,
      wsPort: this.wsPort,
      outputPath: this.outputPath
    };
  }

  async _startFFmpeg() {
    const activeStreams = Array.from(this.streams.keys());
    const streamCount = Math.max(1, activeStreams.length);
    
    const layout = this._calculateLayout(streamCount);
    
    const ffmpegArgs = [
      '-y',
      '-f', 'lavfi',
      '-i', `color=c=black:s=${this.compositionSize.width}x${this.compositionSize.height}:r=30`,
    ];

    for (let i = 0; i < Math.min(streamCount, 9); i++) {
      ffmpegArgs.push(
        '-f', 'lavfi',
        '-i', `testsrc=duration=3600:size=640x360:rate=30,format=yuv420p`
      );
    }

    const filterComplex = this._buildFilterComplex(streamCount, layout);
    
    if (filterComplex) {
      ffmpegArgs.push('-filter_complex', filterComplex);
      ffmpegArgs.push('-map', '[out]');
    }

    ffmpegArgs.push(
      '-c:v', 'libx264',
      '-preset', 'veryfast',
      '-crf', '23',
      '-pix_fmt', 'yuv420p',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-ar', '44100',
      '-ac', '2',
      '-movflags', '+faststart',
      this.outputPath
    );

    return new Promise((resolve, reject) => {
      this.ffmpegProcess = spawn('ffmpeg', ffmpegArgs, {
        stdio: ['ignore', 'pipe', 'pipe']
      });

      this.ffmpegProcess.stdout.on('data', (data) => {
      });

      this.ffmpegProcess.stderr.on('data', (data) => {
      });

      this.ffmpegProcess.on('error', (err) => {
        console.error('FFmpeg error:', err);
        reject(err);
      });

      this.ffmpegProcess.on('exit', (code, signal) => {
        console.log(`FFmpeg exited with code ${code}, signal ${signal}`);
        this.isActive = false;
      });

      setTimeout(resolve, 1000);
    });
  }

  _calculateLayout(streamCount) {
    if (streamCount <= 1) {
      return [{ x: 0, y: 0, width: 1920, height: 1080 }];
    } else if (streamCount <= 2) {
      return [
        { x: 0, y: 0, width: 960, height: 1080 },
        { x: 960, y: 0, width: 960, height: 1080 }
      ];
    } else if (streamCount <= 4) {
      return [
        { x: 0, y: 0, width: 960, height: 540 },
        { x: 960, y: 0, width: 960, height: 540 },
        { x: 0, y: 540, width: 960, height: 540 },
        { x: 960, y: 540, width: 960, height: 540 }
      ];
    } else if (streamCount <= 6) {
      return [
        { x: 0, y: 0, width: 640, height: 540 },
        { x: 640, y: 0, width: 640, height: 540 },
        { x: 1280, y: 0, width: 640, height: 540 },
        { x: 0, y: 540, width: 640, height: 540 },
        { x: 640, y: 540, width: 640, height: 540 },
        { x: 1280, y: 540, width: 640, height: 540 }
      ];
    } else {
      const cols = 3;
      const rows = Math.ceil(streamCount / cols);
      const cellWidth = Math.floor(this.compositionSize.width / cols);
      const cellHeight = Math.floor(this.compositionSize.height / rows);
      const layout = [];

      for (let i = 0; i < streamCount && i < 9; i++) {
        const col = i % cols;
        const row = Math.floor(i / cols);
        layout.push({
          x: col * cellWidth,
          y: row * cellHeight,
          width: cellWidth,
          height: cellHeight
        });
      }
      return layout;
    }
  }

  _buildFilterComplex(streamCount, layout) {
    if (streamCount === 0) return null;

    const parts = [];
    
    for (let i = 0; i < Math.min(streamCount, 9); i++) {
      const pos = layout[i] || { x: 0, y: 0, width: 640, height: 360 };
      parts.push(
        `[${i + 1}:v]scale=${pos.width}:${pos.height},setpts=PTS-STARTPTS[vid${i}]`
      );
    }

    let overlay = '[0:v]';
    for (let i = 0; i < Math.min(streamCount, 9); i++) {
      const pos = layout[i] || { x: 0, y: 0, width: 640, height: 360 };
      const prev = i === 0 ? '' : `[tmp${i - 1}]`;
      const next = i === Math.min(streamCount, 9) - 1 ? '[out]' : `[tmp${i}]`;
      
      if (i === 0) {
        parts.push(
          `[0:v][vid${i}]overlay=x=${pos.x}:y=${pos.y}${next}`
        );
      } else {
        parts.push(
          `${prev}[vid${i}]overlay=x=${pos.x}:y=${pos.y}${next}`
        );
      }
    }

    return parts.join(';');
  }

  addStream(participantId, participantInfo) {
    if (!this.streams.has(participantId)) {
      this.streams.set(participantId, {
        ...participantInfo,
        buffer: [],
        isReady: false,
        joinedAt: Date.now()
      });
    }
  }

  removeStream(participantId) {
    this.streams.delete(participantId);
  }

  async stop() {
    if (!this.isActive) return null;

    this.isActive = false;
    this.endTime = Date.now();

    if (this.ffmpegProcess && this.ffmpegProcess.stdin) {
      try {
        this.ffmpegProcess.stdin.write('q');
      } catch (e) {
      }
    }

    await new Promise((resolve) => {
      if (!this.ffmpegProcess) {
        resolve();
        return;
      }
      
      const timeout = setTimeout(() => {
        if (this.ffmpegProcess) {
          this.ffmpegProcess.kill('SIGKILL');
        }
        resolve();
      }, 5000);

      this.ffmpegProcess.on('exit', () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    if (this.wsServer) {
      this.wsServer.close();
      this.wsServer = null;
    }

    this.streams.clear();

    const duration = this.endTime - this.startTime;
    const fileSize = fs.existsSync(this.outputPath) 
      ? fs.statSync(this.outputPath).size 
      : 0;

    return {
      recordingId: this.id,
      roomId: this.roomId,
      outputPath: this.outputPath,
      filename: path.basename(this.outputPath),
      startTime: this.startTime,
      endTime: this.endTime,
      duration,
      fileSize,
      participantCount: this.streams.size
    };
  }

  getStats() {
    return {
      id: this.id,
      roomId: this.roomId,
      isActive: this.isActive,
      startTime: this.startTime,
      duration: this.startTime ? Date.now() - this.startTime : 0,
      streamCount: this.streams.size,
      streamIds: Array.from(this.streams.keys()),
      outputPath: this.outputPath
    };
  }
}

class RecordingManager {
  constructor() {
    this.sessions = new Map();
  }

  startRecording(roomId, layout = 'grid') {
    if (this.sessions.has(roomId)) {
      return { success: false, error: 'Recording already in progress' };
    }

    const session = new RecordingSession(roomId, layout);
    this.sessions.set(roomId, session);

    return session.start()
      .then((result) => ({
        success: true,
        ...result
      }))
      .catch((error) => {
        this.sessions.delete(roomId);
        return { success: false, error: error.message };
      });
  }

  stopRecording(roomId) {
    const session = this.sessions.get(roomId);
    if (!session) {
      return { success: false, error: 'No recording in progress' };
    }

    return session.stop()
      .then((result) => {
        this.sessions.delete(roomId);
        return { success: true, ...result };
      });
  }

  getRecordingSession(roomId) {
    return this.sessions.get(roomId) || null;
  }

  isRecording(roomId) {
    const session = this.sessions.get(roomId);
    return session?.isActive || false;
  }

  addParticipantStream(roomId, participantId, participantInfo) {
    const session = this.sessions.get(roomId);
    if (session) {
      session.addStream(participantId, participantInfo);
    }
  }

  removeParticipantStream(roomId, participantId) {
    const session = this.sessions.get(roomId);
    if (session) {
      session.removeStream(participantId);
    }
  }

  getRecordingStats(roomId) {
    const session = this.sessions.get(roomId);
    return session ? session.getStats() : null;
  }

  getAllSessions() {
    return Array.from(this.sessions.entries()).map(([roomId, session]) => ({
      roomId,
      ...session.getStats()
    }));
  }

  getRecordingFilePath(filename) {
    const filePath = path.join(RECORDINGS_DIR, filename);
    if (fs.existsSync(filePath)) {
      return filePath;
    }
    return null;
  }

  listRecordings() {
    if (!fs.existsSync(RECORDINGS_DIR)) return [];
    
    return fs.readdirSync(RECORDINGS_DIR)
      .filter(file => file.endsWith('.mp4') || file.endsWith('.webm'))
      .map(file => {
        const stats = fs.statSync(path.join(RECORDINGS_DIR, file));
        return {
          filename: file,
          size: stats.size,
          createdAt: stats.birthtime.getTime(),
          url: `/api/recordings/${file}`
        };
      })
      .sort((a, b) => b.createdAt - a.createdAt);
  }

  deleteRecording(filename) {
    const filePath = path.join(RECORDINGS_DIR, filename);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      return true;
    }
    return false;
  }
}

export default RecordingManager;
