# RSS Content Digest System

A sophisticated system for aggregating, filtering, rating, summarizing, and delivering content from RSS feeds with a focus on Chinese language support.

## Features

- RSS Feed Aggregation
  - Reads RSS feeds from OPML configuration
  - Supports both article content and YouTube videos
  - Multi-threaded feed fetching for improved performance
  - Keyword-based content filtering

- Content Processing
  - Extracts article content from web pages
  - Retrieves YouTube video transcripts
  - Supports Chinese text conversion (Simplified/Traditional/Hong Kong/Taiwan variants)
  - Proper Chinese text spacing using Pangu

- AI-Powered Analysis
  - Rates articles using OpenAI's GPT models
  - Generates Chinese summaries for high-rated content
  - Translates titles to Chinese
  - Creates concise 3-5 sentence summaries

- Newsletter Generation
  - Creates formatted newsletters from processed content
  - Generates PNG renderings of content
  - Automated cleanup of temporary files

## System Requirements

Python 3.8 or higher required.

Python packages required:
- feedparser - RSS feed parsing
- requests - HTTP requests
- beautifulsoup4 - HTML parsing
- python-dotenv - Environment variable management
- jinja2 - HTML templating
- Pillow - Image processing
- playwright - Web automation
- youtube_transcript_api - YouTube transcript retrieval
- opencc-python-reimplemented - Chinese text conversion
- pangu - Chinese text spacing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/rss-digest.git
cd rss-digest
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Verify installation:
```bash
python -c "import feedparser, requests, bs4, dotenv, jinja2, PIL, playwright, youtube_transcript_api, opencc, pangu; print('All packages installed successfully')"
```

## Environment Variables

Required environment variables:
- KEYWORDS - Comma-separated list of keywords for content filtering
- THREADS - Number of threads for parallel processing
- DATE_RANGE_DAYS - Number of days of content to process (default: 3)
- CUSTOM_API_URL - OpenAI API endpoint
- API_KEY - OpenAI API key

## Workflow

1. RSS Feed Processing (`rss_digest.py`)
   - Reads RSS feeds from OPML file
   - Filters content by date and keywords
   - Saves articles to text files

2. Content Rating (`rating-openai.py`)
   - Rates articles using AI
   - Identifies high-value content

3. Content Summarization (`summerize-high-rated.py`)
   - Translates titles to Chinese
   - Generates Chinese summaries
   - Applies proper text spacing

4. Newsletter Creation (`make_newsletter.py`)
   - Creates formatted newsletter
   - Includes translated titles and summaries

5. Visual Rendering (`renderpng.py`)
   - Generates PNG versions of content

6. Cleanup (`cleanup.py`)
   - Removes temporary files
   - Maintains system organization

## Usage

Run the entire pipeline:
```bash
python main.py
```

This will execute all components in sequence, processing RSS feeds through to final newsletter generation.

## Output

- `articles.csv` - List of fetched articles
- `articles_text/` - Extracted article content
- `high_rated_articles/` - Filtered high-quality content
- `article_summaries/` - Chinese summaries
- `article_summaries.json` - JSON format of all processed content