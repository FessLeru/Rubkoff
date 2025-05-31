from setuptools import setup, find_packages

setup(
    name="rubkoff-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiogram==3.20.0.post0",
        "aiohttp==3.11.18",
        "aiosqlite==0.21.0",
        "beautifulsoup4==4.13.4",
        "httpx==0.28.1",
        "openai==1.78.1",
        "python-dotenv==1.1.0",
        "SQLAlchemy==2.0.41",
        "typing_extensions==4.13.2",
        "pydantic==2.11.4",
        "alembic==1.15.2"
    ]
) 