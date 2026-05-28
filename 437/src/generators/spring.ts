import { Edge, Node } from 'reactflow';
import { StateNodeData, EdgeData } from '../types';

interface SpringAST {
  packageName: string;
  imports: string[];
  className: string;
  machineName: string;
  statesEnum: string[];
  eventsEnum: string[];
  initialState: string;
  stateConfigs: StateConfig[];
  transitionConfigs: TransitionConfig[];
}

interface StateConfig {
  name: string;
  entryAction?: string;
}

interface TransitionConfig {
  source: string;
  target: string;
  event: string;
  guard?: string;
  actions: string[];
}

function toPascalCase(str: string): string {
  return str
    .replace(/\s+/g, '_')
    .split('_')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase())
    .join('');
}

function toSnakeCase(str: string): string {
  return str.replace(/\s+/g, '_').toUpperCase();
}

function parseActions(actionsStr?: string): string[] {
  if (!actionsStr) return [];
  return actionsStr
    .split(',')
    .map((a) => a.trim().replace(/[()]/g, ''))
    .filter(Boolean);
}

function buildSpringAST(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  machineName: string = 'StateMachine'
): SpringAST {
  const ast: SpringAST = {
    packageName: 'com.example.statemachine',
    imports: [
      'org.springframework.context.annotation.Bean',
      'org.springframework.context.annotation.Configuration',
      'org.springframework.statemachine.config.EnableStateMachine',
      'org.springframework.statemachine.config.StateMachineConfigurerAdapter',
      'org.springframework.statemachine.config.builders.StateMachineConfigurationConfigurer',
      'org.springframework.statemachine.config.builders.StateMachineStateConfigurer',
      'org.springframework.statemachine.config.builders.StateMachineTransitionConfigurer',
      'org.springframework.statemachine.listener.StateMachineListener',
      'org.springframework.statemachine.listener.StateMachineListenerAdapter',
      'org.springframework.statemachine.state.State',
      'java.util.EnumSet',
    ],
    className: toPascalCase(machineName) + 'Config',
    machineName,
    statesEnum: [],
    eventsEnum: [],
    initialState: '',
    stateConfigs: [],
    transitionConfigs: [],
  };

  if (nodes.length === 0) {
    ast.statesEnum = ['IDLE'];
    ast.eventsEnum = ['EVENT'];
    ast.initialState = 'IDLE';
    return ast;
  }

  const initialNode = nodes.find((n) => n.data.nodeType === 'initial' || n.data.isInitial);
  ast.initialState = toSnakeCase(initialNode?.data.label || nodes[0].data.label);

  ast.statesEnum = nodes.map((node) => toSnakeCase(node.data.label));

  const eventSet = new Set<string>();
  edges.forEach((edge) => {
    const event = toSnakeCase(String(edge.data?.event || edge.label || 'TRANSITION'));
    eventSet.add(event);
  });
  ast.eventsEnum = Array.from(eventSet);

  ast.stateConfigs = nodes.map((node) => {
    const config: StateConfig = {
      name: toSnakeCase(node.data.label),
    };
    if (node.data.entry) {
      config.entryAction = node.data.entry.replace(/[()]/g, '');
    }
    return config;
  });

  ast.transitionConfigs = edges
    .map((edge) => {
      const sourceNode = nodes.find((n) => n.id === edge.source);
      const targetNode = nodes.find((n) => n.id === edge.target);
      if (!sourceNode || !targetNode) return null;

      return {
        source: toSnakeCase(sourceNode.data.label),
        target: toSnakeCase(targetNode.data.label),
        event: toSnakeCase(String(edge.data?.event || edge.label || 'TRANSITION')),
        guard: edge.data?.guard ? edge.data.guard.replace(/[()]/g, '') : undefined,
        actions: parseActions(edge.data?.actions),
      };
    })
    .filter((t) => t !== null) as TransitionConfig[];

  return ast;
}

function astToCode(ast: SpringAST): string {
  const lines: string[] = [];

  lines.push(`package ${ast.packageName};`);
  lines.push('');

  ast.imports.forEach((imp) => {
    lines.push(`import ${imp};`);
  });
  lines.push('');

  lines.push(`@Configuration`);
  lines.push(`@EnableStateMachine`);
  lines.push(`public class ${ast.className} extends StateMachineConfigurerAdapter<States, Events> {`);
  lines.push('');

  lines.push(`    @Override`);
  lines.push(`    public void configure(StateMachineStateConfigurer<States, Events> states) throws Exception {`);
  lines.push(`        states`);
  lines.push(`            .withStates()`);
  lines.push(`            .initial(States.${ast.initialState})`);

  ast.stateConfigs.forEach((config) => {
    if (config.entryAction) {
      lines.push(`            .state(States.${config.name}, action("${config.entryAction}"))`);
    } else {
      lines.push(`            .state(States.${config.name})`);
    }
  });
  lines.push(`            ;`);
  lines.push(`    }`);
  lines.push('');

  lines.push(`    @Override`);
  lines.push(`    public void configure(StateMachineTransitionConfigurer<States, Events> transitions) throws Exception {`);
  lines.push(`        transitions`);

  ast.transitionConfigs.forEach((config, index) => {
    const prefix = index === 0 ? '            ' : '            ';
    lines.push(`${prefix}.withExternal()`);
    lines.push(`${prefix}    .source(States.${config.source}).target(States.${config.target}).event(Events.${config.event})`);
    if (config.guard) {
      lines.push(`${prefix}    .guard("${config.guard}")`);
    }
    config.actions.forEach((action) => {
      lines.push(`${prefix}    .action("${action}")`);
    });
  });
  lines.push(`            ;`);
  lines.push(`    }`);
  lines.push('');

  lines.push(`    @Override`);
  lines.push(`    public void configure(StateMachineConfigurationConfigurer<States, Events> config) throws Exception {`);
  lines.push(`        config`);
  lines.push(`            .withConfiguration()`);
  lines.push(`            .listener(listener());`);
  lines.push(`    }`);
  lines.push('');

  lines.push(`    @Bean`);
  lines.push(`    public StateMachineListener<States, Events> listener() {`);
  lines.push(`        return new StateMachineListenerAdapter<>() {`);
  lines.push(`            @Override`);
  lines.push(`            public void stateChanged(State<States, Events> from, State<States, Events> to) {`);
  lines.push(`                System.out.println("State changed from " + (from != null ? from.getId() : "null") + " to " + to.getId());`);
  lines.push(`            }`);
  lines.push(`        };`);
  lines.push(`    }`);
  lines.push(`}`);
  lines.push('');

  lines.push(`enum States {`);
  ast.statesEnum.forEach((state, index) => {
    lines.push(`    ${state}${index < ast.statesEnum.length - 1 ? ',' : ''}`);
  });
  lines.push(`}`);
  lines.push('');

  lines.push(`enum Events {`);
  ast.eventsEnum.forEach((event, index) => {
    lines.push(`    ${event}${index < ast.eventsEnum.length - 1 ? ',' : ''}`);
  });
  lines.push(`}`);

  return lines.join('\n');
}

export function generateSpringStateMachineCode(
  nodes: Node<StateNodeData>[],
  edges: Edge<EdgeData>[],
  machineName: string = 'StateMachine'
): string {
  const ast = buildSpringAST(nodes, edges, machineName);
  return astToCode(ast);
}

export { buildSpringAST };
