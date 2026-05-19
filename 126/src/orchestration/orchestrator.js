class OrchestrationEngine {
  constructor(options = {}) {
    this.dataSources = options.dataSources || {};
    this.variables = new Map();
    this.executionHistory = [];
    this.maxLoopIterations = options.maxLoopIterations || 100;
    this.timeout = options.timeout || 30000;
    this.registerDefaultFunctions();
  }

  registerDefaultFunctions() {
    this.functions = {
      log: (...args) => console.log('[Orchestrator]', ...args),
      now: () => new Date().toISOString(),
      formatDate: (date, format) => new Date(date).toLocaleString(),
      parseInt: (val) => parseInt(val, 10),
      parseFloat: (val) => parseFloat(val),
      toString: (val) => String(val),
      toUpperCase: (str) => String(str).toUpperCase(),
      toLowerCase: (str) => String(str).toLowerCase(),
      trim: (str) => String(str).trim(),
      concat: (...args) => args.join(''),
      slice: (arr, start, end) => Array.isArray(arr) ? arr.slice(start, end) : [],
      length: (arr) => Array.isArray(arr) ? arr.length : 0,
      get: (obj, path, defaultValue) => {
        const keys = path.split('.');
        let result = obj;
        for (const key of keys) {
          if (result == null) return defaultValue;
          result = result[key];
        }
        return result ?? defaultValue;
      },
      set: (obj, path, value) => {
        const keys = path.split('.');
        let current = obj;
        for (let i = 0; i < keys.length - 1; i++) {
          if (current[keys[i]] == null) {
            current[keys[i]] = {};
          }
          current = current[keys[i]];
        }
        current[keys[keys.length - 1]] = value;
        return obj;
      },
      math: {
        add: (a, b) => a + b,
        sub: (a, b) => a - b,
        mul: (a, b) => a * b,
        div: (a, b) => a / b,
        mod: (a, b) => a % b,
        pow: (a, b) => Math.pow(a, b),
        min: (...args) => Math.min(...args),
        max: (...args) => Math.max(...args),
        round: (num) => Math.round(num),
        floor: (num) => Math.floor(num),
        ceil: (num) => Math.ceil(num),
        abs: (num) => Math.abs(num),
      },
      array: {
        map: (arr, fn) => Array.isArray(arr) ? arr.map(fn) : [],
        filter: (arr, fn) => Array.isArray(arr) ? arr.filter(fn) : [],
        reduce: (arr, fn, init) => Array.isArray(arr) ? arr.reduce(fn, init) : init,
        find: (arr, fn) => Array.isArray(arr) ? arr.find(fn) : undefined,
        includes: (arr, val) => Array.isArray(arr) && arr.includes(val),
        join: (arr, separator) => Array.isArray(arr) ? arr.join(separator) : '',
        push: (arr, ...items) => {
          if (Array.isArray(arr)) {
            arr.push(...items);
          }
          return arr;
        },
        pop: (arr) => Array.isArray(arr) ? arr.pop() : undefined,
        shift: (arr) => Array.isArray(arr) ? arr.shift() : undefined,
        unshift: (arr, ...items) => {
          if (Array.isArray(arr)) {
            arr.unshift(...items);
          }
          return arr;
        },
      },
    };
  }

  registerFunction(name, fn) {
    this.functions[name] = fn;
  }

  registerDataSource(name, dataSource) {
    this.dataSources[name] = dataSource;
  }

  setVariable(name, value) {
    this.variables.set(name, value);
  }

  getVariable(name) {
    return this.variables.get(name);
  }

  evaluateExpression(expression, context = {}) {
    if (typeof expression !== 'string') {
      return expression;
    }

    if (!expression.includes('{{')) {
      return expression;
    }

    const evalContext = {
      ...Object.fromEntries(this.variables),
      ...context,
      $: this.functions,
    };

    let result = expression;
    const regex = /\{\{([\s\S]*?)\}\}/g;
    
    result = result.replace(regex, (match, expr) => {
      try {
        const fn = new Function(...Object.keys(evalContext), `return ${expr.trim()}`);
        const value = fn(...Object.values(evalContext));
        return value;
      } catch (error) {
        console.error(`Expression evaluation error: ${expr}`, error);
        return match;
      }
    });

    return result;
  }

  evaluateCondition(condition, context = {}) {
    if (typeof condition === 'boolean') {
      return condition;
    }

    if (typeof condition === 'string') {
      const result = this.evaluateExpression(`{{${condition}}}`, context);
      return Boolean(result);
    }

    if (condition && typeof condition === 'object') {
      const { $and, $or, $not, $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin } = condition;

      if ($and) {
        return $and.every(cond => this.evaluateCondition(cond, context));
      }

      if ($or) {
        return $or.some(cond => this.evaluateCondition(cond, context));
      }

      if ($not) {
        return !this.evaluateCondition($not, context);
      }

      if ($eq && $eq.length === 2) {
        const left = this.evaluateExpression($eq[0], context);
        const right = this.evaluateExpression($eq[1], context);
        return left === right;
      }

      if ($ne && $ne.length === 2) {
        const left = this.evaluateExpression($ne[0], context);
        const right = this.evaluateExpression($ne[1], context);
        return left !== right;
      }

      if ($gt && $gt.length === 2) {
        const left = this.evaluateExpression($gt[0], context);
        const right = this.evaluateExpression($gt[1], context);
        return left > right;
      }

      if ($gte && $gte.length === 2) {
        const left = this.evaluateExpression($gte[0], context);
        const right = this.evaluateExpression($gte[1], context);
        return left >= right;
      }

      if ($lt && $lt.length === 2) {
        const left = this.evaluateExpression($lt[0], context);
        const right = this.evaluateExpression($lt[1], context);
        return left < right;
      }

      if ($lte && $lte.length === 2) {
        const left = this.evaluateExpression($lte[0], context);
        const right = this.evaluateExpression($lte[1], context);
        return left <= right;
      }

      if ($in && $in.length === 2) {
        const value = this.evaluateExpression($in[0], context);
        const array = this.evaluateExpression($in[1], context);
        return Array.isArray(array) && array.includes(value);
      }

      if ($nin && $nin.length === 2) {
        const value = this.evaluateExpression($nin[0], context);
        const array = this.evaluateExpression($nin[1], context);
        return Array.isArray(array) && !array.includes(value);
      }
    }

    return false;
  }

  async executeStep(step, context = {}) {
    const stepId = step.id || `step_${Date.now()}`;
    const stepContext = { ...context, stepId };

    const startTime = Date.now();
    let result;
    let error = null;

    try {
      if (step.if !== undefined) {
        result = await this.executeConditional(step, stepContext);
      } else if (step.foreach !== undefined) {
        result = await this.executeForeach(step, stepContext);
      } else if (step.while !== undefined) {
        result = await this.executeWhile(step, stepContext);
      } else if (step.parallel !== undefined) {
        result = await this.executeParallel(step, stepContext);
      } else if (step.call !== undefined) {
        result = await this.executeCall(step, stepContext);
      } else if (step.set !== undefined) {
        result = await this.executeSet(step, stepContext);
      } else if (step.log !== undefined) {
        result = await this.executeLog(step, stepContext);
      } else if (step.try !== undefined) {
        result = await this.executeTryCatch(step, stepContext);
      } else if (step.wait !== undefined) {
        result = await this.executeWait(step, stepContext);
      } else {
        throw new Error(`Unknown step type: ${Object.keys(step).join(', ')}`);
      }
    } catch (err) {
      error = err;
      if (!step.continueOnError) {
        throw err;
      }
    }

    const executionTime = Date.now() - startTime;

    this.executionHistory.push({
      id: stepId,
      type: Object.keys(step).find(k => k !== 'id' && k !== 'continueOnError' && k !== 'description'),
      success: !error,
      error: error?.message,
      executionTime,
      timestamp: new Date().toISOString(),
    });

    return result;
  }

  async executeConditional(step, context) {
    const { if: condition, then, else: elseBranch } = step;
    
    if (this.evaluateCondition(condition, context)) {
      if (Array.isArray(then)) {
        for (const subStep of then) {
          await this.executeStep(subStep, context);
        }
      } else if (then) {
        await this.executeStep(then, context);
      }
    } else if (elseBranch) {
      if (Array.isArray(elseBranch)) {
        for (const subStep of elseBranch) {
          await this.executeStep(subStep, context);
        }
      } else {
        await this.executeStep(elseBranch, context);
      }
    }

    return { conditionResult: this.evaluateCondition(condition, context) };
  }

  async executeForeach(step, context) {
    const { foreach: arrayExpr, as = 'item', do: doSteps } = step;
    const array = this.evaluateExpression(arrayExpr, context);
    
    if (!Array.isArray(array)) {
      throw new Error('Foreach requires an array');
    }

    const results = [];
    for (let i = 0; i < array.length; i++) {
      const item = array[i];
      const loopContext = {
        ...context,
        [as]: item,
        $index: i,
        $first: i === 0,
        $last: i === array.length - 1,
      };

      if (Array.isArray(doSteps)) {
        for (const subStep of doSteps) {
          await this.executeStep(subStep, loopContext);
        }
      } else if (doSteps) {
        await this.executeStep(doSteps, loopContext);
      }

      results.push(item);
    }

    return { iterations: results.length, results };
  }

  async executeWhile(step, context) {
    const { while: condition, do: doSteps, maxIterations } = step;
    const max = maxIterations || this.maxLoopIterations;
    let iterations = 0;
    const results = [];

    while (this.evaluateCondition(condition, context) && iterations < max) {
      const loopContext = {
        ...context,
        $index: iterations,
      };

      if (Array.isArray(doSteps)) {
        for (const subStep of doSteps) {
          await this.executeStep(subStep, loopContext);
        }
      } else if (doSteps) {
        await this.executeStep(doSteps, loopContext);
      }

      iterations++;
      results.push({ iteration: iterations });
    }

    if (iterations >= max) {
      console.warn(`While loop reached max iterations (${max})`);
    }

    return { iterations, maxIterations: max };
  }

  async executeParallel(step, context) {
    const { parallel: steps } = step;
    
    if (!Array.isArray(steps)) {
      throw new Error('Parallel requires an array of steps');
    }

    const promises = steps.map(subStep => this.executeStep(subStep, context));
    const results = await Promise.allSettled(promises);
    
    return {
      total: results.length,
      fulfilled: results.filter(r => r.status === 'fulfilled').length,
      rejected: results.filter(r => r.status === 'rejected').length,
      results,
    };
  }

  async executeCall(step, context) {
    const { call, args = [], resultVar } = step;
    const evaluatedArgs = args.map(arg => this.evaluateExpression(arg, context));
    
    let result;
    const dataSourceName = call.split('.')[0];
    const methodName = call.split('.')[1];
    
    if (this.dataSources[dataSourceName]) {
      const dataSource = this.dataSources[dataSourceName];
      if (typeof dataSource[methodName] === 'function') {
        result = await dataSource[methodName](...evaluatedArgs);
      } else {
        throw new Error(`Method ${methodName} not found on data source ${dataSourceName}`);
      }
    } else if (call in this.functions) {
      result = this.functions[call](...evaluatedArgs);
    } else {
      throw new Error(`Data source or function not found: ${call}`);
    }

    if (resultVar) {
      this.setVariable(resultVar, result);
    }

    return { call, args: evaluatedArgs, result, resultVar };
  }

  async executeSet(step, context) {
    const { set: assignments } = step;
    
    for (const [key, valueExpr] of Object.entries(assignments)) {
      const value = this.evaluateExpression(valueExpr, context);
      this.setVariable(key, value);
    }

    return { assignments: Object.keys(assignments).length };
  }

  async executeLog(step, context) {
    const { log: message, level = 'info' } = step;
    const evaluatedMessage = this.evaluateExpression(message, context);
    
    if (level === 'error') {
      console.error('[Orchestrator Log]', evaluatedMessage);
    } else if (level === 'warn') {
      console.warn('[Orchestrator Log]', evaluatedMessage);
    } else {
      console.log('[Orchestrator Log]', evaluatedMessage);
    }

    return { level, message: evaluatedMessage };
  }

  async executeTryCatch(step, context) {
    const { try: trySteps, catch: catchSteps, finally: finallySteps } = step;
    let error = null;
    let success = true;

    try {
      if (Array.isArray(trySteps)) {
        for (const subStep of trySteps) {
          await this.executeStep(subStep, context);
        }
      } else if (trySteps) {
        await this.executeStep(trySteps, context);
      }
    } catch (err) {
      error = err;
      success = false;
      
      if (catchSteps) {
        const catchContext = { ...context, $error: err };
        if (Array.isArray(catchSteps)) {
          for (const subStep of catchSteps) {
            await this.executeStep(subStep, catchContext);
          }
        } else {
          await this.executeStep(catchSteps, catchContext);
        }
      }
    } finally {
      if (finallySteps) {
        if (Array.isArray(finallySteps)) {
          for (const subStep of finallySteps) {
            await this.executeStep(subStep, context);
          }
        } else {
          await this.executeStep(finallySteps, context);
        }
      }
    }

    return { success, error: error?.message };
  }

  async executeWait(step, context) {
    const { wait: ms } = step;
    const evaluatedMs = parseInt(this.evaluateExpression(ms, context), 10) || 0;
    
    await new Promise(resolve => setTimeout(resolve, evaluatedMs));
    
    return { waited: evaluatedMs };
  }

  async execute(workflow, initialVariables = {}) {
    this.variables = new Map(Object.entries(initialVariables));
    this.executionHistory = [];

    const startTime = Date.now();
    const { name, description, steps } = workflow;

    if (!Array.isArray(steps)) {
      throw new Error('Workflow must have a steps array');
    }

    console.log(`🚀 Starting workflow: ${name || 'unnamed'}`);
    if (description) {
      console.log(`📝 ${description}`);
    }

    try {
      for (const step of steps) {
        await this.executeStep(step, {});
      }

      const executionTime = Date.now() - startTime;
      console.log(`✅ Workflow completed in ${executionTime}ms`);

      return {
        success: true,
        workflowName: name,
        executionTime,
        completedSteps: this.executionHistory.length,
        history: this.executionHistory,
        variables: Object.fromEntries(this.variables),
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      console.error(`❌ Workflow failed: ${error.message}`);

      return {
        success: false,
        workflowName: name,
        executionTime,
        error: error.message,
        completedSteps: this.executionHistory.length,
        history: this.executionHistory,
        variables: Object.fromEntries(this.variables),
      };
    }
  }

  getExecutionHistory() {
    return this.executionHistory;
  }

  getVariables() {
    return Object.fromEntries(this.variables);
  }

  reset() {
    this.variables.clear();
    this.executionHistory = [];
  }

  validateWorkflow(workflow) {
    const errors = [];
    
    if (!workflow.steps || !Array.isArray(workflow.steps)) {
      errors.push('Workflow must have a steps array');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }
}

export const orchestrator = new OrchestrationEngine();
export default OrchestrationEngine;
