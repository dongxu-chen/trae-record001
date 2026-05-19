const geoip = require('geoip-lite');
const useragent = require('express-useragent');

const analyticsMiddleware = (req, res, next) => {
  const ip = req.ip || req.connection.remoteAddress || 
             req.headers['x-forwarded-for']?.split(',')[0] || '127.0.0.1';
  
  const geo = geoip.lookup(ip === '::1' ? '127.0.0.1' : ip);
  const ua = useragent.parse(req.headers['user-agent']);
  
  req.analytics = {
    ip,
    userAgent: req.headers['user-agent'] || '',
    referer: req.headers['referer'] || '',
    country: geo?.country || 'Unknown',
    region: geo?.region || 'Unknown',
    city: geo?.city || 'Unknown',
    browser: ua?.browser || 'Unknown',
    os: ua?.os || 'Unknown',
    device: ua?.isMobile ? 'Mobile' : ua?.isTablet ? 'Tablet' : 'Desktop'
  };
  
  next();
};

module.exports = analyticsMiddleware;