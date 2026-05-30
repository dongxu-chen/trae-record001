const Template = require('../models/Template');
const Task = require('../models/Task');

const DEFAULT_TEMPLATES = [
  {
    id: 'ner-basic',
    name: '基础命名实体识别',
    description: '通用的人名、组织、地点、日期等基础实体标注模板',
    category: 'entity',
    isGlobal: true,
    entities: [
      { label: 'PERSON', color: '#FF6B6B', description: '人物名称', examples: ['张三', 'John Smith', '李明'] },
      { label: 'ORGANIZATION', color: '#4ECDC4', description: '组织机构', examples: ['百度', 'Google', '清华大学'] },
      { label: 'LOCATION', color: '#45B7D1', description: '地理位置', examples: ['北京', '上海', 'New York'] },
      { label: 'DATE', color: '#96CEB4', description: '日期时间', examples: ['2024年1月1日', '2024-01-01'] },
      { label: 'EMAIL', color: '#FFEAA7', description: '电子邮箱', examples: ['test@example.com'] }
    ],
    relations: [],
    events: [],
    createdBy: 'system'
  },
  {
    id: 'business-relations',
    name: '商业关系抽取',
    description: '企业、人物之间的商业关系标注模板',
    category: 'relation',
    isGlobal: true,
    entities: [
      { label: 'PERSON', color: '#FF6B6B', description: '人物' },
      { label: 'ORGANIZATION', color: '#4ECDC4', description: '企业/组织' },
      { label: 'PRODUCT', color: '#9B59B6', description: '产品/服务' },
      { label: 'LOCATION', color: '#45B7D1', description: '地点' }
    ],
    relations: [
      { label: 'WORK_FOR', color: '#E74C3C', sourceLabel: 'PERSON', targetLabel: 'ORGANIZATION', description: '就职于' },
      { label: 'FOUNDED', color: '#F39C12', sourceLabel: 'PERSON', targetLabel: 'ORGANIZATION', description: '创立' },
      { label: 'LOCATED_IN', color: '#3498DB', sourceLabel: 'ORGANIZATION', targetLabel: 'LOCATION', description: '位于' },
      { label: 'PRODUCES', color: '#2ECC71', sourceLabel: 'ORGANIZATION', targetLabel: 'PRODUCT', description: '生产' },
      { label: 'CEO_OF', color: '#9B59B6', sourceLabel: 'PERSON', targetLabel: 'ORGANIZATION', description: '担任CEO' }
    ],
    events: [],
    createdBy: 'system'
  },
  {
    id: 'news-events',
    name: '新闻事件抽取',
    description: '新闻中常见事件类型的标注模板',
    category: 'event',
    isGlobal: true,
    entities: [
      { label: 'PERSON', color: '#FF6B6B', description: '人物' },
      { label: 'ORGANIZATION', color: '#4ECDC4', description: '组织' },
      { label: 'LOCATION', color: '#45B7D1', description: '地点' },
      { label: 'DATE', color: '#96CEB4', description: '日期' }
    ],
    relations: [],
    events: [
      {
        label: 'MEETING',
        color: '#E74C3C',
        description: '会议事件',
        roleTypes: [
          { role: 'participant', description: '参会者', entityLabel: 'PERSON' },
          { role: 'organizer', description: '主办方', entityLabel: 'ORGANIZATION' },
          { role: 'location', description: '地点', entityLabel: 'LOCATION' },
          { role: 'date', description: '日期', entityLabel: 'DATE' }
        ]
      },
      {
        label: 'CONTRACT',
        color: '#F39C12',
        description: '签约事件',
        roleTypes: [
          { role: 'party_a', description: '甲方', entityLabel: 'ORGANIZATION' },
          { role: 'party_b', description: '乙方', entityLabel: 'ORGANIZATION' },
          { role: 'signatory', description: '签署人', entityLabel: 'PERSON' },
          { role: 'date', description: '签署日期', entityLabel: 'DATE' }
        ]
      },
      {
        label: 'ACQUISITION',
        color: '#9B59B6',
        description: '收购事件',
        roleTypes: [
          { role: 'acquirer', description: '收购方', entityLabel: 'ORGANIZATION' },
          { role: 'target', description: '被收购方', entityLabel: 'ORGANIZATION' },
          { role: 'date', description: '日期', entityLabel: 'DATE' }
        ]
      }
    ],
    createdBy: 'system'
  },
  {
    id: 'general-ie',
    name: '通用信息抽取',
    description: '包含实体、关系、事件的完整标注模板',
    category: 'composite',
    isGlobal: true,
    entities: [
      { label: 'PERSON', color: '#FF6B6B', description: '人物' },
      { label: 'ORGANIZATION', color: '#4ECDC4', description: '组织' },
      { label: 'LOCATION', color: '#45B7D1', description: '地点' },
      { label: 'DATE', color: '#96CEB4', description: '日期' },
      { label: 'PRODUCT', color: '#9B59B6', description: '产品' },
      { label: 'EVENT', color: '#F39C12', description: '事件名' }
    ],
    relations: [
      { label: 'WORK_FOR', color: '#E74C3C', sourceLabel: 'PERSON', targetLabel: 'ORGANIZATION', description: '就职于' },
      { label: 'LOCATED_IN', color: '#3498DB', sourceLabel: 'ORGANIZATION', targetLabel: 'LOCATION', description: '位于' },
      { label: 'FOUNDED', color: '#F39C12', sourceLabel: 'PERSON', targetLabel: 'ORGANIZATION', description: '创立' }
    ],
    events: [
      {
        label: 'MEETING',
        color: '#E74C3C',
        description: '会议',
        roleTypes: [
          { role: 'participant', description: '参会者', entityLabel: 'PERSON' },
          { role: 'location', description: '地点', entityLabel: 'LOCATION' }
        ]
      }
    ],
    createdBy: 'system'
  }
];

exports.initializeDefaultTemplates = async () => {
  try {
    const existing = await Template.countDocuments({ createdBy: 'system' });
    if (existing === 0) {
      await Template.insertMany(DEFAULT_TEMPLATES);
      console.log('Default templates initialized');
    }
  } catch (error) {
    console.error('Error initializing templates:', error);
  }
};

exports.getAllTemplates = async (req, res) => {
  try {
    const { category, taskId, isGlobal } = req.query;
    
    const query = {};
    if (category) query.category = category;
    if (isGlobal !== undefined) query.isGlobal = isGlobal === 'true';
    if (taskId) query.$or = [{ taskId }, { isGlobal: true }];
    
    const templates = await Template.find(query)
      .sort({ isGlobal: -1, usageCount: -1, createdAt: -1 });
    
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getTemplateById = async (req, res) => {
  try {
    const template = await Template.findById(req.params.id);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.json(template);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.createTemplate = async (req, res) => {
  try {
    const template = new Template({
      ...req.body,
      createdBy: req.body.createdBy || 'user',
      isGlobal: req.body.isGlobal || false
    });
    await template.save();
    res.status(201).json(template);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.updateTemplate = async (req, res) => {
  try {
    const template = await Template.findByIdAndUpdate(
      req.params.id,
      { ...req.body, updatedAt: Date.now() },
      { new: true }
    );
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.json(template);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.deleteTemplate = async (req, res) => {
  try {
    const template = await Template.findByIdAndDelete(req.params.id);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    res.json({ message: 'Template deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.applyTemplateToTask = async (req, res) => {
  try {
    const { templateId, taskId } = req.params;
    
    const template = await Template.findById(templateId);
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    
    const task = await Task.findById(taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    const existingLabels = task.entityTypes?.map(et => et.label) || [];
    const newEntityTypes = [...(task.entityTypes || [])];
    
    template.entities.forEach(entity => {
      if (!existingLabels.includes(entity.label)) {
        newEntityTypes.push({
          label: entity.label,
          color: entity.color,
          description: entity.description
        });
      }
    });
    
    task.entityTypes = newEntityTypes;
    
    if (!task.relationTypes) task.relationTypes = [];
    template.relations.forEach(rel => {
      const exists = task.relationTypes.some(rt => rt.label === rel.label);
      if (!exists) {
        task.relationTypes.push({
          label: rel.label,
          color: rel.color,
          description: rel.description
        });
      }
    });
    
    if (!task.eventTypes) task.eventTypes = [];
    template.events.forEach(evt => {
      const exists = task.eventTypes.some(et => et.label === evt.label);
      if (!exists) {
        task.eventTypes.push({
          label: evt.label,
          color: evt.color,
          description: evt.description,
          roleTypes: evt.roleTypes
        });
      }
    });
    
    task.updatedAt = Date.now();
    await task.save();
    
    template.usageCount = (template.usageCount || 0) + 1;
    await template.save();
    
    res.json({
      message: 'Template applied successfully',
      task,
      appliedEntityCount: template.entities.length,
      appliedRelationCount: template.relations.length,
      appliedEventCount: template.events.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.rateTemplate = async (req, res) => {
  try {
    const { rating } = req.body;
    const template = await Template.findById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    
    const currentRating = template.rating || 0;
    const currentCount = template.ratingCount || 0;
    const newRating = ((currentRating * currentCount) + rating) / (currentCount + 1);
    
    template.rating = Math.round(newRating * 10) / 10;
    template.ratingCount = currentCount + 1;
    template.updatedAt = Date.now();
    await template.save();
    
    res.json({
      message: 'Rating submitted',
      rating: template.rating,
      ratingCount: template.ratingCount
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.getTemplateSuggestions = async (req, res) => {
  try {
    const { taskId } = req.params;
    
    const task = await Task.findById(taskId);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    const templates = await Template.find({
      $or: [{ isGlobal: true }, { taskId }]
    }).sort({ usageCount: -1, rating: -1 }).limit(10);
    
    const suggestions = templates.map(t => ({
      template: t,
      matchScore: calculateMatchScore(task, t)
    })).sort((a, b) => b.matchScore - a.matchScore);
    
    res.json(suggestions);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

function calculateMatchScore(task, template) {
  let score = 0;
  const taskLabels = task.entityTypes?.map(et => et.label) || [];
  const templateLabels = template.entities.map(e => e.label);
  
  templateLabels.forEach(label => {
    if (taskLabels.includes(label)) {
      score += 10;
    }
  });
  
  if (template.isGlobal) score += 5;
  if (template.usageCount > 10) score += 5;
  if (template.rating >= 4) score += 5;
  
  return Math.min(100, score);
}
