# CRD Core Modules

This directory contains the core logic for the Content Research Digest pipeline.

-   `cli.py`: The main command-line interface entry point that orchestrates the entire pipeline.
-   `fetcher.py`: Responsible for fetching articles from RSS feeds and external URLs.
-   `analyzer.py`: Handles the rating of articles using an AI model based on configured criteria.
-   `summarizer.py`: Summarizes the top-rated articles using an AI model and stores them in the database. Designed to be robust against partial failures.
-   `renderer.py`: Generates output assets, such as images for the newsletter, from the processed data.
-   `database.py`: Manages all interactions with the SQLite database, which serves as the central data store.
-   `utils/`: Contains utility modules for configuration, API clients, logging, and operational statistics.
-   `web/`: A Flask-based web application to display the generated digest.