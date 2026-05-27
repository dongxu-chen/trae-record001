import React, { useState, useMemo } from 'react';
import { Library, Search, Star, Plus, Download, Upload } from 'lucide-react';
import ThemeCard from '@/components/ThemeCard';
import SaveThemeModal from '@/components/ThemeModal/SaveThemeModal';
import { useSavedThemes, useThemeActions } from '@/store/useThemeStore';
import { CollapsibleSection } from './ColorSection';
import './ThemeSections.less';

const ThemeLibrary: React.FC = () => {
  const savedThemes = useSavedThemes();
  const {
    saveTheme,
    applySavedTheme,
    deleteTheme,
    renameTheme,
    toggleFavorite,
    exportLibrary,
    importLibrary,
  } = useThemeActions();

  const [showSaveModal, setShowSaveModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const filteredThemes = useMemo(() => {
    let result = [...savedThemes];

    if (showFavoritesOnly) {
      result = result.filter((t) => t.isFavorite);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query),
      );
    }

    result.sort((a, b) => {
      if (a.isFavorite !== b.isFavorite) return a.isFavorite ? -1 : 1;
      return b.updatedAt - a.updatedAt;
    });

    return result;
  }, [savedThemes, searchQuery, showFavoritesOnly]);

  const handleDelete = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (confirmDelete === id) {
      deleteTheme(id);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(id);
      setTimeout(() => setConfirmDelete(null), 3000);
    }
  };

  const handleExportLibrary = () => {
    const json = exportLibrary();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `theme-library-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportLibrary = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      importLibrary(text);
    } catch {
      console.error('Failed to import library');
    }
    e.target.value = '';
  };

  const getPreviewColors = (theme: typeof savedThemes[0]) => {
    return theme.theme.color.slice(0, 5);
  };

  return (
    <CollapsibleSection title="团队主题库" icon={<Library size={16} />} defaultOpen={false}>
      <div className="library-toolbar">
        <div className="search-box">
          <Search size={14} />
          <input
            type="text"
            placeholder="搜索主题..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button
          className={`icon-btn ${showFavoritesOnly ? 'active' : ''}`}
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          title={showFavoritesOnly ? '显示全部' : '仅显示收藏'}
        >
          <Star size={16} fill={showFavoritesOnly ? 'currentColor' : 'none'} />
        </button>
        <button className="icon-btn" onClick={() => setShowSaveModal(true)} title="保存当前主题">
          <Plus size={16} />
        </button>
        <button className="icon-btn" onClick={handleExportLibrary} title="导出主题库">
          <Download size={16} />
        </button>
        <button className="icon-btn" onClick={handleImportLibrary} title="导入主题库">
          <Upload size={16} />
        </button>
      </div>

      {filteredThemes.length === 0 ? (
        <div className="empty-state">
          <Library size={32} />
          <p>
            {searchQuery || showFavoritesOnly
              ? '没有找到匹配的主题'
              : '主题库为空，点击「+」保存当前主题'}
          </p>
        </div>
      ) : (
        <div className="theme-grid">
          {filteredThemes.map((saved) => (
            <div key={saved.id} className="saved-theme-wrapper">
              {confirmDelete === saved.id && (
                <div className="delete-confirm">
                  <span>确认删除？</span>
                  <button
                    className="confirm-delete"
                    onClick={(e) => handleDelete(saved.id, e)}
                  >
                    删除
                  </button>
                </div>
              )}
              <ThemeCard
                theme={{
                  ...saved,
                  previewColors: getPreviewColors(saved),
                }}
                onApply={() => applySavedTheme(saved.id)}
                onFavorite={() => toggleFavorite(saved.id)}
                onDelete={(e) => handleDelete(saved.id, e)}
                onRename={(name, desc) => renameTheme(saved.id, name, desc)}
                showActions={true}
                isSaved={true}
              />
            </div>
          ))}
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      <SaveThemeModal
        visible={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={saveTheme}
      />
    </CollapsibleSection>
  );
};

export default React.memo(ThemeLibrary);
