let stages = [];
let stageTypes = [];
let templates = [];
let categories = [];
let selectedStage = null;
let currentCategory = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadStageTypes();
  await loadTemplates();
  initDragAndDrop();
});

async function loadStageTypes() {
  try {
    const response = await fetch('/api/editor/stage-types');
    const data = await response.json();
    stageTypes = data.types;
    renderStagePalette();
  } catch (err) {
    console.error('加载阶段类型失败:', err);
  }
}

async function loadTemplates() {
  try {
    const response = await fetch('/api/templates');
    const data = await response.json();
    templates = data.templates;
    categories = data.categories;
  } catch (err) {
    console.error('加载模板失败:', err);
  }
}

function renderStagePalette() {
  const palette = document.getElementById('stagePalette');
  palette.innerHTML = stageTypes.map(type => `
    <div class="palette-item" draggable="true" data-type="${type.id}">
      <div class="palette-icon" style="background: ${type.color}20; color: ${type.color}">
        ${getIcon(type.icon)}
      </div>
      <span class="palette-name">${type.name}</span>
    </div>
  `).join('');

  palette.querySelectorAll('.palette-item').forEach(item => {
    item.addEventListener('dragstart', handlePaletteDragStart);
  });
}

function getIcon(iconName) {
  const icons = {
    'git-branch': '🌿',
    'package': '📦',
    'hammer': '🔨',
    'check-circle': '✅',
    'shield': '🛡️',
    'archive': '🗃️',
    'rocket': '🚀',
    'terminal': '💻'
  };
  return icons[iconName] || '📋';
}

function initDragAndDrop() {
  const canvas = document.getElementById('pipelineCanvas');
  
  canvas.addEventListener('dragover', (e) => {
    e.preventDefault();
    canvas.classList.add('drag-over');
  });
  
  canvas.addEventListener('dragleave', () => {
    canvas.classList.remove('drag-over');
  });
  
  canvas.addEventListener('drop', (e) => {
    e.preventDefault();
    canvas.classList.remove('drag-over');
    
    const stageType = e.dataTransfer.getData('stageType');
    if (stageType) {
      addStageFromType(stageType);
    }
  });

  new Sortable(document.getElementById('stagesList'), {
    animation: 150,
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    handle: '.stage-header',
    onEnd: () => {
      updateStagesOrder();
    }
  });
}

function handlePaletteDragStart(e) {
  const stageType = e.target.getAttribute('data-type');
  e.dataTransfer.setData('stageType', stageType);
}

function addStageFromType(typeId) {
  const type = stageTypes.find(t => t.id === typeId);
  if (!type) return;

  const stage = {
    id: `stage-${Date.now()}`,
    type: typeId,
    name: type.name,
    icon: type.icon,
    color: type.color,
    script: getDefaultScript(typeId),
    image: getDefaultImage(typeId),
    cache: null,
    artifacts: null,
    parallel: false,
    tasks: [],
    condition: null,
    qualityGate: null,
    retry: 0,
    volumes: []
  };

  stages.push(stage);
  renderStages();
}

function addCustomStage() {
  const stage = {
    id: `stage-${Date.now()}`,
    type: 'custom',
    name: '自定义阶段',
    icon: 'terminal',
    color: '#5c6370',
    script: ['echo "Hello World"'],
    image: 'alpine:latest',
    cache: null,
    artifacts: null,
    parallel: false,
    tasks: [],
    condition: null,
    qualityGate: null,
    retry: 0,
    volumes: []
  };

  stages.push(stage);
  renderStages();
}

function getDefaultScript(typeId) {
  const scripts = {
    checkout: ['git clone $CLONE_URL .', 'git checkout $GIT_COMMIT'],
    install: ['npm ci'],
    build: ['npm run build'],
    test: ['npm test'],
    quality: ['npm run lint'],
    package: ['tar -czf dist.tar.gz dist/'],
    deploy: ['echo "Deploying..."'],
    custom: ['echo "Custom script"']
  };
  return scripts[typeId] || ['echo "Running..."'];
}

function getDefaultImage(typeId) {
  const images = {
    checkout: 'alpine/git:latest',
    install: 'node:18-alpine',
    build: 'node:18-alpine',
    test: 'node:18-alpine',
    quality: 'node:18-alpine',
    package: 'alpine:latest',
    deploy: 'docker:latest',
    custom: 'alpine:latest'
  };
  return images[typeId] || 'alpine:latest';
}

function renderStages() {
  const stagesList = document.getElementById('stagesList');
  const emptyState = document.getElementById('emptyState');

  if (stages.length === 0) {
    stagesList.classList.add('hidden');
    emptyState.classList.remove('hidden');
    return;
  }

  stagesList.classList.remove('hidden');
  emptyState.classList.add('hidden');

  stagesList.innerHTML = stages.map((stage, index) => `
    <div class="stage-card" data-id="${stage.id}" onclick="selectStage('${stage.id}')">
      <div class="stage-header">
        <div class="stage-icon" style="background: ${stage.color}20; color: ${stage.color}">
          ${getIcon(stage.icon)}
        </div>
        <div class="stage-info">
          <div class="stage-name">${stage.name}</div>
          <div class="stage-type">${getTypeName(stage.type)}</div>
        </div>
        <div class="stage-actions">
          ${stage.cache ? '<span class="stage-badge badge-cache">💾 缓存</span>' : ''}
          ${stage.parallel ? '<span class="stage-badge badge-parallel">⚡ 并行</span>' : ''}
          ${stage.qualityGate ? '<span class="stage-badge badge-quality">🛡️ 质量</span>' : ''}
          ${stage.retry > 0 ? `<span class="stage-badge badge-retry">🔄 重试${stage.retry}</span>` : ''}
        </div>
        <button class="delete-stage-btn" onclick="event.stopPropagation(); deleteStage('${stage.id}')">
          ×
        </button>
      </div>
      <div class="stage-script-preview">
        ${Array.isArray(stage.script) ? stage.script.join(' && ') : stage.script}
      </div>
    </div>
    ${index < stages.length - 1 ? '<div class="stage-connector"><div class="connector-line"></div></div>' : ''}
  `).join('');
}

function getTypeName(typeId) {
  const type = stageTypes.find(t => t.id === typeId);
  return type ? type.name : '自定义';
}

function updateStagesOrder() {
  const stageCards = document.querySelectorAll('.stage-card');
  const newOrder = Array.from(stageCards).map(card => card.getAttribute('data-id'));
  
  stages = newOrder.map(id => stages.find(s => s.id === id)).filter(Boolean);
}

function selectStage(stageId) {
  selectedStage = stages.find(s => s.id === stageId);
  if (!selectedStage) return;

  renderConfigPanel();
  document.getElementById('configPanel').classList.add('active');
}

function closeConfigPanel() {
  document.getElementById('configPanel').classList.remove('active');
  selectedStage = null;
}

function renderConfigPanel() {
  if (!selectedStage) return;

  const content = document.getElementById('configContent');
  content.innerHTML = `
    <div class="config-section">
      <div class="config-section-title">基本配置</div>
      
      <div class="form-group">
        <label>阶段名称</label>
        <input type="text" value="${selectedStage.name}" 
               onchange="updateStage('name', this.value)">
      </div>
      
      <div class="form-group">
        <label>Docker 镜像</label>
        <input type="text" value="${selectedStage.image || ''}" 
               placeholder="node:18-alpine"
               onchange="updateStage('image', this.value)">
      </div>
    </div>

    <div class="config-section">
      <div class="config-section-title">执行脚本</div>
      <div class="form-group">
        <label>命令（每行一个）</label>
        <textarea class="script-editor" 
                  onchange="updateStageScript(this.value)">${Array.isArray(selectedStage.script) ? selectedStage.script.join('\n') : selectedStage.script}</textarea>
      </div>
    </div>

    <div class="config-section">
      <div class="config-section-title">高级选项</div>
      
      <div class="checkbox-group">
        <input type="checkbox" id="enableCache" 
               ${selectedStage.cache ? 'checked' : ''}
               onchange="toggleCache()">
        <label for="enableCache">启用任务缓存</label>
      </div>

      ${selectedStage.cache ? `
        <div class="form-group" style="margin-top: 12px;">
          <label>缓存 Key</label>
          <input type="text" value="${selectedStage.cache?.key || ''}" 
                 placeholder="node-modules-{{ checksum 'package-lock.json' }}"
                 onchange="updateCache('key', this.value)">
        </div>
        <div class="form-group">
          <label>缓存路径（每行一个）</label>
          <div class="path-list" id="cachePathList">
            ${(selectedStage.cache?.paths || []).map((p, i) => `
              <div class="path-item">
                <input type="text" value="${p}" onchange="updateCachePath(${i}, this.value)">
                <button class="remove-path-btn" onclick="removeCachePath(${i})">×</button>
              </div>
            `).join('')}
          </div>
          <button class="add-task-btn" style="margin-top: 8px;" onclick="addCachePath()">+ 添加路径</button>
        </div>
      ` : ''}

      <div class="checkbox-group">
        <input type="checkbox" id="enableParallel" 
               ${selectedStage.parallel ? 'checked' : ''}
               onchange="toggleParallel()">
        <label for="enableParallel">并行执行任务</label>
      </div>

      ${selectedStage.parallel ? `
        <div class="parallel-tasks" style="margin-top: 12px;">
          ${(selectedStage.tasks || []).map((task, i) => `
            <div class="parallel-task">
              <input type="text" placeholder="任务名称" value="${task.name || ''}"
                     onchange="updateTask(${i}, 'name', this.value)">
              <input type="text" placeholder="脚本命令" value="${task.script || ''}"
                     onchange="updateTask(${i}, 'script', this.value)">
              <button class="remove-path-btn" onclick="removeTask(${i})">×</button>
            </div>
          `).join('')}
          <button class="add-task-btn" onclick="addTask()">+ 添加并行任务</button>
        </div>
      ` : ''}

      <div class="checkbox-group">
        <input type="checkbox" id="enableQuality" 
               ${selectedStage.qualityGate ? 'checked' : ''}
               onchange="toggleQualityGate()">
        <label for="enableQuality">质量红线检查</label>
      </div>

      ${selectedStage.qualityGate ? `
        <div class="form-group" style="margin-top: 12px;">
          <label>测试覆盖率阈值 (%)</label>
          <input type="number" value="${selectedStage.qualityGate?.coverageThreshold || 80}" 
                 min="0" max="100"
                 onchange="updateQualityGate('coverageThreshold', parseInt(this.value))">
        </div>
        <div class="form-group">
          <label>覆盖率报告文件</label>
          <input type="text" value="${selectedStage.qualityGate?.coverageFile || ''}" 
                 placeholder="coverage/coverage-summary.json"
                 onchange="updateQualityGate('coverageFile', this.value)">
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="blockDeploy" 
                 ${selectedStage.qualityGate?.blockDeployment ? 'checked' : ''}
                 onchange="updateQualityGate('blockDeployment', this.checked)">
          <label for="blockDeploy">不达标时阻断部署</label>
        </div>
      ` : ''}

      <div class="form-group" style="margin-top: 16px;">
        <label>失败重试次数</label>
        <input type="number" value="${selectedStage.retry || 0}" 
               min="0" max="10"
               onchange="updateStage('retry', parseInt(this.value))">
      </div>
    </div>

    <div class="config-section">
      <div class="config-section-title">条件执行</div>
      <div class="form-group">
        <label>执行分支（逗号分隔，留空表示所有分支）</label>
        <input type="text" value="${selectedStage.condition?.branch?.join(', ') || ''}" 
               placeholder="main, master, develop"
               onchange="updateConditionBranch(this.value)">
      </div>
    </div>

    <div class="config-section">
      <div class="config-section-title">构建产物</div>
      <div class="checkbox-group">
        <input type="checkbox" id="enableArtifacts" 
               ${selectedStage.artifacts ? 'checked' : ''}
               onchange="toggleArtifacts()">
        <label for="enableArtifacts">归档构建产物</label>
      </div>

      ${selectedStage.artifacts ? `
        <div class="form-group" style="margin-top: 12px;">
          <label>产物名称</label>
          <input type="text" value="${selectedStage.artifacts?.name || ''}" 
                 placeholder="build-output"
                 onchange="updateArtifacts('name', this.value)">
        </div>
        <div class="form-group">
          <label>产物路径（每行一个）</label>
          <div class="path-list" id="artifactPathList">
            ${(selectedStage.artifacts?.paths || []).map((p, i) => `
              <div class="path-item">
                <input type="text" value="${p}" onchange="updateArtifactPath(${i}, this.value)">
                <button class="remove-path-btn" onclick="removeArtifactPath(${i})">×</button>
              </div>
            `).join('')}
          </div>
          <button class="add-task-btn" style="margin-top: 8px;" onclick="addArtifactPath()">+ 添加路径</button>
        </div>
      ` : ''}
    </div>
  `;
}

function updateStage(field, value) {
  if (!selectedStage) return;
  selectedStage[field] = value;
  renderStages();
}

function updateStageScript(value) {
  if (!selectedStage) return;
  selectedStage.script = value.split('\n').filter(s => s.trim());
  renderStages();
}

function toggleCache() {
  if (!selectedStage) return;
  if (selectedStage.cache) {
    selectedStage.cache = null;
  } else {
    selectedStage.cache = { key: '', paths: ['node_modules'] };
  }
  renderConfigPanel();
  renderStages();
}

function updateCache(field, value) {
  if (!selectedStage || !selectedStage.cache) return;
  selectedStage.cache[field] = value;
}

function updateCachePath(index, value) {
  if (!selectedStage || !selectedStage.cache) return;
  selectedStage.cache.paths[index] = value;
}

function addCachePath() {
  if (!selectedStage || !selectedStage.cache) return;
  selectedStage.cache.paths.push('');
  renderConfigPanel();
}

function removeCachePath(index) {
  if (!selectedStage || !selectedStage.cache) return;
  selectedStage.cache.paths.splice(index, 1);
  renderConfigPanel();
}

function toggleParallel() {
  if (!selectedStage) return;
  selectedStage.parallel = !selectedStage.parallel;
  if (selectedStage.parallel && !selectedStage.tasks) {
    selectedStage.tasks = [{ name: 'task-1', script: '' }];
  }
  renderConfigPanel();
  renderStages();
}

function updateTask(index, field, value) {
  if (!selectedStage || !selectedStage.tasks) return;
  selectedStage.tasks[index][field] = value;
}

function addTask() {
  if (!selectedStage || !selectedStage.tasks) return;
  selectedStage.tasks.push({ name: `task-${selectedStage.tasks.length + 1}`, script: '' });
  renderConfigPanel();
}

function removeTask(index) {
  if (!selectedStage || !selectedStage.tasks) return;
  selectedStage.tasks.splice(index, 1);
  renderConfigPanel();
}

function toggleQualityGate() {
  if (!selectedStage) return;
  if (selectedStage.qualityGate) {
    selectedStage.qualityGate = null;
  } else {
    selectedStage.qualityGate = {
      coverageThreshold: 80,
      coverageFile: 'coverage/coverage-summary.json',
      blockDeployment: true
    };
  }
  renderConfigPanel();
  renderStages();
}

function updateQualityGate(field, value) {
  if (!selectedStage || !selectedStage.qualityGate) return;
  selectedStage.qualityGate[field] = value;
}

function updateConditionBranch(value) {
  if (!selectedStage) return;
  const branches = value.split(',').map(b => b.trim()).filter(Boolean);
  if (branches.length > 0) {
    if (!selectedStage.condition) selectedStage.condition = {};
    selectedStage.condition.branch = branches;
  } else {
    if (selectedStage.condition) {
      delete selectedStage.condition.branch;
      if (Object.keys(selectedStage.condition).length === 0) {
        selectedStage.condition = null;
      }
    }
  }
}

function toggleArtifacts() {
  if (!selectedStage) return;
  if (selectedStage.artifacts) {
    selectedStage.artifacts = null;
  } else {
    selectedStage.artifacts = { name: 'build-output', paths: ['dist/'] };
  }
  renderConfigPanel();
  renderStages();
}

function updateArtifacts(field, value) {
  if (!selectedStage || !selectedStage.artifacts) return;
  selectedStage.artifacts[field] = value;
}

function updateArtifactPath(index, value) {
  if (!selectedStage || !selectedStage.artifacts) return;
  selectedStage.artifacts.paths[index] = value;
}

function addArtifactPath() {
  if (!selectedStage || !selectedStage.artifacts) return;
  selectedStage.artifacts.paths.push('');
  renderConfigPanel();
}

function removeArtifactPath(index) {
  if (!selectedStage || !selectedStage.artifacts) return;
  selectedStage.artifacts.paths.splice(index, 1);
  renderConfigPanel();
}

function deleteStage(stageId) {
  stages = stages.filter(s => s.id !== stageId);
  if (selectedStage?.id === stageId) {
    closeConfigPanel();
  }
  renderStages();
}

function showTemplates() {
  document.getElementById('templatesModal').classList.add('active');
  renderTemplates();
  renderCategoryFilters();
}

function closeTemplates() {
  document.getElementById('templatesModal').classList.remove('active');
}

function renderCategoryFilters() {
  const container = document.getElementById('categoryFilters');
  container.innerHTML = `
    <span class="category-tag ${!currentCategory ? 'active' : ''}" onclick="filterByCategory(null)">全部</span>
    ${categories.map(cat => `
      <span class="category-tag ${currentCategory === cat ? 'active' : ''}" onclick="filterByCategory('${cat}')">${cat}</span>
    `).join('')}
  `;
}

function filterByCategory(category) {
  currentCategory = category;
  renderTemplates();
  renderCategoryFilters();
}

function filterTemplates() {
  renderTemplates();
}

function renderTemplates() {
  const search = document.getElementById('templateSearch').value.toLowerCase();
  
  let filtered = templates;
  
  if (currentCategory) {
    filtered = filtered.filter(t => t.category === currentCategory);
  }
  
  if (search) {
    filtered = filtered.filter(t => 
      t.name.toLowerCase().includes(search) ||
      t.description.toLowerCase().includes(search) ||
      t.tags?.some(tag => tag.toLowerCase().includes(search))
    );
  }

  const grid = document.getElementById('templatesGrid');
  grid.innerHTML = filtered.map(template => `
    <div class="template-card" onclick="useTemplate('${template.id}')">
      <div class="template-header">
        <div class="template-icon">${getTemplateIcon(template.icon)}</div>
        <div class="template-meta">
          <h3>${template.name}</h3>
          <div class="template-category">${template.category}</div>
        </div>
      </div>
      <p class="template-desc">${template.description}</p>
      <div class="template-tags">
        ${(template.tags || []).map(tag => `<span class="template-tag">${tag}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

function getTemplateIcon(iconName) {
  const icons = {
    nodejs: '🟢',
    docker: '🐳',
    java: '☕',
    python: '🐍',
    go: '🔷',
    react: '⚛️',
    vue: '💚',
    monorepo: '📦'
  };
  return icons[iconName] || '📋';
}

async function useTemplate(templateId) {
  try {
    const response = await fetch(`/api/templates/${templateId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('pipelineName').value,
        repository: document.getElementById('repository').value,
        branch: document.getElementById('branch').value
      })
    });

    const data = await response.json();
    importPipelineData(data.config);
    closeTemplates();
    showToast('模板已应用！', 'success');
  } catch (err) {
    console.error('应用模板失败:', err);
    showToast('应用模板失败', 'error');
  }
}

function importPipelineData(config) {
  stages = (config.stages || []).map((stageConfig, index) => {
    const type = guessStageType(stageConfig.name);
    const typeInfo = stageTypes.find(t => t.id === type) || { icon: 'terminal', color: '#5c6370' };
    
    return {
      id: `stage-${Date.now()}-${index}`,
      type: type,
      name: stageConfig.name,
      icon: typeInfo.icon,
      color: typeInfo.color,
      script: stageConfig.script || [],
      image: stageConfig.image || '',
      cache: stageConfig.cache || null,
      artifacts: stageConfig.artifacts || null,
      parallel: stageConfig.parallel || false,
      tasks: stageConfig.tasks || [],
      condition: stageConfig.condition || null,
      qualityGate: stageConfig.qualityGate || null,
      retry: stageConfig.retry || 0,
      volumes: stageConfig.volumes || []
    };
  });

  renderStages();
}

function guessStageType(stageName) {
  const name = stageName.toLowerCase();
  if (name.includes('checkout') || name.includes('clone')) return 'checkout';
  if (name.includes('install') || name.includes('setup')) return 'install';
  if (name.includes('build') || name.includes('compile')) return 'build';
  if (name.includes('test')) return 'test';
  if (name.includes('quality') || name.includes('lint')) return 'quality';
  if (name.includes('package') || name.includes('artifact')) return 'package';
  if (name.includes('deploy') || name.includes('release')) return 'deploy';
  return 'custom';
}

async function exportConfig() {
  const pipeline = {
    name: document.getElementById('pipelineName').value,
    repository: document.getElementById('repository').value,
    branch: document.getElementById('branch').value,
    stages: stages
  };

  try {
    const response = await fetch('/api/editor/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pipeline, format: 'yaml' })
    });

    const yaml = await response.text();
    document.getElementById('exportOutput').textContent = yaml;
    document.getElementById('exportModal').classList.add('active');
  } catch (err) {
    console.error('导出失败:', err);
    showToast('导出失败', 'error');
  }
}

function closeExport() {
  document.getElementById('exportModal').classList.remove('active');
}

function copyToClipboard() {
  const output = document.getElementById('exportOutput').textContent;
  navigator.clipboard.writeText(output).then(() => {
    showToast('已复制到剪贴板！', 'success');
  });
}

function downloadYaml() {
  const output = document.getElementById('exportOutput').textContent;
  const blob = new Blob([output], { type: 'text/yaml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${document.getElementById('pipelineName').value || 'pipeline'}.yaml`;
  a.click();
  URL.revokeObjectURL(url);
}

function importConfig() {
  document.getElementById('importFile').click();
}

async function handleImport(event) {
  const file = event.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const response = await fetch('/api/editor/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        pipeline: { stages: [] }, 
        format: 'json' 
      })
    });
    
    showToast('请使用导出的YAML格式文件', 'error');
  } catch (err) {
    console.error('导入失败:', err);
    showToast('导入失败', 'error');
  }
  
  event.target.value = '';
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 3000);
}
