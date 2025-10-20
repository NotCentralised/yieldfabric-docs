"""
Setup script for YieldFabric Python Port
Python port of YieldFabric bash scripts for executing GraphQL commands
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "YieldFabric Python Port - Execute GraphQL commands from YAML files"

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [
        'requests>=2.31.0',
        'PyYAML>=6.0.1'
    ]

setup(
    name="yieldfabric-python",
    version="1.0.0",
    author="YieldFabric Team",
    author_email="team@yieldfabric.io",
    description="Python port of YieldFabric bash scripts for executing GraphQL commands",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yieldfabric/yieldfabric-docs",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "enhanced": [
            "ruamel.yaml>=0.17.32",
            "gql>=3.4.0",
            "httpx>=0.24.0",
            "python-dotenv>=1.0.0",
            "loguru>=0.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "yieldfabric-python=yieldfabric.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="yieldfabric, graphql, yaml, commands, execution, python, port",
    project_urls={
        "Bug Reports": "https://github.com/yieldfabric/yieldfabric-docs/issues",
        "Source": "https://github.com/yieldfabric/yieldfabric-docs",
        "Documentation": "https://github.com/yieldfabric/yieldfabric-docs/blob/main/python/README.md",
    },
)
