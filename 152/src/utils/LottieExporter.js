export class LottieExporter {
  constructor() {
    this.animation = {
      v: '5.7.0',
      fr: 30,
      ip: 0,
      op: 60,
      w: 800,
      h: 600,
      nm: 'Vector Editor Export',
      ddd: 0,
      assets: [],
      layers: []
    }
  }

  setSize(width, height) {
    this.animation.w = width
    this.animation.h = height
  }

  setDuration(frames, frameRate = 30) {
    this.animation.fr = frameRate
    this.animation.op = frames
  }

  rgbaToHex(rgba) {
    const [r, g, b, a = 1] = rgba
    return [r, g, b, a]
  }

  hexToLottieColor(hex) {
    if (Array.isArray(hex)) {
      return hex
    }
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result ? [
      parseInt(result[1], 16) / 255,
      parseInt(result[2], 16) / 255,
      parseInt(result[3], 16) / 255,
      1
    ] : [0, 0, 0, 1]
  }

  pathToShapeData(pathModel, index) {
    return {
      ty: 'gr',
      it: [
        {
          ty: 'sh',
          ks: {
            a: 0,
            k: this.pathDataToShape(pathModel.pathData)
          },
          ind: index
        },
        {
          ty: 'fl',
          c: {
            a: 0,
            k: this.hexToLottieColor(pathModel.fillColor)
          },
          o: { a: 0, k: pathModel.fillColor[3] * 100 },
          r: 1,
          bm: 0
        },
        {
          ty: 'st',
          c: {
            a: 0,
            k: this.hexToLottieColor(pathModel.strokeColor)
          },
          o: { a: 0, k: pathModel.strokeColor[3] * 100 },
          w: { a: 0, k: pathModel.strokeWidth },
          lc: 2,
          lj: 2,
          ml: 4,
          bm: 0
        },
        {
          ty: 'tr',
          p: { a: 0, k: [0, 0] },
          a: { a: 0, k: [0, 0] },
          s: { a: 0, k: [100, 100] },
          r: { a: 0, k: 0 },
          o: { a: 0, k: 100 }
        }
      ],
      nm: pathModel.name || `Shape ${index}`
    }
  }

  pathDataToShape(pathData) {
    const commands = pathData.match(/[MLCQ][^MLCQZ]*/gi) || []
    const vertices = []
    const inPoints = []
    const outPoints = []
    
    let currentPos = [0, 0]
    let closed = pathData.toLowerCase().endsWith('z')
    
    commands.forEach(cmd => {
      const type = cmd[0].toUpperCase()
      const nums = cmd.slice(1).split(/[,\s]+/)
        .filter(Boolean)
        .map(Number)
      
      switch (type) {
        case 'M':
          currentPos = [nums[0], nums[1]]
          vertices.push([currentPos[0], currentPos[1]])
          inPoints.push([0, 0])
          outPoints.push([0, 0])
          break
          
        case 'L':
          currentPos = [nums[0], nums[1]]
          vertices.push([currentPos[0], currentPos[1]])
          inPoints.push([0, 0])
          outPoints.push([0, 0])
          break
          
        case 'C':
          const cp1 = [nums[0], nums[1]]
          const cp2 = [nums[2], nums[3]]
          currentPos = [nums[4], nums[5]]
          
          outPoints[outPoints.length - 1] = [
            cp1[0] - vertices[vertices.length - 1][0],
            cp1[1] - vertices[vertices.length - 1][1]
          ]
          inPoints.push([
            cp2[0] - currentPos[0],
            cp2[1] - currentPos[1]
          ])
          outPoints.push([0, 0])
          vertices.push([currentPos[0], currentPos[1]])
          break
          
        case 'Q':
          const cp = [nums[0], nums[1]]
          const end = [nums[2], nums[3]]
          
          outPoints[outPoints.length - 1] = [
            cp[0] - vertices[vertices.length - 1][0],
            cp[1] - vertices[vertices.length - 1][1]
          ]
          inPoints.push([
            cp[0] - end[0],
            cp[1] - end[1]
          ])
          outPoints.push([0, 0])
          vertices.push([end[0], end[1]])
          currentPos = end
          break
      }
    })
    
    return {
      c: closed,
      v: vertices.flat(),
      i: inPoints.flat(),
      o: outPoints.flat()
    }
  }

  addLayer(pathModels, layerName = 'Shapes') {
    const shapes = pathModels.map((path, index) => this.pathToShapeData(path, index))
    
    const layer = {
      ty: 4,
      nm: layerName,
      sr: 1,
      ks: {
        o: { a: 0, k: 100 },
        r: { a: 0, k: 0 },
        p: { a: 0, k: [this.animation.w / 2, this.animation.h / 2] },
        a: { a: 0, k: [0, 0] },
        s: { a: 0, k: [100, 100] }
      },
      shapes: shapes,
      ip: this.animation.ip,
      op: this.animation.op,
      st: 0,
      ddd: 0
    }
    
    this.animation.layers.push(layer)
  }

  addAnimatedLayer(pathModel, animationType = 'scale', options = {}) {
    const shapeData = this.pathToShapeData(pathModel, 0)
    
    const transform = shapeData.it.find(i => i.ty === 'tr')
    
    switch (animationType) {
      case 'scale':
        transform.s = {
          a: 1,
          k: [
            { t: 0, s: [50, 50], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } },
            { t: 30, s: [100, 100], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } },
            { t: 60, s: [50, 50], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } }
          ]
        }
        break
      
      case 'rotate':
        transform.r = {
          a: 1,
          k: [
            { t: 0, s: [0], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } },
            { t: 60, s: [360], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } }
          ]
        }
        break
      
      case 'opacity':
        transform.o = {
          a: 1,
          k: [
            { t: 0, s: [0], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } },
            { t: 30, s: [100], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } },
            { t: 60, s: [0], i: { x: [0.83], y: [0.83] }, o: { x: [0.83], y: [0.83] } }
          ]
        }
        break
    }
    
    const layer = {
      ty: 4,
      nm: pathModel.name || 'Animated Shape',
      sr: 1,
      ks: {
        o: { a: 0, k: 100 },
        r: { a: 0, k: 0 },
        p: { a: 0, k: [this.animation.w / 2, this.animation.h / 2] },
        a: { a: 0, k: [0, 0] },
        s: { a: 0, k: [100, 100] }
      },
      shapes: [shapeData],
      ip: this.animation.ip,
      op: this.animation.op,
      st: 0,
      ddd: 0
    }
    
    this.animation.layers.push(layer)
  }

  export() {
    return JSON.stringify(this.animation, null, 2)
  }

  download(filename = 'animation.json') {
    const json = this.export()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  static exportFromPaths(pathModels, options = {}) {
    const exporter = new LottieExporter()
    
    if (options.width) exporter.animation.w = options.width
    if (options.height) exporter.animation.h = options.height
    if (options.frameRate) exporter.animation.fr = options.frameRate
    if (options.duration) exporter.animation.op = options.duration
    
    exporter.addLayer(pathModels)
    return exporter.export()
  }
}

export default LottieExporter
