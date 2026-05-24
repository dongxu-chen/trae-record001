export function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function exportAsJSON(data, filename = 'mindmap.json') {
  const jsonStr = JSON.stringify(data, null, 2)
  downloadFile(jsonStr, filename, 'application/json')
}

export function exportAsMarkdown(markdown, filename = 'mindmap.md') {
  downloadFile(markdown, filename, 'text/markdown')
}

export function exportAsImage(canvasElement, filename = 'mindmap.png', scale = 2) {
  return new Promise((resolve, reject) => {
    try {
      const dataUrl = canvasElement.toDataURL('image/png', 1.0)
      const link = document.createElement('a')
      link.href = dataUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      resolve()
    } catch (error) {
      reject(error)
    }
  })
}

export function exportAsSVG(stage, filename = 'mindmap.svg') {
  const dataUrl = stage.toDataURL({ mimeType: 'image/svg+xml' })
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
