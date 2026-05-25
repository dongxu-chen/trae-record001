import DOMPurify from 'dompurify'

const SVG_COLOR_PROPERTIES = [
  'fill',
  'stroke',
  'stop-color',
  'flood-color',
  'lighting-color',
  'color',
]

export interface SanitizeResult {
  clean: string
  warnings: string[]
  removedElements: string[]
}

export function sanitizeSvg(svgContent: string): SanitizeResult {
  const warnings: string[] = []
  const removedElements: string[] = []

  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = svgContent
  const svg = tempDiv.querySelector('svg')

  if (svg) {
    const dangerousElements = svg.querySelectorAll('script, iframe, foreignObject')
    dangerousElements.forEach((el) => {
      removedElements.push(el.tagName.toLowerCase())
      el.remove()
    })

    const allElements = svg.querySelectorAll('*')
    allElements.forEach((el) => {
      Array.from(el.attributes).forEach((attr) => {
        if (attr.name.startsWith('on')) {
          el.removeAttribute(attr.name)
          warnings.push(`Removed event handler: ${attr.name}`)
        }
        if (attr.value.includes('javascript:')) {
          el.removeAttribute(attr.name)
          warnings.push(`Removed javascript URL in: ${attr.name}`)
        }
      })
    })
  }

  const clean = DOMPurify.sanitize(svgContent, {
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_TAGS: ['svg', 'path', 'g', 'circle', 'rect', 'ellipse', 'line', 'polyline', 'polygon', 'defs', 'filter', 'linearGradient', 'radialGradient', 'stop', 'clipPath', 'use', 'mask', 'pattern', 'symbol', 'marker', 'title', 'desc'],
    ADD_ATTR: ['viewBox', 'd', 'cx', 'cy', 'r', 'x', 'y', 'width', 'height', 'x1', 'y1', 'x2', 'y2', 'points', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'transform', 'opacity', 'fill-opacity', 'stroke-opacity', 'id', 'class', 'href', 'xlink:href', 'offset', 'stop-color', 'stop-opacity', 'clip-path', 'filter', 'mask', 'patternUnits', 'patternContentUnits', 'preserveAspectRatio', 'marker-end', 'marker-start', 'marker-mid'],
    FORBID_TAGS: ['script', 'iframe', 'foreignObject'],
    FORBID_ATTR: ['onload', 'onclick', 'onmouseover', 'onerror', 'style'],
  })

  if (removedElements.length > 0) {
    warnings.push(`Removed dangerous elements: ${removedElements.join(', ')}`)
  }

  return { clean, warnings, removedElements }
}

export function extractColorsFromSvg(svgContent: string): string[] {
  const colors: Set<string> = new Set()
  
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = svgContent
  const allElements = tempDiv.querySelectorAll('*')

  allElements.forEach((el) => {
    SVG_COLOR_PROPERTIES.forEach((prop) => {
      const value = el.getAttribute(prop)
      if (value && value !== 'none' && value !== 'transparent') {
        if (value.startsWith('#') || value.startsWith('rgb') || value.startsWith('hsl')) {
          colors.add(value)
        }
      }
    })
  })

  return Array.from(colors)
}

export function replaceSvgColors(
  svgContent: string,
  colorMap: Record<string, string>
): string {
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = svgContent
  const svg = tempDiv.querySelector('svg')

  if (!svg) return svgContent

  const allElements = svg.querySelectorAll('*')

  allElements.forEach((el) => {
    SVG_COLOR_PROPERTIES.forEach((prop) => {
      const currentValue = el.getAttribute(prop)
      if (currentValue && colorMap[currentValue]) {
        el.setAttribute(prop, colorMap[currentValue])
      }
    })
  })

  return svg.outerHTML
}

export function replaceSvgSingleColor(
  svgContent: string,
  newColor: string
): string {
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = svgContent
  const svg = tempDiv.querySelector('svg')

  if (!svg) return svgContent

  const allElements = svg.querySelectorAll('*')

  allElements.forEach((el) => {
    SVG_COLOR_PROPERTIES.forEach((prop) => {
      const currentValue = el.getAttribute(prop)
      if (currentValue && currentValue !== 'none' && currentValue !== 'transparent') {
        if (currentValue.startsWith('#') || currentValue.startsWith('rgb') || currentValue.startsWith('hsl')) {
          el.setAttribute(prop, newColor)
        }
      }
    })
  })

  return svg.outerHTML
}

export function convertToCssVariables(
  svgContent: string,
  variablePrefix: string = 'icon'
): { svg: string; variables: Record<string, string> } {
  const variables: Record<string, string> = {}
  let colorIndex = 0

  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = svgContent
  const svg = tempDiv.querySelector('svg')

  if (!svg) return { svg: svgContent, variables }

  const colorToVarMap: Record<string, string> = {}
  const allElements = svg.querySelectorAll('*')

  allElements.forEach((el) => {
    SVG_COLOR_PROPERTIES.forEach((prop) => {
      const currentValue = el.getAttribute(prop)
      if (currentValue && currentValue !== 'none' && currentValue !== 'transparent') {
        if (currentValue.startsWith('#') || currentValue.startsWith('rgb') || currentValue.startsWith('hsl')) {
          if (!colorToVarMap[currentValue]) {
            const varName = `--${variablePrefix}-color-${colorIndex}`
            colorToVarMap[currentValue] = `var(${varName})`
            variables[varName] = currentValue
            colorIndex++
          }
          el.setAttribute(prop, colorToVarMap[currentValue])
        }
      }
    })
  })

  return {
    svg: svg.outerHTML,
    variables,
  }
}

export function generateReactComponentWithCssVars(
  iconName: string,
  svgContent: string,
  variables: Record<string, string>
): string {
  const varNames = Object.keys(variables)
  const hasVars = varNames.length > 0

  const varTypes = varNames
    .map((v) => `'${v}'`)
    .join(' | ')

  return `import { SVGProps } from 'react'

interface ${iconName}Props extends SVGProps<SVGSVGElement> {
  size?: number
  color?: string
  colorVars?: Partial<Record<${hasVars ? varTypes : 'string'}, string>>
}

${hasVars ? `const defaultColors = ${JSON.stringify(variables, null, 2)} as const` : ''}

export function ${iconName}({ 
  size = 24, 
  color,
  colorVars,
  style,
  ...props 
}: ${iconName}Props) {
  const computedStyle = {
    ${hasVars ? "...defaultColors," : ""}
    ...colorVars,
    ...style,
    ...(color ? { '--icon-color-0': color, color } as any : {}),
  }

  return (
    ${svgContent
      .replace('<svg', `<svg width={size} height={size} style={computedStyle}`)
      .replace(/\n/g, '\n    ')}
  )
}

export default ${iconName}`
}

export function generateVueComponentWithCssVars(
  iconName: string,
  svgContent: string,
  variables: Record<string, string>
): string {
  const varNames = Object.keys(variables)
  const hasVars = varNames.length > 0

  return `<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: number
  color?: string
  colorVars?: Partial<Record<string, string>>
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  color: undefined,
  colorVars: () => ({}),
})

${hasVars ? `const defaultColors = ${JSON.stringify(variables, null, 2)}` : ''}

const iconStyle = computed(() => ({
  ${hasVars ? "...defaultColors," : ""}
  ...props.colorVars,
  ...(props.color ? { '--icon-color-0': props.color, color: props.color } : {}),
}))
</script>

<template>
  ${svgContent
    .replace('<svg', `<svg :width="size" :height="size" :style="iconStyle"`)
    .replace(/\n/g, '\n  ')}
</template>

<script lang="ts">
export default {
  name: '${iconName}'
}
</script>`
}

export function validateSvgFile(file: File): Promise<{
  valid: boolean
  content?: string
  error?: string
}> {
  return new Promise((resolve) => {
    if (file.type !== 'image/svg+xml' && !file.name.endsWith('.svg')) {
      resolve({ valid: false, error: '仅支持SVG格式文件' })
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      if (!content.includes('<svg') || !content.includes('</svg>')) {
        resolve({ valid: false, error: '无效的SVG文件格式' })
        return
      }
      resolve({ valid: true, content })
    }
    reader.onerror = () => {
      resolve({ valid: false, error: '文件读取失败' })
    }
    reader.readAsText(file)
  })
}
