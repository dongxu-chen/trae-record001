import { useState, useEffect } from 'react';
import { useTemplateStore } from '@/stores/templateStore';
import TemplateCard from '@/components/TemplateCard';
import DecorativeDivider from '@/components/DecorativeDivider';
import { Plus, Trash2, X } from 'lucide-react';
import type { CardTemplate, TemplateLayout } from '@/types';

const DEFAULT_LAYOUT: TemplateLayout = {
  name: { x: 30, y: 35, fontSize: 22, color: '#d4a853', fontFamily: 'Cinzel, serif' },
  type: { x: 30, y: 58, fontSize: 13, color: '#a89b8c' },
  rarity: { x: 370, y: 35, iconSize: 18 },
  attributes: {
    attack: { x: 30, y: 530, fontSize: 16, color: '#e74c3c' },
    defense: { x: 120, y: 530, fontSize: 16, color: '#3498db' },
    health: { x: 210, y: 530, fontSize: 16, color: '#2ecc71' },
    cost: { x: 300, y: 530, fontSize: 16, color: '#9b59b6' },
  },
  skills: { x: 30, y: 370, maxWidth: 340, fontSize: 12, lineHeight: 18 },
  description: { x: 30, y: 290, maxWidth: 340, fontSize: 12, lineHeight: 18 },
  flavorText: { x: 30, y: 460, maxWidth: 340, fontSize: 11, fontStyle: 'italic' },
  backgroundImage: { x: 0, y: 0, width: 400, height: 560 },
  characterImage: { x: 50, y: 80, width: 300, height: 200 },
};

function createEmptyTemplate(): CardTemplate {
  return {
    id: crypto.randomUUID(),
    name: '',
    description: '',
    style: 'fantasy',
    width: 400,
    height: 560,
    colors: {
      background: '#1a1a2e',
      primary: '#d4a853',
      secondary: '#a89b8c',
      accent: '#e74c3c',
      text: '#e8e0d4',
      textSecondary: '#a89b8c',
      cardBackground: '#16213e',
      divider: '#2a2a4a',
    },
    borders: { width: 3, color: '#d4a853', radius: 12, style: 'ornate' },
    layout: { ...DEFAULT_LAYOUT },
    builtIn: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

const STYLE_OPTIONS = [
  { value: 'fantasy', label: '奇幻' },
  { value: 'sci-fi', label: '科幻' },
  { value: 'minimal', label: '极简' },
  { value: 'classic', label: '经典' },
  { value: 'custom', label: '自定义' },
];

export default function Templates() {
  const { templates, fetchTemplates, createTemplate, updateTemplate, deleteTemplate } = useTemplateStore();
  const [editing, setEditing] = useState<CardTemplate | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleCreate = () => {
    setEditing(createEmptyTemplate());
    setShowEditor(true);
  };

  const handleEdit = (template: CardTemplate) => {
    setEditing({ ...template });
    setShowEditor(true);
  };

  const handleSave = async () => {
    if (!editing || !editing.name) return;
    const existing = templates.find((t) => t.id === editing.id);
    if (existing) {
      await updateTemplate(editing.id, editing);
    } else {
      await createTemplate(editing);
    }
    setShowEditor(false);
    setEditing(null);
  };

  const handleDelete = async (id: string) => {
    const tmpl = templates.find((t) => t.id === id);
    if (tmpl?.builtIn) return;
    await deleteTemplate(id);
  };

  const updateEditing = (partial: Partial<CardTemplate>) => {
    if (!editing) return;
    setEditing({ ...editing, ...partial });
  };

  const updateColors = (key: string, value: string) => {
    if (!editing) return;
    setEditing({ ...editing, colors: { ...editing.colors, [key]: value } });
  };

  const updateBorders = (key: string, value: number | string) => {
    if (!editing) return;
    setEditing({ ...editing, borders: { ...editing.borders, [key]: value } });
  };

  const LAYOUT_SECTIONS = [
    { key: 'name' as const, label: '名称' },
    { key: 'type' as const, label: '类型' },
    { key: 'skills' as const, label: '技能' },
    { key: 'description' as const, label: '描述' },
    { key: 'flavorText' as const, label: '风味文字' },
  ];

  return (
    <div className="min-h-screen p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-cinzel text-2xl text-gold-500">模板管理</h1>
        <button onClick={handleCreate} className="metal-button-primary px-4 py-2 rounded flex items-center gap-2 text-sm">
          <Plus size={16} /> 创建模板
        </button>
      </div>

      <DecorativeDivider />

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-6">
        {templates.map((tmpl) => (
          <div key={tmpl.id} className="relative group">
            <TemplateCard
              template={tmpl}
              selected={false}
              onClick={() => handleEdit(tmpl)}
            />
            {!tmpl.builtIn && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(tmpl.id);
                }}
                className="absolute top-2 right-2 p-1 bg-dark-900/80 rounded text-crimson-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        ))}
      </div>

      {showEditor && editing && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowEditor(false)} />
          <div className="relative ml-auto w-full max-w-lg bg-dark-800 border-l border-dark-600 overflow-y-auto">
            <div className="sticky top-0 bg-dark-800 border-b border-dark-600 p-4 flex items-center justify-between">
              <h2 className="font-cinzel text-gold-500">编辑模板</h2>
              <button onClick={() => setShowEditor(false)} className="text-parchment-200/60 hover:text-parchment-200">
                <X size={20} />
              </button>
            </div>

            <div className="p-4 space-y-5">
              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-1">名称</label>
                <input
                  type="text"
                  value={editing.name}
                  onChange={(e) => updateEditing({ name: e.target.value })}
                  className="dark-input w-full text-sm"
                  placeholder="模板名称"
                />
              </div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-1">描述</label>
                <textarea
                  value={editing.description}
                  onChange={(e) => updateEditing({ description: e.target.value })}
                  className="dark-input w-full text-sm resize-none"
                  rows={2}
                  placeholder="模板描述"
                />
              </div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-1">风格</label>
                <select
                  value={editing.style}
                  onChange={(e) => updateEditing({ style: e.target.value as CardTemplate['style'] })}
                  className="dark-input w-full text-sm"
                >
                  {STYLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-1">尺寸</label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] text-parchment-200/40">宽度</span>
                    <input
                      type="number"
                      value={editing.width}
                      onChange={(e) => updateEditing({ width: Number(e.target.value) })}
                      className="dark-input w-full text-sm"
                      min={200} max={800}
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-parchment-200/40">高度</span>
                    <input
                      type="number"
                      value={editing.height}
                      onChange={(e) => updateEditing({ height: Number(e.target.value) })}
                      className="dark-input w-full text-sm"
                      min={200} max={1200}
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-2">配色</label>
                <div className="grid grid-cols-2 gap-3">
                  {([
                    { key: 'primary', label: '主色' },
                    { key: 'secondary', label: '副色' },
                    { key: 'background', label: '背景色' },
                    { key: 'text', label: '文字色' },
                    { key: 'accent', label: '强调色' },
                  ]).map((item) => (
                    <div key={item.key} className="flex items-center gap-2">
                      <input
                        type="color"
                        value={editing.colors[item.key] || '#000000'}
                        onChange={(e) => updateColors(item.key, e.target.value)}
                        className="w-8 h-8 rounded cursor-pointer bg-transparent border border-dark-600"
                      />
                      <span className="text-xs text-parchment-200/60 font-cinzel">{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-2">边框</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-parchment-200/40">宽度</span>
                    <input
                      type="number"
                      value={editing.borders.width}
                      onChange={(e) => updateBorders('width', Number(e.target.value))}
                      className="dark-input w-full text-sm"
                      min={0} max={10}
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-parchment-200/40">圆角</span>
                    <input
                      type="number"
                      value={editing.borders.radius}
                      onChange={(e) => updateBorders('radius', Number(e.target.value))}
                      className="dark-input w-full text-sm"
                      min={0} max={30}
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-parchment-200/40">颜色</span>
                    <input
                      type="color"
                      value={editing.borders.color}
                      onChange={(e) => updateBorders('color', e.target.value)}
                      className="w-full h-8 rounded cursor-pointer bg-transparent border border-dark-600"
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-parchment-200/40">样式</span>
                    <select
                      value={editing.borders.style}
                      onChange={(e) => updateBorders('style', e.target.value)}
                      className="dark-input w-full text-sm"
                    >
                      <option value="solid">实线</option>
                      <option value="double">双线</option>
                      <option value="ornate">华丽</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="divider-ornate text-xs font-cinzel">◆</div>

              <div>
                <label className="block font-cinzel text-gold-500 text-xs mb-2">布局位置</label>
                <div className="space-y-3">
                  {LAYOUT_SECTIONS.map((item) => {
                    const pos = editing.layout[item.key] as { x: number; y: number; fontSize: number; maxWidth?: number; lineHeight?: number };
                    return (
                      <div key={item.key} className="bg-dark-900/50 rounded p-2">
                        <span className="text-[10px] text-gold-500/70 font-cinzel">{item.label}</span>
                        <div className="flex gap-2 mt-1">
                          <div className="flex-1">
                            <span className="text-[9px] text-parchment-200/30">X</span>
                            <input
                              type="number"
                              value={pos.x}
                              onChange={(e) => {
                                const layout = { ...editing.layout, [item.key]: { ...editing.layout[item.key], x: Number(e.target.value) } };
                                updateEditing({ layout: layout as TemplateLayout });
                              }}
                              className="dark-input w-full text-xs py-1"
                            />
                          </div>
                          <div className="flex-1">
                            <span className="text-[9px] text-parchment-200/30">Y</span>
                            <input
                              type="number"
                              value={pos.y}
                              onChange={(e) => {
                                const layout = { ...editing.layout, [item.key]: { ...editing.layout[item.key], y: Number(e.target.value) } };
                                updateEditing({ layout: layout as TemplateLayout });
                              }}
                              className="dark-input w-full text-xs py-1"
                            />
                          </div>
                          <div className="flex-1">
                            <span className="text-[9px] text-parchment-200/30">字号</span>
                            <input
                              type="number"
                              value={pos.fontSize}
                              onChange={(e) => {
                                const layout = { ...editing.layout, [item.key]: { ...editing.layout[item.key], fontSize: Number(e.target.value) } };
                                updateEditing({ layout: layout as TemplateLayout });
                              }}
                              className="dark-input w-full text-xs py-1"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <button
                onClick={handleSave}
                className="metal-button-primary w-full py-2.5 rounded text-sm"
                disabled={!editing.name}
              >
                保存模板
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
