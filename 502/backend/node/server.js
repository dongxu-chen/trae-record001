const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

const UPLOAD_DIR = path.resolve(__dirname, '../../uploads');
const EXPORT_DIR = path.resolve(__dirname, '../../exports');

[UPLOAD_DIR, EXPORT_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

app.use('/exports', express.static(EXPORT_DIR));

const FRONTEND_BUILD = path.resolve(__dirname, '../../frontend/build');
if (fs.existsSync(FRONTEND_BUILD)) {
    app.use(express.static(FRONTEND_BUILD));
    app.get('*', (req, res) => {
        if (!req.path.startsWith('/api')) {
            res.sendFile(path.join(FRONTEND_BUILD, 'index.html'));
        }
    });
}

const setupUploadRoutes = require('./routes/upload');
const { setupAnalysisRoutes } = require('./routes/analyze');
const setupExportRoutes = require('./routes/export');
const { setupMusicRoutes, setupSubtitleRoutes, setupTemplateRoutes } = require('./routes/extras');

setupUploadRoutes(app);
setupAnalysisRoutes(app);
setupExportRoutes(app);
setupMusicRoutes(app);
setupSubtitleRoutes(app);
setupTemplateRoutes(app);

app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/formats', (req, res) => {
    res.json({
        formats: [
            { id: 'mp4', name: 'MP4', description: 'H.264 + AAC', ext: '.mp4' },
            { id: 'webm', name: 'WebM', description: 'VP9 + Opus', ext: '.webm' },
            { id: 'avi', name: 'AVI', description: 'H.264 + MP3', ext: '.avi' },
            { id: 'mov', name: 'MOV', description: 'H.264 + AAC (QuickTime)', ext: '.mov' },
            { id: 'gif', name: 'GIF', description: 'Animated GIF (no audio)', ext: '.gif' }
        ],
        resolutions: [
            { id: 'original', name: 'Original' },
            { id: '4k', name: '4K (3840x2160)' },
            { id: '1080p', name: '1080p (1920x1080)' },
            { id: '720p', name: '720p (1280x720)' },
            { id: '480p', name: '480p (854x480)' }
        ],
        qualityPresets: [
            { id: 'ultra', name: '超高品质', description: '最大画质，文件较大', crf: '15', approxBitrate: '约 8-15 Mbps' },
            { id: 'high', name: '高品质', description: '画质与文件大小平衡', crf: '18', approxBitrate: '约 5-8 Mbps' },
            { id: 'balanced', name: '均衡', description: '推荐设置，画质与体积均衡', crf: '23', approxBitrate: '约 3-5 Mbps' },
            { id: 'compact', name: '紧凑', description: '较小文件，画质可接受', crf: '28', approxBitrate: '约 1.5-3 Mbps' },
            { id: 'minimal', name: '最小体积', description: '最小文件大小，画质有损失', crf: '32', approxBitrate: '约 0.5-1.5 Mbps' }
        ],
        transitions: [
            { id: 'none', name: '无过渡', description: '直接拼接' },
            { id: 'fade', name: '淡入淡出', description: '每个片段首尾淡入淡出' },
            { id: 'crossfade', name: '交叉溶解', description: '相邻片段交叉溶解过渡' },
            { id: 'zoom', name: '缩放过渡', description: '片段间缩放效果过渡' }
        ]
    });
});

app.use((err, req, res, next) => {
    if (err.name === 'MulterError') {
        if (err.code === 'LIMIT_FILE_SIZE') {
            return res.status(413).json({ error: 'File too large. Maximum size is 500MB.' });
        }
        return res.status(400).json({ error: `Upload error: ${err.message}` });
    }

    if (err.message && err.message.includes('Unsupported file type')) {
        return res.status(400).json({ error: err.message });
    }

    console.error('Server error:', err);
    res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
    console.log(`Video Clipper API server running on http://localhost:${PORT}`);
    console.log(`Upload directory: ${UPLOAD_DIR}`);
    console.log(`Export directory: ${EXPORT_DIR}`);
});

module.exports = app;
