from prefect import task
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
import json
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class QualityRuleEngine:
    """质量规则引擎，支持JSON配置和SQL验证"""

    def __init__(self, rules_config: Dict[str, Any] = None):
        self.rules_config = rules_config or {}

    def load_rules_from_json(self, json_str: str):
        """从JSON字符串加载规则"""
        self.rules_config = json.loads(json_str)

    def load_rules_from_dict(self, config_dict: Dict[str, Any]):
        """从字典加载规则"""
        self.rules_config = config_dict

    def execute_rule(self, rule_type: str, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """执行质量规则"""
        rule_handlers = {
            "null_check": self._null_check,
            "duplicate_check": self._duplicate_check,
            "range_check": self._range_check,
            "regex_check": self._regex_check,
            "unique_check": self._unique_check,
            "sql_validation": self._sql_validation,
            "custom_condition": self._custom_condition
        }

        handler = rule_handlers.get(rule_type)
        if not handler:
            raise ValueError(f"Unknown rule type: {rule_type}")

        return handler(input_data, **kwargs)

    def _null_check(self, input_data: Dict[str, Any], columns: List[str] = None, threshold: float = 0.0, **kwargs) -> Dict[str, Any]:
        """空值检查"""
        df = pd.DataFrame(input_data["data"])
        if columns is None:
            columns = df.columns.tolist()

        results = {}
        overall_success = True

        for col in columns:
            null_count = df[col].isnull().sum()
            null_ratio = null_count / len(df) if len(df) > 0 else 0
            passed = null_ratio <= threshold
            if not passed:
                overall_success = False

            results[col] = {
                "null_count": int(null_count),
                "null_ratio": float(null_ratio),
                "threshold": threshold,
                "passed": passed
            }

        return {
            "success": overall_success,
            "check_type": "null_values",
            "results": results,
            "total_rows": len(df)
        }

    def _duplicate_check(self, input_data: Dict[str, Any], columns: List[str] = None, **kwargs) -> Dict[str, Any]:
        """重复数据检查"""
        df = pd.DataFrame(input_data["data"])
        if columns is None:
            columns = df.columns.tolist()

        duplicate_count = df.duplicated(subset=columns).sum()
        duplicate_ratio = duplicate_count / len(df) if len(df) > 0 else 0

        return {
            "success": duplicate_count == 0,
            "check_type": "duplicates",
            "results": {
                "duplicate_count": int(duplicate_count),
                "duplicate_ratio": float(duplicate_ratio),
                "checked_columns": columns
            },
            "total_rows": len(df)
        }

    def _range_check(self, input_data: Dict[str, Any], column: str, min_value: float = None, max_value: float = None, **kwargs) -> Dict[str, Any]:
        """数值范围检查"""
        df = pd.DataFrame(input_data["data"])

        out_of_range_count = 0
        if min_value is not None:
            out_of_range_count += (df[column] < min_value).sum()
        if max_value is not None:
            out_of_range_count += (df[column] > max_value).sum()

        out_of_range_ratio = out_of_range_count / len(df) if len(df) > 0 else 0

        return {
            "success": out_of_range_count == 0,
            "check_type": "range",
            "results": {
                "column": column,
                "min_value": min_value,
                "max_value": max_value,
                "out_of_range_count": int(out_of_range_count),
                "out_of_range_ratio": float(out_of_range_ratio)
            },
            "total_rows": len(df)
        }

    def _regex_check(self, input_data: Dict[str, Any], column: str, pattern: str, **kwargs) -> Dict[str, Any]:
        """正则表达式检查"""
        df = pd.DataFrame(input_data["data"])
        import re
        pattern_compiled = re.compile(pattern)
        invalid_count = ~df[column].astype(str).apply(lambda x: bool(pattern_compiled.match(x)))
        invalid_count = invalid_count.sum()

        invalid_ratio = invalid_count / len(df) if len(df) > 0 else 0

        return {
            "success": invalid_count == 0,
            "check_type": "regex",
            "results": {
                "column": column,
                "pattern": pattern,
                "invalid_count": int(invalid_count),
                "invalid_ratio": float(invalid_ratio)
            },
            "total_rows": len(df)
        }

    def _unique_check(self, input_data: Dict[str, Any], column: str, **kwargs) -> Dict[str, Any]:
        """唯一性检查"""
        df = pd.DataFrame(input_data["data"])
        unique_count = df[column].nunique()
        is_unique = unique_count == len(df)

        return {
            "success": is_unique,
            "check_type": "unique",
            "results": {
                "column": column,
                "unique_count": int(unique_count),
                "total_count": len(df),
                "duplicate_count": len(df) - unique_count
            },
            "total_rows": len(df)
        }

    def _sql_validation(self, input_data: Dict[str, Any], sql_query: str, connection_string: str = None, expected_result: Any = None, **kwargs) -> Dict[str, Any]:
        """SQL验证规则"""
        df = pd.DataFrame(input_data["data"])

        try:
            if connection_string:
                # 使用外部数据库
                engine = create_engine(connection_string)
                with engine.connect() as conn:
                    result = conn.execute(text(sql_query))
                    sql_result = result.fetchall()
                    columns = result.keys()
                    result_df = pd.DataFrame(sql_result, columns=columns)
            else:
                # 使用内存数据库（SQLite）验证
                from sqlalchemy import create_engine
                engine = create_engine('sqlite:///:memory:')
                df.to_sql('temp_data', engine, index=False)
                result_df = pd.read_sql(sql_query, engine)

            # 验证结果
            validation_passed = True
            result_summary = {
                "row_count": len(result_df),
                "columns": list(result_df.columns),
                "sample_data": result_df.head(5).to_dict(orient='records')
            }

            if expected_result is not None:
                # 如果有预期结果，进行比较
                if isinstance(expected_result, dict):
                    for key, value in expected_result.items():
                        if key in result_df.columns:
                            actual_value = result_df[key].iloc[0] if len(result_df) > 0 else None
                            if actual_value != value:
                                validation_passed = False
                                result_summary["mismatch"] = {
                                    "column": key,
                                    "expected": value,
                                    "actual": actual_value
                                }
                                break

            return {
                "success": validation_passed,
                "check_type": "sql_validation",
                "results": result_summary,
                "total_rows": len(df)
            }

        except Exception as e:
            logger.error(f"SQL validation error: {str(e)}")
            return {
                "success": False,
                "check_type": "sql_validation",
                "results": {
                    "error": str(e),
                    "sql_query": sql_query
                },
                "total_rows": len(df)
            }

    def _custom_condition(self, input_data: Dict[str, Any], condition: str, **kwargs) -> Dict[str, Any]:
        """自定义条件检查（使用Pandas表达式）"""
        df = pd.DataFrame(input_data["data"])

        try:
            # 使用eval执行自定义条件
            result_mask = df.eval(condition)
            failed_count = (~result_mask).sum()
            failed_ratio = failed_count / len(df) if len(df) > 0 else 0

            return {
                "success": failed_count == 0,
                "check_type": "custom_condition",
                "results": {
                    "condition": condition,
                    "failed_count": int(failed_count),
                    "failed_ratio": float(failed_ratio)
                },
                "total_rows": len(df)
            }
        except Exception as e:
            logger.error(f"Custom condition error: {str(e)}")
            return {
                "success": False,
                "check_type": "custom_condition",
                "results": {
                    "error": str(e),
                    "condition": condition
                },
                "total_rows": len(df)
            }

    def execute_all_rules(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行所有配置的质量规则"""
        results = []
        overall_success = True

        for rule in self.rules_config.get("rules", []):
            try:
                rule_result = self.execute_rule(
                    rule_type=rule["type"],
                    input_data=input_data,
                    **rule.get("params", {})
                )
                rule_result["rule_name"] = rule.get("name", rule["type"])
                results.append(rule_result)

                if not rule_result["success"]:
                    overall_success = False

            except Exception as e:
                logger.error(f"Rule execution failed: {str(e)}")
                results.append({
                    "rule_name": rule.get("name", rule["type"]),
                    "success": False,
                    "check_type": rule["type"],
                    "error": str(e)
                })
                overall_success = False

        return {
            "success": overall_success,
            "total_rules": len(results),
            "passed_rules": sum(1 for r in results if r["success"]),
            "failed_rules": sum(1 for r in results if not r["success"]),
            "rule_results": results
        }


# Prefect任务封装
@task(name="execute_quality_rules", description="执行数据质量规则")
def execute_quality_rules(input_data: Dict[str, Any], rules_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Prefect任务：执行数据质量规则"""
    engine = QualityRuleEngine(rules_config)
    return engine.execute_all_rules(input_data)


@task(name="sql_validation", description="SQL数据验证")
def sql_validation(input_data: Dict[str, Any], sql_query: str, connection_string: str = None, expected_result: Any = None, **kwargs) -> Dict[str, Any]:
    """Prefect任务：SQL验证"""
    engine = QualityRuleEngine()
    return engine._sql_validation(input_data, sql_query, connection_string, expected_result)


@task(name="check_null_values", description="检查空值")
def check_null_values(input_data: Dict[str, Any], columns: List[str] = None, threshold: float = 0.0, **kwargs) -> Dict[str, Any]:
    engine = QualityRuleEngine()
    return engine._null_check(input_data, columns, threshold)


@task(name="check_duplicates", description="检查重复数据")
def check_duplicates(input_data: Dict[str, Any], columns: List[str] = None, **kwargs) -> Dict[str, Any]:
    engine = QualityRuleEngine()
    return engine._duplicate_check(input_data, columns)


@task(name="check_range", description="检查数值范围")
def check_range(input_data: Dict[str, Any], column: str, min_value: float = None, max_value: float = None, **kwargs) -> Dict[str, Any]:
    engine = QualityRuleEngine()
    return engine._range_check(input_data, column, min_value, max_value)


@task(name="check_regex", description="正则表达式检查")
def check_regex(input_data: Dict[str, Any], column: str, pattern: str, **kwargs) -> Dict[str, Any]:
    engine = QualityRuleEngine()
    return engine._regex_check(input_data, column, pattern)


@task(name="check_unique", description="检查唯一性")
def check_unique(input_data: Dict[str, Any], column: str, **kwargs) -> Dict[str, Any]:
    engine = QualityRuleEngine()
    return engine._unique_check(input_data, column)


# 任务注册表
DATA_QUALITY_REGISTRY = {
    "check_null_values": check_null_values,
    "check_duplicates": check_duplicates,
    "check_range": check_range,
    "check_regex": check_regex,
    "check_unique": check_unique,
    "sql_validation": sql_validation,
    "execute_quality_rules": execute_quality_rules
}
