const express = require('express');
const router = express.Router();
const RenderJob = require('../models/RenderJob');
const EventEmitter = require('events');

class RenderTaskQueue extends EventEmitter {
  constructor() {
    super();
    this.queue = [];
    this.processing = null;
    this.isProcessing = false;
  }

  add(job) {
    this.queue.push(job);
    this.emit('jobAdded', job);
    this.processNext();
    return job;
  }

  async processNext() {
    if (this.isProcessing || this.queue.length === 0) return;
    
    this.isProcessing = true;
    const job = this.queue.shift();
    
    try {
      await this.processJob(job);
    } catch (err) {
      console.error('Render job error:', err);
    }
    
    this.isProcessing = false;
    this.processNext();
  }

  async processJob(job) {
    this.processing = job;
    
    await RenderJob.findByIdAndUpdate(job._id, { 
      status: 'processing',
      startedAt: new Date()
    });

    const totalSteps = 10;
    for (let i = 1; i <= totalSteps; i++) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const progress = (i / totalSteps) * 100;
      await RenderJob.findByIdAndUpdate(job._id, { progress });
      this.emit('progress', job._id, progress);
    }

    const outputPath = `/renders/${job._id}.png`;
    
    await RenderJob.findByIdAndUpdate(job._id, {
      status: 'completed',
      outputPath,
      completedAt: new Date(),
      progress: 100
    });

    this.emit('completed', job._id, outputPath);
    this.processing = null;
  }

  getQueueStatus() {
    return {
      pending: this.queue.length,
      processing: this.processing ? this.processing._id : null
    };
  }
}

const renderQueue = new RenderTaskQueue();

router.get('/queue/status', (req, res) => {
  res.json(renderQueue.getQueueStatus());
});

router.get('/', async (req, res) => {
  try {
    const jobs = await RenderJob.find()
      .populate('modelId')
      .sort({ createdAt: -1 });
    res.json(jobs);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/:id', async (req, res) => {
  try {
    const job = await RenderJob.findById(req.params.id).populate('modelId');
    if (!job) {
      return res.status(404).json({ error: 'Render job not found' });
    }
    res.json(job);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/:id/poll', async (req, res) => {
  try {
    const job = await RenderJob.findById(req.params.id);
    if (!job) {
      return res.status(404).json({ error: 'Render job not found' });
    }
    
    res.json({
      jobId: job._id,
      status: job.status,
      progress: job.progress || 0,
      outputPath: job.outputPath,
      createdAt: job.createdAt,
      completedAt: job.completedAt
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/submit', async (req, res) => {
  try {
    const { modelId, name, settings } = req.body;

    if (!modelId) {
      return res.status(400).json({ error: 'Model ID is required' });
    }

    const renderJob = new RenderJob({
      modelId,
      name: name || `Render_${Date.now()}`,
      status: 'pending',
      progress: 0,
      settings: {
        width: settings?.width || 1920,
        height: settings?.height || 1080,
        samples: settings?.samples || 64,
        engine: settings?.engine || 'cycles',
        cameraAngle: settings?.cameraAngle || { x: 0, y: 0, z: 0 }
      }
    });

    await renderJob.save();
    renderQueue.add(renderJob);

    res.status(201).json({
      jobId: renderJob._id,
      status: renderJob.status,
      message: 'Render job submitted to queue',
      pollUrl: `/api/render/${renderJob._id}/poll`
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.put('/:id/status', async (req, res) => {
    try {
        const { status } = req.body;
        const job = await RenderJob.findByIdAndUpdate(
            req.params.id,
            { status },
            { new: true }
        );
        if (!job) {
            return res.status(404).json({ error: 'Render job not found' });
        }
        res.json(job);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

router.get('/:id/download', async (req, res) => {
    try {
        const job = await RenderJob.findById(req.params.id);
        if (!job) {
            return res.status(404).json({ error: 'Render job not found' });
        }
        if (job.status !== 'completed') {
            return res.status(400).json({ error: 'Render job not completed' });
        }

        const fs = require('fs');
        const path = require('path');
        
        const renderDir = path.join(__dirname, '../../renders');
        if (!fs.existsSync(renderDir)) {
            fs.mkdirSync(renderDir, { recursive: true });
        }
        
        const filename = `${job._id}.png`;
        const filepath = path.join(renderDir, filename);
        
        if (!fs.existsSync(filepath)) {
            const { createCanvas } = require('canvas');
            const canvas = createCanvas(job.settings.width || 1920, job.settings.height || 1080);
            const ctx = canvas.getContext('2d');
            
            const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, '#1a1a2e');
            gradient.addColorStop(1, '#16213e');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = 'rgba(0, 212, 255, 0.1)';
            for (let i = 0; i < 50; i++) {
                const x = Math.random() * canvas.width;
                const y = Math.random() * canvas.height;
                const r = Math.random() * 100 + 50;
                ctx.beginPath();
                ctx.arc(x, y, r, 0, Math.PI * 2);
                ctx.fill();
            }
            
            ctx.fillStyle = '#00d4ff';
            ctx.font = 'bold 48px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('3D Render', canvas.width / 2, canvas.height / 2 - 30);
            
            ctx.font = '24px Arial';
            ctx.fillStyle = '#888';
            ctx.fillText(job.name, canvas.width / 2, canvas.height / 2 + 20);
            ctx.fillText(new Date(job.completedAt || Date.now()).toLocaleString(), canvas.width / 2, canvas.height / 2 + 60);
            
            const buffer = canvas.toBuffer('image/png');
            fs.writeFileSync(filepath, buffer);
        }
        
        res.download(filepath, `${job.name}.png`);
    } catch (err) {
        console.error('Download error:', err);
        res.status(500).json({ error: err.message });
    }
});

router.get('/:id/share', async (req, res) => {
    try {
        const job = await RenderJob.findById(req.params.id);
        if (!job) {
            return res.status(404).json({ error: 'Render job not found' });
        }
        if (job.status !== 'completed') {
            return res.status(400).json({ error: 'Render job not completed' });
        }

        const shareToken = Buffer.from(`${job._id}:${Date.now()}`).toString('base64');
        
        const shareUrl = `${req.protocol}://${req.get('host')}/share/${shareToken}`;
        
        await RenderJob.findByIdAndUpdate(job._id, {
            $set: { shareToken, sharedAt: new Date() }
        });

        res.json({
            shareUrl,
            shareToken,
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

router.get('/completed', async (req, res) => {
    try {
        const jobs = await RenderJob.find({ status: 'completed' })
            .populate('modelId')
            .sort({ completedAt: -1 })
            .limit(20);
        res.json(jobs);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
module.exports.renderQueue = renderQueue;
