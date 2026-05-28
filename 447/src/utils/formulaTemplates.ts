import katex from 'katex';

export interface FormulaTemplate {
  id: string;
  title: string;
  category: string;
  description: string;
  latex: string;
  tags: string[];
  difficulty: 'basic' | 'intermediate' | 'advanced';
  usageCount: number;
}

export interface TemplateCategory {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export const templateCategories: TemplateCategory[] = [
  { id: 'algebra', name: '代数', icon: 'Σ', description: '代数表达式与等式' },
  { id: 'calculus', name: '微积分', icon: '∫', description: '导数、积分与极限' },
  { id: 'linear-algebra', name: '线性代数', icon: '[]', description: '矩阵、向量与行列式' },
  { id: 'statistics', name: '统计学', icon: 'σ', description: '概率分布与统计量' },
  { id: 'physics', name: '物理公式', icon: '⚛', description: '经典与现代物理' },
  { id: 'geometry', name: '几何', icon: '△', description: '几何定理与公式' },
  { id: 'number-theory', name: '数论', icon: 'ℕ', description: '数论与离散数学' },
  { id: 'special', name: '特殊函数', icon: 'Γ', description: '特殊函数与正交多项式' },
];

export const formulaTemplates: FormulaTemplate[] = [
  {
    id: 'quadratic',
    title: '一元二次方程求根公式',
    category: 'algebra',
    description: 'ax² + bx + c = 0 的解',
    latex: 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}',
    tags: ['方程', '二次', '基础'],
    difficulty: 'basic',
    usageCount: 1247,
  },
  {
    id: 'binomial',
    title: '二项式定理',
    category: 'algebra',
    description: '二项式展开式',
    latex: '(a + b)^n = \\sum_{k=0}^{n} \\binom{n}{k} a^{n-k} b^k',
    tags: ['展开', '求和', '组合'],
    difficulty: 'intermediate',
    usageCount: 856,
  },
  {
    id: 'geometric-series',
    title: '等比级数求和',
    category: 'algebra',
    description: '无穷等比级数的和',
    latex: '\\sum_{n=0}^{\\infty} ar^n = \\frac{a}{1-r}, \\quad |r| < 1',
    tags: ['级数', '求和', '收敛'],
    difficulty: 'intermediate',
    usageCount: 643,
  },
  {
    id: 'taylor',
    title: '泰勒级数展开',
    category: 'calculus',
    description: '函数在某点的幂级数展开',
    latex: 'f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!} (x-a)^n',
    tags: ['级数', '导数', '近似'],
    difficulty: 'advanced',
    usageCount: 721,
  },
  {
    id: 'chain-rule',
    title: '链式法则',
    category: 'calculus',
    description: '复合函数求导',
    latex: '\\frac{d}{dx} f(g(x)) = f\'(g(x)) \\cdot g\'(x)',
    tags: ['导数', '复合函数', '基础'],
    difficulty: 'basic',
    usageCount: 1102,
  },
  {
    id: 'product-rule',
    title: '乘积法则',
    category: 'calculus',
    description: '函数乘积的导数',
    latex: '\\frac{d}{dx} [f(x)g(x)] = f\'(x)g(x) + f(x)g\'(x)',
    tags: ['导数', '乘积', '基础'],
    difficulty: 'basic',
    usageCount: 956,
  },
  {
    id: 'integration-by-parts',
    title: '分部积分',
    category: 'calculus',
    description: '乘积函数的积分',
    latex: '\\int u\\,dv = uv - \\int v\\,du',
    tags: ['积分', '技巧', '基础'],
    difficulty: 'intermediate',
    usageCount: 1089,
  },
  {
    id: 'fundamental-theorem',
    title: '微积分基本定理',
    category: 'calculus',
    description: '连接微分与积分',
    latex: '\\int_{a}^{b} f(x)\\,dx = F(b) - F(a)',
    tags: ['定理', '积分', '核心'],
    difficulty: 'intermediate',
    usageCount: 1321,
  },
  {
    id: 'stokes',
    title: '斯托克斯公式',
    category: 'calculus',
    description: '曲面与边界的积分关系',
    latex: '\\int_{\\partial \\Sigma} \\mathbf{F} \\cdot d\\mathbf{r} = \\iint_{\\Sigma} (\\nabla \\times \\mathbf{F}) \\cdot d\\mathbf{S}',
    tags: ['向量分析', '曲面', '高级'],
    difficulty: 'advanced',
    usageCount: 423,
  },
  {
    id: 'matrix-multiplication',
    title: '矩阵乘法',
    category: 'linear-algebra',
    description: '两个矩阵的乘积',
    latex: '(AB)_{ij} = \\sum_{k=1}^{n} A_{ik}B_{kj}',
    tags: ['矩阵', '运算', '基础'],
    difficulty: 'basic',
    usageCount: 897,
  },
  {
    id: 'matrix-inverse',
    title: '逆矩阵公式',
    category: 'linear-algebra',
    description: '利用伴随矩阵求逆',
    latex: 'A^{-1} = \\frac{1}{\\det(A)} \\mathrm{adj}(A)',
    tags: ['矩阵', '逆', '行列式'],
    difficulty: 'intermediate',
    usageCount: 634,
  },
  {
    id: 'cayley-hamilton',
    title: '凯莱-哈密顿定理',
    category: 'linear-algebra',
    description: '矩阵满足其特征方程',
    latex: 'p_A(A) = 0, \\quad p_A(\\lambda) = \\det(A - \\lambda I)',
    tags: ['定理', '特征值', '高级'],
    difficulty: 'advanced',
    usageCount: 312,
  },
  {
    id: 'eigenvalue',
    title: '特征值方程',
    category: 'linear-algebra',
    description: '矩阵的特征值与特征向量',
    latex: 'A \\mathbf{v} = \\lambda \\mathbf{v}',
    tags: ['特征值', '特征向量', '基础'],
    difficulty: 'intermediate',
    usageCount: 978,
  },
  {
    id: 'determinant-3x3',
    title: '3×3 行列式',
    category: 'linear-algebra',
    description: '三阶行列式的展开',
    latex: '\\begin{vmatrix} a & b & c \\\\ d & e & f \\\\ g & h & i \\end{vmatrix} = a(ei - fh) - b(di - fg) + c(dh - eg)',
    tags: ['行列式', '展开', '基础'],
    difficulty: 'basic',
    usageCount: 712,
  },
  {
    id: 'normal-distribution',
    title: '正态分布概率密度',
    category: 'statistics',
    description: '高斯分布的PDF',
    latex: 'f(x;\\mu,\\sigma) = \\frac{1}{\\sigma\\sqrt{2\\pi}} e^{-\\frac{(x-\\mu)^2}{2\\sigma^2}}',
    tags: ['分布', '概率', '基础'],
    difficulty: 'basic',
    usageCount: 1456,
  },
  {
    id: 'bayes-theorem',
    title: '贝叶斯定理',
    category: 'statistics',
    description: '条件概率的核心定理',
    latex: 'P(A|B) = \\frac{P(B|A)P(A)}{P(B)}',
    tags: ['概率', '条件', '定理'],
    difficulty: 'intermediate',
    usageCount: 879,
  },
  {
    id: 'central-limit',
    title: '中心极限定理',
    category: 'statistics',
    description: '样本均值的渐近分布',
    latex: '\\frac{\\bar{X}_n - \\mu}{\\sigma/\\sqrt{n}} \\xrightarrow{d} N(0,1)',
    tags: ['定理', '渐近', '核心'],
    difficulty: 'advanced',
    usageCount: 654,
  },
  {
    id: 'std-deviation',
    title: '标准差公式',
    category: 'statistics',
    description: '总体与样本标准差',
    latex: '\\sigma = \\sqrt{\\frac{1}{N}\\sum_{i=1}^{N}(x_i - \\mu)^2}, \\quad s = \\sqrt{\\frac{1}{n-1}\\sum_{i=1}^{n}(x_i - \\bar{x})^2}',
    tags: ['统计量', '方差', '基础'],
    difficulty: 'basic',
    usageCount: 1134,
  },
  {
    id: 'newton-second-law',
    title: '牛顿第二定律',
    category: 'physics',
    description: '经典力学核心方程',
    latex: '\\mathbf{F} = m\\mathbf{a} = \\frac{d\\mathbf{p}}{dt}',
    tags: ['力学', '运动', '基础'],
    difficulty: 'basic',
    usageCount: 1892,
  },
  {
    id: 'einstein-eq',
    title: '爱因斯坦质能方程',
    category: 'physics',
    description: '质量与能量的等价关系',
    latex: 'E = mc^2',
    tags: ['相对论', '能量', '著名'],
    difficulty: 'basic',
    usageCount: 2134,
  },
  {
    id: 'schrodinger',
    title: '薛定谔方程',
    category: 'physics',
    description: '量子力学基本方程',
    latex: 'i\\hbar\\frac{\\partial}{\\partial t}\\Psi(\\mathbf{r},t) = \\hat{H}\\Psi(\\mathbf{r},t)',
    tags: ['量子力学', '波函数', '高级'],
    difficulty: 'advanced',
    usageCount: 876,
  },
  {
    id: 'maxwell',
    title: '麦克斯韦方程组',
    category: 'physics',
    description: '电磁学基本方程组',
    latex: '\\begin{cases} \\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0} \\\\ \\nabla \\cdot \\mathbf{B} = 0 \\\\ \\nabla \\times \\mathbf{E} = -\\frac{\\partial \\mathbf{B}}{\\partial t} \\\\ \\nabla \\times \\mathbf{B} = \\mu_0 \\mathbf{J} + \\mu_0 \\varepsilon_0 \\frac{\\partial \\mathbf{E}}{\\partial t} \\end{cases}',
    tags: ['电磁学', '方程组', '核心'],
    difficulty: 'advanced',
    usageCount: 1121,
  },
  {
    id: 'pythagorean',
    title: '勾股定理',
    category: 'geometry',
    description: '直角三角形的三边关系',
    latex: 'a^2 + b^2 = c^2',
    tags: ['三角形', '定理', '基础'],
    difficulty: 'basic',
    usageCount: 2456,
  },
  {
    id: 'herons-formula',
    title: '海伦公式',
    category: 'geometry',
    description: '由三边长求三角形面积',
    latex: 'S = \\sqrt{s(s-a)(s-b)(s-c)}, \\quad s = \\frac{a+b+c}{2}',
    tags: ['面积', '三角形', '技巧'],
    difficulty: 'intermediate',
    usageCount: 543,
  },
  {
    id: 'euler-formula',
    title: '欧拉公式',
    category: 'geometry',
    description: '复数与三角函数的联系',
    latex: 'e^{i\\theta} = \\cos\\theta + i\\sin\\theta',
    tags: ['复数', '三角', '著名'],
    difficulty: 'advanced',
    usageCount: 1342,
  },
  {
    id: 'spherical-coords',
    title: '球坐标变换',
    category: 'geometry',
    description: '直角坐标与球坐标的转换',
    latex: '\\begin{cases} x = r\\sin\\theta\\cos\\phi \\\\ y = r\\sin\\theta\\sin\\phi \\\\ z = r\\cos\\theta \\end{cases}',
    tags: ['坐标', '变换', '三维'],
    difficulty: 'intermediate',
    usageCount: 678,
  },
  {
    id: 'fermat-little',
    title: '费马小定理',
    category: 'number-theory',
    description: '素数的重要性质',
    latex: 'a^{p-1} \\equiv 1 \\pmod{p}, \\quad p \\text{ 是素数}, a \\not\\equiv 0 \\pmod{p}',
    tags: ['数论', '素数', '定理'],
    difficulty: 'intermediate',
    usageCount: 432,
  },
  {
    id: 'euclidean-algorithm',
    title: '欧几里得算法',
    category: 'number-theory',
    description: '求最大公约数',
    latex: '\\gcd(a,b) = \\gcd(b, a \\bmod b)',
    tags: ['算法', '数论', '基础'],
    difficulty: 'basic',
    usageCount: 567,
  },
  {
    id: 'euler-totient',
    title: '欧拉定理',
    category: 'number-theory',
    description: '费马小定理的推广',
    latex: 'a^{\\phi(n)} \\equiv 1 \\pmod{n}, \\quad \\gcd(a,n) = 1',
    tags: ['定理', '数论', '欧拉函数'],
    difficulty: 'advanced',
    usageCount: 345,
  },
  {
    id: 'gamma-function',
    title: '伽马函数',
    category: 'special',
    description: '阶乘函数的解析延拓',
    latex: '\\Gamma(z) = \\int_{0}^{\\infty} t^{z-1} e^{-t}\\,dt, \\quad \\mathrm{Re}(z) > 0',
    tags: ['特殊函数', '积分', '高级'],
    difficulty: 'advanced',
    usageCount: 421,
  },
  {
    id: 'bessel',
    title: '贝塞尔方程',
    category: 'special',
    description: '二阶线性常微分方程',
    latex: 'x^2 y\" + x y\' + (x^2 - \\alpha^2) y = 0',
    tags: ['微分方程', '特殊函数'],
    difficulty: 'advanced',
    usageCount: 312,
  },
  {
    id: 'laguerre',
    title: '拉盖尔多项式',
    category: 'special',
    description: '正交多项式之一',
    latex: 'L_n(x) = \\frac{e^x}{n!} \\frac{d^n}{dx^n}\\left(e^{-x} x^n\\right)',
    tags: ['正交多项式', '微分'],
    difficulty: 'advanced',
    usageCount: 234,
  },
  {
    id: 'fourier-transform',
    title: '傅里叶变换',
    category: 'special',
    description: '时域与频域的转换',
    latex: '\\hat{f}(\\omega) = \\int_{-\\infty}^{\\infty} f(x) e^{-i\\omega x}\\,dx',
    tags: ['变换', '频谱', '核心'],
    difficulty: 'advanced',
    usageCount: 890,
  },
];

export function getTemplatesByCategory(categoryId: string): FormulaTemplate[] {
  return formulaTemplates.filter((t) => t.category === categoryId);
}

export function searchTemplates(query: string): FormulaTemplate[] {
  const q = query.toLowerCase();
  return formulaTemplates.filter(
    (t) =>
      t.title.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.tags.some((tag) => tag.toLowerCase().includes(q)) ||
      t.latex.toLowerCase().includes(q),
  );
}

export function getPopularTemplates(limit: number = 10): FormulaTemplate[] {
  return [...formulaTemplates].sort((a, b) => b.usageCount - a.usageCount).slice(0, limit);
}

export function renderTemplatePreview(latex: string): string {
  try {
    return katex.renderToString(latex, { displayMode: true, throwOnError: false });
  } catch {
    return '<span style="color:#EF4444">渲染失败</span>';
  }
}

export const difficultyLabels: Record<string, { label: string; color: string }> = {
  basic: { label: '基础', color: 'bg-accent/20 text-accent' },
  intermediate: { label: '中级', color: 'bg-warning/20 text-warning' },
  advanced: { label: '高级', color: 'bg-danger/20 text-danger' },
};
