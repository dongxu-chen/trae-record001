const path = require('path');
const { spawn } = require('child_process');

const PYTHON_SCRIPT = path.resolve(__dirname, '../python/main.py');
const UPLOAD_DIR = path.resolve(__dirname, '../../uploads');

function runPythonCommand(args) {
    return new Promise((resolve, reject) => {
        const python = spawn('python', [PYTHON_SCRIPT, ...args], {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        python.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        python.on('close', (code) => {
            if (code !== 0) {
                console.error('Python command failed:', stderr);
                reject(new Error(`Python command failed with code ${code}`));
                return;
            }

            try {
                const result = JSON.parse(stdout.trim());
                resolve(result);
            } catch (e) {
                reject(new Error('Failed to parse Python output'));
            }
        });

        python.on('error', (err) => {
            reject(err);
        });
    });
}

function setupMusicRoutes(app) {
    app.post('/api/music/recommend', async (req, res) => {
        try {
            const { videoId, highlights, scenes, options = {} } = req.body;
            const videoPath = path.join(UPLOAD_DIR, videoId);

            const result = await runPythonCommand([
                'recommend_music',
                videoPath,
                JSON.stringify(highlights),
                JSON.stringify(scenes),
                JSON.stringify(options)
            ]);

            res.json(result);
        } catch (error) {
            console.error('Music recommendation error:', error);
            res.status(500).json({ error: 'Failed to recommend music' });
        }
    });

    app.get('/api/music/library', async (req, res) => {
        try {
            const result = await runPythonCommand(['get_music_library']);
            res.json(result);
        } catch (error) {
            console.error('Get music library error:', error);
            res.status(500).json({ error: 'Failed to get music library' });
        }
    });
}

function setupSubtitleRoutes(app) {
    app.post('/api/subtitles/generate', async (req, res) => {
        try {
            const { videoId, options = {} } = req.body;
            const videoPath = path.join(UPLOAD_DIR, videoId);

            const result = await runPythonCommand([
                'generate_subtitles',
                videoPath,
                JSON.stringify(options)
            ]);

            res.json(result);
        } catch (error) {
            console.error('Subtitle generation error:', error);
            res.status(500).json({ error: 'Failed to generate subtitles' });
        }
    });

    app.post('/api/subtitles/export', async (req, res) => {
        try {
            const { videoId, outputPath, options = {} } = req.body;
            const videoPath = path.join(UPLOAD_DIR, videoId);

            const result = await runPythonCommand([
                'export_subtitles',
                videoPath,
                outputPath,
                JSON.stringify(options)
            ]);

            res.json(result);
        } catch (error) {
            console.error('Subtitle export error:', error);
            res.status(500).json({ error: 'Failed to export subtitles' });
        }
    });
}

function setupTemplateRoutes(app) {
    app.get('/api/templates', async (req, res) => {
        try {
            const { category, search, min_rating, limit } = req.query;
            const options = {
                category: category || null,
                search: search || null,
                min_rating: parseFloat(min_rating) || 0.0,
                limit: limit ? parseInt(limit) : null
            };

            const result = await runPythonCommand([
                'get_templates',
                JSON.stringify(options)
            ]);

            res.json(result);
        } catch (error) {
            console.error('Get templates error:', error);
            res.status(500).json({ error: 'Failed to get templates' });
        }
    });

    app.post('/api/templates/apply', async (req, res) => {
        try {
            const { templateId, highlights, scenes, options = {} } = req.body;

            const result = await runPythonCommand([
                'apply_template',
                templateId,
                JSON.stringify(highlights),
                JSON.stringify(scenes),
                JSON.stringify(options)
            ]);

            res.json(result);
        } catch (error) {
            console.error('Apply template error:', error);
            res.status(500).json({ error: 'Failed to apply template' });
        }
    });
}

module.exports = {
    setupMusicRoutes,
    setupSubtitleRoutes,
    setupTemplateRoutes
};
