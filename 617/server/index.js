import express from 'express';
import cors from 'cors';
import { generateSkeleton, generateBatchSkeletons, parseSitemap, ANIMATION_TYPES } from './skeletonGenerator.js';

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.post('/api/generate-skeleton', async (req, res) => {
  try {
    const { url, options = {} } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    console.log(`Generating skeleton for: ${url}`);
    const result = await generateSkeleton(url, options);
    
    res.json(result);
  } catch (error) {
    console.error('Error generating skeleton:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/batch-generate', async (req, res) => {
  try {
    const { urls, options = {} } = req.body;
    
    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return res.status(400).json({ error: 'URLs array is required' });
    }

    if (urls.length > 50) {
      return res.status(400).json({ error: 'Maximum 50 URLs allowed per batch' });
    }

    console.log(`Batch generating ${urls.length} skeletons...`);
    const result = await generateBatchSkeletons(urls, options);
    
    res.json(result);
  } catch (error) {
    console.error('Error in batch generation:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/parse-sitemap', async (req, res) => {
  try {
    const { sitemapUrl } = req.body;
    
    if (!sitemapUrl) {
      return res.status(400).json({ error: 'Sitemap URL is required' });
    }

    console.log(`Parsing sitemap: ${sitemapUrl}`);
    const result = await parseSitemap(sitemapUrl);
    
    res.json(result);
  } catch (error) {
    console.error('Error parsing sitemap:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/animation-types', (req, res) => {
  res.json({ types: ANIMATION_TYPES });
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
