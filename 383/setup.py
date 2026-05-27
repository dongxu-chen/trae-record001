"""Security Fixer 项目配置"""

from setuptools import setup, find_packages

setup(
    name="security-fixer",
    version="1.0.0",
    description="自动检测并修复代码中的安全漏洞（SQL注入、XSS、路径遍历、命令注入）",
    author="Security Fixer Team",
    python_requires=">=3.8",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "full": [
            "astor>=0.8.1",
            "javalang>=0.13.0",
            "esprima>=4.0.1",
            "PyGithub>=2.1.0",
        ],
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "security-fixer=security_fixer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
    ],
)
