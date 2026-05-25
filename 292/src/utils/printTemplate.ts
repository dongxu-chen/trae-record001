import type { PrintTemplate, PrintSection, PrintField, PageSetup, PrintOptions } from '@/types/advanced'
import type { FormSchema, FormField } from '@/types/form'

function generateId(): string {
  return 'pt_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6)
}

export function createDefaultPrintTemplate(schema: FormSchema): PrintTemplate {
  const sections: PrintSection[] = schema.tabs.map(tab => ({
    id: generateId(),
    name: tab.name,
    title: tab.name,
    visible: true,
    fields: tab.fields.map(f => createPrintField(f)),
    style: {}
  }))

  return {
    id: generateId(),
    name: '默认打印模板',
    description: '系统自动生成的默认打印模板',
    isDefault: true,
    layout: 'single-column',
    header: {
      id: generateId(),
      name: '页眉',
      visible: true,
      fields: [],
      style: {}
    },
    footer: {
      id: generateId(),
      name: '页脚',
      visible: true,
      fields: [],
      style: {}
    },
    sections,
    pageSetup: {
      paperSize: 'A4',
      orientation: 'portrait',
      marginTop: 20,
      marginBottom: 20,
      marginLeft: 20,
      marginRight: 20,
      showPageNumbers: true,
      showWatermark: false
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
}

function createPrintField(field: FormField): PrintField {
  return {
    fieldId: field.id,
    fieldName: field.name,
    label: field.label,
    width: 'full',
    visible: true,
    showLabel: true,
    style: {}
  }
}

export function updatePrintTemplate(
  template: PrintTemplate,
  updates: Partial<PrintTemplate>
): PrintTemplate {
  return {
    ...template,
    ...updates,
    updatedAt: new Date().toISOString()
  }
}

export function addPrintSection(template: PrintTemplate, section: PrintSection): PrintTemplate {
  return {
    ...template,
    sections: [...template.sections, section],
    updatedAt: new Date().toISOString()
  }
}

export function removePrintSection(template: PrintTemplate, sectionId: string): PrintTemplate {
  return {
    ...template,
    sections: template.sections.filter(s => s.id !== sectionId),
    updatedAt: new Date().toISOString()
  }
}

export function updatePrintSection(
  template: PrintTemplate,
  sectionId: string,
  updates: Partial<PrintSection>
): PrintTemplate {
  return {
    ...template,
    sections: template.sections.map(s =>
      s.id === sectionId ? { ...s, ...updates } : s
    ),
    updatedAt: new Date().toISOString()
  }
}

export function addFieldToSection(
  template: PrintTemplate,
  sectionId: string,
  field: PrintField
): PrintTemplate {
  return {
    ...template,
    sections: template.sections.map(s =>
      s.id === sectionId ? { ...s, fields: [...s.fields, field] } : s
    ),
    updatedAt: new Date().toISOString()
  }
}

export function removeFieldFromSection(
  template: PrintTemplate,
  sectionId: string,
  fieldName: string
): PrintTemplate {
  return {
    ...template,
    sections: template.sections.map(s =>
      s.id === sectionId ? { ...s, fields: s.fields.filter(f => f.fieldName !== fieldName) } : s
    ),
    updatedAt: new Date().toISOString()
  }
}

export function updateFieldInSection(
  template: PrintTemplate,
  sectionId: string,
  fieldName: string,
  updates: Partial<PrintField>
): PrintTemplate {
  return {
    ...template,
    sections: template.sections.map(s =>
      s.id === sectionId
        ? {
            ...s,
            fields: s.fields.map(f =>
              f.fieldName === fieldName ? { ...f, ...updates } : f
            )
          }
        : s
    ),
    updatedAt: new Date().toISOString()
  }
}

export function generatePrintHtml(
  template: PrintTemplate,
  formData: Record<string, any>,
  options: Partial<PrintOptions> = {}
): string {
  const {
    includeHeader = true,
    includeFooter = true,
    scale = 1,
    showEmptyFields = false
  } = options

  const pageSetup = template.pageSetup

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${template.name}</title>
  <style>
    @page {
      size: ${pageSetup.paperSize} ${pageSetup.orientation};
      margin: ${pageSetup.marginTop}mm ${pageSetup.marginRight}mm ${pageSetup.marginBottom}mm ${pageSetup.marginLeft}mm;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: #333;
      transform: scale(${scale});
      transform-origin: top left;
    }
    .print-header {
      text-align: center;
      padding: 20px 0;
      border-bottom: 2px solid #333;
      margin-bottom: 20px;
    }
    .print-header h1 {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 10px;
    }
    .print-section {
      margin-bottom: 24px;
      page-break-inside: avoid;
    }
    .section-title {
      font-size: 16px;
      font-weight: bold;
      padding: 8px 12px;
      background: #f5f5f5;
      border-left: 4px solid #6366f1;
      margin-bottom: 16px;
    }
    .fields-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px 24px;
    }
    .field-item {
      display: flex;
      align-items: flex-start;
      padding: 6px 0;
    }
    .field-item.full {
      grid-column: span 2;
    }
    .field-item.half {
      grid-column: span 1;
    }
    .field-label {
      min-width: 100px;
      color: #666;
      flex-shrink: 0;
    }
    .field-label.required::after {
      content: '*';
      color: #ef4444;
      margin-left: 2px;
    }
    .field-value {
      flex: 1;
      color: #333;
      word-break: break-all;
    }
    .field-value.empty {
      color: #ccc;
    }
    .print-footer {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      text-align: center;
      padding: 10px 0;
      font-size: 12px;
      color: #999;
      border-top: 1px solid #eee;
    }
    .watermark {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-30deg);
      font-size: 80px;
      color: rgba(0, 0, 0, 0.05);
      pointer-events: none;
      white-space: nowrap;
      z-index: -1;
    }
    @media print {
      body {
        transform: none;
      }
    }
  </style>
</head>
<body>
  ${pageSetup.showWatermark && pageSetup.watermarkText 
    ? `<div class="watermark">${pageSetup.watermarkText}</div>` 
    : ''
  }
  
  ${includeHeader && template.header.visible ? `
    <div class="print-header">
      <h1>${template.name}</h1>
      <p style="font-size: 12px; color: #666;">打印时间: ${new Date().toLocaleString()}</p>
    </div>
  ` : ''}

  ${template.sections.filter(s => s.visible).map(section => `
    <div class="print-section">
      <div class="section-title">${section.title || section.name}</div>
      <div class="fields-grid">
        ${section.fields.filter(f => f.visible).map(field => {
          const value = formData[field.fieldName]
          const hasValue = value !== undefined && value !== null && value !== ''
          
          if (!showEmptyFields && !hasValue) return ''
          
          return `
            <div class="field-item ${field.width}">
              ${field.showLabel ? `<span class="field-label">${field.label}：</span>` : ''}
              <span class="field-value ${!hasValue ? 'empty' : ''}">
                ${formatFieldValue(value)}
              </span>
            </div>
          `
        }).join('')}
      </div>
    </div>
  `).join('')}

  ${includeFooter && template.footer.visible ? `
    <div class="print-footer">
      ${pageSetup.showPageNumbers ? '<span class="page-number">第 <span class="current-page"></span> 页 / 共 <span class="total-pages"></span> 页</span>' : ''}
    </div>
  ` : ''}

  <script>
    (function() {
      window.onload = function() {
        setTimeout(function() {
          window.print();
        }, 100);
      };
    })();
  <\/script>
</body>
</html>
  `
}

function formatFieldValue(value: any): string {
  if (value === undefined || value === null || value === '') {
    return '-'
  }
  
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  
  return String(value)
}

export function printForm(
  template: PrintTemplate,
  formData: Record<string, any>,
  options?: Partial<PrintOptions>
): void {
  const html = generatePrintHtml(template, formData, options)
  const printWindow = window.open('', '_blank', 'width=900,height=700')
  
  if (printWindow) {
    printWindow.document.write(html)
    printWindow.document.close()
  }
}

export function exportPrintPdf(
  template: PrintTemplate,
  formData: Record<string, any>,
  options?: Partial<PrintOptions>
): void {
  printForm(template, formData, options)
}
