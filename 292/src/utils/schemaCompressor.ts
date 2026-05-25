import type { FormSchema, FormField, FormTab, ValidationRule } from '@/types/form'

export interface CompressedSchema {
  version: string
  compressed: boolean
  definitions: SchemaDefinitions
  form: CompressedForm
}

export interface SchemaDefinitions {
  validations: Record<string, ValidationRule[]>
  fieldTemplates: Record<string, Partial<FormField>>
  optionSets: Record<string, Array<{ label: string; value: string }>>
  formulaTemplates: Record<string, { expression: string; dependencies: string[] }>
}

export interface CompressedForm {
  id: string
  name: string
  description: string
  version: string
  createdAt: string
  updatedAt: string
  tabs: CompressedTab[]
}

export interface CompressedTab {
  id: string
  name: string
  icon?: string
  fields: Array<CompressedField | string>
}

export interface CompressedField {
  id: string
  type: string
  name: string
  label: string
  $ref?: string
  $validationRef?: string
  $optionsRef?: string
  $formulaRef?: string
  [key: string]: any
}

export interface CompressionResult {
  original: FormSchema
  compressed: CompressedSchema
  originalSize: number
  compressedSize: number
  compressionRatio: number
  stats: {
    validationDeduplications: number
    optionSetDeduplications: number
    fieldTemplateDeduplications: number
    formulaDeduplications: number
  }
}

function hashObject(obj: any): string {
  const str = JSON.stringify(obj, Object.keys(obj).sort())
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return 'h' + Math.abs(hash).toString(36)
}

function deduplicateValidations(fields: FormField[]): {
  refs: Record<string, string>
  definitions: Record<string, ValidationRule[]>
  count: number
} {
  const definitions: Record<string, ValidationRule[]> = {}
  const refs: Record<string, string> = {}
  let count = 0

  fields.forEach(field => {
    if (field.validation && field.validation.length > 0) {
      const hash = hashObject(field.validation)
      if (!definitions[hash]) {
        definitions[hash] = field.validation
        count++
      }
      refs[field.id] = hash
    }
  })

  return { refs, definitions, count }
}

function deduplicateOptionSets(fields: FormField[]): {
  refs: Record<string, string>
  definitions: Record<string, Array<{ label: string; value: string }>>
  count: number
} {
  const definitions: Record<string, Array<{ label: string; value: string }>> = {}
  const refs: Record<string, string> = {}
  let count = 0

  fields.forEach(field => {
    const options = field.props?.options
    if (options && Array.isArray(options) && options.length > 0) {
      const hash = hashObject(options)
      if (!definitions[hash]) {
        definitions[hash] = options
        count++
      }
      refs[field.id] = hash
    }
  })

  return { refs, definitions, count }
}

function deduplicateFormulas(fields: FormField[]): {
  refs: Record<string, string>
  definitions: Record<string, { expression: string; dependencies: string[] }>
  count: number
} {
  const definitions: Record<string, { expression: string; dependencies: string[] }> = {}
  const refs: Record<string, string> = {}
  let count = 0

  fields.forEach(field => {
    if (field.formula?.expression) {
      const hash = hashObject(field.formula)
      if (!definitions[hash]) {
        definitions[hash] = field.formula
        count++
      }
      refs[field.id] = hash
    }
  })

  return { refs, definitions, count }
}

function getFieldSignature(field: FormField): string {
  const signature: any = {
    type: field.type,
    required: field.required,
    validation: field.validation
  }
  return hashObject(signature)
}

function deduplicateFieldTemplates(fields: FormField[]): {
  refs: Record<string, string>
  definitions: Record<string, Partial<FormField>>
  count: number
} {
  const definitions: Record<string, Partial<FormField>> = {}
  const refs: Record<string, string> = {}
  let count = 0

  const templateGroups = new Map<string, FormField[]>()
  fields.forEach(field => {
    const sig = getFieldSignature(field)
    if (!templateGroups.has(sig)) {
      templateGroups.set(sig, [])
    }
    templateGroups.get(sig)!.push(field)
  })

  templateGroups.forEach((groupFields, sig) => {
    if (groupFields.length >= 2) {
      const template = createFieldTemplate(groupFields[0])
      definitions[sig] = template
      count++
      groupFields.forEach(f => {
        refs[f.id] = sig
      })
    }
  })

  return { refs, definitions, count }
}

function createFieldTemplate(field: FormField): Partial<FormField> {
  const template: Partial<FormField> = {
    type: field.type,
    required: field.required
  }
  return template
}

function getAllFields(schema: FormSchema): FormField[] {
  const fields: FormField[] = []
  schema.tabs.forEach(tab => {
    tab.fields.forEach(field => fields.push(field))
  })
  return fields
}

export function compressSchema(schema: FormSchema): CompressionResult {
  const allFields = getAllFields(schema)
  const originalSize = JSON.stringify(schema).length

  const validations = deduplicateValidations(allFields)
  const optionSets = deduplicateOptionSets(allFields)
  const formulas = deduplicateFormulas(allFields)
  const templates = deduplicateFieldTemplates(allFields)

  const definitions: SchemaDefinitions = {
    validations: validations.definitions,
    optionSets: optionSets.definitions,
    formulaTemplates: formulas.definitions,
    fieldTemplates: templates.definitions
  }

  const compressedTabs: CompressedTab[] = schema.tabs.map(tab => ({
    id: tab.id,
    name: tab.name,
    icon: tab.icon,
    fields: tab.fields.map(field => compressField(
      field,
      validations.refs,
      optionSets.refs,
      formulas.refs,
      templates.refs
    ))
  }))

  const compressedForm: CompressedForm = {
    id: schema.id,
    name: schema.name,
    description: schema.description,
    version: schema.version,
    createdAt: schema.createdAt,
    updatedAt: schema.updatedAt,
    tabs: compressedTabs
  }

  const compressed: CompressedSchema = {
    version: '1.0',
    compressed: true,
    definitions,
    form: compressedForm
  }

  const compressedSize = JSON.stringify(compressed).length
  const compressionRatio = ((originalSize - compressedSize) / originalSize * 100)

  return {
    original: schema,
    compressed,
    originalSize,
    compressedSize,
    compressionRatio: Math.round(compressionRatio * 100) / 100,
    stats: {
      validationDeduplications: validations.count,
      optionSetDeduplications: optionSets.count,
      fieldTemplateDeduplications: templates.count,
      formulaDeduplications: formulas.count
    }
  }
}

function compressField(
  field: FormField,
  validationRefs: Record<string, string>,
  optionRefs: Record<string, string>,
  formulaRefs: Record<string, string>,
  templateRefs: Record<string, string>
): CompressedField | string {
  const templateRef = templateRefs[field.id]
  
  const compressed: CompressedField = {
    id: field.id,
    type: field.type,
    name: field.name,
    label: field.label
  }

  if (templateRef) {
    compressed.$ref = templateRef
  } else {
    if (field.type !== undefined) compressed.type = field.type
    if (field.required !== undefined) compressed.required = field.required
  }

  if (field.placeholder !== undefined) {
    compressed.placeholder = field.placeholder
  }
  if (field.defaultValue !== undefined) {
    compressed.defaultValue = field.defaultValue
  }

  const validationRef = validationRefs[field.id]
  if (validationRef) {
    compressed.$validationRef = validationRef
  } else if (field.validation && field.validation.length > 0) {
    compressed.validation = field.validation
  }

  const optionRef = optionRefs[field.id]
  if (optionRef) {
    compressed.$optionsRef = optionRef
  } else if (field.props?.options) {
    if (!compressed.props) compressed.props = {}
    compressed.props.options = field.props.options
  }

  const formulaRef = formulaRefs[field.id]
  if (formulaRef) {
    compressed.$formulaRef = formulaRef
  } else if (field.formula) {
    compressed.formula = field.formula
  }

  if (field.conditional) {
    compressed.conditional = field.conditional
  }

  if (field.props && Object.keys(field.props).some(k => k !== 'options')) {
    if (!compressed.props) compressed.props = {}
    Object.entries(field.props).forEach(([key, value]) => {
      if (key !== 'options') {
        compressed.props![key] = value
      }
    })
  }

  return compressed
}

export function decompressSchema(compressed: CompressedSchema): FormSchema {
  if (!compressed.compressed) {
    return compressed as unknown as FormSchema
  }

  const { definitions, form } = compressed

  const tabs: FormTab[] = form.tabs.map(tab => ({
    id: tab.id,
    name: tab.name,
    icon: tab.icon,
    fields: tab.fields.map(f => decompressField(f, definitions))
  }))

  return {
    id: form.id,
    name: form.name,
    description: form.description,
    version: form.version,
    createdAt: form.createdAt,
    updatedAt: form.updatedAt,
    tabs
  }
}

function decompressField(
  field: CompressedField | string,
  definitions: SchemaDefinitions
): FormField {
  if (typeof field === 'string') {
    throw new Error('Field reference not supported in this version')
  }

  const decompressed: FormField = {
    id: field.id,
    type: field.type as any,
    name: field.name,
    label: field.label,
    required: field.required,
    placeholder: field.placeholder,
    defaultValue: field.defaultValue,
    props: field.props
  }

  if (field.$ref && definitions.fieldTemplates[field.$ref]) {
    const template = definitions.fieldTemplates[field.$ref]
    Object.assign(decompressed, template)
  }

  if (field.$validationRef && definitions.validations[field.$validationRef]) {
    decompressed.validation = definitions.validations[field.$validationRef]
  } else if (field.validation) {
    decompressed.validation = field.validation
  }

  if (field.$optionsRef && definitions.optionSets[field.$optionsRef]) {
    if (!decompressed.props) decompressed.props = {}
    decompressed.props.options = definitions.optionSets[field.$optionsRef]
  }

  if (field.$formulaRef && definitions.formulaTemplates[field.$formulaRef]) {
    decompressed.formula = definitions.formulaTemplates[field.$formulaRef]
  } else if (field.formula) {
    decompressed.formula = field.formula
  }

  if (field.conditional) {
    decompressed.conditional = field.conditional
  }

  return decompressed
}

export function minifySchema(schema: FormSchema): string {
  return JSON.stringify(schema)
}

export function prettifySchema(schema: FormSchema | CompressedSchema): string {
  return JSON.stringify(schema, null, 2)
}
