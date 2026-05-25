export const DEFAULT_CONFIG = {
  maxParticles: 1000000,
  particleCount: 50000,
  emissionRate: 5000,
  speed: { min: 1, max: 3 },
  life: { min: 1, max: 3 },
  size: { min: 0.1, max: 0.5 },
  color: { start: '#ff6600', end: '#ff0000' },
  direction: { x: 0, y: 1, z: 0 },
  spread: 0.5,
  gravity: { x: 0, y: -0.5, z: 0 },
  emitterPosition: { x: 0, y: 0, z: 0 },
  emitterShape: 'point',
  emitterRadius: 1,
  rotationSpeed: { min: 0, max: 2 },
  blending: 'additive'
}

export const PRESET_DEFAULTS = {
  fire: {
    maxParticles: 1000000,
    particleCount: 150000,
    emissionRate: 30000,
    speed: { min: 2, max: 5 },
    life: { min: 0.5, max: 1.5 },
    size: { min: 0.2, max: 0.8 },
    color: { start: '#ffff00', end: '#ff0000' },
    direction: { x: 0, y: 1, z: 0 },
    spread: 0.6,
    gravity: { x: 0, y: -1, z: 0 },
    emitterPosition: { x: 0, y: -2, z: 0 },
    emitterShape: 'circle',
    emitterRadius: 0.5,
    rotationSpeed: { min: 0, max: 3 },
    blending: 'additive'
  },
  smoke: {
    maxParticles: 500000,
    particleCount: 80000,
    emissionRate: 8000,
    speed: { min: 0.5, max: 1.5 },
    life: { min: 2, max: 5 },
    size: { min: 0.5, max: 1.5 },
    color: { start: '#888888', end: '#333333' },
    direction: { x: 0, y: 1, z: 0 },
    spread: 0.8,
    gravity: { x: 0, y: 0.2, z: 0 },
    emitterPosition: { x: 0, y: -2, z: 0 },
    emitterShape: 'circle',
    emitterRadius: 0.3,
    rotationSpeed: { min: 0.5, max: 2 },
    blending: 'normal'
  },
  stars: {
    maxParticles: 2000000,
    particleCount: 500000,
    emissionRate: 50000,
    speed: { min: 0.05, max: 0.2 },
    life: { min: 3, max: 8 },
    size: { min: 0.05, max: 0.2 },
    color: { start: '#ffffff', end: '#88ccff' },
    direction: { x: 0, y: 0, z: 0 },
    spread: 0,
    gravity: { x: 0, y: 0, z: 0 },
    emitterPosition: { x: 0, y: 0, z: 0 },
    emitterShape: 'sphere',
    emitterRadius: 20,
    rotationSpeed: { min: 0, max: 1 },
    blending: 'additive'
  },
  snow: {
    maxParticles: 1000000,
    particleCount: 200000,
    emissionRate: 15000,
    speed: { min: 0.3, max: 1 },
    life: { min: 5, max: 10 },
    size: { min: 0.1, max: 0.4 },
    color: { start: '#ffffff', end: '#aaddff' },
    direction: { x: 0, y: -1, z: 0 },
    spread: 0.3,
    gravity: { x: 0, y: -0.1, z: 0 },
    emitterPosition: { x: 0, y: 8, z: 0 },
    emitterShape: 'box',
    emitterRadius: 15,
    rotationSpeed: { min: 1, max: 4 },
    blending: 'additive'
  }
}

export function computeDiff(config, defaults = DEFAULT_CONFIG) {
  const diff = {}

  for (const key in config) {
    if (!(key in defaults)) {
      diff[key] = JSON.parse(JSON.stringify(config[key]))
      continue
    }

    const configValue = config[key]
    const defaultvalue = defaults[key]

    if (typeof configValue === 'object' && !Array.isArray(configValue) && configValue !== null) {
      if (typeof defaultvalue === 'object' && !Array.isArray(defaultvalue) && defaultvalue !== null) {
        const nestedDiff = computeDiff(configValue, defaultvalue)
        if (Object.keys(nestedDiff).length > 0) {
          diff[key] = nestedDiff
        }
      } else {
        diff[key] = JSON.parse(JSON.stringify(configValue))
      }
    } else {
      if (configValue !== defaultvalue) {
        diff[key] = configValue
      }
    }
  }

  return diff
}

export function applyDiff(diff, defaults = DEFAULT_CONFIG) {
  const result = JSON.parse(JSON.stringify(defaults))

  for (const key in diff) {
    const diffValue = diff[key]

    if (typeof diffValue === 'object' && !Array.isArray(diffValue) && diffValue !== null) {
      if (typeof result[key] === 'object' && !Array.isArray(result[key]) && result[key] !== null) {
        result[key] = applyDiff(diffValue, result[key])
      } else {
        result[key] = JSON.parse(JSON.stringify(diffValue))
      }
    } else {
      result[key] = diffValue
    }
  }

  return result
}

export function exportConfig(config, metadata = {}, options = {}) {
  const {
    useDiff = true,
    basePreset = null,
    prettyPrint = true
  } = options

  const exportData = {
    version: '2.0.0',
    exportedAt: new Date().toISOString(),
    format: useDiff ? 'diff' : 'full',
    metadata: {
      name: metadata.name || '粒子特效',
      description: metadata.description || '',
      author: metadata.author || '',
      basePreset: basePreset,
      ...metadata
    }
  }

  if (useDiff) {
    const defaults = basePreset && PRESET_DEFAULTS[basePreset] 
      ? PRESET_DEFAULTS[basePreset] 
      : DEFAULT_CONFIG
    exportData.diff = computeDiff(config, defaults)
    exportData.basePreset = basePreset
  } else {
    exportData.config = JSON.parse(JSON.stringify(config))
  }

  return JSON.stringify(exportData, null, prettyPrint ? 2 : 0)
}

export function importConfig(jsonString) {
  try {
    const data = JSON.parse(jsonString)
    
    let config
    const isDiffFormat = data.format === 'diff' && data.diff

    if (isDiffFormat) {
      const basePreset = data.basePreset || data.metadata?.basePreset
      const defaults = basePreset && PRESET_DEFAULTS[basePreset]
        ? PRESET_DEFAULTS[basePreset]
        : DEFAULT_CONFIG
      config = applyDiff(data.diff, defaults)
    } else {
      if (!data.config) {
        throw new Error('配置文件格式错误：缺少 config 字段')
      }
      config = data.config
    }

    const validation = validateConfig(config)
    if (!validation.valid) {
      throw new Error(`配置验证失败：缺少字段 ${validation.missingFields.join(', ')}`)
    }

    return {
      success: true,
      data: config,
      metadata: data.metadata || {},
      version: data.version,
      format: isDiffFormat ? 'diff' : 'full',
      basePreset: data.basePreset || data.metadata?.basePreset
    }
  } catch (error) {
    return {
      success: false,
      error: error.message
    }
  }
}

export function downloadConfig(config, filename = 'particle-effect.json', metadata = {}, options = {}) {
  const jsonString = exportConfig(config, metadata, options)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}

export function loadConfigFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      const result = importConfig(e.target.result)
      if (result.success) {
        resolve(result)
      } else {
        reject(new Error(result.error))
      }
    }
    
    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }
    
    reader.readAsText(file)
  })
}

export function validateConfig(config) {
  const requiredFields = [
    'maxParticles',
    'particleCount',
    'emissionRate',
    'speed',
    'life',
    'size',
    'color',
    'direction',
    'spread',
    'gravity',
    'emitterPosition',
    'emitterShape',
    'emitterRadius',
    'rotationSpeed',
    'blending'
  ]
  
  const missing = requiredFields.filter(field => !(field in config))
  
  if (missing.length > 0) {
    return {
      valid: false,
      missingFields: missing
    }
  }
  
  return { valid: true }
}

export function mergeWithDefaults(config, defaults) {
  const result = { ...defaults }
  
  for (const key in config) {
    if (typeof config[key] === 'object' && !Array.isArray(config[key]) && config[key] !== null) {
      result[key] = mergeWithDefaults(config[key], result[key] || {})
    } else {
      result[key] = config[key]
    }
  }
  
  return result
}

export function estimateDiffSize(config, basePreset = null) {
  const defaults = basePreset && PRESET_DEFAULTS[basePreset]
    ? PRESET_DEFAULTS[basePreset]
    : DEFAULT_CONFIG

  const fullJson = JSON.stringify(config)
  const diff = computeDiff(config, defaults)
  const diffJson = JSON.stringify(diff)

  return {
    fullSize: fullJson.length,
    diffSize: diffJson.length,
    saved: fullJson.length - diffJson.length,
    savedPercent: Math.round((1 - diffJson.length / fullJson.length) * 100)
  }
}
