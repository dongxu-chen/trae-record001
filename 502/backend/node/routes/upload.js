const express = require('express');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const UPLOAD_DIR = path.resolve(__dirname, '../../../uploads');
const EXPORT_DIR = path.resolve(__dirname, '../../../exports');

const storage = require('../middleware/upload');

function setupUploadRoutes(app) {
    app.post('/api/upload', storage.single('video'), (req, res) => {
        if (!req.file) {
            return res.status(400).json({ error: 'No video file uploaded' });
        }

        const videoId = uuidv4();
        const ext = path.extname(req.file.originalname) || '.mp4';
        const newFilename = `${videoId}${ext}`;
        const newPath = path.join(UPLOAD_DIR, newFilename);

        try {
            fs.renameSync(req.file.path, newPath);

            const videoInfo = {
                id: videoId,
                originalName: req.file.originalname,
                filename: newFilename,
                path: newPath,
                size: req.file.size,
                mimeType: req.file.mimetype,
                uploadedAt: new Date().toISOString()
            };

            const metaPath = path.join(UPLOAD_DIR, `${videoId}.json`);
            fs.writeFileSync(metaPath, JSON.stringify(videoInfo, null, 2));

            res.json({
                success: true,
                video: {
                    id: videoId,
                    originalName: req.file.originalname,
                    size: req.file.size
                }
            });
        } catch (err) {
            console.error('Upload rename error:', err);
            res.status(500).json({ error: 'Failed to process upload' });
        }
    });

    app.get('/api/videos/:id', (req, res) => {
        const metaPath = path.join(UPLOAD_DIR, `${req.params.id}.json`);
        if (!fs.existsSync(metaPath)) {
            return res.status(404).json({ error: 'Video not found' });
        }

        const videoInfo = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
        res.json({ success: true, video: videoInfo });
    });

    app.get('/api/videos/:id/stream', (req, res) => {
        const metaPath = path.join(UPLOAD_DIR, `${req.params.id}.json`);
        if (!fs.existsSync(metaPath)) {
            return res.status(404).json({ error: 'Video not found' });
        }

        const videoInfo = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
        const videoPath = videoInfo.path;

        if (!fs.existsSync(videoPath)) {
            return res.status(404).json({ error: 'Video file not found' });
        }

        const stat = fs.statSync(videoPath);
        const fileSize = stat.size;
        const range = req.headers.range;

        if (range) {
            const parts = range.replace(/bytes=/, '').split('-');
            const start = parseInt(parts[0], 10);
            const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
            const chunksize = end - start + 1;
            const file = fs.createReadStream(videoPath, { start, end });
            const head = {
                'Content-Range': `bytes ${start}-${end}/${fileSize}`,
                'Accept-Ranges': 'bytes',
                'Content-Length': chunksize,
                'Content-Type': videoInfo.mimeType || 'video/mp4'
            };

            res.writeHead(206, head);
            file.pipe(res);
        } else {
            const head = {
                'Content-Length': fileSize,
                'Content-Type': videoInfo.mimeType || 'video/mp4'
            };
            res.writeHead(200, head);
            fs.createReadStream(videoPath).pipe(res);
        }
    });

    app.get('/api/videos/:id/thumbnail', (req, res) => {
        const metaPath = path.join(UPLOAD_DIR, `${req.params.id}.json`);
        if (!fs.existsSync(metaPath)) {
            return res.status(404).json({ error: 'Video not found' });
        }

        const thumbnailPath = path.join(UPLOAD_DIR, `${req.params.id}_thumb.jpg`);
        if (fs.existsSync(thumbnailPath)) {
            res.sendFile(thumbnailPath);
        } else {
            res.status(404).json({ error: 'Thumbnail not found' });
        }
    });
}

module.exports = setupUploadRoutes;
