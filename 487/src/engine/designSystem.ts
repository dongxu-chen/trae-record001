import { IconConfig, IconStyle } from './types';

export interface DesignGuidelineSection {
  id: string;
  title: string;
  content: string;
  items?: { label: string; value: string; description?: string }[];
}

export interface DesignSystemDoc {
  title: string;
  version: string;
  generatedAt: string;
  sections: DesignGuidelineSection[];
  markdown: string;
  html: string;
}

const styleLabels: Record<IconStyle, string> = {
  outline: '线框风格',
  filled: '填充风格',
  gradient: '渐变风格',
  '3d': '3D立体风格',
};

export function generateDesignGuidelines(config: IconConfig): DesignSystemDoc {
  const styleLabel = styleLabels[config.style];

  const sections: DesignGuidelineSection[] = [
    {
      id: 'overview',
      title: '概述',
      content: `本文档定义了「${config.text.toUpperCase()}」图标的设计规范和使用准则。该图标采用${styleLabel}设计，主色调为${config.primaryColor}，适用于品牌标识、应用图标、网页元素等多种场景。`,
    },
    {
      id: 'size',
      title: '尺寸规范',
      content: '为保证图标的清晰度和识别度，请严格遵循以下尺寸规范：',
      items: [
        { label: '推荐尺寸', value: `${config.size} × ${config.size}px`, description: '图标原始设计尺寸' },
        { label: '最小尺寸', value: '64 × 64px', description: '确保细节可辨识的最小尺寸' },
        { label: '最大尺寸', value: '512 × 512px', description: '保证渲染质量的最大尺寸' },
        { label: '常用尺寸', value: '64px / 128px / 256px / 512px', description: '推荐使用的标准尺寸' },
      ],
    },
    {
      id: 'colors',
      title: '颜色规范',
      content: '图标使用以下颜色方案，请勿随意修改颜色值以保持品牌一致性：',
      items: [
        {
          label: '主色调',
          value: config.primaryColor,
          description: config.showBackground ? '用于图标背景填充' : '用于图标主体颜色',
        },
        {
          label: '辅助色',
          value: config.secondaryColor,
          description: '用于渐变过渡、装饰元素',
        },
        {
          label: '文字色',
          value: '#FFFFFF',
          description: config.showBackground ? '图标内文字颜色，保证对比度' : '无需文字色',
        },
        {
          label: '背景色',
          value: config.backgroundColor,
          description: '图标容器背景色，建议使用白色或浅灰色',
        },
      ],
    },
    {
      id: 'spacing',
      title: '间距规范',
      content: '合理的间距确保图标在任何场景下都有良好的视觉表现：',
      items: [
        { label: '内边距', value: `${config.padding}px`, description: '图标内容与边缘的距离' },
        { label: '外边距', value: `≥ ${Math.ceil(config.size * 0.1)}px`, description: '图标与其他元素的最小间距' },
        { label: '圆角', value: `${config.borderRadius}px`, description: '图标背景圆角半径' },
      ],
    },
    {
      id: 'style',
      title: '风格说明',
      content: getStyleDescription(config.style, config),
    },
    {
      id: 'usage',
      title: '使用场景',
      content: '该图标适用于以下场景，请根据实际需求选择合适的尺寸和风格：',
      items: [
        { label: 'App图标', value: '1024 × 1024px', description: 'iOS/Android应用图标' },
        { label: '网站Favicon', value: '32 × 32px / 64 × 64px', description: '浏览器标签页图标' },
        { label: 'Logo标识', value: '任意矢量', description: '公司或产品Logo使用SVG格式' },
        { label: 'UI元素', value: '24 × 24px ~ 64 × 64px', description: '界面内功能图标' },
        { label: '社交媒体', value: '400 × 400px', description: '社交媒体头像' },
        { label: '印刷物料', value: '300DPI矢量', description: '名片、海报等印刷品' },
      ],
    },
    {
      id: 'background',
      title: '背景适配',
      content: '图标在不同背景上的显示规范：',
      items: [
        {
          label: '浅色背景',
          value: '#FFFFFF ~ #F3F4F6',
          description: '推荐使用背景，图标清晰度最佳',
        },
        {
          label: '深色背景',
          value: '#111827 ~ #1F2937',
          description: '需要调整主色调以保证对比度',
        },
        {
          label: '彩色背景',
          value: '低饱和度色块',
          description: '确保与图标颜色有足够对比度',
        },
        {
          label: '透明背景',
          value: '导出PNG/SVG',
          description: '关闭背景层后可用于任意背景',
        },
      ],
    },
    {
      id: 'donts',
      title: '使用禁忌',
      content: '为保持图标的专业性和一致性，请避免以下错误用法：',
      items: [
        { label: '❌ 拉伸变形', value: '禁止', description: '保持等比例缩放，不可单独拉伸宽高' },
        { label: '❌ 修改颜色', value: '禁止', description: '不可随意修改图标配色方案' },
        { label: '❌ 添加描边', value: '禁止', description: '不可在外层添加额外描边或阴影' },
        { label: '❌ 低分辨率', value: '禁止', description: '避免使用低于最小尺寸的位图' },
        { label: '❌ 动画过度', value: '不推荐', description: '动画效果应简洁，避免过度炫技' },
      ],
    },
    {
      id: 'export',
      title: '导出规范',
      content: '根据使用场景选择合适的导出格式：',
      items: [
        {
          label: 'PNG格式',
          value: '.png',
          description: '通用位图格式，支持透明背景，适用于网页和App',
        },
        {
          label: 'SVG格式',
          value: '.svg',
          description: '矢量格式，可无限缩放，适用于Logo和印刷',
        },
        {
          label: 'Lottie动画',
          value: '.json',
          description: '矢量动画格式，可原生渲染于各平台',
        },
      ],
    },
  ];

  const markdown = generateMarkdown(config, sections);
  const html = generateHtml(config, sections);

  return {
    title: `${config.text.toUpperCase()} 图标设计规范`,
    version: '1.0.0',
    generatedAt: new Date().toISOString(),
    sections,
    markdown,
    html,
  };
}

function getStyleDescription(style: IconStyle, config: IconConfig): string {
  switch (style) {
    case 'outline':
      return `线框风格采用简洁的线条设计，线条宽度为${Math.max(3, config.size * 0.03)}px，使用${config.primaryColor}至${config.secondaryColor}的渐变描边。整体风格现代简约，适合科技类产品和文档界面。四个角部装饰圆点增强品牌识别度，圆角${config.borderRadius}px营造亲和感。`;
    case 'filled':
      return `填充风格使用纯色块面设计，主色调${config.primaryColor}从${config.primaryColor}过渡到深色色块，配合白色文字形成强烈对比。圆角${config.borderRadius}px、内边距${config.padding}px，整体稳重专业，适合企业品牌和商务场景。`;
    case 'gradient':
      return `渐变风格采用${config.primaryColor}至${config.secondaryColor}的绚丽渐变，配合光晕和闪光装饰元素，营造年轻活力的视觉效果。外发光效果增强图标的层次感和科技感，适合互联网产品和年轻化品牌。`;
    case '3d':
      return `3D立体风格通过多层挤压和光影模拟实现立体效果，光源方向统一为左上方45°，挤压深度为${config.size * 0.08}px。正面渐变从亮色到暗色过渡，边缘高光和底部阴影增强真实感，适合游戏、娱乐类产品。`;
    default:
      return '';
  }
}

function generateMarkdown(config: IconConfig, sections: DesignGuidelineSection[]): string {
  let md = `# ${config.text.toUpperCase()} 图标设计规范\n\n`;
  md += `> 生成时间: ${new Date().toLocaleString()}\n>\n`;
  md += `> 风格: ${styleLabels[config.style]}\n`;
  md += `> 尺寸: ${config.size} × ${config.size}px\n\n`;

  sections.forEach((section) => {
    md += `## ${section.title}\n\n${section.content}\n\n`;

    if (section.items && section.items.length > 0) {
      md += `| 项目 | 值 | 说明 |\n|------|-----|------|\n`;
      section.items.forEach((item) => {
        md += `| ${item.label} | ${item.value} | ${item.description || '-'} |\n`;
      });
      md += '\n';
    }
  });

  return md;
}

function generateHtml(config: IconConfig, sections: DesignGuidelineSection[]): string {
  let html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${config.text.toUpperCase()} 图标设计规范</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
      line-height: 1.6;
      color: #1f2937;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
      background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }
    .header {
      text-align: center;
      padding: 40px;
      background: linear-gradient(135deg, ${config.primaryColor}, ${config.secondaryColor});
      border-radius: 16px;
      margin-bottom: 32px;
      color: white;
    }
    .header h1 { font-size: 32px; margin-bottom: 8px; }
    .header p { opacity: 0.9; }
    .color-swatch {
      display: inline-block;
      width: 16px;
      height: 16px;
      border-radius: 4px;
      margin-right: 8px;
      vertical-align: middle;
      border: 2px solid white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    section {
      background: white;
      padding: 32px;
      border-radius: 12px;
      margin-bottom: 24px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    h2 {
      font-size: 20px;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 2px solid ${config.primaryColor}20;
      color: ${config.primaryColor};
    }
    p { margin-bottom: 16px; color: #4b5563; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
    }
    th, td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid #e5e7eb;
    }
    th {
      background: #f9fafb;
      font-weight: 600;
      color: #374151;
    }
    tr:hover { background: #f9fafb; }
    .footer {
      text-align: center;
      padding: 24px;
      color: #9ca3af;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>${config.text.toUpperCase()} 图标设计规范</h1>
    <p>风格: ${styleLabels[config.style]} · ${config.size} × ${config.size}px · 版本 1.0.0</p>
  </div>
`;

  sections.forEach((section) => {
    html += `  <section>\n    <h2>${section.title}</h2>\n    <p>${section.content}</p>\n`;

    if (section.items && section.items.length > 0) {
      html += '    <table>\n      <thead>\n        <tr><th>项目</th><th>值</th><th>说明</th></tr>\n      </thead>\n      <tbody>\n';
      section.items.forEach((item) => {
        let value = item.value;
        if (/^#[0-9A-Fa-f]{6}$/.test(item.value)) {
          value = `<span class="color-swatch" style="background:${item.value}"></span>${item.value}`;
        }
        html += `        <tr><td>${item.label}</td><td>${value}</td><td>${item.description || '-'}</td></tr>\n`;
      });
      html += '      </tbody>\n    </table>\n';
    }

    html += '  </section>\n';
  });

  html += `  <div class="footer">
    <p>生成时间: ${new Date().toLocaleString()} · 图标设计系统 v1.0</p>
  </div>
</body>
</html>`;

  return html;
}

export function downloadMarkdown(doc: DesignSystemDoc, filename?: string): void {
  const blob = new Blob([doc.markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `${filename || 'design-guidelines'}.md`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadHtml(doc: DesignSystemDoc, filename?: string): void {
  const blob = new Blob([doc.html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `${filename || 'design-guidelines'}.html`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}
