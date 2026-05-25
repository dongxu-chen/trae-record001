import * as React from "react";
import { ChevronRight, Folder, FolderOpen, File } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TreeNodeData {
  id: string;
  label: string;
  children?: TreeNodeData[];
  icon?: React.ReactNode;
  isLeaf?: boolean;
}

export interface TreeViewProps {
  data: TreeNodeData[];
  selectedId?: string | null;
  defaultExpandedIds?: string[];
  expandedIds?: string[];
  onSelect?: (node: TreeNodeData) => void;
  onExpand?: (expandedIds: string[]) => void;
  className?: string;
}

export interface TreeNodeProps {
  node: TreeNodeData;
  level: number;
  selectedId: string | null;
  expandedIds: Set<string>;
  onSelect: (node: TreeNodeData) => void;
  onToggleExpand: (id: string) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  level,
  selectedId,
  expandedIds,
  onSelect,
  onToggleExpand,
}) => {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(node);
  };

  const handleExpandClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren) {
      onToggleExpand(node.id);
    }
  };

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-1.5 py-1.5 px-2 rounded-md cursor-pointer transition-colors group",
          isSelected
            ? "bg-cyber-500/20 text-cyber-400"
            : "text-gray-300 hover:bg-space-700 hover:text-white"
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={handleClick}
      >
        <div
          className={cn(
            "w-4 h-4 flex items-center justify-center flex-shrink-0 transition-transform duration-200",
            hasChildren ? "cursor-pointer" : "cursor-default"
          )}
          onClick={handleExpandClick}
        >
          {hasChildren ? (
            <ChevronRight
              size={14}
              className={cn(
                "text-gray-400 group-hover:text-cyber-400 transition-colors",
                isExpanded && "rotate-90",
                isSelected && "text-cyber-400"
              )}
            />
          ) : (
            <span className="w-4" />
          )}
        </div>

        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
          {node.icon ? (
            <span
              className={cn(
                "text-gray-400",
                isSelected && "text-cyber-400",
                "group-hover:text-cyber-400 transition-colors"
              )}
            >
              {node.icon}
            </span>
          ) : hasChildren ? (
            isExpanded ? (
              <FolderOpen
                size={14}
                className={cn(
                  "text-yellow-500/70",
                  isSelected && "text-cyber-400",
                  "group-hover:text-cyber-400 transition-colors"
                )}
              />
            ) : (
              <Folder
                size={14}
                className={cn(
                  "text-yellow-500/70",
                  isSelected && "text-cyber-400",
                  "group-hover:text-cyber-400 transition-colors"
                )}
              />
            )
          ) : (
            <File
              size={14}
              className={cn(
                "text-gray-500",
                isSelected && "text-cyber-400",
                "group-hover:text-cyber-400 transition-colors"
              )}
            />
          )}
        </div>

        <span className="text-sm truncate select-none">{node.label}</span>
      </div>

      {hasChildren && isExpanded && (
        <div className="overflow-hidden">
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const TreeView: React.FC<TreeViewProps> = ({
  data,
  selectedId,
  defaultExpandedIds = [],
  expandedIds: controlledExpandedIds,
  onSelect,
  onExpand,
  className,
}) => {
  const [internalExpandedIds, setInternalExpandedIds] = React.useState<Set<string>>(
    new Set(defaultExpandedIds)
  );
  const [internalSelectedId, setInternalSelectedId] = React.useState<string | null>(
    selectedId ?? null
  );

  const expandedIds = controlledExpandedIds
    ? new Set(controlledExpandedIds)
    : internalExpandedIds;
  const currentSelectedId = selectedId ?? internalSelectedId;

  const handleSelect = (node: TreeNodeData) => {
    if (selectedId === undefined) {
      setInternalSelectedId(node.id);
    }
    onSelect?.(node);
  };

  const handleToggleExpand = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }

    if (controlledExpandedIds === undefined) {
      setInternalExpandedIds(newExpanded);
    }
    onExpand?.(Array.from(newExpanded));
  };

  const expandAll = () => {
    const getAllIds = (nodes: TreeNodeData[]): string[] => {
      return nodes.flatMap((node) => [
        node.id,
        ...(node.children ? getAllIds(node.children) : []),
      ]);
    };
    const allIds = getAllIds(data).filter((id) => {
      const findNode = (nodes: TreeNodeData[], targetId: string): TreeNodeData | null => {
        for (const node of nodes) {
          if (node.id === targetId) return node;
          if (node.children) {
            const found = findNode(node.children, targetId);
            if (found) return found;
          }
        }
        return null;
      };
      const node = findNode(data, id);
      return node?.children && node.children.length > 0;
    });
    const newExpanded = new Set(allIds);
    setInternalExpandedIds(newExpanded);
    onExpand?.(allIds);
  };

  const collapseAll = () => {
    setInternalExpandedIds(new Set());
    onExpand?.([]);
  };

  return (
    <div className={cn("select-none", className)}>
      <div className="flex items-center gap-2 px-2 py-1.5 border-b border-space-600 mb-1">
        <button
          onClick={expandAll}
          className="text-xs text-gray-400 hover:text-cyber-400 transition-colors px-1.5 py-0.5 rounded hover:bg-space-700"
        >
          全部展开
        </button>
        <button
          onClick={collapseAll}
          className="text-xs text-gray-400 hover:text-cyber-400 transition-colors px-1.5 py-0.5 rounded hover:bg-space-700"
        >
          全部折叠
        </button>
      </div>
      <div className="py-1">
        {data.map((node) => (
          <TreeNode
            key={node.id}
            node={node}
            level={0}
            selectedId={currentSelectedId}
            expandedIds={expandedIds}
            onSelect={handleSelect}
            onToggleExpand={handleToggleExpand}
          />
        ))}
      </div>
    </div>
  );
};

TreeView.displayName = "TreeView";
TreeNode.displayName = "TreeNode";

export { TreeView, TreeNode };
