import React, { useState, useMemo } from 'react';
import { Search, Download, Star, Tag, Users, ArrowRight, X, Sparkles } from 'lucide-react';
import { useProjectStore } from '@/store/useProjectStore';
import { useEditorStore } from '@/store/useEditorStore';
import { TEMPLATE_CATEGORIES, type AnimationTemplate, type Project } from '@/types';
import { v4 as uuidv4 } from 'uuid';

const BUILTIN_TEMPLATES: AnimationTemplate[] = [
  {
    id: 'tpl-spinner',
    name: 'Spinning Loader',
    description: 'Smooth rotating circle loading animation, perfect for data loading states.',
    category: 'Loading',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Spinning Loader', width: 200, height: 200, duration: 2, fps: 60,
      elements: [
        { id: 'e1', type: 'circle', name: 'Ring', visible: true, locked: false, attributes: { r: 40, fill: 'none', stroke: '#e94560', strokeWidth: 6 }, transform: { x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e1', elementName: 'Ring', property: 'rotation', keyframes: [{ id: 'kf1', time: 0, value: 0 }, { id: 'kf2', time: 2, value: 360 }], type: 'keyframes', easing: 'none', duration: 2, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['loading', 'spinner', 'circle'], downloads: 1250, createdAt: Date.now() - 86400000 * 30,
  },
  {
    id: 'tpl-fade-in',
    name: 'Fade In Up',
    description: 'Classic fade-in with upward motion, ideal for page transitions and content reveals.',
    category: 'Transition',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Fade In Up', width: 400, height: 300, duration: 1.5, fps: 60,
      elements: [
        { id: 'e1', type: 'rect', name: 'Card', visible: true, locked: false, attributes: { width: 200, height: 120, fill: '#0f3460', rx: 12, ry: 12 }, transform: { x: 100, y: 90, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e1', elementName: 'Card', property: 'y', keyframes: [{ id: 'kf1', time: 0, value: 140 }, { id: 'kf2', time: 1.5, value: 90 }], type: 'keyframes', easing: 'power3.out', duration: 1.5, delay: 0 },
        { id: 't2', elementId: 'e1', elementName: 'Card', property: 'opacity', keyframes: [{ id: 'kf3', time: 0, value: 0 }, { id: 'kf4', time: 1.5, value: 1 }], type: 'keyframes', easing: 'power2.out', duration: 1.5, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['fade', 'transition', 'reveal'], downloads: 890, createdAt: Date.now() - 86400000 * 20,
  },
  {
    id: 'tpl-bounce-btn',
    name: 'Bounce Button',
    description: 'Playful bounce effect for interactive buttons with scale animation.',
    category: 'Button',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Bounce Button', width: 300, height: 200, duration: 0.8, fps: 60,
      elements: [
        { id: 'e1', type: 'rect', name: 'Button', visible: true, locked: false, attributes: { width: 160, height: 56, fill: '#e94560', rx: 28, ry: 28 }, transform: { x: 70, y: 72, rotation: 0, scaleX: 1, scaleY: 1 } },
        { id: 'e2', type: 'text', name: 'Label', visible: true, locked: false, attributes: { text: 'Click Me', fontSize: 18, fill: '#ffffff', fontFamily: 'Arial' }, transform: { x: 115, y: 105, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e1', elementName: 'Button', property: 'scale', keyframes: [{ id: 'kf1', time: 0, value: 1 }, { id: 'kf2', time: 0.2, value: 1.15 }, { id: 'kf3', time: 0.4, value: 0.95 }, { id: 'kf4', time: 0.6, value: 1.05 }, { id: 'kf5', time: 0.8, value: 1 }], type: 'keyframes', easing: 'bounce.out', duration: 0.8, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['button', 'bounce', 'interactive'], downloads: 670, createdAt: Date.now() - 86400000 * 15,
  },
  {
    id: 'tpl-pulse-icon',
    name: 'Pulse Icon',
    description: 'Gentle pulse effect for icons and notification badges.',
    category: 'Icon',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Pulse Icon', width: 200, height: 200, duration: 2, fps: 60,
      elements: [
        { id: 'e1', type: 'circle', name: 'Dot', visible: true, locked: false, attributes: { r: 20, fill: '#00ff88' }, transform: { x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1 } },
        { id: 'e2', type: 'circle', name: 'Ring', visible: true, locked: false, attributes: { r: 30, fill: 'none', stroke: '#00ff88', strokeWidth: 2 }, transform: { x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e2', elementName: 'Ring', property: 'scale', keyframes: [{ id: 'kf1', time: 0, value: 1 }, { id: 'kf2', time: 2, value: 2 }], type: 'keyframes', easing: 'power2.out', duration: 2, delay: 0 },
        { id: 't2', elementId: 'e2', elementName: 'Ring', property: 'opacity', keyframes: [{ id: 'kf3', time: 0, value: 0.8 }, { id: 'kf4', time: 2, value: 0 }], type: 'keyframes', easing: 'power2.out', duration: 2, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['pulse', 'icon', 'notification'], downloads: 540, createdAt: Date.now() - 86400000 * 10,
  },
  {
    id: 'tpl-morph-shape',
    name: 'Shape Morph',
    description: 'Smooth shape morphing between circle and star using path animation.',
    category: 'Transition',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Shape Morph', width: 300, height: 300, duration: 3, fps: 60,
      elements: [
        { id: 'e1', type: 'path', name: 'Shape', visible: true, locked: false, attributes: { d: 'M150,50 C200,50 250,100 250,150 C250,200 200,250 150,250 C100,250 50,200 50,150 C50,100 100,50 150,50 Z', fill: '#8b5cf6', stroke: 'none', strokeWidth: 0 }, transform: { x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e1', elementName: 'Shape', property: 'rotation', keyframes: [{ id: 'kf1', time: 0, value: 0 }, { id: 'kf2', time: 3, value: 180 }], type: 'keyframes', easing: 'power1.inOut', duration: 3, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['morph', 'shape', 'transform'], downloads: 430, createdAt: Date.now() - 86400000 * 5,
  },
  {
    id: 'tpl-text-reveal',
    name: 'Text Reveal',
    description: 'Text appear animation with clipping mask reveal effect.',
    category: 'Text Effect',
    thumbnail: '',
    author: 'SVG Animator',
    project: {
      id: '', name: 'Text Reveal', width: 500, height: 200, duration: 2, fps: 60,
      elements: [
        { id: 'e1', type: 'text', name: 'Title', visible: true, locked: false, attributes: { text: 'Hello World', fontSize: 48, fill: '#ffffff', fontFamily: 'Arial' }, transform: { x: 80, y: 120, rotation: 0, scaleX: 1, scaleY: 1 } },
      ],
      tracks: [
        { id: 't1', elementId: 'e1', elementName: 'Title', property: 'x', keyframes: [{ id: 'kf1', time: 0, value: -200 }, { id: 'kf2', time: 1.2, value: 80 }], type: 'keyframes', easing: 'power3.out', duration: 1.2, delay: 0 },
        { id: 't2', elementId: 'e1', elementName: 'Title', property: 'opacity', keyframes: [{ id: 'kf3', time: 0, value: 0 }, { id: 'kf4', time: 0.5, value: 0 }, { id: 'kf5', time: 1.2, value: 1 }], type: 'keyframes', easing: 'power2.out', duration: 1.2, delay: 0 },
      ],
      frameAnimations: [], createdAt: Date.now(), updatedAt: Date.now(),
    },
    tags: ['text', 'reveal', 'typography'], downloads: 380, createdAt: Date.now() - 86400000 * 3,
  },
];

export const Marketplace: React.FC = () => {
  const { loadProject, project: currentProject } = useProjectStore();
  const { setActiveModal } = useEditorStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [showImportSuccess, setShowImportSuccess] = useState(false);

  const filteredTemplates = useMemo(() => {
    return BUILTIN_TEMPLATES.filter(tpl => {
      const matchesCategory = selectedCategory === 'All' || tpl.category === selectedCategory;
      const matchesSearch = searchQuery === '' ||
        tpl.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tpl.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tpl.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesCategory && matchesSearch;
    });
  }, [searchQuery, selectedCategory]);

  const handleUseTemplate = (template: AnimationTemplate) => {
    const newProject: Project = {
      ...template.project,
      id: uuidv4(),
      name: template.name,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    newProject.elements = newProject.elements.map(e => ({ ...e, id: uuidv4() }));
    newProject.tracks = newProject.tracks.map(t => ({
      ...t,
      id: uuidv4(),
      elementId: newProject.elements.find((e, i) => i === template.project.elements.findIndex(te => te.id === t.elementId))?.id || t.elementId,
      keyframes: t.keyframes.map(kf => ({ ...kf, id: uuidv4() })),
    }));
    loadProject(newProject);
    setShowImportSuccess(true);
    setTimeout(() => {
      setShowImportSuccess(false);
      setActiveModal('none');
    }, 1200);
  };

  const handleShareCurrent = () => {
    const json = JSON.stringify(currentProject, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      setShowImportSuccess(true);
      setTimeout(() => setShowImportSuccess(false), 2000);
    });
  };

  const categoryColors: Record<string, string> = {
    Loading: 'bg-blue-500/20 text-blue-400',
    Transition: 'bg-purple-500/20 text-purple-400',
    Button: 'bg-red-500/20 text-red-400',
    Icon: 'bg-green-500/20 text-green-400',
    'Text Effect': 'bg-yellow-500/20 text-yellow-400',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setActiveModal('none')}>
      <div className="bg-bg-secondary border border-border-primary rounded-xl w-[90vw] max-w-[1100px] h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <Sparkles size={20} className="text-accent-primary" />
            <h2 className="text-lg font-semibold text-text-primary">Animation Marketplace</h2>
          </div>
          <button onClick={() => setActiveModal('none')} className="btn-icon text-text-secondary hover:text-text-primary text-xl">×</button>
        </div>

        <div className="flex items-center gap-4 px-6 py-3 border-b border-border-primary">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search templates..."
              className="w-full pl-9"
            />
          </div>
          <button onClick={handleShareCurrent} className="btn-primary text-xs flex items-center gap-1">
            <Users size={14} /> Share Current
          </button>
        </div>

        <div className="flex gap-2 px-6 py-2 border-b border-border-primary overflow-x-auto">
          {TEMPLATE_CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all whitespace-nowrap ${
                selectedCategory === cat
                  ? 'bg-accent-primary text-white'
                  : 'bg-bg-tertiary/50 text-text-secondary hover:text-text-primary'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {filteredTemplates.length === 0 ? (
            <div className="flex items-center justify-center h-full text-text-muted">
              <div className="text-center">
                <Search size={48} className="mx-auto mb-4 opacity-30" />
                <p className="text-lg mb-1">No templates found</p>
                <p className="text-sm">Try a different search or category</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTemplates.map(tpl => (
                <div
                  key={tpl.id}
                  className="bg-bg-primary border border-border-primary rounded-xl overflow-hidden hover:border-accent-secondary/30 transition-all group"
                >
                  <div className="h-32 bg-bg-tertiary/30 flex items-center justify-center relative overflow-hidden">
                    <div className="text-4xl opacity-20">
                      {tpl.category === 'Loading' && '⟳'}
                      {tpl.category === 'Transition' && '→'}
                      {tpl.category === 'Button' && '▽'}
                      {tpl.category === 'Icon' && '✦'}
                      {tpl.category === 'Text Effect' && 'Aa'}
                      {tpl.category === 'Character' && '♡'}
                      {tpl.category === 'Logo' && '◆'}
                      {tpl.category === 'Particle' && '•'}
                      {tpl.category === 'Background' && '▧'}
                    </div>
                    <div className={`absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-medium ${categoryColors[tpl.category] || 'bg-gray-500/20 text-gray-400'}`}>
                      {tpl.category}
                    </div>
                  </div>

                  <div className="p-4">
                    <h3 className="text-sm font-semibold text-text-primary mb-1">{tpl.name}</h3>
                    <p className="text-xs text-text-muted mb-3 line-clamp-2">{tpl.description}</p>

                    <div className="flex flex-wrap gap-1 mb-3">
                      {tpl.tags.map(tag => (
                        <span key={tag} className="px-1.5 py-0.5 bg-bg-tertiary rounded text-[10px] text-text-muted">
                          {tag}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 text-xs text-text-muted">
                        <span className="flex items-center gap-1"><Download size={10} /> {tpl.downloads}</span>
                        <span>{tpl.project.width}×{tpl.project.height}</span>
                      </div>
                      <button
                        onClick={() => handleUseTemplate(tpl)}
                        className="flex items-center gap-1 px-3 py-1 bg-accent-primary/20 text-accent-primary hover:bg-accent-primary hover:text-white rounded text-xs font-medium transition-colors"
                      >
                        Use <ArrowRight size={10} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {showImportSuccess && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-accent-success text-bg-primary px-6 py-3 rounded-lg font-medium text-sm shadow-lg flex items-center gap-2">
            <Sparkles size={16} /> Template loaded successfully!
          </div>
        )}
      </div>
    </div>
  );
};
