"""
Setup script for Nixie's Trading Bot
"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='nixie-trading-bot',
    version='1.0.0',
    author='Blessing Omoregie',
    author_email='contact@github.com',
    description='High-Precision SMC Trading Bot with ML Integration',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Nixiestone/nixie-trading-bot',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial :: Investment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.9',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'nixie-bot=main:main',
        ],
    },
)