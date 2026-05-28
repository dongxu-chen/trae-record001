import { Edge, Node } from 'reactflow';
import { StateNodeData, EdgeData } from '../types';

interface XStateAST {
  imports: string[];
  machine: {
    id: string;
    initial: string;
    states: Record<string, StateAST>;
  };
  options?: {
    guards?: Record<string, string>;
    actions?: Record<string, string>;
  };
}

interface StateAST {
  type?: 'final';
  entry?: string[];
  exit?: string[];
  on?: Record<string, TransitionAST>;
}

interface TransitionAST {
  target: string;
  guard?: string;
  actions?: string[];
}

function sanitizeName(name: string): string {
  return name.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');
}

function parseActions(actionsStr?: string): string[] {
  if (!actionsStr) return [];
  return actionsStr
    .split(',')
    .map((a) => a.trim().replace(/[()]/g, ''))
    .filter(Boolean);
}

function buildXStateAST(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  machineName: string = 'stateMachine'
): XStateAST {
  const ast: XStateAST = {
    imports: ['createMachine'],
    machine: {
      id: machineName,
      initial: '',
      states: {},
    },
    options: {
      guards: {},
      actions: {},
    },
  };

  if (nodes.length === 0) {
    ast.machine.initial = 'idle';
    return ast;
  }

  const initialNode = nodes.find((n) => n.data.nodeType === 'initial' || n.data.isInitial);
  ast.machine.initial = sanitizeName(initialNode?.data.label || nodes[0].data.label);

  const allGuards = new Set<string>();
  const allActions = new Set<string>();

  nodes.forEach((node) => {
    const stateName = sanitizeName(node.data.label);
    const stateAST: StateAST = {};

    if (node.data.nodeType === 'final') {
      stateAST.type = 'final';
    }

    if (node.data.entry) {
      const entries = parseActions(node.data.entry);
      stateAST.entry = entries;
      entries.forEach((a) => allActions.add(a));
    }

    if (node.data.exit) {
      const exits = parseActions(node.data.exit);
      stateAST.exit = exits;
      exits.forEach((a) => allActions.add(a));
    }

    const nodeEdges = edges.filter((e) => e.source === node.id);
    if (nodeEdges.length > 0) {
      stateAST.on = {};
      nodeEdges.forEach((edge) => {
        const targetNode = nodes.find((n) => n.id === edge.target);
        if (targetNode) {
          const eventName = String(edge.data?.event || edge.label || 'TRANSITION');
          const transition: TransitionAST = {
            target: sanitizeName(targetNode.data.label),
          };

          if (edge.data?.guard) {
            const guardName = edge.data.guard.replace(/[()]/g, '');
            transition.guard = guardName;
            allGuards.add(guardName);
          }

          if (edge.data?.actions) {
            const actions = parseActions(edge.data.actions);
            transition.actions = actions;
            actions.forEach((a) => allActions.add(a));
          }

          stateAST.on![eventName] = transition;
        }
      });
    }

    ast.machine.states[stateName] = stateAST;
  });

  if (allGuards.size > 0) {
    allGuards.forEach((guard) => {
      ast.options!.guards![guard] = '({ context, event }) => { return true; }';
    });
  }

  if (allActions.size > 0) {
    allActions.forEach((action) => {
      ast.options!.actions![action] = `({ context, event }) => { console.log('Action: ${action}'); }`;
    });
  }

  if (Object.keys(ast.options!.guards || {}).length === 0) {
    delete ast.options!.guards;
  }
  if (Object.keys(ast.options!.actions || {}).length === 0) {
    delete ast.options!.actions;
  }
  if (Object.keys(ast.options || {}).length === 0) {
    delete ast.options;
  }

  return ast;
}

function astToCode(ast: XStateAST, machineName: string): string {
  const lines: string[] = [];

  lines.push(`import { ${ast.imports.join(', ')} } from 'xstate';`);
  lines.push('');

  lines.push(`export const ${machineName} = createMachine({`);
  lines.push(`  id: '${ast.machine.id}',`);
  lines.push(`  initial: '${ast.machine.initial}',`);
  lines.push(`  states: {`);

  Object.entries(ast.machine.states).forEach(([stateName, state], index, arr) => {
    lines.push(`    '${stateName}': {`);

    if (state.type) {
      lines.push(`      type: '${state.type}',`);
    }

    if (state.entry && state.entry.length > 0) {
      const entries = state.entry.map((e) => `'${e}'`).join(', ');
      lines.push(`      entry: [${entries}],`);
    }

    if (state.exit && state.exit.length > 0) {
      const exits = state.exit.map((e) => `'${e}'`).join(', ');
      lines.push(`      exit: [${exits}],`);
    }

    if (state.on && Object.keys(state.on).length > 0) {
      lines.push(`      on: {`);
      Object.entries(state.on).forEach(([eventName, transition]) => {
        let transitionStr = `        ${eventName}: { target: '${transition.target}'`;
        if (transition.guard) {
          transitionStr += `, guard: '${transition.guard}'`;
        }
        if (transition.actions && transition.actions.length > 0) {
          const actions = transition.actions.map((a) => `'${a}'`).join(', ');
          transitionStr += `, actions: [${actions}]`;
        }
        transitionStr += ' },';
        lines.push(transitionStr);
      });
      lines.push(`      },`);
    }

    lines.push(`    }${index < arr.length - 1 ? ',' : ''}`);
  });

  lines.push(`  }`);

  if (ast.options) {
    lines.push(`}, {`);

    if (ast.options.guards && Object.keys(ast.options.guards).length > 0) {
      lines.push(`  guards: {`);
      Object.entries(ast.options.guards).forEach(([name, body]) => {
        lines.push(`    ${name}: ${body},`);
      });
      lines.push(`  },`);
    }

    if (ast.options.actions && Object.keys(ast.options.actions).length > 0) {
      lines.push(`  actions: {`);
      Object.entries(ast.options.actions).forEach(([name, body]) => {
        lines.push(`    ${name}: ${body},`);
      });
      lines.push(`  }`);
    }

    lines.push(`}`);
  }

  lines.push(`);`);

  return lines.join('\n');
}

export function generateXStateCode(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  machineName: string = 'stateMachine'
): string {
  const ast = buildXStateAST(nodes, edges, machineName);
  return astToCode(ast, machineName);
}

export { buildXStateAST };
