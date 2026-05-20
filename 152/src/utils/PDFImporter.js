import * as pdfjsLib from 'pdfjs-dist'
import * as pdfjsWorker from 'pdfjs-dist/build/pdf.worker.entry'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

class PDFImporter {
  constructor() {
    this.loading = false
  }

  async loadFile(file) {
    this.loading = true
    try {
      const arrayBuffer = await file.arrayBuffer()
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
      return pdf
    } finally {
      this.loading = false
    }
  }

  async parsePage(pdf, pageNumber = 1, scale = 2) {
    const page = await pdf.getPage(pageNumber)
    const viewport = page.getViewport({ scale })
    
    const operatorList = await page.getOperatorList()
    const fnArray = operatorList.fnArray
    const argsArray = operatorList.argsArray
    
    const paths = []
    let currentPath = null
    
    for (let i = 0; i < fnArray.length; i++) {
      const fn = fnArray[i]
      const args = argsArray[i]
      
      switch (fn) {
        case pdfjsLib.OPS.moveTo:
          if (currentPath && currentPath.length > 0) {
            paths.push([...currentPath])
          }
          currentPath = [['M', args[0], viewport.height - args[1]]]
          break
          
        case pdfjsLib.OPS.lineTo:
          if (currentPath) {
            currentPath.push(['L', args[0], viewport.height - args[1]])
          }
          break
          
        case pdfjsLib.OPS.curveTo:
          if (currentPath) {
            currentPath.push([
              'C',
              args[0], viewport.height - args[1],
              args[2], viewport.height - args[3],
              args[4], viewport.height - args[5]
            ])
          }
          break
          
        case pdfjsLib.OPS.curveTo2:
          if (currentPath && currentPath.length > 0) {
            const lastPt = currentPath[currentPath.length - 1].slice(-2)
            currentPath.push([
              'C',
              args[0], viewport.height - args[1],
              args[2], viewport.height - args[3],
              args[2], viewport.height - args[3]
            ])
          }
          break
          
        case pdfjsLib.OPS.curveTo3:
          if (currentPath) {
            currentPath.push([
              'C',
              args[0], viewport.height - args[1],
              args[0], viewport.height - args[1],
              args[2], viewport.height - args[3]
            ])
          }
          break
          
        case pdfjsLib.OPS.closePath:
          if (currentPath) {
            currentPath.push(['Z'])
            paths.push([...currentPath])
            currentPath = null
          }
          break
          
        case pdfjsLib.OPS.rectangle:
          const x = args[0]
          const y = viewport.height - args[1] - args[3]
          const w = args[2]
          const h = args[3]
          paths.push([
            ['M', x, y],
            ['L', x + w, y],
            ['L', x + w, y + h],
            ['L', x, y + h],
            ['Z']
          ])
          break
      }
    }
    
    if (currentPath && currentPath.length > 0) {
      paths.push(currentPath)
    }
    
    return {
      paths: paths.map(p => this.commandsToSVG(p)),
      width: viewport.width,
      height: viewport.height,
      pageNumber
    }
  }

  commandsToSVG(commands) {
    return commands.map(cmd => {
      switch (cmd[0]) {
        case 'M': return `M${cmd[1]},${cmd[2]}`
        case 'L': return `L${cmd[1]},${cmd[2]}`
        case 'C': return `C${cmd[1]},${cmd[2]},${cmd[3]},${cmd[4]},${cmd[5]},${cmd[6]}`
        case 'Z': return 'Z'
        default: return ''
      }
    }).join('')
  }

  async importPDF(file, options = {}) {
    const pdf = await this.loadFile(file)
    const pageData = await this.parsePage(pdf, options.page || 1, options.scale || 2)
    return pageData
  }

  async getAllPagesInfo(file) {
    const pdf = await this.loadFile(file)
    const pages = []
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const viewport = page.getViewport({ scale: 1 })
      pages.push({
        pageNumber: i,
        width: viewport.width,
        height: viewport.height
      })
    }
    return pages
  }
}

export const pdfImporter = new PDFImporter()
export default PDFImporter
