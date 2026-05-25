import type { FormSchema, FormField } from '@/types/form'
import { extractFormulaDependencies } from './formulaEngine'

export interface DependencyNode {
  fieldName: string
  fieldId: string
  dependencies: string[]
}

export interface CircularDependency {
  path: string[]
  type: 'formula' | 'conditional' | 'mixed'
}

export interface DependencyCheckResult {
  hasCircularDependency: boolean
  circularDependencies: CircularDependency[]
  dependencyGraph: Map<string, string[]>
  topologicalOrder: string[]
  errors: string[]
}

function buildDependencyGraph(schema: FormSchema): {
  graph: Map<string, string[]>
  fieldMap: Map<string, FormField>
  errors: string[]
} {
  const graph = new Map<string, string[]>()
  const fieldMap = new Map<string, FormField>()
  const errors: string[] = []
  const nameToId = new Map<string, string>()

  schema.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      nameToId.set(field.name, field.id)
      fieldMap.set(field.name, field)
    })
  })

  schema.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      const dependencies = new Set<string>()

      if (field.formula?.expression) {
        try {
          const deps = extractFormulaDependencies(field.formula.expression, schema)
          deps.forEach(d => dependencies.add(d))
        } catch (e) {
          errors.push(`字段 "${field.name}" 的公式解析错误`)
        }
      }

      if (field.conditional?.show?.field) {
        const depField = findFieldByName(schema, field.conditional.show.field)
        if (depField) {
          dependencies.add(depField.name)
        }
      }

      if (field.conditional?.disable?.field) {
        const depField = findFieldByName(schema, field.conditional.disable.field)
        if (depField) {
          dependencies.add(depField.name)
        }
      }

      graph.set(field.name, Array.from(dependencies))
    })
  })

  return { graph, fieldMap, errors }
}

function findFieldByName(schema: FormSchema, fieldNameOrId: string): FormField | null {
  for (const tab of schema.tabs) {
    for (const field of tab.fields) {
      if (field.name === fieldNameOrId || field.id === fieldNameOrId) {
        return field
      }
    }
  }
  return null
}

function detectCycles(graph: Map<string, string[]>): CircularDependency[] {
  const visited = new Set<string>()
  const recursionStack = new Set<string>()
  const path: string[] = []
  const cycles: CircularDependency[] = []
  const foundCycles = new Set<string>()

  function dfs(node: string) {
    if (recursionStack.has(node)) {
      const cycleStartIndex = path.indexOf(node)
      if (cycleStartIndex !== -1) {
        const cyclePath = [...path.slice(cycleStartIndex), node]
        const cycleKey = cyclePath.sort().join('->')
        
        if (!foundCycles.has(cycleKey)) {
          foundCycles.add(cycleKey)
          cycles.push({
            path: cyclePath,
            type: 'mixed'
          })
        }
      }
      return
    }

    if (visited.has(node)) {
      return
    }

    visited.add(node)
    recursionStack.add(node)
    path.push(node)

    const dependencies = graph.get(node) || []
    for (const dep of dependencies) {
      if (graph.has(dep)) {
        dfs(dep)
      }
    }

    recursionStack.delete(node)
    path.pop()
  }

  for (const node of graph.keys()) {
    if (!visited.has(node)) {
      dfs(node)
    }
  }

  return cycles
}

function topologicalSort(graph: Map<string, string[]>): {
  order: string[]
  hasCycle: boolean
} {
  const inDegree = new Map<string, number>()
  const tempGraph = new Map<string, string[]>()

  for (const [node, deps] of graph.entries()) {
    inDegree.set(node, 0)
    tempGraph.set(node, [])
  }

  for (const [node, deps] of graph.entries()) {
    for (const dep of deps) {
      if (tempGraph.has(dep)) {
        tempGraph.get(dep)!.push(node)
        inDegree.set(node, (inDegree.get(node) || 0) + 1)
      }
    }
  }

  const queue: string[] = []
  for (const [node, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(node)
    }
  }

  const order: string[] = []
  while (queue.length > 0) {
    const node = queue.shift()!
    order.push(node)

    const dependents = tempGraph.get(node) || []
    for (const dep of dependents) {
      const newDegree = (inDegree.get(dep) || 0) - 1
      inDegree.set(dep, newDegree)
      if (newDegree === 0) {
        queue.push(dep)
      }
    }
  }

  return {
    order,
    hasCycle: order.length !== graph.size
  }
}

export function checkDependencies(schema: FormSchema): DependencyCheckResult {
  const { graph, errors } = buildDependencyGraph(schema)
  const cycles = detectCycles(graph)
  const { order, hasCycle } = topologicalSort(graph)

  return {
    hasCircularDependency: hasCycle || cycles.length > 0,
    circularDependencies: cycles,
    dependencyGraph: graph,
    topologicalOrder: order,
    errors
  }
}

export function validateFieldDependencies(
  schema: FormSchema,
  fieldName: string,
  newExpression: string,
  newConditionalField?: string
): {
  valid: boolean
  error: string | null
  circularPath?: string[]
} {
  const tempSchema = JSON.parse(JSON.stringify(schema)) as FormSchema
  
  for (const tab of tempSchema.tabs) {
    const field = tab.fields.find(f => f.name === fieldName)
    if (field) {
      if (newExpression !== undefined) {
        field.formula = { expression: newExpression, dependencies: [] }
      }
      if (newConditionalField !== undefined) {
        if (!field.conditional) field.conditional = {}
        field.conditional.show = { field: newConditionalField, operator: '==', value: '' }
      }
      break
    }
  }

  const result = checkDependencies(tempSchema)
  
  if (result.hasCircularDependency) {
    const cycle = result.circularDependencies[0]
    return {
      valid: false,
      error: `检测到循环依赖: ${cycle.path.join(' → ')}`,
      circularPath: cycle.path
    }
  }

  return { valid: true, error: null }
}

export function getFieldDependents(schema: FormSchema, fieldName: string): string[] {
  const dependents: string[] = []
  const { graph } = buildDependencyGraph(schema)

  for (const [name, deps] of graph.entries()) {
    if (deps.includes(fieldName) && name !== fieldName) {
      dependents.push(name)
    }
  }

  return dependents
}

export function getDependencyChain(schema: FormSchema, fieldName: string): string[] {
  const { graph } = buildDependencyGraph(schema)
  const chain: string[] = []
  const visited = new Set<string>()

  function collectDeps(name: string) {
    if (visited.has(name)) return
    visited.add(name)

    const deps = graph.get(name) || []
    for (const dep of deps) {
      if (!visited.has(dep)) {
        chain.push(dep)
        collectDeps(dep)
      }
    }
  }

  collectDeps(fieldName)
  return chain
}
