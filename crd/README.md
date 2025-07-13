# Content Research Digest (CRD) Core Module

This directory contains the core logic for the Content Research Digest application. Each file represents a step in the pipeline of fetching, analyzing, summarizing, and rendering content for a newsletter.

- `__init__.py`: Package initializer.
- `analyzer.py`: Contains `ArticleAnalyzer` for rating articles.
- `cleanup.py`: Contains `Cleanup` class for archiving and cleaning up generated files.
- `cli.py`: The main command-line interface for running the CRD pipeline.
- `fetcher.py`: Contains `ArticleFetcher` for fetching articles from RSS feeds.
- `renderer.py`: Contains `NewsletterRenderer` for generating the final HTML newsletter.
- `summarizer.py`: Contains `ArticleSummarizer` for summarizing articles.