import * as pdfjsLib from 'pdfjs-dist';

export async function extractFormFields(pdfDoc) {
  const formFields = [];
  
  for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    const annotations = await page.getAnnotations();
    
    const pageFields = annotations
      .filter(ann => ann.subtype === 'Widget')
      .map(ann => {
        const fieldType = ann.fieldType;
        const viewport = page.getViewport({ scale: 1.5 });
        const rect = ann.rect;
        
        return {
          id: ann.id || ann.fieldName,
          name: ann.fieldName || ann.alternativeText || '未命名字段',
          type: fieldType,
          pageNum,
          value: ann.fieldValue || '',
          defaultValue: ann.fieldDefaultValue || '',
          rect: {
            x: rect[0] * 1.5,
            y: viewport.height - rect[3] * 1.5,
            width: (rect[2] - rect[0]) * 1.5,
            height: (rect[3] - rect[1]) * 1.5
          },
          options: ann.choiceOptions || [],
          checked: ann.fieldValue === 'Yes' || ann.fieldValue === 'On',
          readOnly: ann.readOnly || false,
          required: ann.required || false,
          multiline: ann.multiline || false,
          password: ann.password || false
        };
      });
    
    formFields.push(...pageFields);
  }
  
  return formFields;
}

export async function fillFormField(pdfDoc, fieldName, value) {
  // 注意：PDF.js主要用于阅读，修改PDF需要服务端或其他库
  // 这里我们返回修改后的数据结构供前端显示
  return {
    fieldName,
    value,
    timestamp: new Date().toISOString()
  };
}

export function getFormFieldsByType(formFields, type) {
  return formFields.filter(field => field.type === type);
}

export function validateFormField(field, value) {
  const errors = [];
  
  if (field.required && !value) {
    errors.push('此字段为必填项');
  }
  
  if (field.type === 'Tx' && field.maxLen && value.length > field.maxLen) {
    errors.push(`输入不能超过${field.maxLen}个字符`);
  }
  
  return errors;
}
