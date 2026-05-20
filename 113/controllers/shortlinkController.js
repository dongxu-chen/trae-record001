const redis = require('../config/redis');
const { generateUniqueShortCode } = require('../utils/Snowflake');
const { isValidUrl } = require('../utils/shortCode');
const ttlService = require('../services/ttlService');
const messageQueue = require('../services/messageQueue');
require('dotenv').config();

const createShortLink = async (req, res) => {
  try {
    const { longUrl } = req.body;
    
    if (!longUrl || !isValidUrl(longUrl)) {
      return res.status(400).json({ error: 'Invalid URL' });
    }

    const shortCode = generateUniqueShortCode();
    await ttlService.createShortlink(shortCode, longUrl);
    await redis.set(`longlink:${Buffer.from(longUrl).toString('base64')}`, shortCode);

    const shortLink = `${process.env.SHORT_LINK_DOMAIN}/${shortCode}`;

    res.json({
      shortCode,
      shortLink,
      longUrl,
      ttl: '1 year from last access'
    });
  } catch (error) {
    console.error('Create shortlink error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

const redirectToLongUrl = async (req, res) => {
  try {
    const { shortCode } = req.params;
    
    const longUrl = await ttlService.getLongUrl(shortCode);
    
    if (!longUrl) {
      return res.status(404).json({ error: 'Short link not found or expired' });
    }

    const analytics = req.analytics;
    await messageQueue.enqueue({
      short_code: shortCode,
      long_url: longUrl,
      ip: analytics.ip,
      user_agent: analytics.userAgent,
      referer: analytics.referer,
      country: analytics.country,
      region: analytics.region,
      city: analytics.city,
      browser: analytics.browser,
      os: analytics.os,
      device: analytics.device
    });

    res.redirect(302, longUrl);
  } catch (error) {
    console.error('Redirect error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

module.exports = { createShortLink, redirectToLongUrl };