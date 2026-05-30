import type { PageScanResult, BatchScanSession, TesterProfile, TestTask, ColorblindType, WcagReport } from '@/types';
import { analyzeImageRegions } from '@/utils/imageAnalysis';

function generateMockWcagReport(seed: number): WcagReport {
  const random = (min: number, max: number) => Math.floor(Math.abs(Math.sin(seed++) * (max - min)) + min);

  const issues = [
    { severity: 'critical' as const, count: random(0, 3) },
    { severity: 'major' as const, count: random(1, 5) },
    { severity: 'minor' as const, count: random(2, 8) },
  ];

  const failed = issues.reduce((sum, i) => sum + i.count, 0);
  const total = random(30, 60);

  return {
    totalChecks: total,
    passed: total - failed,
    failed,
    passRate: Math.round(((total - failed) / total) * 100),
    issues: [],
    criticalCount: issues[0].count,
    majorCount: issues[1].count,
    minorCount: issues[2].count,
    analyzedRegions: random(80, 150),
    excludedComplexRegions: random(5, 20),
  };
}

export const MOCK_TESTERS: TesterProfile[] = [
  {
    id: 'tester-001',
    name: '张小明',
    colorblindTypes: ['protanopia'],
    severity: 'severe',
    experience: 'expert',
    availability: 'weekdays',
    bio: '产品设计师，红色盲患者，拥有8年无障碍设计经验，熟悉WCAG标准。',
    rating: 4.9,
    completedTests: 47,
    languages: ['中文', 'English'],
  },
  {
    id: 'tester-002',
    name: '李华',
    colorblindTypes: ['deuteranopia', 'deuteranomaly'],
    severity: 'moderate',
    experience: 'intermediate',
    availability: 'flexible',
    bio: '前端开发工程师，绿色弱，专注于Web无障碍开发。',
    rating: 4.7,
    completedTests: 23,
    languages: ['中文', '日本語'],
  },
  {
    id: 'tester-003',
    name: '王芳',
    colorblindTypes: ['tritanopia'],
    severity: 'moderate',
    experience: 'beginner',
    availability: 'weekends',
    bio: '在校大学生，蓝色盲，对产品界面体验敏感。',
    rating: 4.8,
    completedTests: 8,
    languages: ['中文'],
  },
  {
    id: 'tester-004',
    name: 'Chen Wei',
    colorblindTypes: ['protanomaly', 'deuteranomaly'],
    severity: 'mild',
    experience: 'expert',
    availability: 'flexible',
    bio: 'UX研究员，红绿色弱，曾参与多个大型产品的无障碍测试。',
    rating: 4.95,
    completedTests: 89,
    languages: ['中文', 'English', '한국어'],
  },
  {
    id: 'tester-005',
    name: '刘阳',
    colorblindTypes: ['achromatopsia'],
    severity: 'severe',
    experience: 'intermediate',
    availability: 'weekdays',
    bio: '全色盲患者，使用辅助技术浏览网页，对低对比度问题非常敏感。',
    rating: 4.85,
    completedTests: 31,
    languages: ['中文'],
  },
];

export const MOCK_TEST_TASKS: TestTask[] = [
  {
    id: 'task-001',
    title: '电商产品页色盲用户体验测试',
    description: '测试商品列表页的颜色区分能力，重点测试价格标签、库存状态、促销标签的可识别性。',
    url: 'https://example.com/products',
    targetColorblindTypes: ['protanopia', 'deuteranopia', 'deuteranomaly'],
    status: 'open',
    compensation: '¥200 / 次',
    estimatedTime: '30-45分钟',
    createdAt: new Date(Date.now() - 2 * 86400000),
    deadline: new Date(Date.now() + 5 * 86400000),
    applicants: [MOCK_TESTERS[0], MOCK_TESTERS[1]],
  },
  {
    id: 'task-002',
    title: '数据可视化图表可访问性测试',
    description: '测试后台数据看板中各类图表（饼图、折线图、柱状图）在色盲视图下的可读性。',
    url: 'https://example.com/dashboard',
    targetColorblindTypes: ['protanopia', 'deuteranopia', 'tritanopia'],
    status: 'in_progress',
    compensation: '¥300 / 次',
    estimatedTime: '45-60分钟',
    createdAt: new Date(Date.now() - 5 * 86400000),
    deadline: new Date(Date.now() + 2 * 86400000),
    applicants: [MOCK_TESTERS[3]],
    acceptedTester: MOCK_TESTERS[3],
  },
  {
    id: 'task-003',
    title: '表单验证错误提示测试',
    description: '测试表单页面中错误提示（红色警告、绿色成功）的可识别性。',
    url: 'https://example.com/forms',
    targetColorblindTypes: ['protanopia', 'deuteranopia', 'protanomaly', 'deuteranomaly'],
    status: 'open',
    compensation: '¥150 / 次',
    estimatedTime: '20-30分钟',
    createdAt: new Date(Date.now() - 1 * 86400000),
    deadline: new Date(Date.now() + 7 * 86400000),
    applicants: [],
  },
];

export const MOCK_SCAN_RESULTS: PageScanResult[] = [
  {
    id: 'scan-001',
    url: 'https://example.com/',
    title: '首页',
    status: 'completed',
    progress: 100,
    scannedAt: new Date(Date.now() - 3600000),
    report: generateMockWcagReport(1),
  },
  {
    id: 'scan-002',
    url: 'https://example.com/products',
    title: '产品列表页',
    status: 'completed',
    progress: 100,
    scannedAt: new Date(Date.now() - 3200000),
    report: generateMockWcagReport(2),
  },
  {
    id: 'scan-003',
    url: 'https://example.com/about',
    title: '关于我们',
    status: 'completed',
    progress: 100,
    scannedAt: new Date(Date.now() - 2800000),
    report: generateMockWcagReport(3),
  },
  {
    id: 'scan-004',
    url: 'https://example.com/contact',
    title: '联系我们',
    status: 'completed',
    progress: 100,
    scannedAt: new Date(Date.now() - 2400000),
    report: generateMockWcagReport(4),
  },
  {
    id: 'scan-005',
    url: 'https://example.com/blog',
    title: '博客列表',
    status: 'completed',
    progress: 100,
    scannedAt: new Date(Date.now() - 2000000),
    report: generateMockWcagReport(5),
  },
];

export async function scanSinglePage(url: string): Promise<PageScanResult> {
  const result: PageScanResult = {
    id: `scan-${Date.now()}`,
    url,
    title: new URL(url).hostname,
    status: 'scanning',
    progress: 0,
  };

  await new Promise((resolve) => setTimeout(resolve, 500));
  result.progress = 25;

  await new Promise((resolve) => setTimeout(resolve, 500));
  result.progress = 50;

  await new Promise((resolve) => setTimeout(resolve, 500));
  result.progress = 75;

  await new Promise((resolve) => setTimeout(resolve, 500));
  result.progress = 100;
  result.status = 'completed';
  result.scannedAt = new Date();
  result.report = generateMockWcagReport(Date.now());

  return result;
}

export async function batchScanPages(
  urls: string[],
  onProgress?: (index: number, result: PageScanResult) => void
): Promise<BatchScanSession> {
  const session: BatchScanSession = {
    id: `batch-${Date.now()}`,
    name: `批量扫描 - ${new Date().toLocaleDateString()}`,
    urls,
    results: [],
    status: 'scanning',
    createdAt: new Date(),
    overallPassRate: 0,
    totalIssues: 0,
  };

  for (let i = 0; i < urls.length; i++) {
    const result = await scanSinglePage(urls[i]);
    session.results.push(result);

    if (onProgress) {
      onProgress(i, result);
    }
  }

  session.status = 'completed';
  session.completedAt = new Date();

  if (session.results.length > 0) {
    const totalPassRate = session.results.reduce(
      (sum, r) => sum + (r.report?.passRate || 0),
      0
    ) / session.results.length;
    session.overallPassRate = Math.round(totalPassRate);
    session.totalIssues = session.results.reduce(
      (sum, r) => sum + (r.report?.failed || 0),
      0
    );
  }

  return session;
}

export async function scanUrlWithScreenshot(
  url: string
): Promise<{ imageData: ImageData; report: WcagReport }> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const maxWidth = 1200;
      const scale = img.width > maxWidth ? maxWidth / img.width : 1;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const { report } = analyzeImageRegions(imageData);
      resolve({ imageData, report });
    };
    img.src = `https://api.microlink.io/?url=${encodeURIComponent(url)}&screenshot=true&device=desktop`;
  });
}
