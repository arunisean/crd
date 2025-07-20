# Content Research Digest (CRD)

The Content Research Digest (CRD) is an automated pipeline that fetches articles from various RSS feeds, rates them based on custom criteria, summarizes the top-rated content using AI, and generates a web-based digest.

## Features

- **Multi-Source Categorization**: Fetch news from different categories (e.g., Crypto, AI, Academic), each with its own set of RSS feeds and rating criteria defined in `feeds.json`.
- **AI-Powered Rating & Summarization**: Uses an OpenAI-compatible API to rate articles and generate both English and Chinese summaries.
- **Database Backend**: Uses SQLite to store all fetched articles, ratings, and summaries, providing a persistent and queryable data store.
- **Modern UI**: A responsive, modern web interface built with Bootstrap.
- **Statistics Page**: A dedicated page to view content statistics.
- **Sharing Functionality**: Share articles with a custom-generated analysis image.
- **Web Interface**: A simple Flask-based web application to display the generated digest.
- **Automated Pipeline**: A command-line interface to run the entire process from fetching to rendering.
- **Extensible Configuration**: Easily configure API keys, models, and sources through a `.env` file.

## Project Structure

```
crd/
├── crd/
│   ├── __init__.py
│   ├── cli.py           # Main CLI entrypoint
│   ├── fetcher.py
│   ├── analyzer.py
│   ├── summarizer.py
│   ├── renderer.py
│   ├── utils/           # Utility modules (config, api, etc.)
│   ├── tests/           # Unit tests
│   └── web/             # Flask web application
│       ├── app.py
│       ├── static/
│       └── templates/
│           ├── index.html
│           ├── stats.html
│           └── ...
├── .env.example         # Example environment file
├── .gitignore
├── feeds.json           # Feeds and criteria configuration
├── newsletter_template.html
└── requirements.txt
```

## Setup and Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd crd
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browsers**
    The project uses Playwright to render HTML to an image. You need to install its browser dependencies.
    ```bash
    playwright install
    ```

5.  **Configure Environment Variables**
    Copy the example `.env` file and fill in your details.
    ```bash
    cp .env.example .env
    ```
    Now, edit `.env` with your API key and other settings.

6.  **Configure Feeds**
    Edit `feeds.json` to add or change categories, RSS feeds, and the AI rating criteria for each category.

## Usage

### Running the Content Pipeline

To generate a new newsletter, run the CLI. The output will be placed in `crd/web/static/output/` by default, ready for the web app to serve.

```bash
python -m crd.cli
```

You can specify a different output directory:
```bash
python -m crd.cli --output-dir /path/to/your/output
```

If you need to re-run the process for a day that already has output, use the `--force` flag:
```bash
python -m crd.cli --force
```

### Running the Web Server

To view the generated content, start the Flask web server.

```bash
python -m crd.web.app
```

- **Main Page**: Open your browser and navigate to `http://127.0.0.1:5000`.
- **Stats Page**: Access statistics at `http://127.0.0.1:5000/stats`.

## Automation

You can automate the content pipeline to run periodically using a `cron` job (on Linux/macOS).

1.  Open your crontab for editing: `crontab -e`
2.  Add the following line to run the pipeline every day at 9 AM. Make sure to use absolute paths to your virtual environment's Python executable and the project directory.

    ```cron
    # m h  dom mon dow   command
    0 9 * * * /path/to/your/crd/venv/bin/python -m crd.cli > /path/to/your/crd/cron.log 2>&1
    ```

This will update the website's content daily.