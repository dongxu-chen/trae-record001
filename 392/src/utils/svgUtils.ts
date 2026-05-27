import { Icon } from '../types';

export const generateSvgCode = (icon: Icon, color: string, size: number): string => {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}">
  <path d="${icon.svgPath}"/>
</svg>`;
};

export const generateJsxCode = (icon: Icon, color: string, size: number): string => {
  const componentName = icon.name.charAt(0).toUpperCase() + icon.name.slice(1).replace(/[-_]/g, '');
  return `const ${componentName}Icon = ({ color = "${color}", size = ${size} }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="${icon.svgPath}"/>
  </svg>
);

export default ${componentName}Icon;`;
};

export const createSvgElement = (svgPath: string, color: string, size: number): string => {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}"><path d="${svgPath}"/></svg>`;
};

export const parseSvgFile = (content: string): string | null => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(content, 'image/svg+xml');
  const pathElement = doc.querySelector('path');
  
  if (pathElement) {
    return pathElement.getAttribute('d');
  }
  
  return null;
};

export const extractSvgPath = (svgContent: string): string => {
  const match = svgContent.match(/d="([^"]+)"/);
  return match ? match[1] : '';
};
