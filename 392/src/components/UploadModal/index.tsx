import React, { useState, useCallback } from 'react';
import { useIconStore } from '../../store/iconStore';
import { UploadedIcon } from '../../types';
import { X, Upload, FileText, Tag } from 'lucide-react';
import { extractSvgPath } from '../../utils/svgUtils';

const UploadModal: React.FC = () => {
  const { showUploadModal, setShowUploadModal, addUploadedIcon } = useIconStore();
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState('');
  const [svgContent, setSvgContent] = useState('');
  const [iconName, setIconName] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [preview, setPreview] = useState('');

  const handleFile = useCallback((file: File) => {
    if (!file.name.endsWith('.svg')) {
      alert('请上传SVG格式的文件');
      return;
    }

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setSvgContent(content);
      const path = extractSvgPath(content);
      setPreview(path);
      setIconName(file.name.replace('.svg', ''));
    };
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleSubmit = () => {
    if (!svgContent || !iconName || !preview) {
      alert('请填写完整信息');
      return;
    }

    const newIcon: UploadedIcon = {
      id: `custom-${Date.now()}`,
      name: iconName,
      library: 'custom',
      svgPath: preview,
      tags: tags.length > 0 ? tags : [iconName],
      category: '自定义',
      svg: svgContent,
      createdAt: Date.now(),
    };

    addUploadedIcon(newIcon);
    setShowUploadModal(false);
    resetForm();
  };

  const resetForm = () => {
    setFileName('');
    setSvgContent('');
    setIconName('');
    setTags([]);
    setTagInput('');
    setPreview('');
  };

  if (!showUploadModal) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[#12121a] rounded-2xl w-full max-w-lg shadow-2xl border border-[#2a2a3a]">
        <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-200">上传自定义图标</h3>
          <button
            onClick={() => {
              setShowUploadModal(false);
              resetForm();
            }}
            className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {!svgContent ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input')?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                dragOver
                  ? 'border-[#4F46E5] bg-[#4F46E5]/10'
                  : 'border-[#2a2a3a] hover:border-[#3a3a4a] hover:bg-[#1a1a2a]'
              }`}
            >
              <Upload className="w-12 h-12 mx-auto mb-4 text-gray-500" />
              <p className="text-sm text-gray-300 mb-2">拖拽SVG文件到此处</p>
              <p className="text-xs text-gray-500">或点击选择文件</p>
              <input
                id="file-input"
                type="file"
                accept=".svg"
                onChange={handleFileInput}
                className="hidden"
              />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-4 p-4 rounded-xl bg-[#1a1a2a]">
                {preview && (
                  <div className="w-16 h-16 rounded-xl bg-[#0a0a12] flex items-center justify-center">
                    <svg width={32} height={32} viewBox="0 0 24 24" fill="#4F46E5">
                      <path d={preview} />
                    </svg>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText size={14} className="text-gray-500" />
                    <span className="text-sm text-gray-300 truncate">{fileName}</span>
                  </div>
                  <p className="text-xs text-gray-500">SVG 格式</p>
                </div>
                <button
                  onClick={() => {
                    setFileName('');
                    setSvgContent('');
                    setPreview('');
                  }}
                  className="p-1 rounded-md text-gray-500 hover:text-red-400 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">图标名称</label>
                <input
                  type="text"
                  value={iconName}
                  onChange={(e) => setIconName(e.target.value)}
                  placeholder="输入图标名称"
                  className="w-full px-4 py-2.5 rounded-xl bg-[#1a1a2a] border border-[#2a2a3a] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#4F46E5]/50"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2 flex items-center gap-2">
                  <Tag size={14} />
                  标签
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 text-xs rounded-full bg-[#4F46E5]/20 text-[#4F46E5] flex items-center gap-1"
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="hover:text-white"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                    placeholder="输入标签后按回车"
                    className="flex-1 px-4 py-2 rounded-xl bg-[#1a1a2a] border border-[#2a2a3a] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#4F46E5]/50"
                  />
                  <button
                    onClick={handleAddTag}
                    className="px-4 py-2 rounded-xl bg-[#1a1a2a] text-gray-400 hover:text-white hover:bg-[#2a2a3a] transition-all"
                  >
                    添加
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="p-4 border-t border-[#2a2a3a] flex gap-3 justify-end">
          <button
            onClick={() => {
              setShowUploadModal(false);
              resetForm();
            }}
            className="px-4 py-2 rounded-xl text-gray-400 hover:text-white hover:bg-[#1a1a2a] transition-all"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!svgContent || !iconName}
            className="px-6 py-2 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            上传
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;
