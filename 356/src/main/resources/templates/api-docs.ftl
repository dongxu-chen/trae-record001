# ${title}

**版本**: ${version}  
**服务器**: ${serverUrl}  
**生成时间**: ${generatedAt}

> ${description}

## 目录

1. [API接口](#api接口)
<#list controllers as controller>
   - [${controller.className}](#${controller.className?lower_case?replace(" ", "-")})
</#list>
2. [数据模型](#数据模型)
<#list models as model>
   - [${model.className}](#${model.className?lower_case?replace(" ", "-")})
</#list>

---

## API接口

<#list controllers as controller>
### ${controller.className}

**基础路径**: `${controller.basePath}`

<#if controller.description?? && controller.description != "">
${controller.description}
</#if>

<#list controller.methods as method>
#### ${method.httpMethod} ${method.path}

<#if method.summary?? && method.summary != "">
**描述**: ${method.summary}
</#if>

<#if method.deprecated>
⚠️ **此接口已废弃**
</#if>

<#if method.parameters?size &gt; 0>
**请求参数**:

| 名称 | 类型 | 位置 | 必填 | 默认值 | 描述 |
|------|------|------|------|--------|------|
<#list method.parameters as param>
| `${param.name}` | `${param.type}` | `${param.in}` | ${param.required?then('是', '否')} | ${param.defaultValue!'-'} | ${param.description!'-'} |
</#list>
</#if>

<#if method.requestBodyType?? && method.requestBodyType != "">
**请求体**: [`${method.requestBodyType}`](#${method.requestBodyType?lower_case?replace(" ", "-")})
</#if>

**响应类型**: 
<#if method.responseType?? && method.responseType != "" && method.responseType != "void" && method.responseType != "Void">
[`${method.responseType}`](#${method.responseType?lower_case?replace(" ", "-")})
<#else>
无返回值
</#if>

---

</#list>
</#list>

## 数据模型

<#list models as model>
### ${model.className}

<#if model.description?? && model.description != "">
${model.description}

</#if>

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
<#list model.fields as field>
| `${field.name}` | `${field.type}` | ${field.required?then('是', '否')} | ${field.description!'-'} |
</#list>

---

</#list>