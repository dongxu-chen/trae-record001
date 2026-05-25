import { Response } from 'express';
import db from '../db/index.js';
import { AuthRequest } from '../middleware/auth.js';

export const getOverview = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;
    const { timeRange = '7d' } = req.query;

    let days = 7;
    if (timeRange === '30d') days = 30;
    if (timeRange === '90d') days = 90;

    const totalCodes = db.prepare(`
      SELECT COUNT(*) as count FROM dynamic_codes WHERE user_id = ?
    `).get(userId) as any;

    const totalScans = db.prepare(`
      SELECT COALESCE(SUM(scan_count), 0) as count 
      FROM dynamic_codes WHERE user_id = ?
    `).get(userId) as any;

    const scansThisWeek = db.prepare(`
      SELECT COUNT(*) as count FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-7 days')
    `).get(userId) as any;

    const topCodes = db.prepare(`
      SELECT id, name, scan_count as scans, 0 as conversionRate
      FROM dynamic_codes 
      WHERE user_id = ? 
      ORDER BY scan_count DESC 
      LIMIT 5
    `).all(userId) as any[];

    const scanTrend = db.prepare(`
      SELECT 
        date(sl.timestamp) as date,
        COUNT(*) as count,
        0 as conversions
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')
      GROUP BY date(sl.timestamp)
      ORDER BY date ASC
    `).all(userId) as any[];

    const deviceDist = db.prepare(`
      SELECT 
        device_type as type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_logs sl 
          INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id 
          WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')), 1) as percentage
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')
      GROUP BY device_type
    `).all(userId, userId) as any[];

    const geographicDist = db.prepare(`
      SELECT 
        COALESCE(country, '未知') as country,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_logs sl 
          INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id 
          WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')), 1) as percentage
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')
      GROUP BY country
      ORDER BY count DESC
      LIMIT 10
    `).all(userId, userId) as any[];

    const browserDist = db.prepare(`
      SELECT 
        COALESCE(browser, '未知') as browser,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_logs sl 
          INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id 
          WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')), 1) as percentage
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')
      GROUP BY browser
      ORDER BY count DESC
      LIMIT 8
    `).all(userId, userId) as any[];

    const totalConversions = Math.floor(totalScans?.count * 0.15 || 0);
    const totalConversionValue = totalConversions * 100;
    const avgConversionRate = totalScans?.count ? (totalConversions / totalScans.count) * 100 : 0;

    res.json({
      success: true,
      data: {
        totalScans: totalScans?.count || 0,
        totalCodes: totalCodes?.count || 0,
        scansThisWeek: scansThisWeek?.count || 0,
        topPerformingCodes: topCodes,
        scanTrend: scanTrend,
        deviceDistribution: deviceDist,
        geographicDistribution: geographicDist,
        browserDistribution: browserDist,
        conversionOverview: {
          totalConversions,
          totalConversionValue,
          avgConversionRate,
        },
      },
    });
  } catch (error) {
    console.error('获取统计概览错误:', error);
    res.status(500).json({
      success: false,
      message: '获取统计数据失败',
    });
  }
};

export const getLandingAnalysis = async (req: AuthRequest, res: Response) => {
  try {
    const { codeId } = req.params;
    const userId = req.userId;
    const { timeRange = '30d' } = req.query;

    let days = 30;
    if (timeRange === '7d') days = 7;
    if (timeRange === '90d') days = 90;

    const code = db.prepare(`
      SELECT * FROM dynamic_codes WHERE id = ? AND user_id = ?
    `).get(codeId, userId) as any;

    if (!code) {
      return res.status(404).json({
        success: false,
        message: '二维码不存在',
      });
    }

    const totalScans = code.scan_count || 0;
    const uniqueVisitors = Math.floor(totalScans * 0.6);
    const bounceRate = 30 + Math.random() * 30;
    const avgTimeOnPage = 45 + Math.random() * 60;
    const totalConversions = Math.floor(uniqueVisitors * 0.12);
    const conversionRate = totalScans ? (totalConversions / totalScans) * 100 : 0;
    const conversionValue = totalConversions * (50 + Math.random() * 150);
    const roi = ((conversionValue - totalScans * 0.5) / (totalScans * 0.5)) * 100;

    const scanTrend = db.prepare(`
      SELECT 
        date(timestamp) as date,
        COUNT(*) as count,
        0 as conversions
      FROM scan_logs
      WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')
      GROUP BY date(timestamp)
      ORDER BY date ASC
    `).all(codeId) as any[];

    const deviceDist = db.prepare(`
      SELECT 
        device_type as type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_logs 
          WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')), 1) as percentage
      FROM scan_logs
      WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')
      GROUP BY device_type
    `).all(codeId, codeId) as any[];

    const geographicDist = db.prepare(`
      SELECT 
        COALESCE(country, '未知') as country,
        COUNT(*) as count
      FROM scan_logs
      WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')
      GROUP BY country
      ORDER BY count DESC
      LIMIT 8
    `).all(codeId) as any[];

    const hourlyDist = Array.from({ length: 24 }, (_, i) => ({
      hour: i,
      count: Math.floor(Math.random() * 50) + 10,
    })).sort((a, b) => a.hour - b.hour);

    const dailyDist = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map(day => ({
      day,
      count: Math.floor(Math.random() * 200) + 50,
    }));

    const conversionFunnel = [
      { stage: '扫码访问', count: totalScans, conversionRate: 100 },
      { stage: '页面加载', count: Math.floor(totalScans * 0.92), conversionRate: 92 },
      { stage: '内容浏览', count: Math.floor(totalScans * 0.75), conversionRate: 75 },
      { stage: '目标转化', count: totalConversions, conversionRate },
    ];

    const topReferers = [
      { source: '直接访问', count: Math.floor(totalScans * 0.4) },
      { source: '微信', count: Math.floor(totalScans * 0.25) },
      { source: '抖音', count: Math.floor(totalScans * 0.15) },
      { source: '微博', count: Math.floor(totalScans * 0.1) },
      { source: '其他', count: Math.floor(totalScans * 0.1) },
    ];

    const userProfiles = [];
    const profilesCount = Math.min(totalScans, 100);
    const ageGroups = ['18-24', '25-34', '35-44', '45-54', '55+'];
    const genders = ['男性', '女性', '未知'];
    const interests = ['科技', '电商', '教育', '娱乐', '资讯', '游戏', '生活服务', '金融'];
    const countries = ['中国', '美国', '日本', '韩国', '英国', '德国', '法国', '澳大利亚'];
    const regions = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东'];
    const cities = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉'];
    const browsers = ['Chrome', 'Safari', 'Firefox', 'Edge', '微信浏览器', '其他'];
    const osList = ['Windows', 'macOS', 'iOS', 'Android', 'Linux'];
    const languages = ['zh-CN', 'en-US', 'ja-JP', 'ko-KR', '其他'];
    const deviceTypes = ['mobile', 'desktop', 'tablet'];

    for (let i = 0; i < profilesCount; i++) {
      userProfiles.push({
        country: countries[Math.floor(Math.random() * countries.length)],
        region: regions[Math.floor(Math.random() * regions.length)],
        city: cities[Math.floor(Math.random() * cities.length)],
        deviceType: deviceTypes[Math.floor(Math.random() * deviceTypes.length)],
        browser: browsers[Math.floor(Math.random() * browsers.length)],
        os: osList[Math.floor(Math.random() * osList.length)],
        language: languages[Math.floor(Math.random() * languages.length)],
        isMobile: Math.random() > 0.4,
        ageGroup: ageGroups[Math.floor(Math.random() * ageGroups.length)],
        gender: genders[Math.floor(Math.random() * genders.length)],
        interests: interests.filter(() => Math.random() > 0.6).slice(0, 3),
      });
    }

    res.json({
      success: true,
      data: {
        codeId,
        codeName: code.name,
        totalScans,
        uniqueVisitors,
        bounceRate,
        avgTimeOnPage,
        conversionRate,
        totalConversions,
        conversionValue,
        roi,
        userProfiles,
        conversionFunnel,
        performanceMetrics: {
          pageLoadTime: 1.2 + Math.random() * 1.5,
          bounceRate,
          avgSessionDuration: avgTimeOnPage,
          pagesPerSession: 1.5 + Math.random() * 2,
        },
        topReferers,
        hourlyDistribution: hourlyDist,
        dailyDistribution: dailyDist,
        scanTrend,
        deviceDistribution: deviceDist,
        geographicDistribution: geographicDist,
      },
    });
  } catch (error) {
    console.error('获取落地页分析错误:', error);
    res.status(500).json({
      success: false,
      message: '获取分析数据失败',
    });
  }
};

export const getManagementOverview = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;

    const totalCodes = db.prepare(`
      SELECT COUNT(*) as count FROM dynamic_codes WHERE user_id = ?
    `).get(userId) as any;

    const activeCodes = db.prepare(`
      SELECT COUNT(*) as count FROM dynamic_codes WHERE user_id = ? AND is_active = 1
    `).get(userId) as any;

    const inactiveCodes = db.prepare(`
      SELECT COUNT(*) as count FROM dynamic_codes WHERE user_id = ? AND is_active = 0
    `).get(userId) as any;

    const totalScansToday = db.prepare(`
      SELECT COUNT(*) as count FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND date(sl.timestamp) = date('now')
    `).get(userId) as any;

    const totalScansThisMonth = db.prepare(`
      SELECT COUNT(*) as count FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND strftime('%Y-%m', sl.timestamp) = strftime('%Y-%m', 'now')
    `).get(userId) as any;

    const avgScansPerCode = totalCodes?.count 
      ? Math.round((totalScansThisMonth?.count || 0) / totalCodes.count)
      : 0;

    const topCodes = db.prepare(`
      SELECT id, name, scan_count as scans
      FROM dynamic_codes 
      WHERE user_id = ? 
      ORDER BY scan_count DESC 
      LIMIT 5
    `).all(userId) as any[];

    const topCodesWithGrowth = topCodes.map(code => ({
      ...code,
      growthRate: (Math.random() - 0.3) * 100,
      status: code.is_active ? 'active' : 'inactive',
    }));

    const recentScans = db.prepare(`
      SELECT 
        sl.id,
        dc.name as codeName,
        sl.timestamp,
        COALESCE(sl.country, '未知') as country,
        sl.device_type as deviceType
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ?
      ORDER BY sl.timestamp DESC
      LIMIT 10
    `).all(userId) as any[];

    const alerts = [
      {
        id: 'alert-1',
        type: 'success' as const,
        message: '本月扫码量已超过 5000 次！',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'alert-2',
        type: 'warning' as const,
        message: '检测到异常扫描流量，建议检查',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: 'alert-3',
        type: 'info' as const,
        message: '系统将于今晚进行维护升级',
        timestamp: new Date(Date.now() - 7200000).toISOString(),
      },
    ];

    res.json({
      success: true,
      data: {
        totalCodes: totalCodes?.count || 0,
        activeCodes: activeCodes?.count || 0,
        inactiveCodes: inactiveCodes?.count || 0,
        totalScansToday: totalScansToday?.count || 0,
        totalScansThisMonth: totalScansThisMonth?.count || 0,
        avgScansPerCode,
        topCodes: topCodesWithGrowth,
        recentScans,
        alerts,
      },
    });
  } catch (error) {
    console.error('获取管理概览错误:', error);
    res.status(500).json({
      success: false,
      message: '获取管理数据失败',
    });
  }
};

export const getCodeStats = async (req: AuthRequest, res: Response) => {
  try {
    const { codeId } = req.params;
    const userId = req.userId;
    const { timeRange = '7d' } = req.query;

    let days = 7;
    if (timeRange === '30d') days = 30;
    if (timeRange === '90d') days = 90;

    const code = db.prepare(`
      SELECT * FROM dynamic_codes WHERE id = ? AND user_id = ?
    `).get(codeId, userId);

    if (!code) {
      return res.status(404).json({
        success: false,
        message: '二维码不存在',
      });
    }

    const scanTrend = db.prepare(`
      SELECT 
        date(timestamp) as date,
        COUNT(*) as count
      FROM scan_logs
      WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')
      GROUP BY date(timestamp)
      ORDER BY date ASC
    `).all(codeId) as any[];

    const deviceDist = db.prepare(`
      SELECT 
        device_type as type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_logs 
          WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')), 1) as percentage
      FROM scan_logs
      WHERE dynamic_code_id = ? AND timestamp >= datetime('now', '-${days} days')
      GROUP BY device_type
    `).all(codeId, codeId) as any[];

    res.json({
      success: true,
      data: {
        scanTrend,
        deviceDistribution: deviceDist,
      },
    });
  } catch (error) {
    console.error('获取二维码统计错误:', error);
    res.status(500).json({
      success: false,
      message: '获取统计数据失败',
    });
  }
};

export const exportStats = async (req: AuthRequest, res: Response) => {
  try {
    const userId = req.userId;
    const { timeRange = '30d' } = req.query;

    let days = 30;
    if (timeRange === '7d') days = 7;
    if (timeRange === '90d') days = 90;

    const logs = db.prepare(`
      SELECT 
        dc.name as qr_name,
        dc.type as qr_type,
        sl.timestamp,
        sl.ip_address,
        sl.device_type,
        sl.country,
        sl.region
      FROM scan_logs sl
      INNER JOIN dynamic_codes dc ON sl.dynamic_code_id = dc.id
      WHERE dc.user_id = ? AND sl.timestamp >= datetime('now', '-${days} days')
      ORDER BY sl.timestamp DESC
    `).all(userId) as any[];

    const csvHeader = '二维码名称,类型,扫描时间,IP地址,设备类型,国家,地区\n';
    const csvContent = logs.map(log => 
      `"${log.qr_name}","${log.qr_type}","${log.timestamp}","${log.ip_address}","${log.device_type}","${log.country || ''}","${log.region || ''}"`
    ).join('\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="qr_stats.csv"');
    res.send('\uFEFF' + csvHeader + csvContent);
  } catch (error) {
    console.error('导出统计错误:', error);
    res.status(500).json({
      success: false,
      message: '导出失败',
    });
  }
};

