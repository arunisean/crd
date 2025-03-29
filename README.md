# Content Research Digest (CRD)

## Overview
Automated newsletter generation system that:
1. Fetches articles from RSS feeds
2. Rates articles based on criteria 
3. Summarizes top articles
4. Generates newsletter with thumbnails

## Installation
```bash
pip install -e .
```

## Project Introduction

This project is an automated system for processing and generating newsletters. It retrieves articles from RSS feeds, performs rating and generates summaries, and ultimately creates an HTML newsletter with article summaries.

## File Structure
- crd/ - Core package containing all business logic
  - analyzer.py - Article rating logic
  - summarizer.py - Article summarization
  - renderer.py - Newsletter generation
  - cli.py - Command line interface
- main.py - Main entry point
- newsletter_template.html - HTML template
- feeds.opml - RSS feed subscriptions

## Configuration
### Environment Variables

Create a `.env` file in the project root directory and add the following content:
```
CUSTOM_API_URL=https://api.openai.com/v1/chat/completions  # URL of the custom OpenAI compatible API for article rating and summarization
API_KEY=your_api_key  # API key to access the custom API
RATING_CRITERIA=your_rating_criteria  # Criteria or rules for article rating
TOP_ARTICLES=5  # Number of top-rated articles to select
NEWSLETTER_TITLE=Article Summary Newsletter  # Title of the generated newsletter
NEWSLETTER_FONT=Arial, sans-serif  # Font used in the newsletter
WIDTH=800  # Width for rendering the HTML newsletter
KEYWORDS=keyword1,keyword2  # Keywords used for filtering articles (comma-separated)
THREADS=10  # Number of threads used for concurrent processing of RSS feeds
DATE_RANGE_DAYS=7  # Date range (in days) for retrieving articles from RSS feeds
RATING_MODEL=gpt-3.5-turbo  # Model used for rating articles
SUMMARY_MODEL=gpt-4o  # Model used for summarizing articles
TRANSLATION_MODEL=gpt-4o  # Model used for translating content
```

## Usage

### Preparation

Save your subscription OPML file in the current directory and rename it to `feeds.opml`.

### Running the Main Script

Run the following command in the project root directory:

```bash
python main.py
```

This command will run all the sub-scripts sequentially, performing the entire process from article retrieval to rating, summarization, and newsletter generation.

### Advanced options
crd --output-dir my_output --template custom_template.html --skip-cleanup

### Contributing

Pull requests and issue reports are welcome. Feel free to reach out with any suggestions or improvements.

### License

This project is licensed under the MIT License. See the LICENSE file for more details.