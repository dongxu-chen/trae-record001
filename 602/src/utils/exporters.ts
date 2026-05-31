import type { Project, SVGElementData } from '@/types';

const DEFAULT_VALUES: Record<string, Record<string, any>> = {
  rect: { x: 0, y: 0, rx: 0, ry: 0, strokeWidth: 0, stroke: 'none' },
  circle: { cx: 0, cy: 0, strokeWidth: 0, stroke: 'none' },
  ellipse: { cx: 0, cy: 0, strokeWidth: 0, stroke: 'none' },
  line: { x1: 0, y1: 0, strokeWidth: 1 },
  path: { fill: 'none', strokeWidth: 1 },
  polygon: { strokeWidth: 0, stroke: 'none' },
  text: { x: 0, y: 0, fontSize: 16, fontFamily: 'Arial' },
};

const isDefaultValue = (type: string, key: string, value: any): boolean => {
  const defaults = DEFAULT_VALUES[type];
  if (!defaults) return false;
  return defaults[key] === value;
};

const formatNumber = (num: number, precision: number = 1): string => {
  const rounded = Number(num.toFixed(precision));
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(precision);
};

const compressPathData = (d: string): string => {
  if (!d) return '';
  
  return d
    .replace(/\s+/g, ' ')
    .replace(/([a-zA-Z])\s+/g, '$1')
    .replace(/\s+([a-zA-Z])/g, '$1')
    .replace(/(\d)\.0+(?=\D|$)/g, '$1')
    .replace(/0+(\d{1,2})/g, '$1')
    .trim();
};

const buildAttributes = (element: SVGElementData, compressed: boolean): string => {
  const { type, attributes, transform, visible } = element;
  const parts: string[] = [];

  const transformParts: string[] = [];
  
  if (transform.x !== 0 || transform.y !== 0) {
    transformParts.push(`translate(${formatNumber(transform.x)},${formatNumber(transform.y)})`);
  }
  if (transform.rotation !== 0) {
    transformParts.push(`rotate(${formatNumber(transform.rotation)})`);
  }
  if (transform.scaleX !== 1 || transform.scaleY !== 1) {
    if (transform.scaleX === transform.scaleY) {
      transformParts.push(`scale(${formatNumber(transform.scaleX)})`);
    } else {
      transformParts.push(`scale(${formatNumber(transform.scaleX)},${formatNumber(transform.scaleY)})`);
    }
  }
  
  if (transformParts.length > 0) {
    parts.push(`transform="${transformParts.join(' ')}"`);
  }

  if (visible === false) {
    parts.push('opacity="0.3"');
  }

  Object.entries(attributes).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (isDefaultValue(type, key, value) && compressed) return;
    
    const attrName = key.replace(/([A-Z])/g, '-$1').toLowerCase();
    
    if (key === 'd' && typeof value === 'string') {
      parts.push(`d="${compressed ? compressPathData(value) : value}"`);
    } else if (typeof value === 'number') {
      parts.push(`${attrName}="${formatNumber(value)}"`);
    } else {
      parts.push(`${attrName}="${value}"`);
    }
  });

  return parts.join(' ');
};

interface ExportOptions {
  compressed?: boolean;
  minify?: boolean;
  includeStyles?: boolean;
}

export const exportSVG = (project: Project, options: ExportOptions = {}): string => {
  const { width, height, elements } = project;
  const { compressed = false, minify = false } = options;
  
  const nl = minify ? '' : '\n';
  const indent = minify ? '' : '  ';

  let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${nl}`;

  elements.forEach(element => {
    const attrs = buildAttributes(element, compressed);
    const elementId = compressed ? '' : ` id="${element.id}"`;
    
    switch (element.type) {
      case 'rect':
        svgContent += `${indent}<rect${elementId} ${attrs}/>${nl}`;
        break;
      case 'circle':
        svgContent += `${indent}<circle${elementId} ${attrs}/>${nl}`;
        break;
      case 'ellipse':
        svgContent += `${indent}<ellipse${elementId} ${attrs}/>${nl}`;
        break;
      case 'line':
        svgContent += `${indent}<line${elementId} ${attrs}/>${nl}`;
        break;
      case 'path':
        svgContent += `${indent}<path${elementId} ${attrs}/>${nl}`;
        break;
      case 'polygon':
        svgContent += `${indent}<polygon${elementId} ${attrs}/>${nl}`;
        break;
      case 'text':
        svgContent += `${indent}<text${elementId} ${attrs}>${element.attributes.text || ''}</text>${nl}`;
        break;
    }
  });

  svgContent += `</svg>`;
  return svgContent;
};

export const exportJS = (project: Project, options: ExportOptions = {}): string => {
  const { width, height, elements, tracks } = project;
  const { compressed = false, minify = false } = options;
  
  const nl = minify ? '' : '\n';
  const indent = minify ? '' : '  ';
  const indent2 = minify ? '' : '    ';
  const indent3 = minify ? '' : '      ';

  let htmlContent = `<!DOCTYPE html>${nl}<html>${nl}<head>${nl}`;
  
  if (!minify) {
    htmlContent += `${indent}<meta charset="UTF-8">${nl}`;
    htmlContent += `${indent}<title>SVG Animation</title>${nl}`;
  }
  
  const cssStyles = minify 
    ? 'body{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#1a1a2e}.container{position:relative}svg{display:block}'
    : 'body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a1a2e; }\n.container { position: relative; }\nsvg { display: block; }';
    
  htmlContent += `${indent}<style>${cssStyles}</style>${nl}`;
  htmlContent += `</head>${nl}<body>${nl}`;
  htmlContent += `${indent}<div class="container">${nl}`;
  htmlContent += `${indent2}<svg id="a" xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${nl}`;

  elements.forEach((element, idx) => {
    const elId = compressed ? `e${idx}` : element.id;
    const attrs = buildAttributes(element, compressed).replace(`id="${element.id}"`, `id="${elId}"`);
    
    switch (element.type) {
      case 'rect':
        htmlContent += `${indent3}<rect ${attrs}/>${nl}`;
        break;
      case 'circle':
        htmlContent += `${indent3}<circle ${attrs}/>${nl}`;
        break;
      case 'ellipse':
        htmlContent += `${indent3}<ellipse ${attrs}/>${nl}`;
        break;
      case 'line':
        htmlContent += `${indent3}<line ${attrs}/>${nl}`;
        break;
      case 'path':
        htmlContent += `${indent3}<path ${attrs}/>${nl}`;
        break;
      case 'polygon':
        htmlContent += `${indent3}<polygon ${attrs}/>${nl}`;
        break;
      case 'text':
        htmlContent += `${indent3}<text ${attrs}>${element.attributes.text || ''}</text>${nl}`;
        break;
    }
  });

  htmlContent += `${indent2}</svg>${nl}`;
  htmlContent += `${indent}</div>${nl}`;
  
  const gsapUrl = minify 
    ? 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js'
    : 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js';
  const mpUrl = minify
    ? 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/MotionPathPlugin.min.js'
    : 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/MotionPathPlugin.min.js';

  htmlContent += `${indent}<script src="${gsapUrl}"></script>${nl}`;
  
  const hasMotionPath = tracks.some(t => t.type === 'motionPath');
  if (hasMotionPath) {
    htmlContent += `${indent}<script src="${mpUrl}"></script>${nl}`;
  }

  htmlContent += `${indent}<script>${nl}`;
  
  if (minify) {
    let jsCode = 'gsap.registerPlugin(MotionPathPlugin);';
    jsCode += 'const tl=gsap.timeline({repeat:-1,yoyo:!0});';
    
    tracks.forEach((track) => {
      const elementIndex = elements.findIndex(e => e.id === track.elementId);
      const sel = `#e${elementIndex}`;
      
      if (track.type === 'motionPath' && track.motionPath) {
        const path = compressed ? compressPathData(track.motionPath.path) : track.motionPath.path;
        jsCode += `tl.to("${sel}",{motionPath:{path:"${path}",autoRotate:${track.motionPath.orient === 'auto'}},duration:${track.duration},ease:"${track.easing}"},${track.delay});`;
      } else if (track.keyframes.length >= 1) {
        const prop = track.property;
        const kfCode = track.keyframes.map(kf => {
          const val = typeof kf.value === 'string' ? `"${kf.value}"` : kf.value;
          return `{${prop}:${val},ease:"${kf.easing || track.easing}"}`;
        }).join(',');
        jsCode += `tl.to("${sel}",{keyframes:[${kfCode}],duration:${track.duration}},${track.delay});`;
      }
    });
    
    htmlContent += jsCode;
  } else {
    htmlContent += `${indent2}gsap.registerPlugin(MotionPathPlugin);${nl}`;
    htmlContent += `${indent2}const tl = gsap.timeline({ repeat: -1, yoyo: true });${nl}`;
    
    tracks.forEach((track) => {
      const elementIndex = elements.findIndex(e => e.id === track.elementId);
      const sel = compressed ? `#e${elementIndex}` : `#${track.elementId}`;
      
      if (track.type === 'motionPath' && track.motionPath) {
        const path = compressed ? compressPathData(track.motionPath.path) : track.motionPath.path;
        htmlContent += `${indent2}tl.to("${sel}", {motionPath:{path:"${path}",autoRotate:${track.motionPath.orient === 'auto'}},duration:${track.duration},ease:"${track.easing}"},${track.delay});${nl}`;
      } else if (track.keyframes.length >= 1) {
        const kfStr = track.keyframes.map(kf => {
          const val = typeof kf.value === 'string' ? `"${kf.value}"` : kf.value;
          return `${indent3}{ ${track.property}: ${val}, ease: "${kf.easing || track.easing}" }`;
        }).join(`,${nl}`);
        htmlContent += `${indent2}tl.to("${sel}", {${nl}`;
        htmlContent += `${indent3}keyframes: [${nl}${kfStr}${nl}${indent3}],${nl}`;
        htmlContent += `${indent3}duration: ${track.duration}${nl}`;
        htmlContent += `${indent2}}, ${track.delay});${nl}`;
      }
    });
  }
  
  htmlContent += `${indent}</script>${nl}`;
  htmlContent += `</body>${nl}</html>`;

  return htmlContent;
};

export const exportProjectJSON = (project: Project, minify: boolean = false): string => {
  return minify ? JSON.stringify(project) : JSON.stringify(project, null, 2);
};

export const downloadFile = (content: string, filename: string, type: string = 'text/plain') => {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
