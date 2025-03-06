from setuptools import setup, find_packages

setup(
    name="crd",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "feedparser",
        "requests",
        "beautifulsoup4",
        "python-dotenv",
        "jinja2",
        "Pillow",
        "playwright",
        "youtube_transcript_api",
        "opencc-python-reimplemented",
        "pangu",
        # Missing dependencies
        "concurrent-log-handler",  # For rotating log files
        "tqdm"  # For progress bars
    ],
    entry_points={
        'console_scripts': [
            'crd=crd.cli:main',
        ],
    },
    author="Arun",
    author_email="arun@example.com",
    description="Content Research Digest - Newsletter Generator",
    keywords="rss, newsletter, content, digest",
    python_requires=">=3.6",
)