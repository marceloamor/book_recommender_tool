from setuptools import setup, find_packages

setup(
    name="goodreads-recommender",
    version="0.1.0",
    description="A tool to scrape Goodreads and recommend books",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "pandas>=2.1.1",
        "scikit-learn>=1.3.1",
        "tqdm>=4.66.1",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "goodreads-recommender=main:main",
        ],
    },
    python_requires=">=3.6",
) 