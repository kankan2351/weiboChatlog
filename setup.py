from setuptools import setup, find_packages

try:
    with open("chatbot/README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Enhanced chatbot system with summarization and analytics"

try:
    with open("chatbot/requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    requirements = [
        "openai>=1.0.0",
        "chromadb>=0.4.0",
        "redis>=5.0.0",
        "python-dotenv>=1.0.0",
        "tiktoken>=0.5.0",
        "langdetect>=1.0.9",
        "pandas>=2.0.0",
        "numpy>=1.0.0",
        "textblob>=0.0.0",
        "aiohttp>=3.0.0",
        "asyncio>=3.4.3",
    ]

setup(
    name="chatbot",
    version="1.0.0",
    author="ChatBot Team",
    author_email="team@chatbot.example.com",
    description="Enhanced chatbot system with summarization and analytics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/chatbot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "chatbot=chatbot.main:main",
            "chatbot-cli=chatbot.cli:main"
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.env.example"],
    },
)
