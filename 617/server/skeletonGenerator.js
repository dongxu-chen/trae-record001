import puppeteer from 'puppeteer';

const ANIMATION_TYPES = {
  none: 'none',
  pulse: 'pulse',
  shimmer: 'shimmer',
  wave: 'wave',
  blink: 'blink',
  gradient: 'gradient'
};

async function getBrowser() {
  return await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
}

export async function generateSkeleton(url, options = {}) {
  const {
    device = 'desktop',
    backgroundColor = null,
    highlightColor = null,
    animation = true,
    animationType = 'shimmer',
    animationSpeed = 1.5,
    removeImages = true,
    removeText = true,
    autoColor = true
  } = options;

  const browser = await getBrowser();

  try {
    const page = await browser.newPage();
    await setPageViewport(page, device);

    await page.goto(url, {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    await page.waitForTimeout(1000);

    const pageData = await extractPageData(page, { removeImages, removeText, device });

    const finalColors = {
      backgroundColor: backgroundColor || pageData.colors.backgroundColor,
      highlightColor: highlightColor || pageData.colors.highlightColor
    };

    const skeletonHTML = generateSkeletonHTML(pageData, {
      ...finalColors,
      animation,
      animationType,
      device,
      viewportMeta: pageData.viewportMeta
    });

    const skeletonCSS = generateSkeletonCSS({
      ...finalColors,
      animation,
      animationType,
      animationSpeed,
      device
    });

    return {
      url,
      html: skeletonHTML,
      css: skeletonCSS,
      layoutData: pageData,
      extractedColors: pageData.colors,
      viewportMeta: pageData.viewportMeta,
      elements: flattenElements(pageData.body)
    };

  } finally {
    await browser.close();
  }
}

export async function generateBatchSkeletons(urls, options = {}) {
  const browser = await getBrowser();
  const results = [];
  const errors = [];

  try {
    const page = await browser.newPage();
    await setPageViewport(page, options.device || 'desktop');

    for (let i = 0; i < urls.length; i++) {
      const url = urls[i];
      try {
        console.log(`Processing (${i + 1}/${urls.length}): ${url}`);
        
        await page.goto(url, {
          waitUntil: 'networkidle2',
          timeout: 30000
        });

        await page.waitForTimeout(800);

        const pageData = await extractPageData(page, {
          removeImages: options.removeImages ?? true,
          removeText: options.removeText ?? true,
          device: options.device || 'desktop'
        });

        const finalColors = {
          backgroundColor: options.backgroundColor || pageData.colors.backgroundColor,
          highlightColor: options.highlightColor || pageData.colors.highlightColor
        };

        const skeletonHTML = generateSkeletonHTML(pageData, {
          ...finalColors,
          animation: options.animation ?? true,
          animationType: options.animationType || 'shimmer',
          device: options.device || 'desktop',
          viewportMeta: pageData.viewportMeta
        });

        const skeletonCSS = generateSkeletonCSS({
          ...finalColors,
          animation: options.animation ?? true,
          animationType: options.animationType || 'shimmer',
          animationSpeed: options.animationSpeed || 1.5,
          device: options.device || 'desktop'
        });

        results.push({
          url,
          name: extractPageName(url),
          html: skeletonHTML,
          css: skeletonCSS,
          extractedColors: pageData.colors,
          success: true
        });
      } catch (error) {
        errors.push({
          url,
          error: error.message
        });
        results.push({
          url,
          name: extractPageName(url),
          success: false,
          error: error.message
        });
      }
    }

    return {
      results,
      errors,
      total: urls.length,
      success: results.filter(r => r.success).length,
      failed: errors.length
    };

  } finally {
    await browser.close();
  }
}

export async function parseSitemap(sitemapUrl) {
  const browser = await getBrowser();
  
  try {
    const page = await browser.newPage();
    
    try {
      await page.goto(sitemapUrl, {
        waitUntil: 'networkidle2',
        timeout: 15000
      });

      const content = await page.content();
      
      const urls = new Set();
      
      const locMatches = content.match(/<loc>([^<]+)<\/loc>/gi);
      if (locMatches) {
        locMatches.forEach(match => {
          const url = match.replace(/<\/?loc>/gi, '').trim();
          if (url.startsWith('http')) {
            urls.add(url);
          }
        });
      }
      
      const ahrefMatches = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('a'))
          .map(a => a.href)
          .filter(href => href && href.startsWith('http'));
      });
      
      ahrefMatches.forEach(url => urls.add(url));
      
      return {
        sitemapUrl,
        urls: Array.from(urls).slice(0, 50),
        total: Math.min(urls.size, 50)
      };
      
    } catch (error) {
      throw new Error(`Failed to parse sitemap: ${error.message}`);
    }
  } finally {
    await browser.close();
  }
}

async function setPageViewport(page, device) {
  if (device === 'mobile') {
    await page.setViewport({
      width: 375,
      height: 667,
      isMobile: true,
      hasTouch: true
    });
  } else {
    await page.setViewport({
      width: 1280,
      height: 800
    });
  }
}

async function extractPageData(page, options) {
  return await page.evaluate((opts) => {
    const { removeImages, removeText, device } = opts;
    
    function hexToRgb(hex) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
      } : null;
    }
    
    function rgbToHex(r, g, b) {
      return '#' + [r, g, b].map(x => {
        const hex = Math.round(Math.max(0, Math.min(255, x))).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      }).join('');
    }
    
    function parseColor(str) {
      if (!str || str === 'transparent' || str === 'rgba(0, 0, 0, 0)') return null;
      
      const rgbMatch = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if (rgbMatch) {
        return {
          r: parseInt(rgbMatch[1]),
          g: parseInt(rgbMatch[2]),
          b: parseInt(rgbMatch[3]),
          count: 1
        };
      }
      
      const hexMatch = str.match(/#([a-f0-9]{6}|[a-f0-9]{3})/i);
      if (hexMatch) {
        return hexToRgb(hexMatch[0]);
      }
      
      return null;
    }
    
    function adjustBrightness(color, factor) {
      return {
        r: color.r + (255 - color.r) * factor,
        g: color.g + (255 - color.g) * factor,
        b: color.b + (255 - color.b) * factor
      };
    }
    
    function getElementInfo(element, depth = 0, parentRect = null) {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      
      const tagName = element.tagName.toLowerCase();
      const className = typeof element.className === 'string' ? element.className : '';
      const id = element.id || '';
      
      if (rect.width < 5 || rect.height < 5) return null;
      if (rect.top < -50) return null;
      
      const display = style.display;
      if (display === 'none' || display === 'hidden') return null;
      
      const visibility = style.visibility;
      if (visibility === 'hidden') return null;
      
      const opacity = parseFloat(style.opacity);
      if (opacity === 0) return null;
      
      const elementType = detectElementType(element, tagName, className, style, rect);
      
      const relativeRect = parentRect ? {
        top: Math.round(rect.top - parentRect.top),
        left: Math.round(rect.left - parentRect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      } : {
        top: Math.round(rect.top),
        left: Math.round(rect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      };
      
      const absoluteRect = {
        top: Math.round(rect.top),
        left: Math.round(rect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      };
      
      const children = [];
      for (const child of element.children) {
        const childInfo = getElementInfo(child, depth + 1, rect);
        if (childInfo) {
          children.push(childInfo);
        }
      }
      
      return {
        id: `el-${depth}-${Math.random().toString(36).substr(2, 9)}`,
        tagName,
        className,
        htmlId: id,
        type: elementType,
        depth,
        rect: relativeRect,
        absoluteRect,
        style: {
          backgroundColor: style.backgroundColor,
          borderRadius: style.borderRadius,
          padding: style.padding,
          margin: style.margin,
          display: style.display,
          position: style.position
        },
        children
      };
    }
    
    function detectElementType(element, tagName, className, style, rect) {
      const classStr = className.toLowerCase();
      
      if (tagName === 'img' || classStr.includes('img') || classStr.includes('image') || classStr.includes('pic') || classStr.includes('picture')) {
        return 'image';
      }
      
      if (tagName === 'button' || classStr.includes('btn') || classStr.includes('button')) {
        return 'button';
      }
      
      if (tagName === 'input' || tagName === 'textarea' || classStr.includes('input') || tagName === 'select') {
        return 'input';
      }
      
      if (tagName === 'h1' || tagName === 'h2' || tagName === 'h3' || tagName === 'h4' || tagName === 'h5' || tagName === 'h6') {
        return 'heading';
      }
      
      if (tagName === 'nav' || classStr.includes('nav') || classStr.includes('menu')) {
        return 'navigation';
      }
      
      if (tagName === 'header' || classStr.includes('header')) {
        return 'header';
      }
      
      if (tagName === 'footer' || classStr.includes('footer')) {
        return 'footer';
      }
      
      if (tagName === 'aside' || classStr.includes('sidebar')) {
        return 'sidebar';
      }
      
      if (classStr.includes('card')) {
        return 'card';
      }
      
      if (classStr.includes('list') || tagName === 'ul' || tagName === 'ol') {
        return 'list';
      }
      
      if (classStr.includes('avatar')) {
        return 'avatar';
      }
      
      if (tagName === 'li') {
        return 'list-item';
      }
      
      if (tagName === 'p' || tagName === 'span' || tagName === 'a' || tagName === 'label') {
        const textContent = element.textContent?.trim() || '';
        if (textContent.length > 0) {
          return 'text-line';
        }
      }
      
      const textContent = element.textContent?.trim() || '';
      if (textContent.length > 0 && textContent.length < 80 && rect.width / rect.height > 2.5) {
        return 'text-line';
      }
      
      if (textContent.length > 80) {
        return 'text-block';
      }
      
      if (Math.abs(rect.width - rect.height) < Math.min(rect.width, rect.height) * 0.3) {
        if (rect.width < 120 && rect.width > 20) {
          return 'avatar';
        }
      }
      
      if (classStr.includes('container') || tagName === 'div' || tagName === 'section' || tagName === 'article' || tagName === 'main') {
        return 'container';
      }
      
      return 'container';
    }
    
    function extractDominantColors() {
      const colorMap = new Map();
      const elements = document.querySelectorAll('*');
      
      for (const el of elements) {
        const style = window.getComputedStyle(el);
        
        const bgColor = parseColor(style.backgroundColor);
        if (bgColor) {
          const key = `${bgColor.r},${bgColor.g},${bgColor.b}`;
          const existing = colorMap.get(key) || { r: bgColor.r, g: bgColor.g, b: bgColor.b, count: 0 };
          existing.count += 1;
          colorMap.set(key, existing);
        }
        
        const textColor = parseColor(style.color);
        if (textColor) {
          const brightness = (textColor.r * 299 + textColor.g * 587 + textColor.b * 114) / 1000;
          if (brightness < 200) {
            const key = `${textColor.r},${textColor.g},${textColor.b}`;
            const existing = colorMap.get(key) || { r: textColor.r, g: textColor.g, b: textColor.b, count: 0 };
            existing.count += 0.5;
            colorMap.set(key, existing);
          }
        }
      }
      
      const colors = Array.from(colorMap.values()).sort((a, b) => b.count - a.count);
      
      const bodyStyle = window.getComputedStyle(document.body);
      const pageBg = parseColor(bodyStyle.backgroundColor) || { r: 255, g: 255, b: 255 };
      
      let bgColor = pageBg;
      let hlColor = adjustBrightness(pageBg, 0.1);
      
      for (const color of colors) {
        const brightness = (color.r * 299 + color.g * 587 + color.b * 114) / 1000;
        if (brightness > 200 && color.count > 5) {
          bgColor = color;
          break;
        }
      }
      
      for (const color of colors) {
        const brightness = (color.r * 299 + color.g * 587 + color.b * 114) / 1000;
        if (brightness < 200 && brightness > 100 && color.count > 3) {
          hlColor = color;
          break;
        }
      }
      
      const bgBrightness = (bgColor.r * 299 + bgColor.g * 587 + bgColor.b * 114) / 1000;
      
      if (bgBrightness > 220) {
        hlColor = adjustBrightness(bgColor, -0.15);
      } else if (bgBrightness > 180) {
        hlColor = adjustBrightness(bgColor, -0.1);
      } else {
        hlColor = adjustBrightness(bgColor, 0.2);
      }
      
      return {
        backgroundColor: rgbToHex(bgColor.r, bgColor.g, bgColor.b),
        highlightColor: rgbToHex(hlColor.r, hlColor.g, hlColor.b)
      };
    }
    
    function getViewportMeta() {
      const viewportMeta = document.querySelector('meta[name="viewport"]');
      return viewportMeta ? viewportMeta.getAttribute('content') : null;
    }
    
    const bodyInfo = getElementInfo(document.body);
    const pageWidth = document.documentElement.scrollWidth;
    const pageHeight = Math.min(document.documentElement.scrollHeight, window.innerHeight * 3);
    const colors = extractDominantColors();
    const viewportMeta = getViewportMeta();
    
    return {
      body: bodyInfo,
      pageWidth,
      pageHeight,
      devicePixelRatio: window.devicePixelRatio,
      colors,
      viewportMeta
    };
  }, options);
}

function flattenElements(element, flatList = []) {
  if (!element) return flatList;
  
  flatList.push({
    id: element.id,
    type: element.type,
    rect: element.absoluteRect,
    style: element.style
  });
  
  if (element.children) {
    element.children.forEach(child => flattenElements(child, flatList));
  }
  
  return flatList;
}

function extractPageName(url) {
  try {
    const urlObj = new URL(url);
    const path = urlObj.pathname.replace(/\/$/, '');
    const parts = path.split('/');
    return parts[parts.length - 1] || urlObj.hostname;
  } catch {
    return url;
  }
}

function generateSkeletonHTML(pageData, options) {
  const { pageWidth, pageHeight, body, viewportMeta } = pageData;
  const { backgroundColor, device: genDevice } = options;
  
  function renderElement(element, parentHasAbsolute = false) {
    if (!element) return '';
    
    const { type, rect, absoluteRect, style, id } = element;
    
    const isAbsolute = style.position === 'absolute' || style.position === 'fixed';
    const useAbsolute = parentHasAbsolute || isAbsolute;
    const useRect = useAbsolute ? absoluteRect : rect;
    
    const posStyle = useAbsolute 
      ? `position: absolute; top: ${useRect.top}px; left: ${useRect.left}px;`
      : `position: relative;`;
    
    const sizeStyle = `width: ${useRect.width}px; height: ${useRect.height}px;`;
    
    let elementStyle = `${posStyle} ${sizeStyle}`;
    
    if (style.borderRadius && style.borderRadius !== '0px') {
      elementStyle += ` border-radius: ${style.borderRadius};`;
    }
    
    let className = 'skeleton-item';
    if (type === 'image') {
      className += ' skeleton-image';
    } else if (type === 'avatar') {
      className += ' skeleton-avatar';
    } else if (type === 'text-line' || type === 'heading') {
      className += ' skeleton-text-line';
    } else if (type === 'text-block') {
      className += ' skeleton-text-block';
    } else if (type === 'button') {
      className += ' skeleton-button';
    } else if (type === 'input') {
      className += ' skeleton-input';
    } else if (type === 'card') {
      className += ' skeleton-card';
    } else if (type === 'navigation') {
      className += ' skeleton-navigation';
    } else if (type === 'header') {
      className += ' skeleton-header';
    } else if (type === 'footer') {
      className += ' skeleton-footer';
    } else if (type === 'sidebar') {
      className += ' skeleton-sidebar';
    } else if (type === 'list') {
      className += ' skeleton-list';
    } else if (type === 'list-item') {
      className += ' skeleton-list-item';
    } else if (type === 'container') {
      className += ' skeleton-container-block';
    }
    
    let childrenHTML = '';
    if (element.children && element.children.length > 0) {
      childrenHTML = element.children
        .map(child => renderElement(child, useAbsolute))
        .join('');
    }
    
    const isWrapper = type === 'container' || type === 'navigation' || 
                       type === 'header' || type === 'footer' || 
                       type === 'sidebar' || type === 'card' || type === 'list';
    
    const dataAttrs = `data-element-id="${id}" data-element-type="${type}"`;
    
    if (isWrapper) {
      return `<div class="${className}" ${dataAttrs} style="${elementStyle}">${childrenHTML}</div>`;
    } else {
      return `<div class="${className}" ${dataAttrs} style="${elementStyle}"></div>${childrenHTML}`;
    }
  }
  
  const bodyHTML = body ? renderElement(body, false) : '';
  
  const viewportTag = genDevice === 'mobile' 
    ? `<meta name="viewport" content="${viewportMeta || 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'}">`
    : '';
  
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  ${viewportTag}
  <title>Skeleton Screen</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      overflow-x: hidden;
    }
  </style>
</head>
<body>
<div class="skeleton-container" style="width: ${pageWidth}px; min-height: ${pageHeight}px; position: relative; background: ${backgroundColor};">
  ${bodyHTML}
</div>
</body>
</html>
  `.trim();
}

function generateSkeletonCSS(options) {
  const { backgroundColor, highlightColor, animation, animationType, animationSpeed, device } = options;
  
  let animationCSS = '';
  let backgroundStyle = `background: ${highlightColor};`;
  
  if (animation && animationType !== 'none') {
    const speed = animationSpeed || 1.5;
    
    switch (animationType) {
      case 'pulse':
        animationCSS = `
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
`;
        backgroundStyle = `background: ${highlightColor}; animation: skeleton-pulse ${speed}s ease-in-out infinite;`;
        break;
        
      case 'blink':
        animationCSS = `
@keyframes skeleton-blink {
  0%, 50%, 100% { opacity: 1; }
  25%, 75% { opacity: 0.3; }
}
`;
        backgroundStyle = `background: ${highlightColor}; animation: skeleton-blink ${speed}s step-start infinite;`;
        break;
        
      case 'wave':
        animationCSS = `
@keyframes skeleton-wave {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.skeleton-item {
  overflow: hidden;
  position: relative;
}
.skeleton-item::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, ${backgroundColor}, transparent);
  animation: skeleton-wave ${speed}s ease-in-out infinite;
}
`;
        backgroundStyle = `background: ${highlightColor};`;
        break;
        
      case 'gradient':
        animationCSS = `
@keyframes skeleton-gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
`;
        backgroundStyle = `background: linear-gradient(270deg, ${backgroundColor}, ${highlightColor}, ${backgroundColor}); background-size: 400% 400%; animation: skeleton-gradient ${speed * 2}s ease infinite;`;
        break;
        
      case 'shimmer':
      default:
        animationCSS = `
@keyframes skeleton-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
`;
        backgroundStyle = `background: linear-gradient(90deg, ${backgroundColor} 25%, ${highlightColor} 50%, ${backgroundColor} 75%); background-size: 200% 100%; animation: skeleton-shimmer ${speed}s infinite;`;
        break;
    }
  }
  
  const mobileStyles = device === 'mobile' ? `
@media (max-width: 480px) {
  .skeleton-container {
    width: 100% !important;
    max-width: 100%;
    overflow-x: hidden;
  }
  
  .skeleton-item {
    box-sizing: border-box;
  }
}
` : '';
  
  return `
${animationCSS}

* {
  box-sizing: border-box;
}

.skeleton-container {
  overflow: hidden;
  background: ${backgroundColor};
}

.skeleton-item {
  ${backgroundStyle}
  border-radius: 4px;
  box-sizing: border-box;
}

.skeleton-image {
  border-radius: 8px;
}

.skeleton-avatar {
  border-radius: 50%;
}

.skeleton-text-line {
  border-radius: 4px;
  height: 14px !important;
  min-height: 14px;
}

.skeleton-text-block {
  border-radius: 4px;
}

.skeleton-button {
  border-radius: 6px;
}

.skeleton-input {
  border-radius: 6px;
  border: 1px solid rgba(0,0,0,0.1);
}

.skeleton-card {
  border-radius: 12px;
  overflow: hidden;
}

.skeleton-header,
.skeleton-footer,
.skeleton-navigation,
.skeleton-sidebar,
.skeleton-list {
  background: transparent;
  animation: none;
}

.skeleton-container-block {
  background: transparent;
  animation: none;
}

.skeleton-list-item {
  border-radius: 4px;
}

${mobileStyles}
`.trim();
}

export { ANIMATION_TYPES };
