from setuptools import setup, find_packages

setup(
    name="rubkoff-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiogram>=3.3.0",
        "aiohttp>=3.9.0",
        "aiosqlite>=0.19.0",
        "beautifulsoup4>=4.12.0",
        "httpx>=0.26.0",
        "openai>=1.12.0",
        "python-dotenv>=1.0.0",
        "SQLAlchemy>=2.0.0",
        "typing-extensions>=4.9.0",
        "pydantic>=2.5.0",
        "alembic>=1.13.0"
    ]
) 