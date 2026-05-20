from prefect import task
from prefect.runtime import task_run
import pandas as pd
import json
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def get_checkpoint_key():
    return f"checkpoint_{task_run.name}"


@task(name="extract_csv", description="从CSV文件提取数据")
def extract_csv(file_path: str, **kwargs) -> Dict[str, Any]:
    logger.info(f"从CSV提取数据: {file_path}")
    df = pd.read_csv(file_path)
    data = df.to_dict(orient="records")
    return {
        "data": data,
        "columns": list(df.columns),
        "row_count": len(df),
        "source": file_path
    }


@task(name="extract_database", description="从数据库提取数据")
def extract_database(connection_string: str, query: str, **kwargs) -> Dict[str, Any]:
    logger.info("从数据库提取数据")
    df = pd.read_sql(query, connection_string)
    data = df.to_dict(orient="records")
    return {
        "data": data,
        "columns": list(df.columns),
        "row_count": len(df)
    }


@task(name="transform_filter", description="过滤数据")
def transform_filter(input_data: Dict[str, Any], filter_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    logger.info("执行数据过滤")
    df = pd.DataFrame(input_data["data"])
    column = filter_config.get("column")
    operator = filter_config.get("operator")
    value = filter_config.get("value")
    
    if operator == "equals":
        df = df[df[column] == value]
    elif operator == "greater_than":
        df = df[df[column] > value]
    elif operator == "less_than":
        df = df[df[column] < value]
    elif operator == "contains":
        df = df[df[column].astype(str).str.contains(str(value))]
    
    return {
        "data": df.to_dict(orient="records"),
        "columns": list(df.columns),
        "row_count": len(df)
    }


@task(name="transform_rename", description="重命名字段")
def transform_rename(input_data: Dict[str, Any], rename_mapping: Dict[str, str], **kwargs) -> Dict[str, Any]:
    logger.info("执行字段重命名")
    df = pd.DataFrame(input_data["data"])
    df = df.rename(columns=rename_mapping)
    return {
        "data": df.to_dict(orient="records"),
        "columns": list(df.columns),
        "row_count": len(df)
    }


@task(name="transform_select", description="选择字段")
def transform_select(input_data: Dict[str, Any], columns: List[str], **kwargs) -> Dict[str, Any]:
    logger.info("执行字段选择")
    df = pd.DataFrame(input_data["data"])
    df = df[columns]
    return {
        "data": df.to_dict(orient="records"),
        "columns": list(df.columns),
        "row_count": len(df)
    }


@task(name="transform_join", description="数据合并")
def transform_join(left_data: Dict[str, Any], right_data: Dict[str, Any], join_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    logger.info("执行数据合并")
    df_left = pd.DataFrame(left_data["data"])
    df_right = pd.DataFrame(right_data["data"])
    df_merged = pd.merge(
        df_left, 
        df_right,
        on=join_config.get("on"),
        how=join_config.get("how", "inner")
    )
    return {
        "data": df_merged.to_dict(orient="records"),
        "columns": list(df_merged.columns),
        "row_count": len(df_merged)
    }


@task(name="load_csv", description="加载数据到CSV")
def load_csv(input_data: Dict[str, Any], output_path: str, **kwargs) -> Dict[str, Any]:
    logger.info(f"加载数据到CSV: {output_path}")
    df = pd.DataFrame(input_data["data"])
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "output_path": output_path,
        "row_count": len(df),
        "status": "success"
    }


@task(name="load_database", description="加载数据到数据库")
def load_database(input_data: Dict[str, Any], connection_string: str, table_name: str, if_exists: str = "replace", **kwargs) -> Dict[str, Any]:
    logger.info(f"加载数据到数据库表: {table_name}")
    df = pd.DataFrame(input_data["data"])
    df.to_sql(table_name, connection_string, if_exists=if_exists, index=False)
    return {
        "table_name": table_name,
        "row_count": len(df),
        "status": "success"
    }


TASK_REGISTRY = {
    "extract_csv": extract_csv,
    "extract_database": extract_database,
    "transform_filter": transform_filter,
    "transform_rename": transform_rename,
    "transform_select": transform_select,
    "transform_join": transform_join,
    "load_csv": load_csv,
    "load_database": load_database
}
