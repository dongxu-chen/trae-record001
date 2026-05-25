import { ANNOTATION_CATEGORIES, ANNOTATION_TYPES } from '../constants'

export const exportToCOCO = (imagesData, projectInfo = {}) => {
  const categories = ANNOTATION_CATEGORIES.map((cat, index) => ({
    id: index + 1,
    name: cat.id,
    supercategory: 'chart_element'
  }))

  const categoryMap = new Map(ANNOTATION_CATEGORIES.map((cat, index) => [cat.id, index + 1]))

  let annotationId = 1
  const cocoImages = []
  const cocoAnnotations = []

  imagesData.forEach((imgData, imgIndex) => {
    const { image, annotations } = imgData

    cocoImages.push({
      id: imgIndex + 1,
      file_name: image.name,
      width: image.width,
      height: image.height,
      coco_url: '',
      date_captured: new Date().toISOString(),
      license: 1
    })

    annotations.forEach(ann => {
      if (ann.type === ANNOTATION_TYPES.RECTANGLE && ann.imageCoords) {
        const coords = ann.imageCoords
        const categoryId = categoryMap.get(ann.category) || 1

        cocoAnnotations.push({
          id: annotationId++,
          image_id: imgIndex + 1,
          category_id: categoryId,
          segmentation: [
            coords.x, coords.y,
            coords.x + coords.width, coords.y,
            coords.x + coords.width, coords.y + coords.height,
            coords.x, coords.y + coords.height
          ],
          area: coords.width * coords.height,
          bbox: [coords.x, coords.y, coords.width, coords.height],
          iscrowd: 0,
          attributes: {
            label: ann.label || '',
            type: ann.type
          }
        })
      } else if (ann.type === ANNOTATION_TYPES.ARROW && ann.imageCoords) {
        const coords = ann.imageCoords
        const categoryId = categoryMap.get(ann.category) || 1

        cocoAnnotations.push({
          id: annotationId++,
          image_id: imgIndex + 1,
          category_id: categoryId,
          segmentation: [coords.x1, coords.y1, coords.x2, coords.y2],
          area: 0,
          bbox: [
            Math.min(coords.x1, coords.x2),
            Math.min(coords.y1, coords.y2),
            Math.abs(coords.x2 - coords.x1),
            Math.abs(coords.y2 - coords.y1)
          ],
          iscrowd: 0,
          attributes: {
            label: ann.label || '',
            type: ann.type,
            start_point: [coords.x1, coords.y1],
            end_point: [coords.x2, coords.y2]
          }
        })
      } else if (ann.type === ANNOTATION_TYPES.TEXT && ann.imageCoords) {
        const coords = ann.imageCoords
        const categoryId = categoryMap.get(ann.category) || 1

        cocoAnnotations.push({
          id: annotationId++,
          image_id: imgIndex + 1,
          category_id: categoryId,
          segmentation: [coords.x, coords.y],
          area: 0,
          bbox: [coords.x, coords.y, 0, 0],
          iscrowd: 0,
          attributes: {
            label: ann.label || '',
            type: ann.type,
            text: coords.text || ann.label
          }
        })
      }
    })
  })

  const cocoData = {
    info: {
      description: projectInfo.name || 'Chart Annotation Dataset',
      url: '',
      version: '1.0',
      year: new Date().getFullYear(),
      contributor: 'Chart Annotation Tool',
      date_created: new Date().toISOString()
    },
    licenses: [
      {
        id: 1,
        name: 'Unknown',
        url: ''
      }
    ],
    categories,
    images: cocoImages,
    annotations: cocoAnnotations
  }

  return cocoData
}

export const exportToVOC = (imageData, imageInfo) => {
  const { image, annotations } = imageData

  const objects = annotations
    .filter(ann => ann.type === ANNOTATION_TYPES.RECTANGLE && ann.imageCoords)
    .map(ann => {
      const coords = ann.imageCoords
      const categoryInfo = ANNOTATION_CATEGORIES.find(c => c.id === ann.category)

      return {
        name: ann.category,
        pose: 'Unspecified',
        truncated: 0,
        difficult: 0,
        occluded: 0,
        bndbox: {
          xmin: Math.round(coords.x),
          ymin: Math.round(coords.y),
          xmax: Math.round(coords.x + coords.width),
          ymax: Math.round(coords.y + coords.height)
        },
        category: categoryInfo,
        label: ann.label || ''
      }
    })

  const vocXml = `<?xml version="1.0" encoding="UTF-8"?>
<annotation>
  <folder>${imageInfo.folder || 'images'}</folder>
  <filename>${image.name}</filename>
  <path>${imageInfo.path || image.name}</path>
  <source>
    <database>Chart Annotation</database>
    <annotation>Chart Annotation Tool</annotation>
    <image>flickr</image>
  </source>
  <size>
    <width>${image.width}</width>
    <height>${image.height}</height>
    <depth>3</depth>
  </size>
  <segmented>0</segmented>
${objects.map(obj => `  <object>
    <name>${obj.name}</name>
    <pose>${obj.pose}</pose>
    <truncated>${obj.truncated}</truncated>
    <difficult>${obj.difficult}</difficult>
    <occluded>${obj.occluded}</occluded>
    <bndbox>
      <xmin>${obj.bndbox.xmin}</xmin>
      <ymin>${obj.bndbox.ymin}</ymin>
      <xmax>${obj.bndbox.xmax}</xmax>
      <ymax>${obj.bndbox.ymax}</ymax>
    </bndbox>
    <label>${obj.label}</label>
  </object>`).join('\n')}
</annotation>`

  return vocXml
}

export const exportToJSON = (imagesData, projectInfo = {}) => {
  return {
    project: {
      id: projectInfo.id || 'unknown',
      name: projectInfo.name || '未命名项目',
      description: projectInfo.description || '',
      exportDate: new Date().toISOString(),
      exportVersion: '1.0'
    },
    categories: ANNOTATION_CATEGORIES,
    images: imagesData.map(imgData => ({
      id: imgData.image.id,
      name: imgData.image.name,
      width: imgData.image.width,
      height: imgData.image.height,
      annotations: imgData.annotations.map(ann => ({
        id: ann.id,
        type: ann.type,
        category: ann.category,
        label: ann.label,
        imageCoords: ann.imageCoords,
        createdAt: ann.createdAt,
        updatedAt: ann.updatedAt
      }))
    }))
  }
}

export const downloadFile = (content, filename, type = 'application/json') => {
  let blob
  if (type === 'application/xml' || type === 'text/xml') {
    blob = new Blob([content], { type: 'text/xml;charset=utf-8' })
  } else {
    blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json;charset=utf-8' })
  }

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export const exportAnnotations = {
  coco(imagesData, projectInfo) {
    const data = exportToCOCO(imagesData, projectInfo)
    downloadFile(data, `annotations_coco_${Date.now()}.json`, 'application/json')
    return data
  },

  voc(imageData, imageInfo) {
    const xml = exportToVOC(imageData, imageInfo)
    downloadFile(xml, `${imageData.image.name.replace(/\.[^/.]+$/, '')}_voc.xml`, 'text/xml')
    return xml
  },

  vocAll(imagesData, projectInfo) {
    const results = []
    imagesData.forEach(imgData => {
      const xml = exportToVOC(imgData, { folder: projectInfo?.name || 'images' })
      results.push({ name: imgData.image.name, xml })
    })
    return results
  },

  json(imagesData, projectInfo) {
    const data = exportToJSON(imagesData, projectInfo)
    downloadFile(data, `annotations_${Date.now()}.json`, 'application/json')
    return data
  }
}

export default exportAnnotations
