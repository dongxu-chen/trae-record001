import express, { type Request, type Response } from 'express';

const router = express.Router();

interface IconConfig {
  text: string;
  size: number;
  primaryColor: string;
  secondaryColor: string;
  style: 'outline' | 'filled' | 'gradient' | '3d';
  padding: number;
  borderRadius: number;
  backgroundColor: string;
  showBackground: boolean;
}

interface BatchGenerateRequest {
  items: {
    text: string;
    config?: Partial<IconConfig>;
  }[];
  baseConfig: IconConfig;
}

function generateIconSvg(config: IconConfig): string {
  const { text, size, primaryColor, secondaryColor, style, padding, borderRadius, showBackground } = config;
  const displayText = text.substring(0, 2).toUpperCase();
  const center = size / 2;
  const fontSize = (size - padding * 2) * 0.5;

  let fillStyle = '';
  let backgroundStyle = '';

  if (showBackground) {
    if (style === 'gradient') {
      backgroundStyle = `fill="url(#bgGradient)"`;
    } else if (style === '3d') {
      backgroundStyle = `fill="${primaryColor}" filter="url(#shadow)"`;
    } else {
      backgroundStyle = `fill="${primaryColor}"`;
    }
  }

  if (style === 'outline') {
    fillStyle = `stroke="${primaryColor}" stroke-width="3" fill="none"`;
  } else if (style === 'gradient') {
    fillStyle = `fill="url(#textGradient)"`;
  } else {
    fillStyle = `fill="#ffffff"`;
  }

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <defs>
        <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${primaryColor}"/>
          <stop offset="50%" style="stop-color:${secondaryColor}"/>
          <stop offset="100%" style="stop-color:${primaryColor}"/>
        </linearGradient>
        <linearGradient id="textGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#ffffff"/>
          <stop offset="100%" style="stop-color:#e0e7ff"/>
        </linearGradient>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.3"/>
        </filter>
      </defs>
      ${showBackground ? `<rect x="${padding / 2}" y="${padding / 2}" width="${size - padding}" height="${size - padding}" rx="${borderRadius}" ${backgroundStyle}/>` : ''}
      <text x="${center}" y="${center}" font-family="'Space Grotesk', 'Inter', sans-serif" font-size="${fontSize}" font-weight="bold" text-anchor="middle" dominant-baseline="middle" ${fillStyle}>${displayText}</text>
    </svg>
  `.trim();
}

function svgToDataUrl(svg: string): string {
  const encoded = encodeURIComponent(svg)
    .replace(/'/g, '%27')
    .replace(/"/g, '%22');
  return `data:image/svg+xml;charset=UTF-8,${encoded}`;
}

router.post('/generate', (req: Request, res: Response) => {
  try {
    const config: IconConfig = req.body;
    const svg = generateIconSvg(config);
    const dataUrl = svgToDataUrl(svg);

    res.json({
      success: true,
      data: {
        svg,
        dataUrl,
      },
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to generate icon',
    });
  }
});

router.post('/batch-generate', (req: Request, res: Response) => {
  try {
    const { items, baseConfig }: BatchGenerateRequest = req.body;
    const results = items.map((item, index) => {
      const config: IconConfig = {
        ...baseConfig,
        ...item.config,
        text: item.text || 'A',
      };
      const svg = generateIconSvg(config);
      const dataUrl = svgToDataUrl(svg);

      return {
        id: `icon-${index}`,
        text: item.text,
        svg,
        dataUrl,
      };
    });

    res.json({
      success: true,
      data: results,
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to batch generate icons',
    });
  }
});

export default router;
