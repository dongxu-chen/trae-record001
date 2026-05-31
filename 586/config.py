import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'web', 'templates')

DEFAULT_CONFIG = {
    'timeout': 10,
    'max_retries': 2,
    'delay_between_requests': 0.1,
    'anomaly_detection': {
        'check_status_code': True,
        'check_response_time': True,
        'check_error_messages': True,
        'check_sql_errors': True,
        'check_xss_reflection': True,
        'max_response_time': 5000,
        'error_keywords': [
            'error', 'exception', 'traceback', 'fatal', 'warning',
            'undefined', 'null', 'none', 'invalid', 'fail'
        ]
    }
}

SQL_INJECTION_PAYLOADS = [
    "'", "''", "\"", "\"\"", "' OR '1'='1", "' OR 1=1--",
    "' UNION SELECT NULL--", "' UNION SELECT 1,2,3--",
    "1' AND SLEEP(5)--", "1; DROP TABLE users--",
    "' OR 1=1#", "\" OR 1=1--", "') OR ('1'='1"
]

XSS_PAYLOADS = [
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
    "\" onmouseover=\"alert(1)", "<svg onload=alert(1)>",
    "javascript:alert(1)", "'><script>alert(1)</script>"
]

COMMAND_INJECTION_PAYLOADS = [
    "; ls", "&& whoami", "| id", "`cat /etc/passwd`",
    "$(whoami)", "; ping -c 1 127.0.0.1"
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd", "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "/etc/passwd", "C:\\Windows\\System32\\cmd.exe",
    "..././..././etc/passwd"
]

EDGE_CASE_VALUES = {
    'string': [
        "", " ", None, "null", "undefined", "NaN", "Infinity",
        "a" * 1000, "a" * 10000, "\x00", "\n", "\r", "\t",
        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
        "中文", "🔥", "𝄞", "\u0000", "\uFFFF"
    ],
    'integer': [
        0, 1, -1, 2147483647, 2147483648, -2147483648, -2147483649,
        999999999999999999, -999999999999999999, None, "0", "1", "-1",
        "999999999999999999", "abc", "1e1000"
    ],
    'number': [
        0, 0.0, 1.0, -1.0, 3.14159, -3.14159, float('inf'),
        float('-inf'), float('nan'), 1e308, -1e308, None, "0.0", "1.5"
    ],
    'boolean': [
        True, False, None, "true", "false", "True", "False",
        "TRUE", "FALSE", 1, 0, "1", "0", "yes", "no"
    ],
    'array': [
        [], None, [1, 2, 3], ["a", "b"], [None, None],
        [[]], [[[]]], [1, "a", None, True]
    ],
    'object': [
        {}, None, {"key": "value"}, {"a": {"b": {"c": 1}}},
        {"key": None}, {"": "empty", "\x00": "null"}
    ],
    'date': [
        "0000-00-00", "9999-12-31", "2023-02-30", "2023-13-01",
        "not-a-date", None, "2023-01-01T25:00:00Z"
    ],
    'email': [
        "", "notanemail", "@", "@domain.com", "user@",
        "user@.com", "user@domain", "a" * 100 + "@example.com",
        None, "test@test.com", "user+tag@example.com"
    ],
    'url': [
        "", "notaurl", "http://", "https://", "ftp://",
        "http://example.com/" + "a" * 2000, None,
        "javascript:alert(1)", "file:///etc/passwd"
    ]
}
