from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-commit-quality-checker",
    version="1.0.0",
    author="Commit Quality Team",
    description="A Git commit quality checking tool with Conventional Commits support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "GitPython>=3.1.40",
        "PyYAML>=6.0.1",
        "click>=8.1.7",
    ],
    entry_points={
        "console_scripts": [
            "git-commit-check=git_commit_checker.cli:main",
            "gcc=git_commit_checker.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
