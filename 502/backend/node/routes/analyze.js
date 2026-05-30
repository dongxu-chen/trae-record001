const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const EventEmitter = require('events');

const analysisEvents = new EventEmitter();
analysisEvents.setMaxListeners(100);

const PYTHON_DIR = path.resolve(__dirname, '../../python');
const UPLOAD_DIR = path.resolve(__dirname, '../../../uploads');

const analysisStatus = new Map();

function getPythonPath() {
    return process.platform === 'win32' ? 'python' : 'python3';
}

function runPythonCommand(args) {
    return new Promise((resolve, reject) => {
        const python = getPythonPath();
        const proc = spawn(python, [path.join(PYTHON_DIR, 'main.py'), ...args], {
            cwd: PYTHON_DIR,
            env: { ...process.env }
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
            console.log('[Python]', data.toString().trim());
        });

        proc.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python process exited with code ${code}: ${stderr}`));
            } else {
                try {
                    const result = JSON.parse(stdout.trim());
                    resolve(result);
                } catch (e) {
                    reject(new Error(`Failed to parse Python output: ${stdout}`));
                }
            }
        });

        proc.on('error', (err) => {
            reject(new Error(`Failed to start Python process: ${err.message}`));
        });
    });
}

function setupAnalysisRoutes(app) {
    app.post('/api/analyze/:videoId', async (req, res) => {
        const { videoId } = req.params;
        const options = req.body || {};

        const metaPath = path.join(UPLOAD_DIR, `${videoId}.json`);
        if (!fs.existsSync(metaPath)) {
            return res.status(404).json({ error: 'Video not found' });
        }

        const videoInfo = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));

        if (analysisStatus.has(videoId) && analysisStatus.get(videoId).status === 'processing') {
            return res.status(409).json({ error: 'Analysis already in progress' });
        }

        const statusObj = { status: 'processing', progress: 0, videoId };
        analysisStatus.set(videoId, statusObj);

        res.json({
            success: true,
            message: 'Analysis started',
            videoId
        });

        try {
            analysisEvents.emit('progress', { videoId, status: 'processing', progress: 10, message: 'Extracting frames...' });

            const result = await runPythonCommand([
                'analyze',
                videoInfo.path,
                JSON.stringify(options)
            ]);

            if (result.error) {
                statusObj.status = 'error';
                statusObj.error = result.error;
                analysisEvents.emit('progress', { videoId, status: 'error', error: result.error });
            } else {
                statusObj.status = 'completed';
                statusObj.progress = 100;
                statusObj.result = result;

                const resultPath = path.join(UPLOAD_DIR, `${videoId}_analysis.json`);
                fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));

                analysisEvents.emit('progress', { videoId, status: 'completed', progress: 100, result });
            }
        } catch (err) {
            console.error('Analysis error:', err);
            statusObj.status = 'error';
            statusObj.error = err.message;
            analysisEvents.emit('progress', { videoId, status: 'error', error: err.message });
        }
    });

    app.get('/api/analyze/:videoId/status', (req, res) => {
        const { videoId } = req.params;

        const status = analysisStatus.get(videoId);
        if (!status) {
            const resultPath = path.join(UPLOAD_DIR, `${videoId}_analysis.json`);
            if (fs.existsSync(resultPath)) {
                const result = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
                return res.json({ success: true, status: 'completed', result });
            }
            return res.json({ success: true, status: 'not_started' });
        }

        res.json({
            success: true,
            status: status.status,
            progress: status.progress,
            result: status.result,
            error: status.error
        });
    });

    app.get('/api/analyze/:videoId/result', (req, res) => {
        const { videoId } = req.params;

        const resultPath = path.join(UPLOAD_DIR, `${videoId}_analysis.json`);
        if (!fs.existsSync(resultPath)) {
            return res.status(404).json({ error: 'Analysis result not found' });
        }

        const result = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
        res.json({ success: true, result });
    });

    app.get('/api/analyze/:videoId/events', (req, res) => {
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        const { videoId } = req.params;

        const listener = (data) => {
            if (data.videoId === videoId) {
                res.write(`data: ${JSON.stringify(data)}\n\n`);
                if (data.status === 'completed' || data.status === 'error') {
                    res.end();
                }
            }
        };

        analysisEvents.on('progress', listener);

        const current = analysisStatus.get(videoId);
        if (current) {
            res.write(`data: ${JSON.stringify(current)}\n\n`);
            if (current.status === 'completed' || current.status === 'error') {
                res.end();
            }
        }

        req.on('close', () => {
            analysisEvents.off('progress', listener);
        });
    });
}

module.exports = { setupAnalysisRoutes, analysisEvents };
