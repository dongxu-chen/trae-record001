import { DrillNode, LevelData, LEVEL_NAMES } from '@/types/drill';
import { getDataByPath } from '@/data/mockData';

export function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

export function createDrillNode(name: string, level: number, parentId: string | null): DrillNode {
  return {
    id: generateId(),
    name,
    level,
    parentId,
  };
}

export function getLevelName(level: number): string {
  return LEVEL_NAMES[level] || `层级${level}`;
}

export function pathToNames(path: DrillNode[]): string[] {
  return path.map((node) => node.name);
}

export function namesToPath(names: string[]): DrillNode[] {
  const path: DrillNode[] = [];
  let parentId: string | null = null;

  names.forEach((name, index) => {
    const node: DrillNode = {
      id: generateId(),
      name,
      level: index,
      parentId,
    };
    path.push(node);
    parentId = node.id;
  });

  return path;
}

export function getCurrentLevelData(path: DrillNode[]): LevelData | null {
  const names = pathToNames(path);
  return getDataByPath(names);
}

export function canDrillDown(dataPoint: { hasChildren: boolean }, currentLevel: number): boolean {
  return dataPoint.hasChildren && currentLevel < LEVEL_NAMES.length - 1;
}

export function formatValue(value: number): string {
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万';
  }
  return value.toLocaleString();
}

export function calculateTotal(data: { value: number }[]): number {
  return data.reduce((sum, item) => sum + item.value, 0);
}
