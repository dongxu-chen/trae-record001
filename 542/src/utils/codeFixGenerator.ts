import type { RGB, CodeFix, CodeFormat, EnhancedSuggestion } from '@/types';
import { rgbToHex } from '@/utils/color';

export function generateCodeFixes(
  originalColor: RGB,
  suggestedColor: RGB,
  property: string = 'color',
  selector: string = '.element'
): CodeFix[] {
  const origHex = rgbToHex(originalColor).toLowerCase();
  const suggHex = rgbToHex(suggestedColor).toLowerCase();

  const fixes: CodeFix[] = [];

  fixes.push({
    format: 'css',
    original: `${selector} {\n  ${property}: ${origHex};\n}`,
    fixed: `${selector} {\n  ${property}: ${suggHex};\n}`,
    selector,
    property,
  });

  const tailwindMap: Record<string, string> = {
    color: 'text',
    'background-color': 'bg',
    'border-color': 'border',
  };

  const twPrefix = tailwindMap[property] || property;
  fixes.push({
    format: 'tailwind',
    original: `${twPrefix}-[${origHex}]`,
    fixed: `${twPrefix}-[${suggHex}]`,
    selector,
    property,
  });

  fixes.push({
    format: 'inline',
    original: `style="${property}: ${origHex}"`,
    fixed: `style="${property}: ${suggHex}"`,
    selector,
    property,
  });

  fixes.push({
    format: 'scss',
    original: `$${property.replace('-color', '')}: ${origHex};`,
    fixed: `$${property.replace('-color', '')}: ${suggHex};`,
    selector,
    property,
  });

  return fixes;
}

export function generateEnhancedSuggestionWithCode(
  original: RGB,
  suggested: RGB,
  contrastRatio: number,
  aaPass: boolean,
  aaaPass: boolean
): EnhancedSuggestion {
  const alternatives = [
    { type: 'text' as const, label: '文本标签', description: '在图形旁添加明确的文字说明，不依赖颜色区分', icon: 'T' },
    { type: 'icon' as const, label: '图标区分', description: '使用不同的图标形状来表达含义，而非仅靠颜色', icon: '◆' },
    { type: 'pattern' as const, label: '纹理填充', description: '使用不同的填充纹理（斜纹、点状、条纹）来区分', icon: '▦' },
    { type: 'outline' as const, label: '边框样式', description: '使用不同粗细、样式的边框来区分状态', icon: '□' },
    { type: 'border' as const, label: '附加标识', description: '添加勾选标记、箭头或文字徽章作为额外提示', icon: '✓' },
  ];

  const visualLabels = [
    { type: 'text' as const, value: 'OK', display: '状态文字' },
    { type: 'icon' as const, value: '✓', display: '图标标记' },
    { type: 'pattern' as const, value: '▨', display: '纹理填充' },
  ];

  const codeFixes = [
    ...generateCodeFixes(original, suggested, 'color'),
    ...generateCodeFixes(original, suggested, 'background-color'),
  ];

  return {
    original,
    suggested,
    contrastRatio,
    aaPass,
    aaaPass,
    alternatives,
    visualLabels,
    codeFixes,
  };
}

export function formatCodeDiff(codeFix: CodeFix): string {
  return `--- ${codeFix.format.toUpperCase()} ---\n- ${codeFix.original}\n+ ${codeFix.fixed}`;
}

export function generateBatchFixSummary(issues: { foreground: RGB; background: RGB }[]): string {
  const uniqueColors = new Map<string, { original: RGB; suggested: RGB; count: number }>();

  for (const issue of issues) {
    const key = rgbToHex(issue.foreground);
    if (!uniqueColors.has(key)) {
      uniqueColors.set(key, {
        original: issue.foreground,
        suggested: issue.background,
        count: 0,
      });
    }
    uniqueColors.get(key)!.count++;
  }

  let summary = '/* ==================================================\n';
  summary += '   ColorA11y 自动修复建议\n';
  summary += '   生成时间: ' + new Date().toISOString() + '\n';
  summary += '   ================================================== */\n\n';

  uniqueColors.forEach((value, key) => {
    const suggestedHex = rgbToHex(value.suggested);
    summary += `/* 问题颜色: ${key} (出现 ${value.count} 次) */\n`;
    summary += `/* 建议替换: ${suggestedHex} */\n`;
    summary += `--color-fix-${key.slice(1)}: ${suggestedHex};\n\n`;
  });

  return summary;
}
