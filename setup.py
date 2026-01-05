#!/usr/bin/env python3
"""
Setup script for Day-1 Framework
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="netskope-sdet-framework",
    version="1.0.0",
    description="Comprehensive SDET automation framework for cybersecurity API testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Day-1 Team",
    author_email="sdet@netskope.com",
    url="https://github.com/netskope/sdet-framework",
    
    # Package configuration
    packages=find_packages(include=['src', 'src.*', 'tests', 'tests.*']),
    package_dir={'': '.'},
    
    # Include additional files
    include_package_data=True,
    package_data={
        '': [
            'config/*.yaml',
            'config/*.yml', 
            'config/*.json',
            'config/*.conf',
            'config/grafana/**/*',
            'scripts/*.sh',
            'scripts/*.js',
            'tests/mock_responses/**/*.json',
            'docs/*.md',
            '*.yml',
            '*.yaml'
        ]
    },
    
    # Dependencies
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest-cov>=4.0.0',
            'pytest-xdist>=3.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'pre-commit>=3.0.0'
        ],
        'security': [
            'bandit>=1.7.0',
            'safety>=2.0.0',
            'semgrep>=1.0.0'
        ],
        'performance': [
            'locust>=2.0.0',
            'memory-profiler>=0.60.0',
            'py-spy>=0.3.0'
        ],
        'monitoring': [
            'prometheus-client>=0.16.0',
            'opentelemetry-api>=1.15.0',
            'opentelemetry-sdk>=1.15.0'
        ]
    },
    
    # Entry points for CLI commands
    entry_points={
        'console_scripts': [
            'netskope-sdet=src.cli:main',
            'netskope-env=src.environment_manager:main',
            'netskope-services=src.service_manager:main',
            'netskope-local=scripts.start_local_environment:main'
        ]
    },
    
    # Python version requirement
    python_requires='>=3.9',
    
    # Classification
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Topic :: Security',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Framework :: Pytest'
    ],
    
    # Keywords for PyPI
    keywords=[
        'testing', 'sdet', 'automation', 'cybersecurity', 'api-testing',
        'netskope', 'security-testing', 'integration-testing', 'pytest',
        'docker', 'kubernetes', 'redis', 'kafka', 'mongodb', 'aws'
    ],
    
    # Project URLs
    project_urls={
        'Documentation': 'https://github.com/netskope/sdet-framework/docs',
        'Source': 'https://github.com/netskope/sdet-framework',
        'Tracker': 'https://github.com/netskope/sdet-framework/issues',
    },
    
    # Zip safe
    zip_safe=False,
)