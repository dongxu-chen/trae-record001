<template>
  <div class="panel right-panel">
    <div class="panel-header">属性配置</div>
    
    <div v-if="!selectedItem" class="empty-tip">
      请选择一个组件进行配置
    </div>
    
    <div v-else>
      <div class="config-section">
        <div class="config-title">基础属性</div>
        
        <div class="config-item">
          <label class="config-label">字段标签</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.label"
            @input="updateItem"
          />
        </div>
        
        <div class="config-item">
          <label class="config-label">字段名称</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.field"
            @input="updateItem"
          />
        </div>
        
        <div class="config-item">
          <label class="config-label">占位提示</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.placeholder"
            @input="updateItem"
          />
        </div>
        
        <div class="config-item">
          <label class="config-label">默认值</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.defaultValue"
            @input="updateItem"
          />
        </div>
        
        <div class="config-item">
          <label class="config-checkbox">
            <input
              type="checkbox"
              v-model="selectedItem.required"
              @change="updateItem"
            />
            必填字段
          </label>
        </div>
      </div>
      
      <div v-if="hasOptions" class="config-section">
        <div class="config-title">数据源配置</div>
        
        <div class="config-item">
          <label class="config-label">数据源类型</label>
          <select
            class="config-input"
            v-model="selectedItem.dataSource.type"
            @change="updateItem"
          >
            <option value="static">静态数据</option>
            <option value="async">异步加载</option>
          </select>
        </div>
        
        <div v-if="selectedItem.dataSource.type === 'static'">
          <div v-for="(opt, index) in selectedItem.options" :key="index" class="option-item">
            <input
              type="text"
              class="config-input"
              placeholder="标签"
              v-model="opt.label"
              @input="updateItem"
            />
            <input
              type="text"
              class="config-input"
              placeholder="值"
              v-model="opt.value"
              @input="updateItem"
            />
            <button class="btn btn-default btn-small" @click="removeOption(index)">删除</button>
          </div>
          
          <button class="btn btn-default btn-small" @click="addOption">+ 添加选项</button>
        </div>
        
        <div v-else>
          <div class="config-item">
            <label class="config-label">请求地址 (URL)</label>
            <input
              type="text"
              class="config-input"
              v-model="selectedItem.dataSource.url"
              placeholder="https://api.example.com/options"
              @input="updateItem"
            />
          </div>
          
          <div class="config-item">
            <label class="config-label">请求方法</label>
            <select
              class="config-input"
              v-model="selectedItem.dataSource.method"
              @change="updateItem"
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
            </select>
          </div>
          
          <div class="config-row">
            <div class="config-item">
              <label class="config-label">标签字段</label>
              <input
                type="text"
                class="config-input"
                v-model="selectedItem.dataSource.labelField"
                placeholder="label"
                @input="updateItem"
              />
            </div>
            <div class="config-item">
              <label class="config-label">值字段</label>
              <input
                type="text"
                class="config-input"
                v-model="selectedItem.dataSource.valueField"
                placeholder="value"
                @input="updateItem"
              />
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="selectedItem.type === 'number'" class="config-section">
        <div class="config-title">数字配置</div>
        
        <div class="config-row">
          <div class="config-item">
            <label class="config-label">最小值</label>
            <input
              type="number"
              class="config-input"
              v-model.number="selectedItem.min"
              @input="updateItem"
            />
          </div>
          <div class="config-item">
            <label class="config-label">最大值</label>
            <input
              type="number"
              class="config-input"
              v-model.number="selectedItem.max"
              @input="updateItem"
            />
          </div>
        </div>
        
        <div class="config-item">
          <label class="config-label">步长</label>
          <input
            type="number"
            class="config-input"
            v-model.number="selectedItem.step"
            @input="updateItem"
          />
        </div>
      </div>
      
      <div class="config-section">
        <div class="config-title">校验规则</div>
        
        <div class="config-item">
          <label class="config-label">正则表达式</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.validation.pattern"
            placeholder="如: ^[a-zA-Z]+$"
            @input="updateItem"
          />
        </div>
        
        <div v-if="selectedItem.validation.pattern" class="config-item">
          <div class="config-row">
            <button class="btn btn-default btn-small" @click="escapeRegex">转义特殊字符</button>
          </div>
          <div class="config-item" style="margin-top: 8px;">
            <label class="config-label">转义后结果预览:</label>
            <div class="escaped-preview">{{ escapedPattern }}</div>
          </div>
          <div class="config-item" style="margin-top: 8px;">
            <label class="config-label">测试正则:</label>
            <input
              type="text"
              class="config-input"
              v-model="regexTestInput"
              placeholder="输入测试文本"
            />
            <div :class="['regex-result', regexTestResult ? 'valid' : 'invalid']">
              {{ regexTestResult ? '✓ 匹配成功' : '✗ 匹配失败' }}
            </div>
          </div>
        </div>
        
        <div class="config-row">
          <div class="config-item">
            <label class="config-label">最小长度</label>
            <input
              type="number"
              class="config-input"
              v-model.number="selectedItem.validation.minLength"
              @input="updateItem"
            />
          </div>
          <div class="config-item">
            <label class="config-label">最大长度</label>
            <input
              type="number"
              class="config-input"
              v-model.number="selectedItem.validation.maxLength"
              @input="updateItem"
            />
          </div>
        </div>
        
        <div class="config-item">
          <label class="config-label">错误提示</label>
          <input
            type="text"
            class="config-input"
            v-model="selectedItem.validation.message"
            placeholder="自定义错误提示信息"
            @input="updateItem"
          />
        </div>
      </div>
      
      <div class="config-section">
        <div class="config-title">联动配置</div>
        
        <div class="config-item">
          <label class="config-checkbox">
            <input
              type="checkbox"
              v-model="selectedItem.linkage.enabled"
              @change="updateItem"
            />
            启用联动
          </label>
        </div>
        
        <div v-if="selectedItem.linkage.enabled">
          <div v-for="(rule, index) in selectedItem.linkage.rules" :key="index" class="linkage-rule">
            <div class="linkage-row">
              <select
                class="config-input"
                v-model="rule.targetField"
                @change="updateItem"
              >
                <option value="">选择目标字段</option>
                <option
                  v-for="item in otherFields"
                  :key="item.id"
                  :value="item.id"
                >
                  {{ item.label }}
                </option>
              </select>
              <select
                class="config-input"
                v-model="rule.operator"
                @change="updateItem"
              >
                <option value="==">等于</option>
                <option value="!=">不等于</option>
                <option value="includes">包含</option>
                <option value="empty">为空</option>
                <option value="notEmpty">不为空</option>
              </select>
            </div>
            
            <div class="linkage-row">
              <input
                type="text"
                class="config-input"
                v-model="rule.value"
                placeholder="条件值"
                @input="updateItem"
              />
              <select
                class="config-input"
                v-model="rule.action"
                @change="updateItem"
              >
                <option value="hide">隐藏</option>
                <option value="show">显示</option>
              </select>
              <button class="btn btn-default btn-small" @click="removeRule(index)">删除</button>
            </div>
          </div>
          
          <button class="btn btn-default btn-small" @click="addRule">+ 添加联动规则</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  selectedItem: {
    type: Object,
    default: null
  },
  formItems: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['updateItem'])

const regexTestInput = ref('')

const hasOptions = computed(() => {
  return ['radio', 'checkbox', 'select'].includes(props.selectedItem?.type)
})

const otherFields = computed(() => {
  if (!props.selectedItem) return []
  return props.formItems.filter(item => item.id !== props.selectedItem.id)
})

const escapedPattern = computed(() => {
  if (!props.selectedItem?.validation?.pattern) return ''
  return props.selectedItem.validation.pattern
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
})

const regexTestResult = computed(() => {
  if (!props.selectedItem?.validation?.pattern || !regexTestInput.value) return false
  try {
    const regex = new RegExp(props.selectedItem.validation.pattern)
    return regex.test(regexTestInput.value)
  } catch (e) {
    return false
  }
})

const escapeRegex = () => {
  if (!props.selectedItem?.validation?.pattern) return
  props.selectedItem.validation.pattern = props.selectedItem.validation.pattern
    .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  updateItem()
}

const updateItem = () => {
  emit('updateItem')
}

watch(() => props.selectedItem, () => {
  regexTestInput.value = ''
})

const addOption = () => {
  const index = props.selectedItem.options.length + 1
  props.selectedItem.options.push({
    label: `选项${index}`,
    value: `option${index}`
  })
  updateItem()
}

const removeOption = (index) => {
  props.selectedItem.options.splice(index, 1)
  updateItem()
}

const addRule = () => {
  props.selectedItem.linkage.rules.push({
    targetField: '',
    operator: '==',
    value: '',
    action: 'hide'
  })
  updateItem()
}

const removeRule = (index) => {
  props.selectedItem.linkage.rules.splice(index, 1)
  updateItem()
}
</script>
