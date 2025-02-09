from setuptools import setup, find_packages

setup(
    name="your_bot",
    version="0.1",
    packages=find_packages(include=['src', 'src.*']),
    install_requires=[
        'aiohttp>=3.9.0',
        'python-dotenv>=0.19.0',
    ],
    entry_points={
        'console_scripts': [
            'start-bot=src.main:main',
        ],
    },
) 