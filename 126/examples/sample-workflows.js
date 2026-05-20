export const conditionalWorkflow = {
  name: 'Conditional Workflow',
  description: 'Demonstrates if/else conditional execution',
  steps: [
    {
      id: 'set_vars',
      set: {
        userType: 'admin',
        count: 5,
      },
    },
    {
      id: 'check_admin',
      if: { $eq: ['{{userType}}', 'admin'] },
      then: [
        {
          id: 'log_admin',
          log: 'User is an admin, granting elevated access',
        },
        {
          id: 'set_admin_vars',
          set: {
            accessLevel: 'elevated',
            permissions: '["read", "write", "delete"]',
          },
        },
      ],
      else: [
        {
          id: 'log_user',
          log: 'User is a regular user, granting standard access',
        },
        {
          id: 'set_user_vars',
          set: {
            accessLevel: 'standard',
            permissions: '["read"]',
          },
        },
      ],
    },
    {
      id: 'final_log',
      log: 'Access level: {{accessLevel}}, Permissions: {{permissions}}',
    },
  ],
};

export const foreachWorkflow = {
  name: 'ForEach Workflow',
  description: 'Demonstrates loop iteration with foreach',
  steps: [
    {
      id: 'set_users',
      set: {
        users: [
          { id: '1', name: '张三', email: 'zhang@example.com' },
          { id: '2', name: '李四', email: 'li@example.com' },
          { id: '3', name: '王五', email: 'wang@example.com' },
        ],
      },
    },
    {
      id: 'process_users',
      foreach: '{{users}}',
      as: 'user',
      do: [
        {
          id: 'log_user',
          log: 'Processing user {{$index + 1}}: {{user.name}} ({{user.email}})',
        },
        {
          id: 'check_email',
          if: { $eq: ['{{user.email}}', 'zhang@example.com'] },
          then: [
            {
              id: 'log_special',
              log: 'Found special user! This is the admin account',
            },
          ],
        },
      ],
    },
    {
      id: 'summary',
      log: 'Processed {{$.length(users)}} users successfully',
    },
  ],
};

export const whileWorkflow = {
  name: 'While Workflow',
  description: 'Demonstrates while loop execution',
  steps: [
    {
      id: 'init_counter',
      set: {
        counter: 0,
        max: 5,
      },
    },
    {
      id: 'loop_counter',
      while: { $lt: ['{{counter}}', '{{max}}'] },
      do: [
        {
          id: 'increment',
          set: {
            counter: '{{$.math.add(counter, 1)}}',
          },
        },
        {
          id: 'log_count',
          log: 'Counter value: {{counter}} / {{max}}',
        },
      ],
    },
    {
      id: 'complete',
      log: 'Loop completed! Final counter: {{counter}}',
    },
  ],
};

export const parallelWorkflow = {
  name: 'Parallel Workflow',
  description: 'Demonstrates parallel step execution',
  steps: [
    {
      id: 'start_log',
      log: 'Starting parallel execution...',
    },
    {
      id: 'parallel_tasks',
      parallel: [
        {
          id: 'task1',
          log: 'Task 1: Starting fetch operation',
        },
        {
          id: 'task2',
          wait: '50',
        },
        {
          id: 'task3',
          set: {
            task3Result: 'Completed parallel task 3',
          },
        },
      ],
    },
    {
      id: 'complete_log',
      log: 'All parallel tasks completed! Result: {{task3Result}}',
    },
  ],
};

export const tryCatchWorkflow = {
  name: 'Try/Catch Workflow',
  description: 'Demonstrates error handling with try/catch/finally',
  steps: [
    {
      id: 'start',
      log: 'Starting operation that may fail...',
    },
    {
      id: 'risky_operation',
      try: [
        {
          id: 'set_initial',
          set: {
            operation: 'started',
          },
        },
        {
          id: 'simulate_work',
          wait: '100',
        },
        {
          id: 'check_condition',
          if: { $gt: ['{{$.math.random()}}', '0.5'] },
          then: [
            {
              id: 'throw_error',
              log: 'Simulating error condition',
            },
          ],
        },
      ],
      catch: [
        {
          id: 'handle_error',
          log: 'Caught error: {{$error.message}}',
        },
        {
          id: 'set_fallback',
          set: {
            operation: 'failed',
            error: 'Handled gracefully',
          },
        },
      ],
      finally: [
        {
          id: 'cleanup',
          log: 'Performing cleanup operations regardless of outcome',
        },
      ],
    },
    {
      id: 'result',
      log: 'Operation final state: {{operation}}',
    },
  ],
};

export const complexWorkflow = {
  name: 'Complex Data Processing Workflow',
  description: 'Combines multiple DSL features for data processing',
  steps: [
    {
      id: 'init',
      set: {
        users: [
          { id: '1', name: '张三', active: true, score: 85 },
          { id: '2', name: '李四', active: false, score: 72 },
          { id: '3', name: '王五', active: true, score: 93 },
          { id: '4', name: '赵六', active: true, score: 68 },
        ],
        threshold: 80,
        processedCount: 0,
      },
    },
    {
      id: 'log_start',
      log: 'Starting data processing for {{$.length(users)}} users',
    },
    {
      id: 'process_users',
      foreach: '{{users}}',
      as: 'user',
      do: [
        {
          id: 'check_active',
          if: { $eq: ['{{user.active}}', true] },
          then: [
            {
              id: 'check_score',
              if: { $gte: ['{{user.score}}', '{{threshold}}'] },
              then: [
                {
                  id: 'log_passed',
                  log: '✅ User {{user.name}} passed with score {{user.score}}',
                },
                {
                  id: 'increment_passed',
                  set: {
                    processedCount: '{{$.math.add(processedCount, 1)}}',
                  },
                },
              ],
              else: [
                {
                  id: 'log_failed',
                  log: '❌ User {{user.name}} failed with score {{user.score}} (below {{threshold}})',
                },
              ],
            },
          ],
          else: [
            {
              id: 'log_inactive',
              log: '⏭️ User {{user.name}} is inactive, skipping',
            },
          ],
        },
      ],
    },
    {
      id: 'summary',
      log: 'Processing complete! {{processedCount}} users passed the {{threshold}} threshold',
    },
  ],
};

export default {
  conditionalWorkflow,
  foreachWorkflow,
  whileWorkflow,
  parallelWorkflow,
  tryCatchWorkflow,
  complexWorkflow,
};
