import { FieldNode, LineageEdge } from '@/types';

export interface SQLScript {
  id: string;
  name: string;
  content: string;
  filePath?: string;
  datasource: string;
}

export interface ParseResult {
  sourceTables: string[];
  sourceFields: string[];
  targetTable: string;
  targetFields: string[];
  transformations: Record<string, string>;
  cteTables: string[];
  subqueries: string[];
}

export interface CrossFileRelation {
  fromFile: string;
  toFile: string;
  viaTable: string;
}

export class SQLASTParser {
  private scripts: Map<string, SQLScript> = new Map();
  private tableToScript: Map<string, string> = new Map();

  addScript(script: SQLScript) {
    this.scripts.set(script.id, script);
    const result = this.parse(script.content);
    if (result.targetTable) {
      this.tableToScript.set(result.targetTable.toLowerCase(), script.id);
    }
  }

  parse(sql: string): ParseResult {
    const result: ParseResult = {
      sourceTables: [],
      sourceFields: [],
      targetTable: '',
      targetFields: [],
      transformations: {},
      cteTables: [],
      subqueries: [],
    };

    const cleanSql = this.removeComments(sql);

    const cteMatches = cleanSql.match(/WITH\s+(\w+)\s+AS\s*\(/gi);
    if (cteMatches) {
      cteMatches.forEach((match) => {
        const cteName = match.match(/WITH\s+(\w+)\s+AS/i)?.[1];
        if (cteName) {
          result.cteTables.push(cteName.toLowerCase());
        }
      });
    }

    const insertMatch = cleanSql.match(/INSERT\s+(?:INTO\s+)?([\w.]+)/i);
    const createMatch = cleanSql.match(/CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)/i);
    const selectIntoMatch = cleanSql.match(/SELECT\s+.*?INTO\s+([\w.]+)/i);

    if (insertMatch) {
      result.targetTable = this.normalizeTableName(insertMatch[1]);
    } else if (createMatch) {
      result.targetTable = this.normalizeTableName(createMatch[1]);
    } else if (selectIntoMatch) {
      result.targetTable = this.normalizeTableName(selectIntoMatch[1]);
    }

    const fromMatches = cleanSql.matchAll(/FROM\s+([\w.]+)(?:\s+(?:AS\s+)?\w+)?/gi);
    for (const match of fromMatches) {
      const table = this.normalizeTableName(match[1]);
      if (!result.cteTables.includes(table.toLowerCase())) {
        result.sourceTables.push(table);
      }
    }

    const joinMatches = cleanSql.matchAll(/JOIN\s+([\w.]+)(?:\s+(?:AS\s+)?\w+)?/gi);
    for (const match of joinMatches) {
      const table = this.normalizeTableName(match[1]);
      if (!result.cteTables.includes(table.toLowerCase())) {
        result.sourceTables.push(table);
      }
    }

    result.sourceTables = [...new Set(result.sourceTables)];

    const selectClause = this.extractSelectClause(cleanSql);
    if (selectClause) {
      const fields = this.parseSelectFields(selectClause);
      result.targetFields = fields.map(f => f.target);
      result.sourceFields = fields.map(f => f.source).filter(Boolean) as string[];
      fields.forEach(f => {
        if (f.transformation && f.target) {
          result.transformations[f.target] = f.transformation;
        }
      });
    }

    const subqueryMatches = cleanSql.matchAll(/\(\s*SELECT\s+.*?\)\s*(?:AS\s+)?(\w+)?/gi);
    for (const match of subqueryMatches) {
      if (match[1]) {
        result.subqueries.push(match[1]);
      }
    }

    return result;
  }

  parseCrossFileLineage(targetScriptId: string): {
    nodes: FieldNode[];
    edges: LineageEdge[];
  } {
    const targetScript = this.scripts.get(targetScriptId);
    if (!targetScript) {
      return { nodes: [], edges: [] };
    }

    const nodes: FieldNode[] = [];
    const edges: LineageEdge[] = [];
    const visited = new Set<string>();

    this.buildCrossFileLineageRecursive(
      targetScriptId,
      nodes,
      edges,
      visited,
      0
    );

    return { nodes, edges };
  }

  private buildCrossFileLineageRecursive(
    scriptId: string,
    nodes: FieldNode[],
    edges: LineageEdge[],
    visited: Set<string>,
    depth: number
  ) {
    if (visited.has(scriptId)) return;
    visited.add(scriptId);

    const script = this.scripts.get(scriptId);
    if (!script) return;

    const parseResult = this.parse(script.content);

    const targetTableNode: FieldNode = {
      id: `table-${parseResult.targetTable}`,
      name: parseResult.targetTable.split('.').pop() || parseResult.targetTable,
      table: parseResult.targetTable,
      database: parseResult.targetTable.includes('.') ? parseResult.targetTable.split('.')[0] : '',
      datasource: script.datasource,
      type: 'table',
      description: `由 ${script.name} 生成`,
    };
    nodes.push(targetTableNode);

    const etlNode: FieldNode = {
      id: `etl-${scriptId}`,
      name: script.name,
      table: '',
      database: '',
      datasource: '',
      type: 'etl',
      description: script.filePath,
    };
    nodes.push(etlNode);

    edges.push({
      id: `edge-etl-${scriptId}-table`,
      source: etlNode.id,
      target: targetTableNode.id,
      type: 'direct',
    });

    for (const sourceTable of parseResult.sourceTables) {
      const sourceTableNode: FieldNode = {
        id: `table-${sourceTable}`,
        name: sourceTable.split('.').pop() || sourceTable,
        table: sourceTable,
        database: sourceTable.includes('.') ? sourceTable.split('.')[0] : '',
        datasource: script.datasource,
        type: 'table',
      };

      if (!nodes.find(n => n.id === sourceTableNode.id)) {
        nodes.push(sourceTableNode);
      }

      edges.push({
        id: `edge-${sourceTableNode.id}-${etlNode.id}`,
        source: sourceTableNode.id,
        target: etlNode.id,
        type: 'direct',
      });

      const sourceScriptId = this.tableToScript.get(sourceTable.toLowerCase());
      if (sourceScriptId && sourceScriptId !== scriptId) {
        this.buildCrossFileLineageRecursive(
          sourceScriptId,
          nodes,
          edges,
          visited,
          depth + 1
        );
      }
    }
  }

  private removeComments(sql: string): string {
    sql = sql.replace(/--.*$/gm, '');
    sql = sql.replace(/\/\*[\s\S]*?\*\//g, '');
    return sql.trim();
  }

  private normalizeTableName(name: string): string {
    return name.replace(/[`"\[\]]/g, '');
  }

  private extractSelectClause(sql: string): string {
    const selectMatch = sql.match(/SELECT\s+([\s\S]*?)\s+FROM\s+/i);
    return selectMatch ? selectMatch[1].trim() : '';
  }

  private parseSelectFields(selectClause: string): Array<{ source: string; target: string; transformation?: string }> {
    const fields: Array<{ source: string; target: string; transformation?: string }> = [];
    
    const parts = this.splitByComma(selectClause);
    
    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed || trimmed === '*') continue;

      const aliasMatch = trimmed.match(/^(.*?)\s+(?:AS\s+)?([\w]+)$/i);
      if (aliasMatch) {
        const expression = aliasMatch[1].trim();
        const alias = aliasMatch[2].trim();
        
        const simpleFieldMatch = expression.match(/^[\w.]+$/);
        if (simpleFieldMatch) {
          fields.push({ source: expression, target: alias });
        } else {
          fields.push({ source: alias, target: alias, transformation: expression });
        }
      } else {
        const fieldName = trimmed.split('.').pop() || trimmed;
        fields.push({ source: trimmed, target: fieldName });
      }
    }

    return fields;
  }

  private splitByComma(str: string): string[] {
    const result: string[] = [];
    let current = '';
    let depth = 0;
    let inQuote = false;
    let quoteChar = '';

    for (let i = 0; i < str.length; i++) {
      const char = str[i];

      if ((char === '"' || char === "'") && str[i - 1] !== '\\') {
        if (!inQuote) {
          inQuote = true;
          quoteChar = char;
        } else if (char === quoteChar) {
          inQuote = false;
        }
        current += char;
      } else if (inQuote) {
        current += char;
      } else if (char === '(') {
        depth++;
        current += char;
      } else if (char === ')') {
        depth--;
        current += char;
      } else if (char === ',' && depth === 0) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    if (current.trim()) {
      result.push(current.trim());
    }

    return result;
  }

  getCrossFileRelations(): CrossFileRelation[] {
    const relations: CrossFileRelation[] = [];

    for (const [scriptId, script] of this.scripts) {
      const result = this.parse(script.content);
      for (const sourceTable of result.sourceTables) {
        const sourceScriptId = this.tableToScript.get(sourceTable.toLowerCase());
        if (sourceScriptId && sourceScriptId !== scriptId) {
          relations.push({
            fromFile: sourceScriptId,
            toFile: scriptId,
            viaTable: sourceTable,
          });
        }
      }
    }

    return relations;
  }
}

export const sqlParser = new SQLASTParser();
