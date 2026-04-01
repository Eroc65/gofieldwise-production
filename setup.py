from setuptools import setup, find_packages

setup(
    name="auto-gpt-platform",
    version="0.1.0",
    description="AI-powered startup operations platform (Polsia-like)",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.14.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "twitter": ["tweepy>=4.14.0"],
        "meta": ["facebook-sdk>=3.1.0"],
        "database": ["psycopg2-binary>=2.9.9"],
        "browser": ["playwright>=1.42.0"],
        "all": [
            "tweepy>=4.14.0",
            "facebook-sdk>=3.1.0",
            "psycopg2-binary>=2.9.9",
            "playwright>=1.42.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "autogpt=autogpt.main:main",
        ],
    },
)
