class ConfigValidator {
  constructor(schema = {}) {
    this.schema = schema;
    this.errors = [];
  }

  validate(config, schema = this.schema, path = '') {
    this.errors = [];
    this._validate(config, schema, path);
    return {
      valid: this.errors.length === 0,
      errors: this.errors,
      errorCount: this.errors.length,
      message: this.errors.length > 0 
        ? `配置校验失败，共 ${this.errors.length} 个错误：\n${this.errors.map(e => `  - ${e.message}`).join('\n')}`
        : '配置校验通过'
    };
  }

  _validate(value, schema, path) {
    if (!schema || typeof schema !== 'object') {
      return;
    }

    if (schema.required) {
      this._validateRequired(value, schema, path);
    }

    if (value !== undefined && value !== null && value !== '') {
      if (schema.type) {
        this._validateType(value, schema, path);
      }

      if (schema.enum) {
        this._validateEnum(value, schema, path);
      }

      if (schema.minLength !== undefined) {
        this._validateMinLength(value, schema, path);
      }

      if (schema.maxLength !== undefined) {
        this._validateMaxLength(value, schema, path);
      }

      if (schema.min !== undefined) {
        this._validateMin(value, schema, path);
      }

      if (schema.max !== undefined) {
        this._validateMax(value, schema, path);
      }
    }

    if (schema.properties && value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        const currentPath = path ? `${path}.${key}` : key;
        this._validate(value[key], propSchema, currentPath);
      }
    }

    if (schema.items && Array.isArray(value)) {
      value.forEach((item, index) => {
        const currentPath = `${path}[${index}]`;
        this._validate(item, schema.items, currentPath);
      });
    }
  }

  _validateRequired(value, schema, path) {
    if (value === undefined || value === null || value === '') {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 是必填项，但值为 ${value === '' ? '空字符串' : value}`,
        type: 'required',
        expected: '非空值',
        actual: value === '' ? '空字符串' : value
      });
    }
  }

  _validateType(value, schema, path) {
    const expectedType = schema.type;
    let actualType = typeof value;

    if (Array.isArray(value)) {
      actualType = 'array';
    } else if (value === null) {
      actualType = 'null';
    }

    if (actualType !== expectedType) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 类型错误：期望 ${expectedType}，实际为 ${actualType}`,
        type: 'type',
        expected: expectedType,
        actual: actualType,
        value: value
      });
    }
  }

  _validateEnum(value, schema, path) {
    if (!schema.enum.includes(value)) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 值不在允许范围内：期望 [${schema.enum.join(', ')}]，实际为 ${value}`,
        type: 'enum',
        expected: schema.enum,
        actual: value
      });
    }
  }

  _validateMinLength(value, schema, path) {
    if (typeof value === 'string' && value.length < schema.minLength) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 长度不足：最小长度为 ${schema.minLength}，实际长度为 ${value.length}`,
        type: 'minLength',
        expected: `>= ${schema.minLength}`,
        actual: value.length,
        value: value
      });
    }
  }

  _validateMaxLength(value, schema, path) {
    if (typeof value === 'string' && value.length > schema.maxLength) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 长度超出限制：最大长度为 ${schema.maxLength}，实际长度为 ${value.length}`,
        type: 'maxLength',
        expected: `<= ${schema.maxLength}`,
        actual: value.length,
        value: value
      });
    }
  }

  _validateMin(value, schema, path) {
    if (typeof value === 'number' && value < schema.min) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 值过小：最小值为 ${schema.min}，实际值为 ${value}`,
        type: 'min',
        expected: `>= ${schema.min}`,
        actual: value
      });
    }
  }

  _validateMax(value, schema, path) {
    if (typeof value === 'number' && value > schema.max) {
      this.errors.push({
        path: path || '(root)',
        field: path,
        message: `字段 '${path || '(root)'}' 值过大：最大值为 ${schema.max}，实际值为 ${value}`,
        type: 'max',
        expected: `<= ${schema.max}`,
        actual: value
      });
    }
  }

  setSchema(schema) {
    this.schema = schema;
    return this;
  }

  static create(schema) {
    return new ConfigValidator(schema);
  }
}

export default ConfigValidator;
