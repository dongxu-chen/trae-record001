import * as XLSX from 'xlsx';
import { AnalysisResult, FieldNode, ChangeRiskAssessment, FieldDictionary } from '@/types';
import { getChangeTypeLabel, getRiskLevelLabel } from '@/services/riskAssessment';

export const exportToJSON = (result: AnalysisResult) => {
  const dataStr = JSON.stringify(result, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `lineage_analysis_${result.fieldName}_${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const getNodeTypeName = (type: string): string => {
  const types: Record<string, string> = {
    field: '字段',
    table: '数据表',
    etl: 'ETL任务',
    report: '报表',
  };
  return types[type] || type;
};

const sortNodesByDepth = (nodes: FieldNode[]): FieldNode[] => {
  return [...nodes].sort((a, b) => {
    const depthA = a.depth ?? 999;
    const depthB = b.depth ?? 999;
    if (depthA !== depthB) return depthA - depthB;
    return a.name.localeCompare(b.name);
  });
};

export const exportToExcel = (result: AnalysisResult, riskAssessment?: ChangeRiskAssessment, fieldDictionary?: FieldDictionary) => {
  const wb = XLSX.utils.book_new();

  const summaryData = [
    ['字段名称', result.fieldName],
    ['分析时间', new Date().toLocaleString()],
    ['下游节点总数', result.statistics.totalDownstreamNodes],
    ['最大影响深度', result.statistics.maxDepth],
    ['影响ETL任务数', result.statistics.etlTasks],
    ['影响报表数', result.statistics.reports],
    ['影响数据表数', result.statistics.tables],
  ];
  const ws1 = XLSX.utils.aoa_to_sheet(summaryData);
  ws1['!cols'] = [{ wch: 20 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, ws1, '分析摘要');

  const sortedNodes = sortNodesByDepth(result.graph.nodes);
  const nodesByDepth: Record<number, FieldNode[]> = {};
  sortedNodes.forEach(node => {
    const depth = node.depth ?? 0;
    if (!nodesByDepth[depth]) nodesByDepth[depth] = [];
    nodesByDepth[depth].push(node);
  });

  const depthSummary: (string | number)[][] = [
    ['影响深度', '节点数量', '节点类型分布'],
  ];
  Object.keys(nodesByDepth).sort((a, b) => Number(a) - Number(b)).forEach(depthStr => {
    const depth = Number(depthStr);
    const nodes = nodesByDepth[depth];
    const typeCounts: Record<string, number> = {};
    nodes.forEach(n => {
      typeCounts[n.type] = (typeCounts[n.type] || 0) + 1;
    });
    const typeDist = Object.entries(typeCounts)
      .map(([type, count]) => `${getNodeTypeName(type)}:${count}`)
      .join(', ');
    depthSummary.push([depth === 0 ? '根节点' : `第${depth}层`, nodes.length, typeDist]);
  });
  const ws2 = XLSX.utils.aoa_to_sheet(depthSummary);
  ws2['!cols'] = [{ wch: 15 }, { wch: 12 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, ws2, '影响深度统计');

  const allNodesData: (string | number)[][] = [
    ['影响深度', '节点ID', '节点名称', '节点类型', '所属表', '所属库', '数据源', '描述', '是否有子节点'],
    ...sortedNodes.map((n) => [
      n.depth ?? 0,
      n.id,
      n.name,
      getNodeTypeName(n.type),
      n.table || '-',
      n.database || '-',
      n.datasource || '-',
      n.description || '-',
      n.hasChildren ? '是' : '否',
    ]),
  ];
  const ws3 = XLSX.utils.aoa_to_sheet(allNodesData);
  ws3['!cols'] = [
    { wch: 12 }, { wch: 30 }, { wch: 20 }, { wch: 12 }, 
    { wch: 20 }, { wch: 15 }, { wch: 12 }, { wch: 30 }, { wch: 12 }
  ];
  XLSX.utils.book_append_sheet(wb, ws3, '节点明细(按深度排序)');

  Object.keys(nodesByDepth).sort((a, b) => Number(a) - Number(b)).forEach(depthStr => {
    const depth = Number(depthStr);
    const nodes = nodesByDepth[depth];
    const sheetName = depth === 0 ? '第0层-根节点' : `第${depth}层-下游节点`;
    
    const depthData: (string | number)[][] = [
      ['序号', '节点ID', '节点名称', '节点类型', '所属表', '所属库', '描述'],
      ...nodes.map((n, idx) => [
        idx + 1,
        n.id,
        n.name,
        getNodeTypeName(n.type),
        n.table || '-',
        n.database || '-',
        n.description || '-',
      ]),
    ];
    const ws = XLSX.utils.aoa_to_sheet(depthData);
    ws['!cols'] = [
      { wch: 8 }, { wch: 30 }, { wch: 20 }, { wch: 12 },
      { wch: 20 }, { wch: 15 }, { wch: 30 }
    ];
    XLSX.utils.book_append_sheet(wb, ws, sheetName.slice(0, 31));
  });

  if (result.downstreamList.etlTasks.length > 0) {
    const etlData = [
      ['任务ID', '任务名称', '调度周期', '负责人', '上次运行时间', '运行状态'],
      ...result.downstreamList.etlTasks.map((t) => [
        t.id,
        t.name,
        t.schedule,
        t.owner,
        t.lastRun,
        t.status === 'success' ? '成功' : t.status === 'running' ? '运行中' : '失败',
      ]),
    ];
    const ws5 = XLSX.utils.aoa_to_sheet(etlData);
    ws5['!cols'] = [
      { wch: 15 }, { wch: 25 }, { wch: 15 }, { wch: 12 }, { wch: 20 }, { wch: 12 }
    ];
    XLSX.utils.book_append_sheet(wb, ws5, '受影响ETL任务');
  }

  if (result.downstreamList.reports.length > 0) {
    const reportData = [
      ['报表ID', '报表名称', '类型', '负责人', '更新时间'],
      ...result.downstreamList.reports.map((r) => [
        r.id,
        r.name,
        r.type === 'dashboard' ? '看板' : r.type === 'report' ? '报表' : '图表',
        r.owner,
        r.updatedAt,
      ]),
    ];
    const ws6 = XLSX.utils.aoa_to_sheet(reportData);
    ws6['!cols'] = [
      { wch: 15 }, { wch: 25 }, { wch: 10 }, { wch: 12 }, { wch: 15 }
    ];
    XLSX.utils.book_append_sheet(wb, ws6, '受影响报表');
  }

  if (result.downstreamList.tables.length > 0) {
    const tableData = [
      ['表ID', '表名', '数据库', '数据源', '字段数'],
      ...result.downstreamList.tables.map((t) => [
        t.id,
        t.name,
        t.database,
        t.datasource,
        t.fieldCount,
      ]),
    ];
    const ws7 = XLSX.utils.aoa_to_sheet(tableData);
    ws7['!cols'] = [
      { wch: 15 }, { wch: 25 }, { wch: 15 }, { wch: 12 }, { wch: 10 }
    ];
    XLSX.utils.book_append_sheet(wb, ws7, '受影响数据表');
  }

  if (riskAssessment) {
    const riskData: (string | number)[][] = [
      ['变更类型', '风险等级', '风险分数', '影响ETL任务数', '影响报表数', '影响数据表数', '影响负责人数', '最大影响深度', '预估恢复时间', '需要停机'],
      [
        getChangeTypeLabel(riskAssessment.changeType),
        getRiskLevelLabel(riskAssessment.riskLevel),
        riskAssessment.riskScore,
        riskAssessment.impactScope.affectedETLTasks,
        riskAssessment.impactScope.affectedReports,
        riskAssessment.impactScope.affectedTables,
        riskAssessment.impactScope.affectedOwners,
        riskAssessment.impactScope.maxDepth,
        riskAssessment.estimatedRecoveryTime,
        riskAssessment.requiresDowntime ? '是' : '否',
      ],
    ];
    const wsRisk = XLSX.utils.aoa_to_sheet(riskData);
    wsRisk['!cols'] = [{ wch: 15 }, { wch: 12 }, { wch: 10 }, { wch: 15 }, { wch: 12 }, { wch: 12 }, { wch: 12 }, { wch: 12 }, { wch: 15 }, { wch: 10 }];
    XLSX.utils.book_append_sheet(wb, wsRisk, '风险评估');

    if (riskAssessment.riskFactors.length > 0) {
      const factorData = [
        ['风险类别', '风险描述', '严重程度', '受影响项'],
        ...riskAssessment.riskFactors.map(f => [
          f.category,
          f.description,
          getRiskLevelLabel(f.severity),
          f.affectedItems.join(', '),
        ]),
      ];
      const wsFactors = XLSX.utils.aoa_to_sheet(factorData);
      wsFactors['!cols'] = [{ wch: 15 }, { wch: 50 }, { wch: 12 }, { wch: 50 }];
      XLSX.utils.book_append_sheet(wb, wsFactors, '风险因子');
    }

    if (riskAssessment.recommendations.length > 0) {
      const recData = [
        ['序号', '变更建议'],
        ...riskAssessment.recommendations.map((rec, idx) => [idx + 1, rec]),
      ];
      const wsRecs = XLSX.utils.aoa_to_sheet(recData);
      wsRecs['!cols'] = [{ wch: 8 }, { wch: 80 }];
      XLSX.utils.book_append_sheet(wb, wsRecs, '变更建议');
    }
  }

  if (fieldDictionary) {
    const dictData: (string | number)[][] = [
      ['字段名', '数据类型', '是否可空', '默认值', '业务含义', '技术描述', '示例值', '数据模式'],
      [
        fieldDictionary.fieldName,
        fieldDictionary.dataType,
        fieldDictionary.nullable ? '是' : '否',
        fieldDictionary.defaultValue || '-',
        fieldDictionary.businessMeaning,
        fieldDictionary.description,
        fieldDictionary.sampleValues.join(', '),
        fieldDictionary.patterns.join(', '),
      ],
    ];
    const wsDict = XLSX.utils.aoa_to_sheet(dictData);
    wsDict['!cols'] = [{ wch: 15 }, { wch: 15 }, { wch: 10 }, { wch: 15 }, { wch: 50 }, { wch: 50 }, { wch: 30 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, wsDict, '数据字典');

    if (fieldDictionary.enumValues && fieldDictionary.enumValues.length > 0) {
      const enumData = [
        ['枚举值', '标签', '描述', '频率(%)'],
        ...fieldDictionary.enumValues.map(ev => [
          ev.value,
          ev.label,
          ev.description || '-',
          ev.frequency ?? '-',
        ]),
      ];
      const wsEnum = XLSX.utils.aoa_to_sheet(enumData);
      wsEnum['!cols'] = [{ wch: 15 }, { wch: 15 }, { wch: 30 }, { wch: 10 }];
      XLSX.utils.book_append_sheet(wb, wsEnum, '枚举值');
    }
  }

  const edgesData = [
    ['边ID', '源节点', '目标节点', '关系类型', '转换规则', '关联ETL任务'],
    ...result.graph.edges.map((e) => [
      e.id,
      e.source,
      e.target,
      e.type === 'direct' ? '直接' : e.type === 'transform' ? '转换' : '聚合',
      e.transformation || '-',
      e.etlTask || '-',
    ]),
  ];
  const ws8 = XLSX.utils.aoa_to_sheet(edgesData);
  ws8['!cols'] = [
    { wch: 15 }, { wch: 35 }, { wch: 35 }, { wch: 10 }, { wch: 30 }, { wch: 20 }
  ];
  XLSX.utils.book_append_sheet(wb, ws8, '血缘关系');

  XLSX.writeFile(wb, `lineage_analysis_${result.fieldName}_${Date.now()}.xlsx`);
};

export const exportReport = (
  result: AnalysisResult,
  format: 'json' | 'excel',
  riskAssessment?: ChangeRiskAssessment,
  fieldDictionary?: FieldDictionary
) => {
  if (format === 'json') {
    const exportData = {
      ...result,
      riskAssessment: riskAssessment || null,
      fieldDictionary: fieldDictionary || null,
    };
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lineage_analysis_${result.fieldName}_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } else {
    exportToExcel(result, riskAssessment, fieldDictionary);
  }
};
