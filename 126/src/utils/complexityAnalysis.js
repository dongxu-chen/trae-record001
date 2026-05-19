export class ComplexityAnalysis {
  constructor(options = {}) {
    this.maxTotalComplexity = options.maxTotalComplexity || 150;
    this.maxFieldCount = options.maxFieldCount || 50;
    this.maxDepth = options.maxDepth || 10;
    this.defaultComplexity = options.defaultComplexity || 1;
    this.defaultMultiplier = options.defaultMultiplier || 1;
    this.breadthWeight = options.breadthWeight || 1;
    this.depthWeight = options.depthWeight || 1;
  }

  calculateFieldCost(fieldDef, args) {
    const costDirective = fieldDef.astNode?.directives?.find(
      d => d.name.value === 'cost'
    );
    
    if (!costDirective) {
      return this.defaultComplexity;
    }

    let complexity = this.defaultComplexity;
    let multiplier = this.defaultMultiplier;

    costDirective.arguments.forEach(arg => {
      if (arg.name.value === 'complexity') {
        complexity = parseInt(arg.value.value) || this.defaultComplexity;
      }
      if (arg.name.value === 'multipliers') {
        arg.value.values.forEach(value => {
          const multiplierName = value.value;
          if (args[multiplierName]) {
            multiplier *= parseInt(args[multiplierName]) || 1;
          }
        });
      }
    });

    return complexity * multiplier;
  }

  analyze(queryAST, schema) {
    let depthComplexity = 0;
    let maxDepthReached = 0;
    const fieldBreakdown = [];
    const depthFieldCount = {};

    const traverseSelectionSet = (selectionSet, parentType, depth = 0) => {
      if (!selectionSet || !parentType) return;

      maxDepthReached = Math.max(maxDepthReached, depth);
      depthFieldCount[depth] = (depthFieldCount[depth] || 0) + selectionSet.selections.length;

      for (const selection of selectionSet.selections) {
        if (selection.kind === 'Field') {
          const fieldName = selection.name.value;
          const fieldDef = parentType.getFields()[fieldName];
          
          if (fieldDef) {
            const args = {};
            if (selection.arguments) {
              for (const arg of selection.arguments) {
                if (arg.value.kind === 'IntValue') {
                  args[arg.name.value] = parseInt(arg.value.value);
                } else if (arg.value.kind === 'StringValue') {
                  args[arg.name.value] = arg.value.value;
                }
              }
            }

            const fieldCost = this.calculateFieldCost(fieldDef, args);
            const depthMultiplier = 1 + (depth * 0.1);
            const weightedCost = fieldCost * depthMultiplier;
            depthComplexity += weightedCost;
            
            fieldBreakdown.push({
              field: fieldName,
              depth,
              baseCost: fieldCost,
              weightedCost,
              parent: parentType.name,
            });

            let returnType = fieldDef.type;
            while (returnType.ofType) {
              returnType = returnType.ofType;
            }

            if (selection.selectionSet && returnType.getFields) {
              traverseSelectionSet(selection.selectionSet, returnType, depth + 1);
            }
          }
        }
      }
    };

    if (queryAST.definitions) {
      for (const definition of queryAST.definitions) {
        if (definition.kind === 'OperationDefinition') {
          const rootType = definition.operation === 'query' 
            ? schema.getQueryType() 
            : schema.getMutationType();
          
          traverseSelectionSet(definition.selectionSet, rootType);
        }
      }
    }

    const totalFields = fieldBreakdown.length;
    const breadthComplexity = totalFields * this.breadthWeight;
    const totalComplexity = Math.round((depthComplexity * this.depthWeight) + breadthComplexity);
    const exceedsDepthLimit = maxDepthReached > this.maxDepth;
    const exceedsFieldLimit = totalFields > this.maxFieldCount;
    const exceedsComplexityLimit = totalComplexity > this.maxTotalComplexity;
    const exceedsLimit = exceedsDepthLimit || exceedsFieldLimit || exceedsComplexityLimit;

    return {
      totalComplexity,
      maxTotalComplexity: this.maxTotalComplexity,
      totalFields,
      maxFieldCount: this.maxFieldCount,
      maxDepth: this.maxDepth,
      maxDepthReached,
      depthComplexity,
      breadthComplexity,
      exceedsLimit,
      exceedsDepthLimit,
      exceedsFieldLimit,
      exceedsComplexityLimit,
      depthFieldCount,
      fieldBreakdown,
    };
  }

  createPlugin() {
    return {
      requestDidStart: () => ({
        didResolveOperation: async ({ request, document, schema }) => {
          const analysis = this.analyze(document, schema);
          
          console.log('\n[Query Complexity Analysis]');
          console.log(`📊 Total Complexity: ${analysis.totalComplexity} / ${analysis.maxTotalComplexity}`);
          console.log(`📈 Depth Complexity: ${analysis.depthComplexity.toFixed(2)}`);
          console.log(`📉 Breadth Complexity: ${analysis.breadthComplexity} (${analysis.totalFields} fields)`);
          console.log(`🔍 Max Depth: ${analysis.maxDepthReached} / ${analysis.maxDepth}`);
          
          console.log('\nFields by Depth:');
          Object.entries(analysis.depthFieldCount).forEach(([depth, count]) => {
            console.log(`  Depth ${depth}: ${count} fields`);
          });
          
          console.log('\nField Breakdown:');
          analysis.fieldBreakdown.forEach(field => {
            console.log(`  ${'  '.repeat(field.depth)}${field.parent}.${field.field}: ${field.baseCost} (weighted: ${field.weightedCost.toFixed(2)})`);
          });
          
          if (analysis.exceedsLimit) {
            const errors = [];
            if (analysis.exceedsComplexityLimit) {
              errors.push(`total complexity ${analysis.totalComplexity} > ${analysis.maxTotalComplexity}`);
            }
            if (analysis.exceedsDepthLimit) {
              errors.push(`max depth ${analysis.maxDepthReached} > ${analysis.maxDepth}`);
            }
            if (analysis.exceedsFieldLimit) {
              errors.push(`field count ${analysis.totalFields} > ${analysis.maxFieldCount}`);
            }
            throw new Error(
              `Query exceeds limits: ${errors.join(', ')}`
            );
          }
          console.log('');
        },
      }),
    };
  }
}

export const complexityAnalysis = new ComplexityAnalysis({
  maxTotalComplexity: 150,
  maxFieldCount: 50,
  maxDepth: 10,
  defaultComplexity: 1,
  breadthWeight: 1,
  depthWeight: 1,
});
