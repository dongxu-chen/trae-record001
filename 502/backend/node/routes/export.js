const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const PYTHON_DIR = path.resolve(__dirname, '../../python');
const UPLOAD_DIR = path.resolve(__dirname, '../../../uploads');
const EXPORT_DIR = path.resolve(__dirname, '../../../exports');

function getPythonPath() {
    return process.platform === 'win32' ? 'python' : 'python3';
}

function runPythonCommand(args) {
    return new Promise((resolve, reject) => {
        const python = getPythonPath();
        const proc = spawn(python, [path.join(PYTHON_DIR, 'main.py'), ...args], {
            cwd: PYTHON_DIR
        });

        let stdout = '';
        let stderr = '';

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python process exited with code ${code}: ${stderr}`));
            } else {
                try {
                    const result = JSON.parse(stdout.trim());
                    resolve(result);
                } catch (e) {
                    resolve({ success: true, raw: stdout.trim() });
                }
            }
        });

        proc.on('error', (err) => {
            reject(new Error(`Failed to start Python process: ${err.message}`));
        });
    });
}

function setupExportRoutes(app) {
    app.post('/api/compile', async (req, res) => {
        const { videoId, highlights, options } = req.body;

        if (!videoId || !highlights || !Array.isArray(highlights) || highlights.length === 0) {
            return res.status(400).json({ error: 'videoId and highlights array are required' });
        }

        const metaPath = path.join(UPLOAD_DIR, `${videoId}.json`);
        if (!fs.existsSync(metaPath)) {
            return res.status(404).json({ error: 'Video not found' });
        }

        const videoInfo = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
        const compileId = uuidv4();
        const outputPath = path.join(EXPORT_DIR, `${compileId}.mp4`);

        try {
            const result = await runPythonCommand([
                'compile',
                videoInfo.path,
                JSON.stringify(highlights),
                outputPath,
                JSON.stringify(options || {})
            ]);

            if (result.success) {
                const exportMeta = {
                    id: compileId,
                    videoId,
                    outputPath: result.output_path || outputPath,
                    outputInfo: result.output_info,
                    clipsCount: result.clips_count,
                    createdAt: new Date().toISOString()
                };

                const metaPath = path.join(EXPORT_DIR, `${compileId}.json`);
                fs.writeFileSync(metaPath, JSON.stringify(exportMeta, null, 2));

                res.json({
                    success: true,
                    compileId,
                    outputInfo: result.output_info,
                    clipsCount: result.clips_count
                });
            } else {
                res.status(500).json({ error: result.error || 'Compilation failed' });
            }
        } catch (err) {
            console.error('Compile error:', err);
            res.status(500).json({ error: err.message });
        }
    });

    app.post('/api/export', async (req, res) => {
        const { videoId, format, resolution, quality } = req.body;

        if (!videoId) {
            return res.status(400).json({ error: 'videoId is required' });
        }

        const sourcePath = path.join(EXPORT_DIR, `${videoId}.mp4`);
        const altSourcePath = path.join(UPLOAD_DIR, `${videoId}.mp4`);

        let inputPath;
        if (fs.existsSync(sourcePath)) {
            inputPath = sourcePath;
        } else if (fs.existsSync(altSourcePath)) {
            const metaPath = path.join(UPLOAD_DIR, `${videoId}.json`);
            if (fs.existsSync(metaPath)) {
                const info = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
                inputPath = info.path;
            }
        }

        if (!inputPath || !fs.existsSync(inputPath)) {
            return res.status(404).json({ error: 'Source video not found' });
        }

        const exportId = uuidv4();
        const fmt = format || 'mp4';
        const ext = fmt === 'mov' ? 'mov' : fmt;
        const outputPath = path.join(EXPORT_DIR, `${exportId}.${ext}`);

        try {
            const result = await runPythonCommand([
                'export',
                inputPath,
                outputPath,
                JSON.stringify({ format: fmt, resolution: resolution || 'original', quality: quality || 'high' })
            ]);

            if (result.success) {
                res.json({
                    success: true,
                    exportId,
                    downloadUrl: `/api/export/${exportId}/download`,
                    format: fmt
                });
            } else {
                res.status(500).json({ error: 'Export failed' });
            }
        } catch (err) {
            console.error('Export error:', err);
            res.status(500).json({ error: err.message });
        }
    });

    app.get('/api/export/:exportId/download', (req, res) => {
        const { exportId } = req.params;

        const metaPath = path.join(EXPORT_DIR, `${exportId}.json`);
        if (!fs.existsSync(metaPath)) {
            const files = fs.readdirSync(EXPORT_DIR).filter(f => f.startsWith(exportId));
            if (files.length === 0) {
                return res.status(404).json({ error: 'Export not found' });
            }
            const filePath = path.join(EXPORT_DIR, files[0]);
            return res.download(filePath);
        }

        const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
        const filePath = meta.outputPath;

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: 'Export file not found' });
        }

        res.download(filePath);
    });

    app.get('/api/export/:exportId/stream', (req, res) => {
        const { exportId } = req.params;

        const files = fs.readdirSync(EXPORT_DIR).filter(f => f.startsWith(exportId) && !f.endsWith('.json'));
        if (files.length === 0) {
            return res.status(404).json({ error: 'Export not found' });
        }

        const filePath = path.join(EXPORT_DIR, files[0]);
        const stat = fs.statSync(filePath);
        const fileSize = stat.size;
        const range = req.headers.range;

        if (range) {
            const parts = range.replace(/bytes=/, '').split('-');
            const start = parseInt(parts[0], 10);
            const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
            const chunksize = end - start + 1;
            const file = fs.createReadStream(filePath, { start, end });
            const head = {
                'Content-Range': `bytes ${start}-${end}/${fileSize}`,
                'Accept-Ranges': 'bytes',
                'Content-Length': chunksize,
                'Content-Type': 'video/mp4'
            };
            res.writeHead(206, head);
            file.pipe(res);
        } else {
            res.writeHead(200, { 'Content-Length': fileSize, 'Content-Type': 'video/mp4' });
            fs.createReadStream(filePath).pipe(res);
        }
    });
}

module.exports = setupExportRoutes;
