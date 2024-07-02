## Project Introduction

This project is an automated system for processing and generating newsletters. It retrieves articles from RSS feeds, performs rating and generates summaries, and ultimately creates an HTML newsletter with article summaries.

## File Structure

- main.py: Main script that runs other scripts sequentially.
- rss_digest.py: Retrieves articles from RSS feeds and saves them as CSV files.
- rating-openai.py: Rates the articles using a custom API and copies high-rated articles to a specified directory.
- summerize-high-rated.py: Generates summaries for high-rated articles and saves them.
- make_newsletter.py: Generates an HTML newsletter with article summaries.
- renderpng.py: Renders the HTML newsletter as a PNG image.
- cleanup.py: Cleans up generated files and directories and creates an archive.

## Environment Setup

Dependency Installation

Make sure the following dependencies are installed. You can use the following command to install them:

```bash
pip install -r requirements.txt
playwright install
```

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
```

## Usage

### Preparation

Save your subscription OPML file in the current directory and rename it to `feeds.opml`.

### Running the Main Script

Run the following command in the project root directory:

```bash
python3 main.py
```

This command will run all the sub-scripts sequentially, performing the entire process from article retrieval to rating, summarization, and newsletter generation.

### Notes

- Make sure to configure the environment variables correctly before running the scripts.
- Internet connectivity may be required during the execution to access RSS feeds and the custom API.
- The default script uses OpenAI's GPT-3.5-Turbo model for rating. If you want to use a different model, modify the `model` variable in `rating-openai.py`.
- The default script uses OpenAI's GPT-4o model for summarization. If you want to use a different model, modify the `model` variable in `summerize-high-rated.py`.

### Contributing

Pull requests and issue reports are welcome. Feel free to reach out with any suggestions or improvements.

### License

This project is licensed under the MIT License. See the LICENSE file for more details.