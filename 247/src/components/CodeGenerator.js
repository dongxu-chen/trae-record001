export function generateJsonSchema(formItems) {
  const schema = {
    type: 'object',
    title: '表单',
    properties: {},
    required: []
  }

  formItems.forEach(item => {
    const fieldSchema = {
      type: getSchemaType(item.type),
      title: item.label
    }

    if (item.placeholder) {
      fieldSchema.description = item.placeholder
    }

    if (item.defaultValue !== undefined && item.defaultValue !== '') {
      fieldSchema.default = item.defaultValue
    }

    if (['radio', 'select'].includes(item.type) && item.options) {
      fieldSchema.enum = item.options.map(opt => opt.value)
      fieldSchema.enumNames = item.options.map(opt => opt.label)
    }

    if (item.type === 'checkbox' && item.options) {
      fieldSchema.items = {
        type: 'string',
        enum: item.options.map(opt => opt.value),
        enumNames: item.options.map(opt => opt.label)
      }
    }

    if (item.type === 'number') {
      if (item.min !== null && item.min !== undefined) {
        fieldSchema.minimum = item.min
      }
      if (item.max !== null && item.max !== undefined) {
        fieldSchema.maximum = item.max
      }
    }

    if (item.validation?.pattern) {
      fieldSchema.pattern = item.validation.pattern
    }
    if (item.validation?.minLength !== null && item.validation?.minLength !== undefined) {
      fieldSchema.minLength = item.validation.minLength
    }
    if (item.validation?.maxLength !== null && item.validation?.maxLength !== undefined) {
      fieldSchema.maxLength = item.validation.maxLength
    }

    if (item.dataSource?.type === 'async') {
      fieldSchema['x-data-source'] = {
        type: 'async',
        url: item.dataSource.url,
        method: item.dataSource.method,
        labelField: item.dataSource.labelField,
        valueField: item.dataSource.valueField
      }
    }

    schema.properties[item.field] = fieldSchema

    if (item.required) {
      schema.required.push(item.field)
    }
  })

  return JSON.stringify(schema, null, 2)
}

function getSchemaType(type) {
  const typeMap = {
    input: 'string',
    textarea: 'string',
    number: 'number',
    date: 'string',
    radio: 'string',
    checkbox: 'array',
    select: 'string'
  }
  return typeMap[type] || 'string'
}

export function generateVueCode(formItems) {
  const templateCode = generateTemplate(formItems)
  const scriptCode = generateScript(formItems)
  const styleCode = generateStyle()

  return `<template>
${templateCode}
</template>

<script setup>
${scriptCode}
</script>

<style scoped>
${styleCode}
</style>`
}

function generateTemplate(formItems) {
  let template = '  <div class="form-container">\n'
  template += '    <form @submit.prevent="handleSubmit">\n'

  formItems.forEach(item => {
    const vif = generateVif(item)
    template += `      <div class="form-item"${vif}>\n`
    template += `        <label class="form-label">\n`
    if (item.required) {
      template += `          <span class="required">*</span>\n`
    }
    template += `          ${item.label}\n`
    template += `        </label>\n`
    template += generateFieldTemplate(item)
    template += generateErrorTemplate(item)
    template += '      </div>\n'
  })

  template += '      <div class="form-actions">\n'
  template += '        <button type="submit" class="btn btn-primary">提交</button>\n'
  template += '        <button type="button" class="btn btn-default" @click="resetForm">重置</button>\n'
  template += '      </div>\n'
  template += '    </form>\n'
  template += '  </div>'

  return template
}

function generateVif(item) {
  if (!item.linkage?.enabled || !item.linkage.rules?.length) return ''

  const conditions = item.linkage.rules.map(rule => {
    const targetItem = { id: rule.targetField, field: rule.targetField }
    const value = rule.value
    const action = rule.action

    let condition = ''
    switch (rule.operator) {
      case '==':
        condition = `formData.${rule.targetField} == '${value}'`
        break
      case '!=':
        condition = `formData.${rule.targetField} != '${value}'`
        break
      case 'includes':
        condition = `String(formData.${rule.targetField}).includes('${value}')`
        break
      case 'empty':
        condition = `!formData.${rule.targetField}`
        break
      case 'notEmpty':
        condition = `!!formData.${rule.targetField}`
        break
    }

    return action === 'hide' ? `!(${condition})` : condition
  })

  return ` v-if="${conditions.join(' && ')}"`
}

function generateFieldTemplate(item) {
  const field = item.field
  const placeholder = item.placeholder || ''
  const useAsyncOptions = item.dataSource?.type === 'async'
  const optionsVar = useAsyncOptions ? `${field}Options` : 'item.options'

  switch (item.type) {
    case 'input':
      return `        <input\n` +
             `          type="text"\n` +
             `          class="form-input"\n` +
             `          v-model="formData.${field}"\n` +
             `          :placeholder="'${placeholder}'"\n` +
             `          @blur="validateField('${field}')"\n` +
             `        />\n`

    case 'textarea':
      return `        <textarea\n` +
             `          class="form-input"\n` +
             `          v-model="formData.${field}"\n` +
             `          :placeholder="'${placeholder}'"\n` +
             `          rows="3"\n` +
             `          @blur="validateField('${field}')"\n` +
             `        ></textarea>\n`

    case 'number':
      const min = item.min !== null && item.min !== undefined ? `          :min="${item.min}"\n` : ''
      const max = item.max !== null && item.max !== undefined ? `          :max="${item.max}"\n` : ''
      const step = item.step ? `          :step="${item.step}"\n` : ''
      return `        <input\n` +
             `          type="number"\n` +
             `          class="form-input"\n` +
             `          v-model.number="formData.${field}"\n` +
             min + max + step +
             `          :placeholder="'${placeholder}'"\n` +
             `          @blur="validateField('${field}')"\n` +
             `        />\n`

    case 'date':
      return `        <input\n` +
             `          type="date"\n` +
             `          class="form-input"\n` +
             `          v-model="formData.${field}"\n` +
             `          @blur="validateField('${field}')"\n` +
             `        />\n`

    case 'radio':
      let radioTemplate = '        <div class="radio-group">\n'
      if (useAsyncOptions) {
        radioTemplate += `          <label v-for="opt in ${field}Options" :key="opt.value" class="radio-label">\n`
        radioTemplate += `            <input type="radio" v-model="formData.${field}" :value="opt.value" />\n`
        radioTemplate += `            {{ opt.label }}\n`
        radioTemplate += `          </label>\n`
      } else {
        item.options.forEach(opt => {
          radioTemplate += `          <label class="radio-label">\n`
          radioTemplate += `            <input type="radio" v-model="formData.${field}" value="${opt.value}" />\n`
          radioTemplate += `            ${opt.label}\n`
          radioTemplate += `          </label>\n`
        })
      }
      radioTemplate += '        </div>\n'
      return radioTemplate

    case 'checkbox':
      let checkboxTemplate = '        <div class="checkbox-group">\n'
      if (useAsyncOptions) {
        checkboxTemplate += `          <label v-for="opt in ${field}Options" :key="opt.value" class="checkbox-label">\n`
        checkboxTemplate += `            <input type="checkbox" v-model="formData.${field}" :value="opt.value" />\n`
        checkboxTemplate += `            {{ opt.label }}\n`
        checkboxTemplate += `          </label>\n`
      } else {
        item.options.forEach(opt => {
          checkboxTemplate += `          <label class="checkbox-label">\n`
          checkboxTemplate += `            <input type="checkbox" v-model="formData.${field}" value="${opt.value}" />\n`
          checkboxTemplate += `            ${opt.label}\n`
          checkboxTemplate += `          </label>\n`
        })
      }
      checkboxTemplate += '        </div>\n'
      return checkboxTemplate

    case 'select':
      let selectTemplate = `        <select class="form-select" v-model="formData.${field}" @change="validateField('${field}')">\n`
      selectTemplate += `          <option value="">${placeholder || '请选择'}</option>\n`
      if (useAsyncOptions) {
        selectTemplate += `          <option v-for="opt in ${field}Options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>\n`
      } else {
        item.options.forEach(opt => {
          selectTemplate += `          <option value="${opt.value}">${opt.label}</option>\n`
        })
      }
      selectTemplate += '        </select>\n'
      return selectTemplate

    default:
      return ''
  }
}

function generateErrorTemplate(item) {
  if (!item.required && !item.validation?.pattern && !item.validation?.minLength && !item.validation?.maxLength) {
    return ''
  }
  return `        <div v-if="errors.${item.field}" class="error-message">{{ errors.${item.field} }}</div>\n`
}

function generateScript(formItems) {
  const asyncItems = formItems.filter(item => item.dataSource?.type === 'async')
  const hasAsyncData = asyncItems.length > 0

  let script = `import { ref, reactive, onMounted } from 'vue'\n`
  if (hasAsyncData) {
    script += `import axios from 'axios'\n\n`
  } else {
    script += '\n'
  }

  script += `const formData = reactive({\n`
  formItems.forEach(item => {
    const defaultValue = item.type === 'checkbox' ? '[]' : item.defaultValue ? `'${item.defaultValue}'` : "''"
    script += `  ${item.field}: ${defaultValue},\n`
  })
  script += `})\n\n`

  script += `const errors = reactive({\n`
  formItems.forEach(item => {
    script += `  ${item.field}: '',\n`
  })
  script += `})\n\n`

  if (hasAsyncData) {
    asyncItems.forEach(item => {
      script += `const ${item.field}Options = ref([])\n`
    })
    script += '\n'
  }

  script += generateValidationRules(formItems)

  if (hasAsyncData) {
    script += generateDataFetchers(asyncItems)
    script += '\n'
  }

  script += `const validateField = (field) => {\n`
  script += `  const rules = validationRules[field]\n`
  script += `  if (!rules) return true\n`
  script += `  const value = formData[field]\n`
  script += `  errors[field] = ''\n\n`
  script += `  for (const rule of rules) {\n`
  script += `    if (!rule.validator(value)) {\n`
  script += `      errors[field] = rule.message\n`
  script += `      return false\n`
  script += `    }\n`
  script += `  }\n\n`
  script += `  return true\n`
  script += `}\n\n`

  script += `const validateForm = () => {\n`
  script += `  let isValid = true\n`
  script += `  Object.keys(formData).forEach(field => {\n`
  script += `    if (!validateField(field)) {\n`
  script += `      isValid = false\n`
  script += `    }\n`
  script += `  })\n`
  script += `  return isValid\n`
  script += `}\n\n`

  script += `const handleSubmit = () => {\n`
  script += `  if (validateForm()) {\n`
  script += `    console.log('表单数据:', formData)\n`
  script += `    alert('提交成功!')\n`
  script += `  }\n`
  script += `}\n\n`

  script += `const resetForm = () => {\n`
  script += `  Object.keys(formData).forEach(field => {\n`
  const checkboxFields = formItems.filter(item => item.type === 'checkbox').map(item => item.field)
  script += `    formData[field] = ${checkboxFields.length > 0 ? '[]' : "''"}`
  script += `\n`
  script += `  })\n`
  script += `  Object.keys(errors).forEach(field => {\n`
  script += `    errors[field] = ''\n`
  script += `  })\n`
  script += `}\n`

  if (hasAsyncData) {
    script += '\n'
    script += `onMounted(() => {\n`
    asyncItems.forEach(item => {
      script += `  fetch${capitalize(item.field)}Options()\n`
    })
    script += `})\n`
  }

  return script
}

function generateValidationRules(formItems) {
  let rules = `const validationRules = {\n`

  formItems.forEach(item => {
    const fieldRules = []

    if (item.required) {
      const message = item.validation?.message || `${item.label}不能为空`
      fieldRules.push({
        validator: `(v) => ${item.type === 'checkbox' ? 'v && v.length > 0' : '!!v'}`,
        message
      })
    }

    if (item.validation?.pattern) {
      const message = item.validation?.message || `${item.label}格式不正确`
      fieldRules.push({
        validator: `(v) => !v || /${item.validation.pattern}/.test(v)`,
        message
      })
    }

    if (item.validation?.minLength !== null && item.validation?.minLength !== undefined) {
      const message = item.validation?.message || `${item.label}最少${item.validation.minLength}个字符`
      fieldRules.push({
        validator: `(v) => !v || v.length >= ${item.validation.minLength}`,
        message
      })
    }

    if (item.validation?.maxLength !== null && item.validation?.maxLength !== undefined) {
      const message = item.validation?.message || `${item.label}最多${item.validation.maxLength}个字符`
      fieldRules.push({
        validator: `(v) => !v || v.length <= ${item.validation.maxLength}`,
        message
      })
    }

    if (fieldRules.length > 0) {
      rules += `  ${item.field}: [\n`
      fieldRules.forEach(rule => {
        rules += `    {\n`
        rules += `      validator: ${rule.validator},\n`
        rules += `      message: '${rule.message}'\n`
        rules += `    },\n`
      })
      rules += `  ],\n`
    }
  })

  rules += `}\n\n`
  return rules
}

function generateDataFetchers(asyncItems) {
  let script = ''

  asyncItems.forEach(item => {
    const fieldName = item.field
    const ds = item.dataSource
    script += `const fetch${capitalize(fieldName)}Options = async () => {\n`
    script += `  try {\n`
    script += `    const response = await axios({\n`
    script += `      url: '${ds.url}',\n`
    script += `      method: '${ds.method}'\n`
    script += `    })\n`
    script += `    const data = response.data\n`
    script += `    ${fieldName}Options.value = (Array.isArray(data) ? data : (data.data || data.list || [])).map(item => ({\n`
    script += `      label: item['${ds.labelField}'],\n`
    script += `      value: item['${ds.valueField}']\n`
    script += `    }))\n`
    script += `  } catch (error) {\n`
    script += `    console.error('获取${item.label}选项失败:', error)\n`
    script += `  }\n`
    script += `}\n\n`
  })

  return script
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

function generateStyle() {
  return `.form-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.required {
  color: #f56c6c;
  margin-right: 4px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #409eff;
}

.radio-group,
.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.radio-label,
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.error-message {
  margin-top: 4px;
  color: #f56c6c;
  font-size: 12px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary {
  background: #409eff;
  color: #fff;
}

.btn-primary:hover {
  background: #66b1ff;
}

.btn-default {
  background: #fff;
  border: 1px solid #dcdfe6;
  color: #606266;
}

.btn-default:hover {
  color: #409eff;
  border-color: #c6e2ff;
}`
}
