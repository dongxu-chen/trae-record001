import { Edge, Node } from 'reactflow';
import { StateNodeData, EdgeData } from '../types';

interface PlantUMLAST {
  states: {
    name: string;
    type: 'initial' | 'normal' | 'final' | 'parallel' | 'history';
    isInitial: boolean;
    entry?: string;
    exit?: string;
  }[];
  transitions: {
    from: string;
    to: string;
    event: string;
    guard?: string;
    actions?: string[];
  }[];
}

function buildPlantUMLAST(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[]
): PlantUMLAST {
  const ast: PlantUMLAST = {
    states: [],
    transitions: [],
  };

  nodes.forEach((node) => {
    ast.states.push({
      name: node.data.label,
      type: node.data.nodeType,
      isInitial: node.data.nodeType === 'initial' || node.data.isInitial === true,
      entry: node.data.entry,
      exit: node.data.exit,
    });
  });

  edges.forEach((edge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    const targetNode = nodes.find((n) => n.id === edge.target);
    if (sourceNode && targetNode) {
      const actions = edge.data?.actions
        ? edge.data.actions.split(',').map((a) => a.trim().replace(/[()]/g, ''))
        : undefined;
      ast.transitions.push({
        from: sourceNode.data.label,
        to: targetNode.data.label,
        event: String(edge.data?.event || edge.label || 'TRANSITION'),
        guard: edge.data?.guard?.replace(/[()]/g, ''),
        actions,
      });
    }
  });

  return ast;
}

function astToPlantUML(ast: PlantUMLAST): string {
  const lines: string[] = [];

  lines.push('@startuml');
  lines.push('');
  lines.push('skinparam state {');
  lines.push('  BackgroundColor #1e293b');
  lines.push('  BorderColor #6366f1');
  lines.push('  ArrowColor #6366f1');
  lines.push('  FontColor #f1f5f9');
  lines.push('  FontName JetBrains Mono');
  lines.push('}');
  lines.push('');

  const initialState = ast.states.find((s) => s.isInitial);
  if (initialState) {
    lines.push(`[*] --> ${initialState.name}`);
    lines.push('');
  }

  ast.states.forEach((state) => {
    if (state.type === 'final') {
      lines.push(`state ${state.name} {`);
      lines.push(`  [*] --> ${state.name}`);
      lines.push(`}`);
      lines.push('');
    }
  });

  ast.transitions.forEach((transition) => {
    let label = transition.event;
    if (transition.guard) {
      label += ` [${transition.guard}]`;
    }
    if (transition.actions && transition.actions.length > 0) {
      label += ` / ${transition.actions.join(', ')}`;
    }
    lines.push(`${transition.from} --> ${transition.to} : ${label}`);
  });

  ast.states.forEach((state) => {
    if (state.entry || state.exit) {
      lines.push('');
      if (state.entry) {
        lines.push(`${state.name} : entry / ${state.entry}`);
      }
      if (state.exit) {
        lines.push(`${state.name} : exit / ${state.exit}`);
      }
    }
  });

  const finalStates = ast.states.filter((s) => s.type === 'final');
  finalStates.forEach((state) => {
    lines.push('');
    lines.push(`${state.name} --> [*]`);
  });

  lines.push('');
  lines.push('@enduml');

  return lines.join('\n');
}

export function generatePlantUMLCode(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[]
): string {
  const ast = buildPlantUMLAST(nodes, edges);
  return astToPlantUML(ast);
}

export { buildPlantUMLAST };
