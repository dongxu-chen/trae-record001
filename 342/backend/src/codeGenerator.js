const NODE_TYPES = {
  START: 'start',
  END: 'end',
  PROCESS: 'process',
  DECISION: 'decision',
  INPUT_OUTPUT: 'input_output',
};

function buildGraph(nodes, edges) {
  const nodeMap = new Map();
  nodes.forEach((n) => nodeMap.set(n.id, { ...n, incoming: [], outgoing: [] }));

  edges.forEach((e) => {
    const from = nodeMap.get(e.from);
    const to = nodeMap.get(e.to);
    if (from && to) {
      from.outgoing.push({ node: to, label: e.label || '' });
      to.incoming.push({ node: from, label: e.label || '' });
    }
  });

  return nodeMap;
}

function findStartNodes(nodes) {
  return nodes.filter((n) => n.type === NODE_TYPES.START);
}

function findEndNodes(nodes) {
  return nodes.filter((n) => n.type === NODE_TYPES.END);
}

function findDecisionNodes(nodes) {
  return nodes.filter((n) => n.type === NODE_TYPES.DECISION);
}

function sanitize(text) {
  if (!text) return '';
  return text.replace(/\s+/g, ' ').trim();
}

function toIdentifier(text, fallback) {
  const cleaned = sanitize(text).toUpperCase();
  const letters = cleaned.replace(/[^A-Z0-9_]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  if (letters && letters.length > 0) {
    return letters.slice(0, 40);
  }
  return fallback || 'STATE';
}

function findYesNoEdges(node) {
  const yesEdge = node.outgoing.find((e) => e.label && /是|yes|true|Y/i.test(e.label)) || node.outgoing[0];
  const noEdge = node.outgoing.find((e) => e.label && /否|no|false|N/i.test(e.label)) || node.outgoing[1];
  return { yesEdge, noEdge };
}

function getNodeStats(nodes) {
  const stats = { total: nodes.length, process: 0, decision: 0, io: 0 };
  nodes.forEach((n) => {
    if (n.type === NODE_TYPES.PROCESS) stats.process++;
    if (n.type === NODE_TYPES.DECISION) stats.decision++;
    if (n.type === NODE_TYPES.INPUT_OUTPUT) stats.io++;
  });
  return stats;
}

const LANGUAGES = ['pseudocode', 'plantuml', 'python', 'java', 'go', 'javascript'];

function toCamelCase(text, fallback) {
  const cleaned = sanitize(text).replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
  if (!cleaned) return fallback || 'func';
  const words = cleaned.split(/\s+/);
  return words[0].toLowerCase() + words.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
}

function toPascalCase(text, fallback) {
  const camel = toCamelCase(text, fallback);
  return camel.charAt(0).toUpperCase() + camel.slice(1);
}

function toSnakeCase(text, fallback) {
  const cleaned = sanitize(text).replace(/[^a-zA-Z0-9\s]/g, ' ').trim();
  if (!cleaned) return fallback || 'func';
  return cleaned.split(/\s+/).map(w => w.toLowerCase()).join('_');
}

function traverseFlowchart(nodeMap, startId, visitFn) {
  const visited = new Set();
  const stack = [startId];
  while (stack.length > 0) {
    const id = stack.pop();
    if (visited.has(id)) continue;
    visited.add(id);
    const node = nodeMap.get(id);
    if (!node) continue;
    visitFn(node);
    node.outgoing.slice().reverse().forEach(e => {
      if (!visited.has(e.node.id)) stack.push(e.node.id);
    });
  }
}

// ─────────────────────────────────────────────────────────────────────
// PYTHON GENERATOR (type hints, dataclasses, context managers)
// ─────────────────────────────────────────────────────────────────────

function generatePython(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const stats = getNodeStats(nodes);
  const startNodes = findStartNodes(nodes);
  const endNodes = findEndNodes(nodes);
  const decisions = findDecisionNodes(nodes);

  const lines = [];
  lines.push('# ════════════════════════════════════════════════════');
  lines.push('#  自动生成的流程图代码 (Python)');
  lines.push('# ════════════════════════════════════════════════════');
  lines.push('# 节点总数: ' + stats.total);
  lines.push('# 处理节点: ' + stats.process);
  lines.push('# 判断节点: ' + stats.decision);
  lines.push('# 输入输出: ' + stats.io);
  lines.push('# 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('from __future__ import annotations');
  lines.push('');
  lines.push('import time');
  lines.push('import logging');
  lines.push('from enum import Enum');
  lines.push('from typing import Any, Dict, Optional, Tuple');
  lines.push('from dataclasses import dataclass, field');
  lines.push('from contextlib import contextmanager');
  lines.push('');
  lines.push('logger = logging.getLogger(__name__)');
  lines.push('');
  lines.push('class ErrorCode(Enum):');
  lines.push('    INVALID_INPUT = 1001');
  lines.push('    TIMEOUT = 1002');
  lines.push('    PROCESSING_FAILED = 1003');
  lines.push('    MEMORY_ERROR = 1004');
  lines.push('    UNKNOWN_ERROR = 1005');
  lines.push('');
  lines.push('class FlowchartError(Exception):');
  lines.push('    def __init__(self, code: ErrorCode, message: str, cause: Optional[Exception] = None):');
  lines.push('        self.code = code');
  lines.push('        self.message = message');
  lines.push('        self.cause = cause');
  lines.push('        super().__init__(f"{code.name}: {message}")');
  lines.push('');
  lines.push('    def __str__(self) -> str:');
  lines.push('        return f"[{self.code.value}] {self.code.name}: {self.message}"');
  lines.push('');
  lines.push('@dataclass');
  lines.push('class ProcessingResult:');
  lines.push('    success: bool');
  lines.push('    data: Dict[str, Any] = field(default_factory=dict)');
  lines.push('    error: Optional[FlowchartError] = None');
  lines.push('    execution_time_ms: float = 0.0');
  lines.push('');
  lines.push('    def __post_init__(self):');
  lines.push('        if self.success and self.error:');
  lines.push('            raise ValueError("成功结果不能包含错误")');
  lines.push('        if not self.success and not self.error:');
  lines.push('            raise ValueError("失败结果必须包含错误")');
  lines.push('');
  lines.push('@contextmanager');
  lines.push('def timeout_scope(seconds: float):');
  lines.push('    start = time.monotonic()');
  lines.push('    try:');
  lines.push('        yield lambda: time.monotonic() - start > seconds');
  lines.push('    finally:');
  lines.push('        pass');
  lines.push('');
  lines.push('def process_flowchart(input_data: Any, *, max_retries: int = 3, timeout: float = 30.0) -> Dict[str, Any]:');
  lines.push('    """');
  lines.push('    执行流程图逻辑。');
  lines.push('    ');
  lines.push('    Args:');
  lines.push('        input_data: 输入数据');
  lines.push('        max_retries: 最大重试次数 (默认: 3)');
  lines.push('        timeout: 超时时间（秒）(默认: 30.0)');
  lines.push('    ');
  lines.push('    Returns:');
  lines.push('        处理结果字典');
  lines.push('    ');
  lines.push('    Raises:');
  lines.push('        FlowchartError: 处理失败时抛出');
  lines.push('    """');
  lines.push('    start_time = time.monotonic()');
  lines.push('    retry_count = 0');
  lines.push('    ');
  lines.push('    if input_data is None:');
  lines.push('        raise FlowchartError(ErrorCode.INVALID_INPUT, "输入不能为空")');
  lines.push('    ');
  lines.push('    if max_retries < 0:');
  lines.push('        raise FlowchartError(ErrorCode.INVALID_INPUT, "max_retries 不能为负数")');
  lines.push('    ');
  lines.push('    if timeout <= 0:');
  lines.push('        raise FlowchartError(ErrorCode.INVALID_INPUT, "timeout 必须大于 0")');
  lines.push('    ');
  lines.push('    result: Dict[str, Any] = {');
  lines.push('        "input": input_data,');
  lines.push('        "retries": 0,');
  lines.push('        "execution_path": [],');
  lines.push('        "timestamp": time.time(),');
  lines.push('    }');
  lines.push('    ');
  lines.push('    while retry_count < max_retries:');
  lines.push('        try:');
  lines.push('            logger.info(f"尝试第 {retry_count + 1} 次执行, 超时: {timeout}s")');
  lines.push('            ');
  lines.push('            with timeout_scope(timeout) as check_timeout:');
  lines.push('                context = {');
  lines.push('                    "input": input_data,');
  lines.push('                    "output": {},');
  lines.push('                    "start_time": start_time,');
  lines.push('                    "check_timeout": check_timeout,');
  lines.push('                }');
  lines.push('                ');

  const indentLevel = 4;
  const indent = (level) => '    '.repeat(level);

  if (startNodes.length > 0) {
    lines.push(indent(4) + '# 开始节点: ' + startNodes.map(n => sanitize(n.text) || n.id).join(', '));
    startNodes.forEach(startNode => {
      traverseFlowchart(nodeMap, startNode.id, (node) => {
        if (node.type === NODE_TYPES.START) {
          lines.push(indent(4) + '# [开始] ' + sanitize(node.text));
          lines.push(indent(4) + 'context["execution_path"].append("' + toSnakeCase(node.text, node.id) + '")');
        } else if (node.type === NODE_TYPES.END) {
          lines.push(indent(4) + '# [结束] ' + sanitize(node.text));
          lines.push(indent(4) + 'context["execution_path"].append("' + toSnakeCase(node.text, node.id) + '")');
          lines.push(indent(4) + 'result["output"] = context["output"]');
          lines.push(indent(4) + 'result["success"] = True');
          lines.push(indent(4) + 'result["execution_time_ms"] = (time.monotonic() - start_time) * 1000');
          lines.push(indent(4) + 'return result');
        } else if (node.type === NODE_TYPES.PROCESS) {
          const funcName = toSnakeCase(node.text, 'process_node');
          lines.push('');
          lines.push(indent(4) + '# [处理] ' + sanitize(node.text));
          lines.push(indent(4) + 'context["execution_path"].append("' + funcName + '")');
          lines.push(indent(4) + 'if check_timeout():');
          lines.push(indent(5) + 'raise FlowchartError(ErrorCode.TIMEOUT, "处理超时")');
          lines.push(indent(4) + 'context["output"]["' + funcName + '"] = ' + funcName + '(context)');
        } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
          const ioName = toSnakeCase(node.text, 'io_operation');
          lines.push('');
          lines.push(indent(4) + '# [输入输出] ' + sanitize(node.text));
          lines.push(indent(4) + 'context["execution_path"].append("' + ioName + '")');
          lines.push(indent(4) + 'context["output"]["' + ioName + '"] = ' + ioName + '(context)');
        } else if (node.type === NODE_TYPES.DECISION) {
          const { yesEdge, noEdge } = findYesNoEdges(node);
          const condName = toSnakeCase(node.text, 'condition');
          lines.push('');
          lines.push(indent(4) + '# [判断] ' + sanitize(node.text));
          lines.push(indent(4) + 'context["execution_path"].append("' + condName + '")');
          lines.push(indent(4) + 'if check_timeout():');
          lines.push(indent(5) + 'raise FlowchartError(ErrorCode.TIMEOUT, "判断超时")');
          lines.push(indent(4) + 'if ' + condName + '(context):');
          lines.push(indent(5) + '# 分支: ' + (yesEdge?.label || '是'));
          if (yesEdge && yesEdge.node) {
            lines.push(indent(5) + 'context["execution_path"].append("' + condName + '_yes")');
          }
          lines.push(indent(4) + 'else:');
          lines.push(indent(5) + '# 分支: ' + (noEdge?.label || '否'));
          if (noEdge && noEdge.node) {
            lines.push(indent(5) + 'context["execution_path"].append("' + condName + '_no")');
          }
        }
      });
    });
  }

  lines.push('');
  lines.push(indent(4) + 'raise FlowchartError(ErrorCode.PROCESSING_FAILED, "流程图执行未到达结束节点")');
  lines.push('');
  lines.push(indent(3) + 'except FlowchartError:');
  lines.push(indent(4) + 'raise');
  lines.push(indent(3) + 'except MemoryError as e:');
  lines.push(indent(4) + 'logger.error("内存错误: %s", e)');
  lines.push(indent(4) + 'raise FlowchartError(ErrorCode.MEMORY_ERROR, "内存不足", e)');
  lines.push(indent(3) + 'except TimeoutError as e:');
  lines.push(indent(4) + 'logger.error("超时错误: %s", e)');
  lines.push(indent(4) + 'retry_count += 1');
  lines.push(indent(4) + 'if retry_count < max_retries:');
  lines.push(indent(5) + 'wait_time = 0.1 * (2 ** (retry_count - 1))');
  lines.push(indent(5) + 'logger.info("等待 %.1fs 后重试", wait_time)');
  lines.push(indent(5) + 'time.sleep(wait_time)');
  lines.push(indent(4) + 'else:');
  lines.push(indent(5) + 'raise FlowchartError(ErrorCode.TIMEOUT, f"重试 {max_retries} 次后仍超时", e)');
  lines.push(indent(3) + 'except Exception as e:');
  lines.push(indent(4) + 'logger.error("未知错误: %s", e, exc_info=True)');
  lines.push(indent(4) + 'retry_count += 1');
  lines.push(indent(4) + 'if retry_count < max_retries:');
  lines.push(indent(5) + 'wait_time = 0.1 * (2 ** (retry_count - 1))');
  lines.push(indent(5) + 'logger.info("等待 %.1fs 后重试", wait_time)');
  lines.push(indent(5) + 'time.sleep(wait_time)');
  lines.push(indent(4) + 'else:');
  lines.push(indent(5) + 'raise FlowchartError(ErrorCode.UNKNOWN_ERROR, f"重试 {max_retries} 次后失败: {e}", e)');
  lines.push('');
  lines.push(indent(2) + 'raise FlowchartError(ErrorCode.UNKNOWN_ERROR, "未知处理错误")');

  lines.push('');
  lines.push('# ──────────────────────────────────────────────');
  lines.push('# 辅助函数 - 根据流程图节点生成');
  lines.push('# ──────────────────────────────────────────────');
  lines.push('');

  nodes.forEach((node, idx) => {
    if (node.type === NODE_TYPES.START || node.type === NODE_TYPES.END) return;
    const funcName = toSnakeCase(node.text, 'func_' + idx);
    if (node.type === NODE_TYPES.PROCESS) {
      lines.push('def ' + funcName + '(context: Dict[str, Any]) -> Dict[str, Any]:');
      lines.push('    """' + sanitize(node.text) + '"""');
      lines.push('    logger.info("执行: ' + sanitize(node.text) + '")');
      lines.push('    try:');
      lines.push('        result = {');
      lines.push('            "status": "completed",');
      lines.push('            "timestamp": time.time(),');
      lines.push('        }');
      lines.push('        # TODO: 实现具体业务逻辑');
      lines.push('        return result');
      lines.push('    except Exception as e:');
      lines.push('        logger.error("' + sanitize(node.text) + ' 失败: %s", e)');
      lines.push('        raise');
      lines.push('');
    } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
      lines.push('def ' + funcName + '(context: Dict[str, Any]) -> Dict[str, Any]:');
      lines.push('    """' + sanitize(node.text) + '"""');
      lines.push('    logger.info("IO操作: ' + sanitize(node.text) + '")');
      lines.push('    return {');
      lines.push('        "operation": "' + funcName + '",');
      lines.push('        "status": "completed",');
      lines.push('        "timestamp": time.time(),');
      lines.push('    }');
      lines.push('');
    } else if (node.type === NODE_TYPES.DECISION) {
      lines.push('def ' + funcName + '(context: Dict[str, Any]) -> bool:');
      lines.push('    """' + sanitize(node.text) + '"""');
      lines.push('    logger.info("判断: ' + sanitize(node.text) + '")');
      lines.push('    # TODO: 实现判断逻辑');
      lines.push('    return True');
      lines.push('');
    }
  });

  lines.push('');
  lines.push('if __name__ == "__main__":');
  lines.push('    logging.basicConfig(level=logging.INFO)');
  lines.push('    import sys');
  lines.push('    if len(sys.argv) > 1:');
  lines.push('        test_input = sys.argv[1]');
  lines.push('    else:');
  lines.push('        test_input = {"key": "test_value"}');
  lines.push('    try:');
  lines.push('        result = process_flowchart(test_input)');
  lines.push('        print("执行成功:", result)');
  lines.push('    except FlowchartError as e:');
  lines.push('        print("执行失败:", e)');
  lines.push('        sys.exit(1)');
  lines.push('');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// JAVA GENERATOR (Spring Boot style, SLF4J, Builder pattern)
// ─────────────────────────────────────────────────────────────────────

function generateJava(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const stats = getNodeStats(nodes);
  const startNodes = findStartNodes(nodes);
  const endNodes = findEndNodes(nodes);
  const decisions = findDecisionNodes(nodes);
  const className = 'FlowchartProcessor';

  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  自动生成的流程图代码 (Java 17)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('// 节点总数: ' + stats.total);
  lines.push('// 处理节点: ' + stats.process);
  lines.push('// 判断节点: ' + stats.decision);
  lines.push('// 输入输出: ' + stats.io);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('package com.flowchart.generated;');
  lines.push('');
  lines.push('import org.slf4j.Logger;');
  lines.push('import org.slf4j.LoggerFactory;');
  lines.push('');
  lines.push('import java.time.Duration;');
  lines.push('import java.time.Instant;');
  lines.push('import java.util.*;');
  lines.push('import java.util.concurrent.TimeoutException;');
  lines.push('import java.util.function.Predicate;');
  lines.push('');
  lines.push('public class ' + className + ' {');
  lines.push('');
  lines.push('    private static final Logger log = LoggerFactory.getLogger(' + className + '.class);');
  lines.push('');
  lines.push('    public enum ErrorCode {');
  lines.push('        INVALID_INPUT(1001),');
  lines.push('        TIMEOUT(1002),');
  lines.push('        PROCESSING_FAILED(1003),');
  lines.push('        MEMORY_ERROR(1004),');
  lines.push('        UNKNOWN_ERROR(1005);');
  lines.push('');
  lines.push('        private final int code;');
  lines.push('        ErrorCode(int code) { this.code = code; }');
  lines.push('        public int getCode() { return code; }');
  lines.push('    }');
  lines.push('');
  lines.push('    public static class FlowchartException extends RuntimeException {');
  lines.push('        private final ErrorCode code;');
  lines.push('        public FlowchartException(ErrorCode code, String message) {');
  lines.push('            super(message);');
  lines.push('            this.code = code;');
  lines.push('        }');
  lines.push('        public FlowchartException(ErrorCode code, String message, Throwable cause) {');
  lines.push('            super(message, cause);');
  lines.push('            this.code = code;');
  lines.push('        }');
  lines.push('        public ErrorCode getErrorCode() { return code; }');
  lines.push('    }');
  lines.push('');
  lines.push('    public record ProcessingResult(');
  lines.push('        boolean success,');
  lines.push('        Map<String, Object> data,');
  lines.push('        FlowchartException error,');
  lines.push('        long executionTimeMs');
  lines.push('    ) {');
  lines.push('        public static ProcessingResult success(Map<String, Object> data, long executionTimeMs) {');
  lines.push('            return new ProcessingResult(true, data, null, executionTimeMs);');
  lines.push('        }');
  lines.push('        public static ProcessingResult failure(FlowchartException error, long executionTimeMs) {');
  lines.push('            return new ProcessingResult(false, Collections.emptyMap(), error, executionTimeMs);');
  lines.push('        }');
  lines.push('    }');
  lines.push('');
  lines.push('    private final int maxRetries;');
  lines.push('    private final Duration timeout;');
  lines.push('');
  lines.push('    private ' + className + '(Builder builder) {');
  lines.push('        this.maxRetries = builder.maxRetries;');
  lines.push('        this.timeout = builder.timeout;');
  lines.push('    }');
  lines.push('');
  lines.push('    public static Builder builder() {');
  lines.push('        return new Builder();');
  lines.push('    }');
  lines.push('');
  lines.push('    public static class Builder {');
  lines.push('        private int maxRetries = 3;');
  lines.push('        private Duration timeout = Duration.ofSeconds(30);');
  lines.push('');
  lines.push('        public Builder withMaxRetries(int maxRetries) {');
  lines.push('            if (maxRetries < 0) throw new IllegalArgumentException("maxRetries must be >= 0");');
  lines.push('            this.maxRetries = maxRetries;');
  lines.push('            return this;');
  lines.push('        }');
  lines.push('');
  lines.push('        public Builder withTimeout(Duration timeout) {');
  lines.push('            if (timeout == null || timeout.isZero() || timeout.isNegative()) {');
  lines.push('                throw new IllegalArgumentException("timeout must be positive");');
  lines.push('            }');
  lines.push('            this.timeout = timeout;');
  lines.push('            return this;');
  lines.push('        }');
  lines.push('');
  lines.push('        public ' + className + ' build() {');
  lines.push('            return new ' + className + '(this);');
  lines.push('        }');
  lines.push('    }');
  lines.push('');
  lines.push('    public ProcessingResult process(Object inputData) {');
  lines.push('        Instant start = Instant.now();');
  lines.push('        int retryCount = 0;');
  lines.push('');
  lines.push('        if (inputData == null) {');
  lines.push('            throw new FlowchartException(ErrorCode.INVALID_INPUT, "输入不能为空");');
  lines.push('        }');
  lines.push('');
  lines.push('        Map<String, Object> result = new LinkedHashMap<>();');
  lines.push('        result.put("input", inputData);');
  lines.push('        result.put("timestamp", System.currentTimeMillis());');
  lines.push('');
  lines.push('        while (retryCount <= maxRetries) {');
  lines.push('            try {');
  lines.push('                log.info("尝试第 {} 次执行, 超时: {}", retryCount + 1, timeout);');
  lines.push('');
  lines.push('                Instant deadline = start.plus(timeout);');
  lines.push('                Predicate<Void> checkTimeout = v -> Instant.now().isAfter(deadline);');
  lines.push('');
  lines.push('                Map<String, Object> context = new LinkedHashMap<>();');
  lines.push('                context.put("input", inputData);');
  lines.push('                context.put("output", new LinkedHashMap<String, Object>());');
  lines.push('                context.put("executionPath", new ArrayList<String>());');
  lines.push('');

  const indent = (level) => '    '.repeat(level);

  if (startNodes.length > 0) {
    lines.push(indent(4) + '// 开始节点: ' + startNodes.map(n => sanitize(n.text) || n.id).join(', '));
    startNodes.forEach(startNode => {
      traverseFlowchart(nodeMap, startNode.id, (node) => {
        if (node.type === NODE_TYPES.START) {
          lines.push(indent(4) + '// [开始] ' + sanitize(node.text));
          lines.push(indent(4) + 'context.put("executionPath", addToPath(context, "' + toCamelCase(node.text, node.id) + '"));');
        } else if (node.type === NODE_TYPES.END) {
          lines.push(indent(4) + '// [结束] ' + sanitize(node.text));
          lines.push(indent(4) + 'context.put("executionPath", addToPath(context, "' + toCamelCase(node.text, node.id) + '"));');
          lines.push(indent(4) + 'long execMs = Duration.between(start, Instant.now()).toMillis();');
          lines.push(indent(4) + '@SuppressWarnings("unchecked")');
          lines.push(indent(4) + 'Map<String, Object> output = (Map<String, Object>) context.get("output");');
          lines.push(indent(4) + 'return ProcessingResult.success(output, execMs);');
        } else if (node.type === NODE_TYPES.PROCESS) {
          const methodName = toCamelCase(node.text, 'processNode');
          lines.push('');
          lines.push(indent(4) + '// [处理] ' + sanitize(node.text));
          lines.push(indent(4) + 'context.put("executionPath", addToPath(context, "' + methodName + '"));');
          lines.push(indent(4) + 'if (checkTimeout.test(null)) {');
          lines.push(indent(5) + 'throw new FlowchartException(ErrorCode.TIMEOUT, "处理超时");');
          lines.push(indent(4) + '}');
          lines.push(indent(4) + '@SuppressWarnings("unchecked")');
          lines.push(indent(4) + 'Map<String, Object> out = (Map<String, Object>) context.get("output");');
          lines.push(indent(4) + 'out.put("' + methodName + '", ' + methodName + '(context));');
        } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
          const ioName = toCamelCase(node.text, 'ioOperation');
          lines.push('');
          lines.push(indent(4) + '// [输入输出] ' + sanitize(node.text));
          lines.push(indent(4) + 'context.put("executionPath", addToPath(context, "' + ioName + '"));');
          lines.push(indent(4) + '@SuppressWarnings("unchecked")');
          lines.push(indent(4) + 'Map<String, Object> outIo = (Map<String, Object>) context.get("output");');
          lines.push(indent(4) + 'outIo.put("' + ioName + '", ' + ioName + '(context));');
        } else if (node.type === NODE_TYPES.DECISION) {
          const { yesEdge, noEdge } = findYesNoEdges(node);
          const condName = toCamelCase(node.text, 'condition');
          lines.push('');
          lines.push(indent(4) + '// [判断] ' + sanitize(node.text));
          lines.push(indent(4) + 'context.put("executionPath", addToPath(context, "' + condName + '"));');
          lines.push(indent(4) + 'if (checkTimeout.test(null)) {');
          lines.push(indent(5) + 'throw new FlowchartException(ErrorCode.TIMEOUT, "判断超时");');
          lines.push(indent(4) + '}');
          lines.push(indent(4) + 'if (' + condName + '(context)) {');
          lines.push(indent(5) + '// 分支: ' + (yesEdge?.label || '是'));
          if (yesEdge && yesEdge.node) {
            lines.push(indent(5) + 'context.put("executionPath", addToPath(context, "' + condName + 'Yes"));');
          }
          lines.push(indent(4) + '} else {');
          lines.push(indent(5) + '// 分支: ' + (noEdge?.label || '否'));
          if (noEdge && noEdge.node) {
            lines.push(indent(5) + 'context.put("executionPath", addToPath(context, "' + condName + 'No"));');
          }
          lines.push(indent(4) + '}');
        }
      });
    });
  }

  lines.push('');
  lines.push(indent(4) + 'throw new FlowchartException(ErrorCode.PROCESSING_FAILED, "流程图执行未到达结束节点");');
  lines.push('');
  lines.push(indent(3) + '} catch (FlowchartException e) {');
  lines.push(indent(4) + 'throw e;');
  lines.push(indent(3) + '} catch (OutOfMemoryError e) {');
  lines.push(indent(4) + 'log.error("内存错误", e);');
  lines.push(indent(4) + 'throw new FlowchartException(ErrorCode.MEMORY_ERROR, "内存不足", e);');
  lines.push(indent(3) + '} catch (TimeoutException e) {');
  lines.push(indent(4) + 'log.error("超时错误", e);');
  lines.push(indent(4) + 'retryCount++;');
  lines.push(indent(4) + 'if (retryCount <= maxRetries) {');
  lines.push(indent(5) + 'long waitMs = (long) (100 * Math.pow(2, retryCount - 1));');
  lines.push(indent(5) + 'log.info("等待 {}ms 后重试", waitMs);');
  lines.push(indent(5) + 'Thread.sleep(waitMs);');
  lines.push(indent(4) + '} else {');
  lines.push(indent(5) + 'throw new FlowchartException(ErrorCode.TIMEOUT, "重试 " + maxRetries + " 次后仍超时", e);');
  lines.push(indent(4) + '}');
  lines.push(indent(3) + '} catch (Exception e) {');
  lines.push(indent(4) + 'log.error("未知错误", e);');
  lines.push(indent(4) + 'retryCount++;');
  lines.push(indent(4) + 'if (retryCount <= maxRetries) {');
  lines.push(indent(5) + 'long waitMs = (long) (100 * Math.pow(2, retryCount - 1));');
  lines.push(indent(5) + 'log.info("等待 {}ms 后重试", waitMs);');
  lines.push(indent(5) + 'Thread.sleep(waitMs);');
  lines.push(indent(4) + '} else {');
  lines.push(indent(5) + 'throw new FlowchartException(ErrorCode.UNKNOWN_ERROR, "重试 " + maxRetries + " 次后失败: " + e.getMessage(), e);');
  lines.push(indent(4) + '}');
  lines.push(indent(3) + '}');
  lines.push(indent(2) + '}');
  lines.push('');
  lines.push(indent(2) + 'throw new FlowchartException(ErrorCode.UNKNOWN_ERROR, "未知处理错误");');
  lines.push(indent(1) + '}');
  lines.push('');
  lines.push(indent(1) + '@SuppressWarnings("unchecked")');
  lines.push(indent(1) + 'private List<String> addToPath(Map<String, Object> context, String step) {');
  lines.push(indent(2) + 'List<String> path = (List<String>) context.getOrDefault("executionPath", new ArrayList<>());');
  lines.push(indent(2) + 'path.add(step);');
  lines.push(indent(2) + 'return path;');
  lines.push(indent(1) + '}');
  lines.push('');

  nodes.forEach((node, idx) => {
    if (node.type === NODE_TYPES.START || node.type === NODE_TYPES.END) return;
    const methodName = toCamelCase(node.text, 'func' + idx);
    if (node.type === NODE_TYPES.PROCESS) {
      lines.push(indent(1) + 'private Map<String, Object> ' + methodName + '(Map<String, Object> context) {');
      lines.push(indent(2) + 'log.info("执行: ' + sanitize(node.text) + '");');
      lines.push(indent(2) + 'try {');
      lines.push(indent(3) + 'Map<String, Object> result = new LinkedHashMap<>();');
      lines.push(indent(3) + 'result.put("status", "completed");');
      lines.push(indent(3) + 'result.put("timestamp", System.currentTimeMillis());');
      lines.push(indent(3) + '// TODO: 实现具体业务逻辑');
      lines.push(indent(3) + 'return result;');
      lines.push(indent(2) + '} catch (Exception e) {');
      lines.push(indent(3) + 'log.error("' + sanitize(node.text) + ' 失败", e);');
      lines.push(indent(3) + 'throw e;');
      lines.push(indent(2) + '}');
      lines.push(indent(1) + '}');
      lines.push('');
    } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
      lines.push(indent(1) + 'private Map<String, Object> ' + methodName + '(Map<String, Object> context) {');
      lines.push(indent(2) + 'log.info("IO操作: ' + sanitize(node.text) + '");');
      lines.push(indent(2) + 'Map<String, Object> result = new LinkedHashMap<>();');
      lines.push(indent(2) + 'result.put("operation", "' + methodName + '");');
      lines.push(indent(2) + 'result.put("status", "completed");');
      lines.push(indent(2) + 'result.put("timestamp", System.currentTimeMillis());');
      lines.push(indent(2) + 'return result;');
      lines.push(indent(1) + '}');
      lines.push('');
    } else if (node.type === NODE_TYPES.DECISION) {
      lines.push(indent(1) + 'private boolean ' + methodName + '(Map<String, Object> context) {');
      lines.push(indent(2) + 'log.info("判断: ' + sanitize(node.text) + '");');
      lines.push(indent(2) + '// TODO: 实现判断逻辑');
      lines.push(indent(2) + 'return true;');
      lines.push(indent(1) + '}');
      lines.push('');
    }
  });

  lines.push(indent(1) + 'public static void main(String[] args) {');
  lines.push(indent(2) + className + ' processor = ' + className + '.builder()');
  lines.push(indent(3) + '.withMaxRetries(3)');
  lines.push(indent(3) + '.withTimeout(Duration.ofSeconds(30))');
  lines.push(indent(3) + '.build();');
  lines.push('');
  lines.push(indent(2) + 'Object testInput = args.length > 0 ? args[0] : Map.of("key", "testValue");');
  lines.push('');
  lines.push(indent(2) + 'try {');
  lines.push(indent(3) + 'ProcessingResult result = processor.process(testInput);');
  lines.push(indent(3) + 'System.out.println("执行成功: " + result);');
  lines.push(indent(2) + '} catch (FlowchartException e) {');
  lines.push(indent(3) + 'System.err.println("执行失败: " + e.getErrorCode() + ": " + e.getMessage());');
  lines.push(indent(3) + 'System.exit(1);');
  lines.push(indent(2) + '}');
  lines.push(indent(1) + '}');
  lines.push('}');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// GO GENERATOR (context, error wrapping, functional options)
// ─────────────────────────────────────────────────────────────────────

function generateGo(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const stats = getNodeStats(nodes);
  const startNodes = findStartNodes(nodes);
  const endNodes = findEndNodes(nodes);
  const decisions = findDecisionNodes(nodes);

  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  自动生成的流程图代码 (Go 1.21)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('// 节点总数: ' + stats.total);
  lines.push('// 处理节点: ' + stats.process);
  lines.push('// 判断节点: ' + stats.decision);
  lines.push('// 输入输出: ' + stats.io);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('package flowchart');
  lines.push('');
  lines.push('import (');
  lines.push('\t"context"');
  lines.push('\t"errors"');
  lines.push('\t"fmt"');
  lines.push('\t"log"');
  lines.push('\t"math"');
  lines.push('\t"os"');
  lines.push('\t"sync"');
  lines.push('\t"time"');
  lines.push(')');
  lines.push('');
  lines.push('type ErrorCode int');
  lines.push('');
  lines.push('const (');
  lines.push('\tErrorCodeInvalidInput ErrorCode = 1001');
  lines.push('\tErrorCodeTimeout      ErrorCode = 1002');
  lines.push('\tErrorCodeProcessing   ErrorCode = 1003');
  lines.push('\tErrorCodeMemory       ErrorCode = 1004');
  lines.push('\tErrorCodeUnknown      ErrorCode = 1005');
  lines.push(')');
  lines.push('');
  lines.push('type FlowchartError struct {');
  lines.push('\tCode    ErrorCode');
  lines.push('\tMessage string');
  lines.push('\tCause   error');
  lines.push('}');
  lines.push('');
  lines.push('func (e *FlowchartError) Error() string {');
  lines.push('\tif e.Cause != nil {');
  lines.push('\t\treturn fmt.Sprintf("[%d] %s: %s (cause: %v)", e.Code, e.codeName(), e.Message, e.Cause)');
  lines.push('\t}');
  lines.push('\treturn fmt.Sprintf("[%d] %s: %s", e.Code, e.codeName(), e.Message)');
  lines.push('}');
  lines.push('');
  lines.push('func (e *FlowchartError) Unwrap() error {');
  lines.push('\treturn e.Cause');
  lines.push('}');
  lines.push('');
  lines.push('func (e *FlowchartError) codeName() string {');
  lines.push('\tswitch e.Code {');
  lines.push('\tcase ErrorCodeInvalidInput: return "INVALID_INPUT"');
  lines.push('\tcase ErrorCodeTimeout: return "TIMEOUT"');
  lines.push('\tcase ErrorCodeProcessing: return "PROCESSING_FAILED"');
  lines.push('\tcase ErrorCodeMemory: return "MEMORY_ERROR"');
  lines.push('\tdefault: return "UNKNOWN_ERROR"');
  lines.push('\t}');
  lines.push('}');
  lines.push('');
  lines.push('func NewFlowchartError(code ErrorCode, msg string, cause error) *FlowchartError {');
  lines.push('\treturn &FlowchartError{Code: code, Message: msg, Cause: cause}');
  lines.push('}');
  lines.push('');
  lines.push('type ProcessingResult struct {');
  lines.push('\tSuccess          bool                   `json:"success"`');
  lines.push('\tData             map[string]interface{} `json:"data"`');
  lines.push('\tError            *FlowchartError        `json:"error,omitempty"`');
  lines.push('\tExecutionTimeMs  int64                  `json:"execution_time_ms"`');
  lines.push('\tmu               sync.Mutex');
  lines.push('}');
  lines.push('');
  lines.push('type Processor struct {');
  lines.push('\tmaxRetries int');
  lines.push('\ttimeout    time.Duration');
  lines.push('\tlogger     *log.Logger');
  lines.push('}');
  lines.push('');
  lines.push('type Option func(*Processor)');
  lines.push('');
  lines.push('func WithMaxRetries(n int) Option {');
  lines.push('\treturn func(p *Processor) {');
  lines.push('\t\tif n < 0 { n = 0 }');
  lines.push('\t\tp.maxRetries = n');
  lines.push('\t}');
  lines.push('}');
  lines.push('');
  lines.push('func WithTimeout(d time.Duration) Option {');
  lines.push('\treturn func(p *Processor) {');
  lines.push('\t\tif d <= 0 { d = 30 * time.Second }');
  lines.push('\t\tp.timeout = d');
  lines.push('\t}');
  lines.push('}');
  lines.push('');
  lines.push('func WithLogger(l *log.Logger) Option {');
  lines.push('\treturn func(p *Processor) {');
  lines.push('\t\tif l != nil { p.logger = l }');
  lines.push('\t}');
  lines.push('}');
  lines.push('');
  lines.push('func NewProcessor(opts ...Option) *Processor {');
  lines.push('\tp := &Processor{');
  lines.push('\t\tmaxRetries: 3,');
  lines.push('\t\ttimeout:    30 * time.Second,');
  lines.push('\t\tlogger:     log.New(os.Stderr, "[flowchart] ", log.LstdFlags),');
  lines.push('\t}');
  lines.push('\tfor _, opt := range opts {');
  lines.push('\t\topt(p)');
  lines.push('\t}');
  lines.push('\treturn p');
  lines.push('}');
  lines.push('');
  lines.push('func (p *Processor) Process(ctx context.Context, inputData interface{}) (*ProcessingResult, error) {');
  lines.push('\tstart := time.Now()');
  lines.push('\tretryCount := 0');
  lines.push('');
  lines.push('\tif inputData == nil {');
  lines.push('\t\treturn nil, NewFlowchartError(ErrorCodeInvalidInput, "输入不能为空", nil)');
  lines.push('\t}');
  lines.push('');
  lines.push('\tresult := &ProcessingResult{');
  lines.push('\t\tData: map[string]interface{}{');
  lines.push('\t\t\t"input":     inputData,');
  lines.push('\t\t\t"timestamp": time.Now().Unix(),');
  lines.push('\t\t},');
  lines.push('\t}');
  lines.push('');
  lines.push('\tfor retryCount <= p.maxRetries {');
  lines.push('\t\tp.logger.Printf("尝试第 %d 次执行, 超时: %v", retryCount+1, p.timeout)');
  lines.push('');
  lines.push('\t\tctxTimeout, cancel := context.WithTimeout(ctx, p.timeout)');
  lines.push('\t\tdefer cancel()');
  lines.push('');
  lines.push('\t\tcontextMap := map[string]interface{}{');
  lines.push('\t\t\t"input":          inputData,');
  lines.push('\t\t\t"output":         map[string]interface{}{},');
  lines.push('\t\t\t"execution_path": []string{},');
  lines.push('\t\t}');
  lines.push('');

  const indent = (level) => '\t'.repeat(level);

  if (startNodes.length > 0) {
    lines.push(indent(3) + '// 开始节点: ' + startNodes.map(n => sanitize(n.text) || n.id).join(', '));
    startNodes.forEach(startNode => {
      traverseFlowchart(nodeMap, startNode.id, (node) => {
        if (node.type === NODE_TYPES.START) {
          lines.push(indent(3) + '// [开始] ' + sanitize(node.text));
          lines.push(indent(3) + 'contextMap = addToPath(contextMap, "' + toSnakeCase(node.text, node.id) + '")');
        } else if (node.type === NODE_TYPES.END) {
          lines.push(indent(3) + '// [结束] ' + sanitize(node.text));
          lines.push(indent(3) + 'contextMap = addToPath(contextMap, "' + toSnakeCase(node.text, node.id) + '")');
          lines.push(indent(3) + 'result.Success = true');
          lines.push(indent(3) + 'result.Data["output"] = contextMap["output"]');
          lines.push(indent(3) + 'result.Data["execution_path"] = contextMap["execution_path"]');
          lines.push(indent(3) + 'result.ExecutionTimeMs = time.Since(start).Milliseconds()');
          lines.push(indent(3) + 'return result, nil');
        } else if (node.type === NODE_TYPES.PROCESS) {
          const funcName = toSnakeCase(node.text, 'process_node');
          lines.push('');
          lines.push(indent(3) + '// [处理] ' + sanitize(node.text));
          lines.push(indent(3) + 'contextMap = addToPath(contextMap, "' + funcName + '")');
          lines.push(indent(3) + 'select {');
          lines.push(indent(4) + 'case <-ctxTimeout.Done():');
          lines.push(indent(5) + 'return nil, NewFlowchartError(ErrorCodeTimeout, "处理超时", ctxTimeout.Err())');
          lines.push(indent(4) + 'default:');
          lines.push(indent(5) + '// 继续执行');
          lines.push(indent(3) + '}');
          lines.push(indent(3) + 'out, err := p.' + toPascalCase(funcName, 'Func') + '(ctxTimeout, contextMap)');
          lines.push(indent(3) + 'if err != nil { return nil, err }');
          lines.push(indent(3) + 'contextMap["output"].(map[string]interface{})["' + funcName + '"] = out');
        } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
          const ioName = toSnakeCase(node.text, 'io_operation');
          lines.push('');
          lines.push(indent(3) + '// [输入输出] ' + sanitize(node.text));
          lines.push(indent(3) + 'contextMap = addToPath(contextMap, "' + ioName + '")');
          lines.push(indent(3) + 'out, err := p.' + toPascalCase(ioName, 'IO') + '(ctxTimeout, contextMap)');
          lines.push(indent(3) + 'if err != nil { return nil, err }');
          lines.push(indent(3) + 'contextMap["output"].(map[string]interface{})["' + ioName + '"] = out');
        } else if (node.type === NODE_TYPES.DECISION) {
          const { yesEdge, noEdge } = findYesNoEdges(node);
          const condName = toSnakeCase(node.text, 'condition');
          lines.push('');
          lines.push(indent(3) + '// [判断] ' + sanitize(node.text));
          lines.push(indent(3) + 'contextMap = addToPath(contextMap, "' + condName + '")');
          lines.push(indent(3) + 'select {');
          lines.push(indent(4) + 'case <-ctxTimeout.Done():');
          lines.push(indent(5) + 'return nil, NewFlowchartError(ErrorCodeTimeout, "判断超时", ctxTimeout.Err())');
          lines.push(indent(4) + 'default:');
          lines.push(indent(5) + '// 继续执行');
          lines.push(indent(3) + '}');
          lines.push(indent(3) + 'if p.' + toPascalCase(condName, 'Cond') + '(ctxTimeout, contextMap) {');
          lines.push(indent(4) + '// 分支: ' + (yesEdge?.label || '是'));
          if (yesEdge && yesEdge.node) {
            lines.push(indent(4) + 'contextMap = addToPath(contextMap, "' + condName + '_yes")');
          }
          lines.push(indent(3) + '} else {');
          lines.push(indent(4) + '// 分支: ' + (noEdge?.label || '否'));
          if (noEdge && noEdge.node) {
            lines.push(indent(4) + 'contextMap = addToPath(contextMap, "' + condName + '_no")');
          }
          lines.push(indent(3) + '}');
        }
      });
    });
  }

  lines.push('');
  lines.push(indent(3) + 'return nil, NewFlowchartError(ErrorCodeProcessing, "流程图执行未到达结束节点", nil)');
  lines.push('');
  lines.push(indent(2) + '// 错误处理 - Go 风格错误检查');
  lines.push(indent(2) + 'var fcErr *FlowchartError');
  lines.push(indent(2) + 'if errors.As(err, &fcErr) {');
  lines.push(indent(3) + 'return nil, err');
  lines.push(indent(2) + '}');
  lines.push('');
  lines.push(indent(2) + 'retryCount++');
  lines.push(indent(2) + 'if retryCount <= p.maxRetries {');
  lines.push(indent(3) + 'waitMs := time.Duration(100*math.Pow(2, float64(retryCount-1))) * time.Millisecond');
  lines.push(indent(3) + 'p.logger.Printf("等待 %v 后重试", waitMs)');
  lines.push(indent(3) + 'select {');
  lines.push(indent(4) + 'case <-ctx.Done():');
  lines.push(indent(5) + 'return nil, ctx.Err()');
  lines.push(indent(4) + 'case <-time.After(waitMs):');
  lines.push(indent(3) + '}');
  lines.push(indent(2) + '} else {');
  lines.push(indent(3) + 'return nil, NewFlowchartError(ErrorCodeUnknown, fmt.Sprintf("重试 %d 次后失败: %v", p.maxRetries, err), err)');
  lines.push(indent(2) + '}');
  lines.push(indent(1) + '}');
  lines.push('');
  lines.push(indent(1) + 'return nil, NewFlowchartError(ErrorCodeUnknown, "未知处理错误", nil)');
  lines.push('}');
  lines.push('');
  lines.push(indent(1) + 'func addToPath(ctx map[string]interface{}, step string) map[string]interface{} {');
  lines.push(indent(2) + 'path, _ := ctx["execution_path"].([]string)');
  lines.push(indent(2) + 'ctx["execution_path"] = append(path, step)');
  lines.push(indent(2) + 'return ctx');
  lines.push(indent(1) + '}');
  lines.push('');

  nodes.forEach((node, idx) => {
    if (node.type === NODE_TYPES.START || node.type === NODE_TYPES.END) return;
    const funcName = toPascalCase(node.text, 'Func' + idx);
    if (node.type === NODE_TYPES.PROCESS) {
      lines.push(indent(1) + 'func (p *Processor) ' + funcName + '(ctx context.Context, contextMap map[string]interface{}) (map[string]interface{}, error) {');
      lines.push(indent(2) + 'p.logger.Printf("执行: ' + sanitize(node.text) + '")');
      lines.push(indent(2) + 'select {');
      lines.push(indent(3) + 'case <-ctx.Done():');
      lines.push(indent(4) + 'return nil, NewFlowchartError(ErrorCodeTimeout, "' + sanitize(node.text) + ' 超时", ctx.Err())');
      lines.push(indent(3) + 'default:');
      lines.push(indent(2) + '}');
      lines.push(indent(2) + 'result := map[string]interface{}{');
      lines.push(indent(3) + '"status":     "completed",');
      lines.push(indent(3) + '"timestamp": time.Now().Unix(),');
      lines.push(indent(2) + '}');
      lines.push(indent(2) + '// TODO: 实现具体业务逻辑');
      lines.push(indent(2) + 'return result, nil');
      lines.push(indent(1) + '}');
      lines.push('');
    } else if (node.type === NODE_TYPES.INPUT_OUTPUT) {
      lines.push(indent(1) + 'func (p *Processor) ' + funcName + '(ctx context.Context, contextMap map[string]interface{}) (map[string]interface{}, error) {');
      lines.push(indent(2) + 'p.logger.Printf("IO操作: ' + sanitize(node.text) + '")');
      lines.push(indent(2) + 'result := map[string]interface{}{');
      lines.push(indent(3) + '"operation": "' + toSnakeCase(node.text, 'io') + '",');
      lines.push(indent(3) + '"status":     "completed",');
      lines.push(indent(3) + '"timestamp": time.Now().Unix(),');
      lines.push(indent(2) + '}');
      lines.push(indent(2) + 'return result, nil');
      lines.push(indent(1) + '}');
      lines.push('');
    } else if (node.type === NODE_TYPES.DECISION) {
      lines.push(indent(1) + 'func (p *Processor) ' + funcName + '(ctx context.Context, contextMap map[string]interface{}) bool {');
      lines.push(indent(2) + 'p.logger.Printf("判断: ' + sanitize(node.text) + '")');
      lines.push(indent(2) + '// TODO: 实现判断逻辑');
      lines.push(indent(2) + 'return true');
      lines.push(indent(1) + '}');
      lines.push('');
    }
  });

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// PSEUDOCODE GENERATOR (template-based)
// ─────────────────────────────────────────────────────────────────────

function generatePseudocode(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const starts = findStartNodes(nodes);
  const ends = findEndNodes(nodes);
  const stats = getNodeStats(nodes);

  if (starts.length === 0) return '// ⚠ 未找到开始节点，无法生成伪代码';

  const visited = new Set();
  const printedEnd = new Set();
  const lines = [];

  lines.push('// ════════════════════════════════════════════');
  lines.push('//  流程图 → 伪代码');
  lines.push('// ════════════════════════════════════════════');
  lines.push(`// 节点总数: ${stats.total}  (处理:${stats.process}  判断:${stats.decision}  输入输出:${stats.io})`);
  lines.push(`// 开始节点: ${starts.length}  |  结束节点: ${ends.length}`);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');

  lines.push('// ── 输入参数 ──');
  lines.push('// INPUT: 待处理数据');
  lines.push('// OUTPUT: 处理结果');
  lines.push('// EXCEPTIONS: 参数为空、格式错误、超时');
  lines.push('');

  lines.push('// ── 边界条件检查 ──');
  lines.push('IF input IS NULL THEN');
  lines.push('    RAISE ERROR("输入不能为空")');
  lines.push('END IF');
  lines.push('');
  lines.push('// ── 主流程 ──');

  function traverse(node, indent = 0) {
    const prefix = '    '.repeat(indent);
    const key = node.id;

    if (node.type === NODE_TYPES.END) {
      if (!printedEnd.has(key)) {
        printedEnd.add(key);
        const endText = sanitize(node.text) || '流程结束';
        lines.push(`${prefix}// ── 结束 ──`);
        lines.push(`${prefix}RETURN ${endText}`);
      } else {
        lines.push(`${prefix}// ── [汇合到结束] ──`);
      }
      return;
    }

    if (visited.has(key)) {
      lines.push(`${prefix}// ── [回到 ${sanitize(node.text) || node.id}] ──`);
      return;
    }
    visited.add(key);

    switch (node.type) {
      case NODE_TYPES.START:
        lines.push(`${prefix}// ── 开始 ──`);
        lines.push(`${prefix}BEGIN: ${sanitize(node.text) || '流程开始'}`);
        lines.push(`${prefix}TRY`);
        node.outgoing.forEach((e) => traverse(e.node, indent + 1));
        lines.push(`${prefix}CATCH ERROR`);
        lines.push(`${prefix}    LOG("流程异常: " + ERROR.MESSAGE)`);
        lines.push(`${prefix}    RAISE`);
        lines.push(`${prefix}END TRY`);
        break;

      case NODE_TYPES.PROCESS:
        lines.push(`${prefix}// ── 处理步骤 ──`);
        lines.push(`${prefix}EXECUTE: ${sanitize(node.text) || '处理步骤'}`);
        node.outgoing.forEach((e) => traverse(e.node, indent));
        break;

      case NODE_TYPES.DECISION: {
        const question = sanitize(node.text) || '判断条件';
        lines.push(`${prefix}// ── 判断分支 ──`);
        lines.push(`${prefix}DECISION: ${question}`);
        lines.push(`${prefix}IF (${question}) THEN`);
        if (node.outgoing.length >= 2) {
          const { yesEdge, noEdge } = findYesNoEdges(node);
          const yesLabel = sanitize(yesEdge?.label) || '是';
          const noLabel = sanitize(noEdge?.label) || '否';
          lines.push(`${prefix}    // 分支: ${yesLabel}/True`);
          if (yesEdge) traverse(yesEdge.node, indent + 1);
          lines.push(`${prefix}ELSE`);
          lines.push(`${prefix}    // 分支: ${noLabel}/False`);
          if (noEdge) traverse(noEdge.node, indent + 1);
        } else {
          node.outgoing.forEach((e) => traverse(e.node, indent + 1));
        }
        lines.push(`${prefix}END IF`);
        break;
      }

      case NODE_TYPES.INPUT_OUTPUT:
        lines.push(`${prefix}// ── 输入/输出 ──`);
        lines.push(`${prefix}IO_OPERATION: ${sanitize(node.text) || '数据'}`);
        node.outgoing.forEach((e) => traverse(e.node, indent));
        break;

      default:
        lines.push(`${prefix}// ── 未知节点 ──`);
        lines.push(`${prefix}UNKNOWN: ${sanitize(node.text) || node.type}`);
        node.outgoing.forEach((e) => traverse(e.node, indent));
    }
  }

  starts.forEach((s) => traverse(nodeMap.get(s.id)));

  lines.push('');
  lines.push('// ── 异常处理 ──');
  lines.push('// 1. 输入验证失败 → 返回错误码 INVALID_INPUT');
  lines.push('// 2. 处理超时 → 返回错误码 TIMEOUT');
  lines.push('// 3. 资源不足 → 返回错误码 OUT_OF_RESOURCE');
  lines.push('// 4. 未知异常 → 返回错误码 UNKNOWN_ERROR');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// PLANTUML GENERATOR (template-based)
// ─────────────────────────────────────────────────────────────────────

function generatePlantUML(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const starts = findStartNodes(nodes);
  const ends = findEndNodes(nodes);
  const stats = getNodeStats(nodes);

  const lines = [];

  lines.push('@startuml');
  lines.push('!theme plain');
  lines.push('title 流程图 → PlantUML 活动图');
  lines.push('');
  lines.push('skinparam activity {');
  lines.push('  BackgroundColor White');
  lines.push('  BorderColor Black');
  lines.push('  ArrowColor #444');
  lines.push('  ArrowThickness 1.5');
  lines.push('  StartColor #4ade80');
  lines.push('  EndColor #f87171');
  lines.push('  DiamondBackgroundColor #fbbf24');
  lines.push('  NoteBackgroundColor #e0e7ff');
  lines.push('}');
  lines.push('');

  lines.push('partition "输入校验" {');
  lines.push('  :接收输入数据;');
  lines.push('  if (输入为空?) then (空)');
  lines.push('    :返回 INVALID_INPUT;');
  lines.push('    stop');
  lines.push('  else (非空)');
  lines.push('    :格式校验;');
  lines.push('  endif');
  lines.push('}');
  lines.push('');

  lines.push('partition "主处理流程" {');
  lines.push('start');

  const visited = new Set();
  const endPrinted = new Set();

  function nodeLabel(node) {
    return sanitize(node.text) || node.id;
  }

  function traverse(node) {
    if (node.type === NODE_TYPES.END) {
      if (!endPrinted.has(node.id)) {
        endPrinted.add(node.id);
        lines.push('stop');
      }
      return;
    }

    if (visited.has(node.id)) {
      lines.push(`# ${nodeLabel(node)} (已访问)`);
      return;
    }
    visited.add(node.id);

    switch (node.type) {
      case NODE_TYPES.PROCESS:
        lines.push(`:${nodeLabel(node)};`);
        node.outgoing.forEach((e) => traverse(e.node));
        break;

      case NODE_TYPES.DECISION: {
        const question = nodeLabel(node);
        if (node.outgoing.length >= 2) {
          const { yesEdge, noEdge } = findYesNoEdges(node);
          const yesLabel = sanitize(yesEdge?.label) || '是';
          const noLabel = sanitize(noEdge?.label) || '否';
          lines.push(`if (${question}) then (${yesLabel})`);
          if (yesEdge) traverse(yesEdge.node);
          if (noEdge) {
            lines.push(`else (${noLabel})`);
            traverse(noEdge.node);
          }
          lines.push('endif');
        } else {
          lines.push(`:${question};`);
          node.outgoing.forEach((e) => traverse(e.node));
        }
        break;
      }

      case NODE_TYPES.INPUT_OUTPUT:
        lines.push(`:${nodeLabel(node)};`);
        node.outgoing.forEach((e) => traverse(e.node));
        break;

      case NODE_TYPES.START:
        node.outgoing.forEach((e) => traverse(e.node));
        break;

      default:
        lines.push(`:${nodeLabel(node)};`);
        node.outgoing.forEach((e) => traverse(e.node));
    }
  }

  if (starts.length > 0) {
    starts.forEach((s) => traverse(nodeMap.get(s.id)));
  } else {
    lines.push('note right: 未找到开始节点');
    nodes.forEach((n) => traverse(nodeMap.get(n.id)));
  }

  if (!lines.includes('stop')) {
    lines.push('stop');
  }

  lines.push('}');
  lines.push('');

  lines.push('partition "异常处理" {');
  lines.push('  :捕获异常;');
  lines.push('  switch (异常类型) case (类型)');
  lines.push('  case (INVALID_INPUT)');
  lines.push('    :记录参数错误日志;');
  lines.push('  case (TIMEOUT)');
  lines.push('    :记录超时日志;');
  lines.push('  case (OUT_OF_RESOURCE)');
  lines.push('    :记录资源不足日志;');
  lines.push('  case else');
  lines.push('    :记录未知异常日志;');
  lines.push('  endswitch');
  lines.push('  :返回错误响应;');
  lines.push('}');
  lines.push('');

  lines.push('legend right');
  lines.push('  |= 符号 |= 含义 |');
  lines.push('  | <$start> | 流程开始 |');
  lines.push('  | 矩形 | 处理步骤 |');
  lines.push('  | 菱形 | 判断分支 |');
  lines.push('  | 平行四边形 | 输入/输出 |');
  lines.push('  | <$end> | 流程结束 |');
  lines.push('endlegend');
  lines.push('');

  lines.push('note bottom of title');
  lines.push('  节点统计:');
  lines.push('  处理节点: ' + stats.process);
  lines.push('  判断节点: ' + stats.decision);
  lines.push('  输入输出: ' + stats.io);
  lines.push('  总计: ' + stats.total);
  lines.push('end note');

  lines.push('@enduml');
  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// STATE MACHINE GENERATOR (template-based with guards & error states)
// ─────────────────────────────────────────────────────────────────────

function generateStateMachine(flowchart) {
  const { nodes, edges } = flowchart;
  const nodeMap = buildGraph(nodes, edges);
  const stats = getNodeStats(nodes);

  const allStates = [];
  const stateMap = new Map();

  nodes.forEach((n) => {
    if (n.type === NODE_TYPES.START || n.type === NODE_TYPES.END) return;
    const id = toIdentifier(n.text, n.id.toUpperCase());
    let uniqueId = id;
    let counter = 1;
    while (stateMap.has(uniqueId)) {
      uniqueId = `${id}_${counter}`;
      counter++;
    }
    const state = {
      id: uniqueId,
      originalId: n.id,
      name: sanitize(n.text) || n.id,
      type: n.type,
    };
    allStates.push(state);
    stateMap.set(uniqueId, state);
  });

  const originalToState = new Map();
  allStates.forEach((s) => originalToState.set(s.originalId, s));

  const firstState = allStates[0];
  const lastState = allStates[allStates.length - 1];

  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  流程图 → 状态机代码 (JavaScript)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push(`// 节点统计: 处理=${stats.process}  判断=${stats.decision}  IO=${stats.io}  总计=${stats.total}`);
  lines.push(`// 状态数: ${allStates.length}`);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');

  lines.push('// ── 状态枚举 ──');
  lines.push('const State = {');
  lines.push('  // 错误/边界状态');
  lines.push('  ERROR_INVALID_INPUT: "ERROR_INVALID_INPUT",');
  lines.push('  ERROR_TIMEOUT: "ERROR_TIMEOUT",');
  lines.push('  ERROR_RESOURCE: "ERROR_RESOURCE",');
  lines.push('  ERROR_UNKNOWN: "ERROR_UNKNOWN",');
  lines.push('  // 正常流程状态');
  allStates.forEach((s, i) => {
    const comma = i < allStates.length - 1 ? ',' : '';
    lines.push(`  ${s.id}: "${s.id}"${comma}`);
  });
  lines.push('};');
  lines.push('');

  lines.push('// ── 状态机配置 ──');
  lines.push('const STATE_CONFIG = {');
  allStates.forEach((s, i) => {
    const origNode = nodeMap.get(s.originalId);
    const comma = i < allStates.length - 1 ? ',' : '';
    lines.push(`  [State.${s.id}]: {`);
    lines.push(`    name: "${s.name}",`);
    lines.push(`    type: "${s.type}",`);
    lines.push(`    timeout: 30000,`);
    lines.push(`    retryable: ${s.type !== NODE_TYPES.DECISION},`);
    lines.push(`    maxRetries: 3,`);
    lines.push(`    onEnter: async (ctx) => { console.log("[ENTER] ${s.name}"); },`);
    lines.push(`    onExit:  async (ctx) => { console.log("[EXIT]  ${s.name}"); },`);
    lines.push(`    validate:  (ctx) => ctx !== null && ctx !== undefined,`);
    lines.push(`  }${comma}`);
  });
  lines.push('};');
  lines.push('');

  lines.push('// ── 状态机类 ──');
  lines.push('class FlowchartStateMachine {');
  lines.push('  constructor(options = {}) {');
  lines.push('    this.currentState = options.initialState ||');
  lines.push(`      State.${firstState?.id || 'ERROR_UNKNOWN'};`);
  lines.push('    this.previousState = null;');
  lines.push('    this.isFinished = false;');
  lines.push('    this.transitionCount = 0;');
  lines.push('    this.maxTransitions = options.maxTransitions || 1000;');
  lines.push('    this.retryCount = new Map();');
  lines.push('    this.errorState = null;');
  lines.push('    this.eventLog = [];');
  lines.push('  }');
  lines.push('');

  lines.push('  // ── 状态转换 (含边界检查与异常处理) ──');
  lines.push('  async transition(condition = null, context = {}) {');
  lines.push('    // 循环保护');
  lines.push('    if (++this.transitionCount > this.maxTransitions) {');
  lines.push('      this.errorState = State.ERROR_TIMEOUT;');
  lines.push('      throw new Error("状态转换次数超过上限，可能存在无限循环");');
  lines.push('    }');
  lines.push('');
  lines.push('    // 上下文校验');
  lines.push('    const config = STATE_CONFIG[this.currentState];');
  lines.push('    if (config && config.validate && !config.validate(context)) {');
  lines.push('      this.errorState = State.ERROR_INVALID_INPUT;');
  lines.push('      this._log("warn", `[${this.currentState}] 上下文校验失败`);');
  lines.push('      return this.errorState;');
  lines.push('    }');
  lines.push('');
  lines.push('    // 进入状态钩子');
  lines.push('    if (config?.onEnter) {');
  lines.push('      try { await config.onEnter(context); }');
  lines.push('      catch (e) {');
  lines.push('        this._log("error", `[${this.currentState}] onEnter异常: ${e.message}`);');
  lines.push('        this.errorState = State.ERROR_UNKNOWN;');
  lines.push('        return this.errorState;');
  lines.push('      }');
  lines.push('    }');
  lines.push('');
  lines.push('    this.previousState = this.currentState;');
  lines.push('    const nextState = this._computeNextState(condition);');
  lines.push('');
  lines.push('    // 退出状态钩子');
  lines.push('    if (config?.onExit) {');
  lines.push('      try { await config.onExit(context); }');
  lines.push('      catch (e) { this._log("warn", `onExit异常: ${e.message}`); }');
  lines.push('    }');
  lines.push('');
  lines.push('    this.currentState = nextState;');
  lines.push('    this._log("info", `状态转换: ${this.previousState} → ${nextState}`);');
  lines.push('    return this.currentState;');
  lines.push('  }');
  lines.push('');

  lines.push('  // ── 根据当前状态计算下一个状态 ──');
  lines.push('  _computeNextState(condition) {');
  lines.push('    switch (this.currentState) {');

  allStates.forEach((s) => {
    const origNode = nodeMap.get(s.originalId);
    if (!origNode) return;

    lines.push(`      case State.${s.id}: {`);

    if (origNode.type === NODE_TYPES.DECISION && origNode.outgoing.length >= 2) {
      const { yesEdge, noEdge } = findYesNoEdges(origNode);
      const yesState = yesEdge?.node ? originalToState.get(yesEdge.node.id) : null;
      const noState = noEdge?.node ? originalToState.get(noEdge.node.id) : null;
      lines.push(`        // 判断: ${origNode.text || '条件'}`);
      lines.push('        if (this._evaluateCondition(condition)) {');
      if (yesEdge?.node.type === NODE_TYPES.END) {
        lines.push('          this.isFinished = true;');
        lines.push(`          return this.currentState; // 分支结束`);
      } else {
        lines.push(`          return State.${yesState?.id || 'ERROR_UNKNOWN'}; // 分支: 是/True`);
      }
      lines.push('        } else {');
      if (noEdge?.node.type === NODE_TYPES.END) {
        lines.push('          this.isFinished = true;');
        lines.push(`          return this.currentState; // 分支结束`);
      } else {
        lines.push(`          return State.${noState?.id || 'ERROR_UNKNOWN'}; // 分支: 否/False`);
      }
      lines.push('        }');
    } else {
      if (origNode.outgoing.length > 0) {
        const nextEdge = origNode.outgoing[0];
        const nextState = nextEdge?.node ? originalToState.get(nextEdge.node.id) : null;
        if (nextEdge?.node.type === NODE_TYPES.END) {
          lines.push(`        // 处理: ${origNode.text || '步骤'}`);
          lines.push('        this.isFinished = true;');
          lines.push(`        return this.currentState; // 流程结束`);
        } else {
          lines.push(`        // 处理: ${origNode.text || '步骤'}`);
          lines.push(`        return State.${nextState?.id || 'ERROR_UNKNOWN'};`);
        }
      } else {
        lines.push('        this.isFinished = true;');
        lines.push('        return this.currentState; // 无后继节点');
      }
    }

    lines.push('        break;');
    lines.push('      }');
  });

  lines.push('      default:');
  lines.push('        this.isFinished = true;');
  lines.push('        this._log("warn", `未知状态: ${this.currentState}`);');
  lines.push('        return this.currentState;');
  lines.push('    }');
  lines.push('  }');
  lines.push('');

  lines.push('  // ── 条件求值 (含异常保护) ──');
  lines.push('  _evaluateCondition(condition) {');
  lines.push('    try {');
  lines.push('      if (typeof condition === "function") return !!condition();');
  lines.push('      return !!condition;');
  lines.push('    } catch (e) {');
  lines.push('      this._log("error", `条件求值异常: ${e.message}`);');
  lines.push('      return false;');
  lines.push('    }');
  lines.push('  }');
  lines.push('');

  lines.push('  // ── 带重试的执行入口 ──');
  lines.push('  async run(inputValue = null, maxRetry = 3) {');
  lines.push('    let retry = 0;');
  lines.push('    while (!this.isFinished && retry < maxRetry) {');
  lines.push('      try {');
  lines.push('        this._log("info", `当前状态: ${this.currentState}`);');
  lines.push('        await this.transition(inputValue);');
  lines.push('        retry = 0; // 成功后重置重试计数');
  lines.push('      } catch (e) {');
  lines.push('        retry++;');
  lines.push('        this._log("warn", `执行失败 (${retry}/${maxRetry}): ${e.message}`);');
  lines.push('        if (retry >= maxRetry) {');
  lines.push('          this.errorState = State.ERROR_TIMEOUT;');
  lines.push('          throw e;');
  lines.push('        }');
  lines.push('        await this._sleep(100 * retry); // 指数退避');
  lines.push('      }');
  lines.push('    }');
  lines.push('    if (this.isFinished) {');
  lines.push('      this._log("info", "流程执行完毕");');
  lines.push('    }');
  lines.push('    return {');
  lines.push('      success: this.isFinished && !this.errorState,');
  lines.push('      finalState: this.currentState,');
  lines.push('      errorState: this.errorState,');
  lines.push('      transitions: this.transitionCount,');
  lines.push('    };');
  lines.push('  }');
  lines.push('');

  lines.push('  // ── 工具方法 ──');
  lines.push('  _log(level, message) {');
  lines.push('    this.eventLog.push({ level, message, time: Date.now() });');
  lines.push('    const prefix = `[${new Date().toISOString()}] [${level.toUpperCase()}]`;');
  lines.push('    console[level === "info" ? "log" : level](`${prefix} ${message}`);');
  lines.push('  }');
  lines.push('');
  lines.push('  _sleep(ms) {');
  lines.push('    return new Promise((resolve) => setTimeout(resolve, ms));');
  lines.push('  }');
  lines.push('}');
  lines.push('');

  lines.push('// ── 使用示例 ──');
  lines.push('// (async () => {');
  lines.push('//   const machine = new FlowchartStateMachine({');
  if (firstState) {
    lines.push(`//     initialState: State.${firstState.id},`);
  }
  lines.push('//     maxTransitions: 500,');
  lines.push('//   });');
  lines.push('//   const result = await machine.run(conditionValue);');
  lines.push('//   console.log("执行结果:", result);');
  lines.push('//   console.log("事件日志:", machine.eventLog);');
  lines.push('// })();');
  lines.push('');
  lines.push('// ── 导出 ──');
  lines.push('if (typeof module !== "undefined" && module.exports) {');
  lines.push('  module.exports = { State, FlowchartStateMachine, STATE_CONFIG };');
  lines.push('}');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// UNIT TEST GENERATOR
// ─────────────────────────────────────────────────────────────────────

function generateUnitTests(flowchart, language = 'javascript') {
  const { nodes, edges } = flowchart;
  const decisions = findDecisionNodes(nodes);
  const stats = getNodeStats(nodes);

  const testCases = [];

  // Test case 1: Null input
  testCases.push({
    name: 'test_null_input_should_raise_invalid_input',
    description: '空输入应返回 INVALID_INPUT 错误',
    input: null,
    expectedError: 'INVALID_INPUT',
  });

  // Test case 2: Happy path (all decisions true)
  testCases.push({
    name: 'test_happy_path_all_yes',
    description: '所有判断条件为是时应正常执行',
    input: 'valid_input',
    conditions: decisions.map(() => true),
    expectedSuccess: true,
  });

  // Test case 3: All decisions false
  testCases.push({
    name: 'test_all_decision_no',
    description: '所有判断条件为否时应正常执行',
    input: 'valid_input',
    conditions: decisions.map(() => false),
    expectedSuccess: true,
  });

  // Test case 4: Timeout simulation
  testCases.push({
    name: 'test_max_retries_exceeded',
    description: '超过最大重试次数应返回 TIMEOUT',
    input: 'valid_input',
    simulateError: true,
    expectedError: 'TIMEOUT',
  });

  // Generate individual decision tests
  decisions.forEach((d, i) => {
    const name = sanitize(d.text) || `decision_${i}`;
    testCases.push({
      name: `test_decision_${toSnakeCase(name)}_yes`,
      description: `判断 [${name}] 为是的分支`,
      input: 'valid_input',
      decisionIndex: i,
      decisionValue: true,
      expectedSuccess: true,
    });
    testCases.push({
      name: `test_decision_${toSnakeCase(name)}_no`,
      description: `判断 [${name}] 为否的分支`,
      input: 'valid_input',
      decisionIndex: i,
      decisionValue: false,
      expectedSuccess: true,
    });
  });

  switch (language) {
    case 'python':
      return generatePythonTests(flowchart, testCases, stats);
    case 'java':
      return generateJavaTests(flowchart, testCases, stats);
    case 'go':
      return generateGoTests(flowchart, testCases, stats);
    case 'javascript':
    default:
      return generateJavascriptTests(flowchart, testCases, stats);
  }
}

function generateJavascriptTests(flowchart, testCases, stats) {
  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  自动生成的单元测试 (Jest)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push(`// 测试用例数: ${testCases.length}`);
  lines.push(`// 节点覆盖: ${stats.total} 个节点, ${stats.decision} 个判断分支`);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push("const { FlowchartStateMachine, State } = require('./flowchart_state_machine');");
  lines.push('');
  lines.push('describe("FlowchartStateMachine", () => {');
  lines.push('  let machine;');
  lines.push('');
  lines.push('  beforeEach(() => {');
  lines.push('    machine = new FlowchartStateMachine({ maxTransitions: 100 });');
  lines.push('  });');
  lines.push('');

  testCases.forEach((tc) => {
    lines.push(`  test("${tc.description}", async () => {`);
    if (tc.input === null) {
      lines.push('    await expect(machine.run(null)).rejects.toThrow();');
    } else if (tc.simulateError) {
      lines.push('    // 模拟错误场景');
      lines.push('    const original = machine.transition;');
      lines.push('    machine.transition = jest.fn().mockRejectedValue(new Error("模拟失败"));');
      lines.push('    await expect(machine.run("test", 2)).rejects.toThrow();');
    } else {
      lines.push(`    const result = await machine.run(${JSON.stringify(tc.input)});`);
      lines.push('    expect(result).toBeDefined();');
      lines.push('    if (result.success) {');
      lines.push('      expect(machine.isFinished).toBe(true);');
      lines.push('    }');
    }
    lines.push('  });');
    lines.push('');
  });

  lines.push('  test("should_log_transitions", async () => {');
  lines.push('    const result = await machine.run("test");');
  lines.push('    expect(machine.eventLog.length).toBeGreaterThan(0);');
  lines.push('    expect(machine.transitionCount).toBeGreaterThan(0);');
  lines.push('  });');
  lines.push('');
  lines.push('  test("should_prevent_infinite_loop", async () => {');
  lines.push('    machine.maxTransitions = 3;');
  lines.push('    await expect(machine.run("test")).rejects.toThrow("状态转换次数超过上限");');
  lines.push('  });');
  lines.push('});');

  return lines.join('\n');
}

function generatePythonTests(flowchart, testCases, stats) {
  const lines = [];
  lines.push('# ════════════════════════════════════════════════════');
  lines.push('#  自动生成的单元测试 (pytest)');
  lines.push('# ════════════════════════════════════════════════════');
  lines.push(`# 测试用例数: ${testCases.length}`);
  lines.push(`# 节点覆盖: ${stats.total} 个节点, ${stats.decision} 个判断分支`);
  lines.push('# 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('import pytest');
  lines.push('from flowchart import process_flowchart, FlowchartError, ErrorCode');
  lines.push('');

  testCases.forEach((tc) => {
    lines.push(`def ${tc.name}():`);
    lines.push(`    """${tc.description}"""`);
    if (tc.input === null) {
      lines.push('    with pytest.raises(FlowchartError) as exc_info:');
      lines.push('        process_flowchart(None)');
      lines.push('    assert exc_info.value.code == ErrorCode.INVALID_INPUT');
    } else if (tc.simulateError) {
      lines.push('    # 模拟重试耗尽场景');
      lines.push('    with pytest.raises(FlowchartError) as exc_info:');
      lines.push('        process_flowchart("test", max_retries=1, timeout=0.001)');
      lines.push('    assert exc_info.value.code in (ErrorCode.TIMEOUT, ErrorCode.UNKNOWN_ERROR)');
    } else {
      lines.push(`    result = process_flowchart(${JSON.stringify(tc.input)})`);
      lines.push('    assert result is not None');
      lines.push('    assert "success" in result');
    }
    lines.push('');
  });

  lines.push('def test_boundary_large_input():');
  lines.push('    """测试大输入边界条件"""');
  lines.push('    large_input = "x" * 10000');
  lines.push('    result = process_flowchart(large_input)');
  lines.push('    assert result is not None');
  lines.push('');
  lines.push('def test_boundary_special_characters():');
  lines.push('    """测试特殊字符输入"""');
  lines.push('    special_input = "<script>alert(1)</script>\\0\\n\\r"');
  lines.push('    result = process_flowchart(special_input)');
  lines.push('    assert result is not None');

  return lines.join('\n');
}

function generateJavaTests(flowchart, testCases, stats) {
  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  自动生成的单元测试 (JUnit 5)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push(`// 测试用例数: ${testCases.length}`);
  lines.push(`// 节点覆盖: ${stats.total} 个节点, ${stats.decision} 个判断分支`);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('package com.flowchart.generated;');
  lines.push('');
  lines.push('import org.junit.jupiter.api.*;');
  lines.push('import static org.junit.jupiter.api.Assertions.*;');
  lines.push('import static org.junit.jupiter.api.Assertions.assertThrows;');
  lines.push('');
  lines.push('class FlowchartProcessorTest {');
  lines.push('');
  lines.push('    private FlowchartProcessor processor;');
  lines.push('');
  lines.push('    @BeforeEach');
  lines.push('    void setUp() {');
  lines.push('        processor = new FlowchartProcessor();');
  lines.push('    }');
  lines.push('');

  testCases.forEach((tc, i) => {
    const methodName = toCamelCase(tc.name, `testCase${i}`);
    lines.push(`    @Test`);
    lines.push(`    @DisplayName("${tc.description}")`);
    lines.push(`    void ${methodName}() {`);
    if (tc.input === null) {
      lines.push('        FlowchartException ex = assertThrows(FlowchartException.class, () -> {');
      lines.push('            processor.process(null);');
      lines.push('        });');
      lines.push('        assertEquals(FlowchartProcessor.ErrorCode.INVALID_INPUT, ex.getCode());');
    } else if (tc.simulateError) {
      lines.push('        // 测试超时场景');
      lines.push('        assertThrows(FlowchartException.class, () -> {');
      lines.push('            processor.process("test", 1, 1);');
      lines.push('        });');
    } else {
      lines.push(`        ProcessingResult result = processor.process(${JSON.stringify(tc.input)});`);
      lines.push('        assertNotNull(result);');
    }
    lines.push('    }');
    lines.push('');
  });

  lines.push('    @Test');
  lines.push('    @DisplayName("测试空字符串输入")');
  lines.push('    void testEmptyStringInput() {');
  lines.push('        ProcessingResult result = processor.process("");');
  lines.push('        assertNotNull(result);');
  lines.push('    }');
  lines.push('');
  lines.push('    @Test');
  lines.push('    @DisplayName("测试最大重试次数边界")');
  lines.push('    void testMaxRetriesBoundary() {');
  lines.push('        assertThrows(FlowchartException.class, () -> {');
  lines.push('            processor.process("test", 0, 1000);');
  lines.push('        });');
  lines.push('    }');
  lines.push('}');

  return lines.join('\n');
}

function generateGoTests(flowchart, testCases, stats) {
  const lines = [];
  lines.push('// ════════════════════════════════════════════════════');
  lines.push('//  自动生成的单元测试 (testing)');
  lines.push('// ════════════════════════════════════════════════════');
  lines.push(`// 测试用例数: ${testCases.length}`);
  lines.push(`// 节点覆盖: ${stats.total} 个节点, ${stats.decision} 个判断分支`);
  lines.push('// 生成时间: ' + new Date().toISOString());
  lines.push('');
  lines.push('package flowchart');
  lines.push('');
  lines.push('import (');
  lines.push('\t"context"');
  lines.push('\t"errors"');
  lines.push('\t"testing"');
  lines.push('\t"time"');
  lines.push(')');
  lines.push('');

  testCases.forEach((tc, i) => {
    const funcName = 'Test' + toPascalCase(tc.name, `TestCase${i}`);
    lines.push(`func ${funcName}(t *testing.T) {`);
    lines.push(`\t// ${tc.description}`);
    lines.push('\tp := NewProcessor()');
    lines.push('');
    if (tc.input === null) {
      lines.push('\t_, err := p.Process(context.Background(), nil)');
      lines.push('\tif err == nil {');
      lines.push('\t\tt.Fatal("expected error for nil input")');
      lines.push('\t}');
      lines.push('\tvar flowErr *FlowchartError');
      lines.push('\tif !errors.As(err, &flowErr) || flowErr.Code != ErrInvalidInput {');
      lines.push('\t\tt.Fatalf("expected ErrInvalidInput, got %v", err)');
      lines.push('\t}');
    } else if (tc.simulateError) {
      lines.push('\tp = p.WithMaxRetries(1).WithTimeout(1 * time.Millisecond)');
      lines.push('\t_, err := p.Process(context.Background(), "test")');
      lines.push('\tif err == nil {');
      lines.push('\t\tt.Fatal("expected timeout error")');
      lines.push('\t}');
    } else {
      lines.push(`\tresult, err := p.Process(context.Background(), ${JSON.stringify(tc.input)})`);
      lines.push('\tif err != nil {');
      lines.push('\t\tt.Fatalf("unexpected error: %v", err)');
      lines.push('\t}');
      lines.push('\tif result == nil {');
      lines.push('\t\tt.Fatal("expected result")');
      lines.push('\t}');
    }
    lines.push('}');
    lines.push('');
  });

  lines.push('func TestBoundaryLargeInput(t *testing.T) {');
  lines.push('\tp := NewProcessor()');
  lines.push('\tlargeInput := make([]byte, 1024*1024) // 1MB');
  lines.push('\tfor i := range largeInput {');
  lines.push('\t\tlargeInput[i] = 0x41');
  lines.push('\t}');
  lines.push('\t_, err := p.Process(context.Background(), string(largeInput))');
  lines.push('\tif err != nil {');
  lines.push('\t\tt.Logf("large input returned (expected for timeout): %v", err)');
  lines.push('\t}');
  lines.push('}');
  lines.push('');
  lines.push('func TestContextCancellation(t *testing.T) {');
  lines.push('\tp := NewProcessor()');
  lines.push('\tctx, cancel := context.WithCancel(context.Background())');
  lines.push('\tcancel() // 立即取消');
  lines.push('\t_, err := p.Process(ctx, "test")');
  lines.push('\tif err == nil {');
  lines.push('\t\tt.Fatal("expected error from cancelled context")');
  lines.push('\t}');
  lines.push('}');

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────
// UNIFIED CODE GENERATION ENTRY
// ─────────────────────────────────────────────────────────────────────

function generateCode(flowchart, language = 'pseudocode') {
  switch (language.toLowerCase()) {
    case 'python':
    case 'py':
      return generatePython(flowchart);
    case 'java':
      return generateJava(flowchart);
    case 'go':
    case 'golang':
      return generateGo(flowchart);
    case 'javascript':
    case 'js':
      return generateJavaScript(flowchart);
    case 'pseudocode':
      return generatePseudocode(flowchart);
    case 'plantuml':
      return generatePlantUML(flowchart);
    case 'statemachine':
    case 'state_machine':
      return generateJavaScript(flowchart);
    default:
      return `// 不支持的语言: ${language}\n// 支持的语言: python, java, go, javascript, pseudocode, plantuml`;
  }
}

function generateAllLanguages(flowchart) {
  return {
    pseudocode: generatePseudocode(flowchart),
    plantuml: generatePlantUML(flowchart),
    python: generatePython(flowchart),
    java: generateJava(flowchart),
    go: generateGo(flowchart),
    javascript: generateJavaScript(flowchart),
    tests: {
      python: generateUnitTests(flowchart, 'python'),
      java: generateUnitTests(flowchart, 'java'),
      go: generateUnitTests(flowchart, 'go'),
      javascript: generateUnitTests(flowchart, 'javascript'),
    },
  };
}

function generateJavaScript(flowchart) {
  return generateStateMachine(flowchart);
}

module.exports = {
  generatePseudocode,
  generatePlantUML,
  generateStateMachine,
  generateJavaScript,
  generatePython,
  generateJava,
  generateGo,
  generateCode,
  generateAllLanguages,
  generateUnitTests,
  NODE_TYPES,
  LANGUAGES,
  buildGraph,
  toIdentifier,
  toCamelCase,
  toPascalCase,
  toSnakeCase,
};
