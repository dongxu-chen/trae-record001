import { Edge, Node } from 'reactflow';
import { StateNodeData, EdgeData, nodeTypeConfig } from '../types';

interface GraphvizAST {
  graphName: string;
  nodes: {
    id: string;
    label: string;
    type: 'initial' | 'normal' | 'final' | 'parallel' | 'history';
    isInitial: boolean;
    entry?: string;
    exit?: string;
  }[];
  edges: {
    from: string;
    to: string;
    label: string;
    guard?: string;
    actions?: string[];
  }[];
}

function buildGraphvizAST(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  graphName: string = 'StateMachine'
): GraphvizAST {
  const ast: GraphvizAST = {
    graphName,
    nodes: [],
    edges: [],
  };

  nodes.forEach((node) => {
    ast.nodes.push({
      id: node.id,
      label: node.data.label,
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
      ast.edges.push({
        from: sourceNode.id,
        to: targetNode.id,
        label: String(edge.data?.event || edge.label || 'TRANSITION'),
        guard: edge.data?.guard?.replace(/[()]/g, ''),
        actions,
      });
    }
  });

  return ast;
}

function escapeLabel(label: string): string {
  return label.replace(/"/g, '\\"');
}

function astToGraphviz(ast: GraphvizAST): string {
  const lines: string[] = [];

  lines.push(`digraph ${ast.graphName} {`);
  lines.push('  rankdir=LR;');
  lines.push('  bgcolor="#0f172a";');
  lines.push('  fontname="JetBrains Mono";');
  lines.push('  fontcolor="#f1f5f9";');
  lines.push('');
  lines.push('  node [');
  lines.push('    shape=rounded,');
  lines.push('    style="filled,rounded",');
  lines.push('    fillcolor="#1e293b",');
  lines.push('    color="#6366f1",');
  lines.push('    fontcolor="#f1f5f9",');
  lines.push('    fontname="JetBrains Mono",');
  lines.push('    penwidth=2');
  lines.push('  ];');
  lines.push('');
  lines.push('  edge [');
  lines.push('    color="#6366f1",');
  lines.push('    fontcolor="#94a3b8",');
  lines.push('    fontname="JetBrains Mono",');
  lines.push('    penwidth=2,');
  lines.push('    arrowsize=1');
  lines.push('  ];');
  lines.push('');

  const initialNode = ast.nodes.find((n) => n.isInitial);
  if (initialNode) {
    lines.push('  start [shape=point, color="#10b981", width=0.3];');
    lines.push(`  start -> "n_${initialNode.id}" [color="#10b981"];`);
    lines.push('');
  }

  ast.nodes.forEach((node) => {
    const color = nodeTypeConfig[node.type].color;
    let shapeLabel = '';
    
    if (node.type === 'final') {
      lines.push(`  "n_${node.id}" [`);
      lines.push(`    label=<`);
      lines.push(`      <table border="0" cellborder="0" cellspacing="0">`);
      lines.push(`        <tr><td bgcolor="${color}" width="10" height="10" fixedsize="true"/></tr>`);
      lines.push(`        <tr><td>${escapeLabel(node.label)}</td></tr>`);
      lines.push(`      </table>`);
      lines.push(`    >,`);
      lines.push(`    color="${color}",`);
      lines.push(`    fillcolor="#1e293b"`);
      lines.push(`  ];`);
    } else {
      let label = escapeLabel(node.label);
      if (node.entry || node.exit) {
        label += '\\n';
        if (node.entry) label += `\\n<entry> / ${node.entry}`;
        if (node.exit) label += `\\n<exit> / ${node.exit}`;
      }
      lines.push(`  "n_${node.id}" [label="${label}", color="${color}"];`);
    }
    lines.push('');
  });

  ast.edges.forEach((edge) => {
    let label = edge.label;
    if (edge.guard) {
      label += ` [${edge.guard}]`;
    }
    if (edge.actions && edge.actions.length > 0) {
      label += ` / ${edge.actions.join(', ')}`;
    }
    lines.push(`  "n_${edge.from}" -> "n_${edge.to}" [label="${label}"];`);
  });

  const finalNodes = ast.nodes.filter((n) => n.type === 'final');
  if (finalNodes.length > 0) {
    lines.push('');
    lines.push('  end [shape=doublecircle, color="#ef4444", fillcolor="#1e293b", width=0.3];');
    finalNodes.forEach((node) => {
      lines.push(`  "n_${node.id}" -> end [color="#ef4444", style="dashed"];`);
    });
  }

  lines.push('}');

  return lines.join('\n');
}

export function generateGraphvizCode(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  graphName: string = 'StateMachine'
): string {
  const ast = buildGraphvizAST(nodes, edges, graphName);
  return astToGraphviz(ast);
}

export { buildGraphvizAST };
