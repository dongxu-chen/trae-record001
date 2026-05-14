from datetime import datetime
from typing import Dict, Any


def generate_commit_message(template: str, extra_info: Dict[str, Any] = None) -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    context = {
        "timestamp": timestamp,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "hour": now.strftime("%H"),
        "minute": now.strftime("%M"),
        "second": now.strftime("%S"),
    }
    
    if extra_info:
        context.update(extra_info)
    
    try:
        return template.format(**context)
    except KeyError as e:
        raise ValueError(f"提交信息模板中包含未定义的占位符: {e}")


def generate_default_message() -> str:
    return generate_commit_message("自动备份: {timestamp}")


if __name__ == "__main__":
    print("测试提交信息生成:")
    print(generate_default_message())
    print(generate_commit_message("备份: {date} - {time}", {"branch": "main"}))
