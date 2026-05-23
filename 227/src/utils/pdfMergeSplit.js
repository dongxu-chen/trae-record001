export async function mergePDFCanvases(pageDataList) {
  const pdfData = {
    type: 'merged',
    pages: pageDataList,
    createdAt: new Date().toISOString(),
    pageCount: pageDataList.length
  };
  
  return pdfData;
}

export function splitPDFPages(allPages, ranges) {
  const splits = [];
  
  ranges.forEach((range, index) => {
    const { start, end, name } = range;
    const startIdx = parseInt(start) - 1;
    const endIdx = parseInt(end) - 1;
    
    if (startIdx >= 0 && endIdx < allPages.length && startIdx <= endIdx) {
      splits.push({
        name: name || `拆分文档_${index + 1}`,
        pages: allPages.slice(startIdx, endIdx + 1),
        pageRange: `${start}-${end}`
      });
    }
  });
  
  return splits;
}

export function parsePageRange(rangeString, totalPages) {
  const ranges = [];
  const parts = rangeString.split(',');
  
  parts.forEach(part => {
    part = part.trim();
    if (part.includes('-')) {
      const [start, end] = part.split('-').map(n => parseInt(n.trim()));
      if (!isNaN(start) && !isNaN(end)) {
        ranges.push({
          start: Math.max(1, start),
          end: Math.min(totalPages, end),
          name: `pages_${start}-${end}`
        });
      }
    } else {
      const page = parseInt(part);
      if (!isNaN(page)) {
        ranges.push({
          start: Math.max(1, page),
          end: Math.min(totalPages, page),
          name: `page_${page}`
        });
      }
    }
  });
  
  return ranges;
}

export function extractPages(pageDataList, pageNumbers) {
  return pageNumbers
    .map(num => pageDataList[num - 1])
    .filter(page => page !== undefined);
}

export function reorderPages(pageDataList, newOrder) {
  return newOrder.map(index => pageDataList[index]).filter(page => page !== undefined);
}

export function rotatePage(pageData, degrees) {
  return {
    ...pageData,
    rotation: ((pageData.rotation || 0) + degrees) % 360
  };
}

export function deletePages(pageDataList, pageNumbers) {
  return pageDataList.filter((_, index) => !pageNumbers.includes(index + 1));
}

export function downloadAsJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.json') ? filename : `${filename}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function downloadAsImage(canvas, filename) {
  const url = canvas.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.png') ? filename : `${filename}.png`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

export function readPDFFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

export function getPageInfo(pageData, index) {
  return {
    index: index + 1,
    width: pageData.width || 595,
    height: pageData.height || 842,
    rotation: pageData.rotation || 0,
    hasAnnotations: (pageData.annotations || []).length > 0,
    hasFormFields: (pageData.formFields || []).length > 0
  };
}

export function validateMergeFiles(files) {
  const errors = [];
  
  files.forEach((file, index) => {
    if (file.type !== 'application/pdf') {
      errors.push(`文件 ${index + 1}: 不是有效的PDF文件`);
    }
  });
  
  return errors;
}

export function validateSplitRanges(ranges, totalPages) {
  const errors = [];
  
  ranges.forEach((range, index) => {
    if (range.start < 1 || range.start > totalPages) {
      errors.push(`范围 ${index + 1}: 起始页码超出范围`);
    }
    if (range.end < 1 || range.end > totalPages) {
      errors.push(`范围 ${index + 1}: 结束页码超出范围`);
    }
    if (range.start > range.end) {
      errors.push(`范围 ${index + 1}: 起始页码大于结束页码`);
    }
  });
  
  return errors;
}
