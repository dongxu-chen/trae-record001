import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

const A4_WIDTH = 210
const A4_HEIGHT = 297
const MARGIN = 10

export async function exportToPDF() {
  const element = document.getElementById('dashboard-content')
  if (!element) {
    alert('没有可导出的内容')
    return
  }

  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#f5f7fa',
    })

    const imgData = canvas.toDataURL('image/png')
    const imgWidth = canvas.width
    const imgHeight = canvas.height

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4',
    })

    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const contentWidth = pageWidth - MARGIN * 2
    const contentHeight = pageHeight - MARGIN * 2

    const ratio = contentWidth / imgWidth
    const scaledImgHeight = imgHeight * ratio

    const pagesNeeded = Math.ceil(scaledImgHeight / contentHeight)

    if (pagesNeeded === 1) {
      const imgX = MARGIN
      const imgY = MARGIN
      pdf.addImage(imgData, 'PNG', imgX, imgY, contentWidth, scaledImgHeight)
    } else {
      for (let page = 0; page < pagesNeeded; page++) {
        const srcY = (page * contentHeight) / ratio
        const srcHeight = Math.min(
          imgHeight - srcY,
          contentHeight / ratio
        )

        const pageCanvas = document.createElement('canvas')
        pageCanvas.width = imgWidth
        pageCanvas.height = srcHeight
        const pageCtx = pageCanvas.getContext('2d')
        pageCtx.drawImage(
          canvas,
          0, srcY, imgWidth, srcHeight,
          0, 0, imgWidth, srcHeight
        )

        const pageImgData = pageCanvas.toDataURL('image/png')
        const pageScaledHeight = srcHeight * ratio

        if (page > 0) {
          pdf.addPage()
        }

        pdf.addImage(
          pageImgData,
          'PNG',
          MARGIN,
          MARGIN,
          contentWidth,
          pageScaledHeight
        )

        pdf.setFontSize(10)
        pdf.setTextColor(150)
        pdf.text(
          `第 ${page + 1} 页 / 共 ${pagesNeeded} 页`,
          pageWidth / 2,
          pageHeight - 5,
          { align: 'center' }
        )
      }
    }

    pdf.setFontSize(12)
    pdf.setTextColor(100)
    pdf.text(
      `仪表板导出 - ${new Date().toLocaleString('zh-CN')}`,
      MARGIN,
      pageHeight - 5
    )

    pdf.save(`仪表板_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.pdf`)
  } catch (error) {
    console.error('导出PDF失败:', error)
    alert('导出PDF失败，请重试')
  }
}

export async function exportToPDFWithHeader() {
  const element = document.getElementById('dashboard-content')
  if (!element) {
    alert('没有可导出的内容')
    return
  }

  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#f5f7fa',
    })

    const imgData = canvas.toDataURL('image/png')
    const imgWidth = canvas.width
    const imgHeight = canvas.height

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4',
    })

    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()

    const headerHeight = 25
    const footerHeight = 15
    const contentTop = MARGIN + headerHeight
    const contentBottom = pageHeight - MARGIN - footerHeight
    const contentHeight = contentBottom - contentTop
    const contentWidth = pageWidth - MARGIN * 2

    const ratio = contentWidth / imgWidth
    const scaledImgHeight = imgHeight * ratio
    const pagesNeeded = Math.ceil(scaledImgHeight / contentHeight)

    for (let page = 0; page < pagesNeeded; page++) {
      if (page > 0) {
        pdf.addPage()
      }

      pdf.setFillColor(102, 126, 234)
      pdf.rect(0, 0, pageWidth, headerHeight, 'F')
      pdf.setTextColor(255, 255, 255)
      pdf.setFontSize(16)
      pdf.setFont(undefined, 'bold')
      pdf.text('动态仪表板报告', MARGIN, 15)
      pdf.setFontSize(10)
      pdf.setFont(undefined, 'normal')
      pdf.text(`生成时间: ${new Date().toLocaleString('zh-CN')}`, MARGIN, 22)

      const srcY = (page * contentHeight) / ratio
      const srcHeight = Math.min(
        imgHeight - srcY,
        contentHeight / ratio
      )

      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = imgWidth
      pageCanvas.height = srcHeight
      const pageCtx = pageCanvas.getContext('2d')
      pageCtx.drawImage(
        canvas,
        0, srcY, imgWidth, srcHeight,
        0, 0, imgWidth, srcHeight
      )

      const pageImgData = pageCanvas.toDataURL('image/png')
      const pageScaledHeight = srcHeight * ratio

      pdf.addImage(
        pageImgData,
        'PNG',
        MARGIN,
        contentTop,
        contentWidth,
        pageScaledHeight
      )

      pdf.setFillColor(245, 247, 250)
      pdf.rect(0, pageHeight - footerHeight, pageWidth, footerHeight, 'F')
      pdf.setTextColor(100)
      pdf.setFontSize(10)
      pdf.text(
        `第 ${page + 1} 页 / 共 ${pagesNeeded} 页`,
        pageWidth / 2,
        pageHeight - 5,
        { align: 'center' }
      )
      pdf.text(
        '动态仪表板构建器',
        MARGIN,
        pageHeight - 5
      )
    }

    pdf.save(`仪表板报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.pdf`)
  } catch (error) {
    console.error('导出PDF失败:', error)
    alert('导出PDF失败，请重试')
  }
}

export default exportToPDF
