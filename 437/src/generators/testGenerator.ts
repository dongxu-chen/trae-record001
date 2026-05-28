import { Edge, Node } from 'reactflow';
import { StateNodeData, EdgeData } from '../types';

export interface TestCase {
  id: string;
  name: string;
  description: string;
  path: string[];
  events: string[];
  expectedFinalState: string;
  guards?: string[];
  actions?: string[];
}

export interface TestSuite {
  name: string;
  testCases: TestCase[];
  coverage: {
    states: string[];
    transitions: number;
    totalStates: number;
    totalTransitions: number;
  };
}

function findAllPaths(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  startId: string,
  endIds: Set<string>,
  maxDepth: number = 10
): TestCase[] {
  const testCases: TestCase[] = [];
  const visitedPaths = new Set<string>();

  function dfs(
    currentId: string,
    path: string[],
    events: string[],
    guards: string[],
    actions: string[],
    depth: number
  ) {
    if (depth > maxDepth) return;

    const currentNode = nodes.find((n) => n.id === currentId);
    if (!currentNode) return;

    const currentLabel = currentNode.data.label;
    const newPath = [...path, currentLabel];
    const pathKey = newPath.join('->');

    if (visitedPaths.has(pathKey)) return;
    visitedPaths.add(pathKey);

    const outgoingEdges = edges.filter((e) => e.source === currentId);

    if (outgoingEdges.length === 0 || endIds.has(currentId)) {
      if (newPath.length > 1) {
        testCases.push({
          id: `test_${testCases.length + 1}`,
          name: `Path: ${newPath[0]} → ${currentLabel}`,
          description: `Test transition path: ${newPath.join(' → ')}`,
          path: newPath,
          events: [...events],
          expectedFinalState: currentLabel,
          guards: guards.length > 0 ? guards : undefined,
          actions: actions.length > 0 ? actions : undefined,
        });
      }
    }

    outgoingEdges.forEach((edge) => {
      const event = String(edge.data?.event || edge.label || 'TRANSITION');
      const guard = edge.data?.guard?.replace(/[()]/g, '');
      const edgeActions = edge.data?.actions
        ? edge.data.actions.split(',').map((a) => a.trim().replace(/[()]/g, ''))
        : [];

      dfs(
        edge.target,
        newPath,
        [...events, event],
        guard ? [...guards, guard] : guards,
        [...actions, ...edgeActions],
        depth + 1
      );
    });
  }

  dfs(startId, [], [], [], [], 0);
  return testCases;
}

export function generateTestCases(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[]
): TestSuite {
  const startNode = nodes.find(
    (n) => n.data.nodeType === 'initial' || n.data.isInitial === true
  );

  if (!startNode) {
    return {
      name: 'StateMachine Tests',
      testCases: [],
      coverage: {
        states: [],
        transitions: 0,
        totalStates: nodes.length,
        totalTransitions: edges.length,
      },
    };
  }

  const endNodes = nodes.filter((n) => n.data.nodeType === 'final');
  const endIds = new Set(endNodes.map((n) => n.id));

  const testCases = findAllPaths(nodes, edges, startNode.id, endIds);

  const coveredStates = new Set<string>();
  testCases.forEach((tc) => {
    tc.path.forEach((s) => coveredStates.add(s));
  });

  return {
    name: 'StateMachine Tests',
    testCases,
    coverage: {
      states: Array.from(coveredStates),
      transitions: testCases.reduce((sum, tc) => sum + tc.events.length, 0),
      totalStates: nodes.length,
      totalTransitions: edges.length,
    },
  };
}

export function generateJestTests(testSuite: TestSuite): string {
  const lines: string[] = [];

  lines.push(`describe('${testSuite.name}', () => {`);
  lines.push('  let machine: any;');
  lines.push('');
  lines.push('  beforeEach(() => {');
  lines.push('    machine = createMachine({ /* machine config */ });');
  lines.push('  });');
  lines.push('');

  testSuite.testCases.forEach((testCase) => {
    lines.push(`  test('${testCase.name}', () => {`);
    lines.push(`    // ${testCase.description}`);
    
    if (testCase.guards && testCase.guards.length > 0) {
      lines.push('    // Guards to verify:');
      testCase.guards.forEach((guard) => {
        lines.push(`    //   - ${guard}`);
      });
    }

    if (testCase.actions && testCase.actions.length > 0) {
      lines.push('    // Expected actions:');
      testCase.actions.forEach((action) => {
        lines.push(`    //   - ${action}`);
      });
    }

    lines.push('');
    lines.push(`    let state = machine.initialState;`);
    lines.push('');
    
    testCase.events.forEach((event, index) => {
      lines.push(`    // Step ${index + 1}: ${testCase.path[index]} → ${testCase.path[index + 1]}`);
      lines.push(`    state = machine.transition(state, { type: '${event}' });`);
    });

    lines.push('');
    lines.push(`    expect(state.value).toBe('${testCase.expectedFinalState}');`);
    lines.push('  });');
    lines.push('');
  });

  lines.push(`  describe('Coverage', () => {`);
  lines.push(`    test('should cover ${testSuite.coverage.states.length}/${testSuite.coverage.totalStates} states', () => {`);
  lines.push(`      const coveredStates = ${JSON.stringify(testSuite.coverage.states)};`);
  lines.push(`      expect(coveredStates.length).toBe(${testSuite.coverage.states.length});`);
  lines.push('    });');
  lines.push('  });');
  lines.push('});');

  return lines.join('\n');
}

export function generatePlainTextTests(testSuite: TestSuite): string {
  const lines: string[] = [];

  lines.push(`# ${testSuite.name}`);
  lines.push('');
  lines.push('## Coverage Summary');
  lines.push(`- States covered: ${testSuite.coverage.states.length}/${testSuite.coverage.totalStates}`);
  lines.push(`- Transitions tested: ${testSuite.coverage.transitions}/${testSuite.coverage.totalTransitions}`);
  lines.push('');
  lines.push('---');
  lines.push('');

  testSuite.testCases.forEach((testCase, index) => {
    lines.push(`## Test Case ${index + 1}: ${testCase.name}`);
    lines.push('');
    lines.push(`**Description:** ${testCase.description}`);
    lines.push('');
    lines.push('**Test Steps:**');
    testCase.events.forEach((event, i) => {
      lines.push(`${i + 1}. Event: \`${event}\``);
      lines.push(`   - From: ${testCase.path[i]}`);
      lines.push(`   - To: ${testCase.path[i + 1]}`);
    });
    lines.push('');
    lines.push(`**Expected Result:** Final state = \`${testCase.expectedFinalState}\``);
    
    if (testCase.guards && testCase.guards.length > 0) {
      lines.push('');
      lines.push('**Guards to verify:**');
      testCase.guards.forEach((guard) => {
        lines.push(`- ${guard}`);
      });
    }

    if (testCase.actions && testCase.actions.length > 0) {
      lines.push('');
      lines.push('**Expected actions:**');
      testCase.actions.forEach((action) => {
        lines.push(`- ${action}`);
      });
    }

    lines.push('');
    lines.push('---');
    lines.push('');
  });

  return lines.join('\n');
}
