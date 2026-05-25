import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { Search, Bone, RotateCcw, ChevronDown, ChevronRight, Plus, Edit3 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useEditorStore } from '@/store/editorStore';
import { useSkeletonData } from '@/hooks/useSkeletonData';
import { cn } from '@/lib/utils';
import type { BoneNode } from '@/types/skeleton';

interface TreeNode {
  id: string;
  children?: TreeNode[];
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  boneUuid: string | null;
}

const SkeletonHierarchy = () => {
  const {
    skeleton,
    selectedBoneUuid,
    setSelectedBone,
    model,
    addKeyframe,
    currentTime,
  } = useEditorStore();

  const { resetBonePose, resetAllBonePoses } = useSkeletonData(model);

  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState<string[]>([]);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    boneUuid: null,
  });
  const [renamingUuid, setRenamingUuid] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const contextMenuRef = useRef<HTMLDivElement>(null);

  const buildTreeData = useCallback(
    (bones: BoneNode[], filter: string): TreeNode[] => {
      const boneMap = new Map<string, BoneNode>();
      const childrenMap = new Map<string, BoneNode[]>();

      bones.forEach((bone) => {
        boneMap.set(bone.uuid, bone);
        if (bone.parentUuid) {
          if (!childrenMap.has(bone.parentUuid)) {
            childrenMap.set(bone.parentUuid, []);
          }
          childrenMap.get(bone.parentUuid)!.push(bone);
        }
      });

      const rootBones = bones.filter((b) => b.parentUuid === null);

      const filterMatch = (bone: BoneNode): boolean => {
        if (!filter) return true;
        const query = filter.toLowerCase();
        return (
          bone.name.toLowerCase().includes(query) ||
          bone.boneIndex.toString().includes(query)
        );
      };

      const hasMatchingDescendant = (bone: BoneNode): boolean => {
        if (filterMatch(bone)) return true;
        const children = childrenMap.get(bone.uuid) || [];
        return children.some((child) => hasMatchingDescendant(child));
      };

      const buildNode = (bone: BoneNode): TreeNode | null => {
        const children = childrenMap.get(bone.uuid) || [];
        const filteredChildren = children
          .map((child) => buildNode(child))
          .filter((n): n is TreeNode => n !== null);

        if (filter && !filterMatch(bone) && filteredChildren.length === 0) {
          return null;
        }

        return {
          id: bone.uuid,
          children: filteredChildren.length > 0 ? filteredChildren : undefined,
        };
      };

      return rootBones
        .map((bone) => buildNode(bone))
        .filter((n): n is TreeNode => n !== null);
    },
    []
  );

  const treeData = useMemo(() => {
    return buildTreeData(skeleton, searchQuery);
  }, [skeleton, searchQuery, buildTreeData]);

  useEffect(() => {
    const allIds = skeleton.map((b) => b.uuid);
    setExpandedIds(allIds);
  }, [skeleton]);

  useEffect(() => {
    if (searchQuery && skeleton.length > 0) {
      const idsToExpand: string[] = [];
      const query = searchQuery.toLowerCase();

      const findParentUuids = (bone: BoneNode) => {
        const matches =
          bone.name.toLowerCase().includes(query) ||
          bone.boneIndex.toString().includes(query);

        if (matches && bone.parentUuid) {
          let currentUuid = bone.parentUuid;
          while (currentUuid) {
            if (!idsToExpand.includes(currentUuid)) {
              idsToExpand.push(currentUuid);
            }
            const currentBone = skeleton.find((b) => b.uuid === currentUuid);
            currentUuid = currentBone?.parentUuid || null;
          }
        }

        return matches;
      };

      skeleton.forEach(findParentUuids);
      setExpandedIds((prev) => [...new Set([...prev, ...idsToExpand])]);
    }
  }, [searchQuery, skeleton]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        contextMenuRef.current &&
        !contextMenuRef.current.contains(e.target as Node)
      ) {
        setContextMenu({ visible: false, x: 0, y: 0, boneUuid: null });
      }
    };

    if (contextMenu.visible) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [contextMenu.visible]);

  const handleSelect = (boneUuid: string) => {
    if (renamingUuid !== boneUuid) {
      setSelectedBone(boneUuid);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, boneUuid: string) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedBone(boneUuid);
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      boneUuid,
    });
  };

  const handleToggleExpand = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedIds(Array.from(newExpanded));
  };

  const handleExpandAll = () => {
    const allIds = skeleton.map((b) => b.uuid);
    setExpandedIds(allIds);
  };

  const handleCollapseAll = () => {
    setExpandedIds([]);
  };

  const handleResetPose = () => {
    resetAllBonePoses();
  };

  const handleResetBonePose = (boneUuid: string) => {
    resetBonePose(boneUuid);
    setContextMenu({ visible: false, x: 0, y: 0, boneUuid: null });
  };

  const handleAddKeyframe = (boneUuid: string) => {
    const bone = skeleton.find((b) => b.uuid === boneUuid);
    if (bone) {
      addKeyframe(boneUuid, 'position', 'x', currentTime, [bone.position[0]]);
      addKeyframe(boneUuid, 'position', 'y', currentTime, [bone.position[1]]);
      addKeyframe(boneUuid, 'position', 'z', currentTime, [bone.position[2]]);
      addKeyframe(boneUuid, 'rotation', 'x', currentTime, [bone.rotation[0]]);
      addKeyframe(boneUuid, 'rotation', 'y', currentTime, [bone.rotation[1]]);
      addKeyframe(boneUuid, 'rotation', 'z', currentTime, [bone.rotation[2]]);
      addKeyframe(boneUuid, 'rotation', 'w', currentTime, [bone.rotation[3]]);
      addKeyframe(boneUuid, 'scale', 'x', currentTime, [bone.scale[0]]);
      addKeyframe(boneUuid, 'scale', 'y', currentTime, [bone.scale[1]]);
      addKeyframe(boneUuid, 'scale', 'z', currentTime, [bone.scale[2]]);
    }
    setContextMenu({ visible: false, x: 0, y: 0, boneUuid: null });
  };

  const handleRename = (boneUuid: string) => {
    const bone = skeleton.find((b) => b.uuid === boneUuid);
    if (bone) {
      setRenameValue(bone.name);
      setRenamingUuid(boneUuid);
    }
    setContextMenu({ visible: false, x: 0, y: 0, boneUuid: null });
  };

  const handleRenameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (renamingUuid && renameValue.trim()) {
      const bone = skeleton.find((b) => b.uuid === renamingUuid);
      if (bone && model) {
        const threeBone = model.getObjectByProperty('uuid', renamingUuid);
        if (threeBone) {
          threeBone.name = renameValue.trim();
        }
        bone.name = renameValue.trim();
        useEditorStore.setState({
          skeleton: [...skeleton],
        });
      }
    }
    setRenamingUuid(null);
    setRenameValue('');
  };

  const handleRenameBlur = () => {
    setRenamingUuid(null);
    setRenameValue('');
  };

  const renderTreeNode = (node: TreeNode, level: number) => {
    const bone = skeleton.find((b) => b.uuid === node.id);
    if (!bone) return null;

    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedIds.includes(node.id);
    const isSelected = selectedBoneUuid === node.id;
    const isRenaming = renamingUuid === node.id;

    const handleClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!isRenaming) {
        handleSelect(node.id);
      }
    };

    const handleExpandClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (hasChildren) {
        handleToggleExpand(node.id);
      }
    };

    const handleNodeContextMenu = (e: React.MouseEvent) => {
      handleContextMenu(e, node.id);
    };

    return (
      <div key={node.id}>
        <div
          className={cn(
            'flex items-center gap-1.5 py-1.5 px-2 rounded-md cursor-pointer transition-colors group',
            isSelected
              ? 'bg-cyber-500/20 text-cyber-400'
              : 'text-gray-300 hover:bg-space-700 hover:text-white'
          )}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={handleClick}
          onContextMenu={handleNodeContextMenu}
        >
          <div
            className={cn(
              'w-4 h-4 flex items-center justify-center flex-shrink-0 transition-transform duration-200',
              hasChildren ? 'cursor-pointer' : 'cursor-default'
            )}
            onClick={handleExpandClick}
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown
                  size={14}
                  className={cn(
                    'text-gray-400 group-hover:text-cyber-400 transition-colors',
                    isSelected && 'text-cyber-400'
                  )}
                />
              ) : (
                <ChevronRight
                  size={14}
                  className={cn(
                    'text-gray-400 group-hover:text-cyber-400 transition-colors',
                    isSelected && 'text-cyber-400'
                  )}
                />
              )
            ) : (
              <span className="w-4" />
            )}
          </div>

          <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
            <Bone
              size={14}
              className={cn(
                'text-gray-400',
                isSelected && 'text-cyber-400',
                'group-hover:text-cyber-400 transition-colors'
              )}
            />
          </div>

          {isRenaming ? (
            <form onSubmit={handleRenameSubmit} className="flex-1 flex items-center gap-1">
              <input
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={handleRenameBlur}
                autoFocus
                className="flex-1 bg-space-800 text-cyber-400 text-sm px-1.5 py-0.5 rounded border border-cyber-500/50 focus:outline-none focus:border-cyber-400"
              />
            </form>
          ) : (
            <span className="text-sm truncate select-none flex-1">
              {bone.name}
            </span>
          )}

          {!isRenaming && (
            <span className="text-xs text-gray-500 flex-shrink-0">
              #{bone.boneIndex}
            </span>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div className="overflow-hidden">
            {node.children!.map((child) => renderTreeNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (skeleton.length === 0) {
    return (
      <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-space-600 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-300">骨骼层级</h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <Bone size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无骨骼数据</p>
            <p className="text-xs mt-1">请先加载模型文件</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-space-800/50 border border-space-600 rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-space-600 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300">骨骼层级</h3>
      </div>

      <div className="px-3 py-2 border-b border-space-600">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500"
          />
          <input
            type="text"
            placeholder="搜索骨骼..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-space-700 text-sm text-gray-200 pl-8 pr-3 py-1.5 rounded-md border border-space-600 focus:outline-none focus:border-cyber-500/50 transition-colors placeholder:text-gray-500"
          />
        </div>
      </div>

      <div className="px-3 py-1.5 border-b border-space-600 flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleExpandAll}
          className="text-xs"
        >
          全部展开
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCollapseAll}
          className="text-xs"
        >
          全部折叠
        </Button>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          onClick={handleResetPose}
          className="text-xs"
        >
          <RotateCcw size={12} />
          重置姿态
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {treeData.map((node) => renderTreeNode(node, 0))}
      </div>

      {contextMenu.visible && contextMenu.boneUuid && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 min-w-[140px] bg-space-800 border border-space-600 rounded-md shadow-lg py-1"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={() => handleRename(contextMenu.boneUuid!)}
          >
            <Edit3 size={14} />
            重命名
          </button>
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={() => handleResetBonePose(contextMenu.boneUuid!)}
          >
            <RotateCcw size={14} />
            重置姿态
          </button>
          <button
            className="w-full px-3 py-1.5 text-left text-sm text-gray-300 hover:bg-space-700 hover:text-cyber-400 flex items-center gap-2 transition-colors"
            onClick={() => handleAddKeyframe(contextMenu.boneUuid!)}
          >
            <Plus size={14} />
            添加关键帧
          </button>
        </div>
      )}
    </div>
  );
};

SkeletonHierarchy.displayName = 'SkeletonHierarchy';

export { SkeletonHierarchy };
