export function downloadDataUrl(dataUrl: string, filename: string): void {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function canvasToPng(canvas: HTMLCanvasElement, filename: string): void {
  const dataUrl = canvas.toDataURL('image/png');
  downloadDataUrl(dataUrl, filename);
}

export function canvasToSvg(canvas: HTMLCanvasElement, filename: string): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const svgContent = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
      <foreignObject width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml">
          <img src="${canvas.toDataURL('image/png')}" width="${canvas.width}" height="${canvas.height}"/>
        </div>
      </foreignObject>
    </svg>
  `.trim();

  const svgBlob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
  const svgUrl = URL.createObjectURL(svgBlob);
  downloadDataUrl(svgUrl, filename);
  URL.revokeObjectURL(svgUrl);
}

export function downloadSvg(svgString: string, filename: string): void {
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
  const svgUrl = URL.createObjectURL(svgBlob);
  downloadDataUrl(svgUrl, filename);
  URL.revokeObjectURL(svgUrl);
}

export async function downloadBatch(
  items: { name: string; dataUrl: string }[],
  format: 'png' | 'svg'
): Promise<void> {
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const ext = format === 'png' ? '.png' : '.svg';
    downloadDataUrl(item.dataUrl, `${item.name}${ext}`);
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
}
