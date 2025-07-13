# Content Research Digest (CRD) Core Module

This directory contains the core logic for the Content Research Digest application. Each file represents a step in the pipeline of fetching, analyzing, summarizing, and rendering content for a newsletter.

- `__init__.py`: Package initializer.
- `analyzer.py`: Contains `ArticleAnalyzer` for rating articles.
- `cleanup.py`: Contains `Cleanup` class for archiving and cleaning up generated files.
- `cli.py`: The main command-line interface for orchestrating the CRD pipeline.
- `database.py`: Contains `DatabaseManager` for all SQLite database operations.
- `fetcher.py`: Contains `ArticleFetcher` for fetching articles from RSS feeds and extracting content. It supports both standard requests and Playwright for dynamically rendered pages and now correctly interacts with the database.
- `renderer.py`: Contains `NewsletterRenderer` for generating a top news summary image, handling thumbnail downloads, and taking article screenshots as a fallback.
- `summarizer.py`: Contains `ArticleSummarizer` for summarizing articles.