import os
import json
import logging
import re
from crd.utils.config import Config
from crd.summarizer import ArticleSummarizer
from crd.utils.io import read_file, write_file, write_json
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = Config()
    # Access api_client from config
    from crd.utils.api_client import APIClient
    api_client = APIClient(config.api_url, config.api_key)
    summarizer = ArticleSummarizer(api_client=api_client, model=config.summary_model)

    high_rated_dir = 'output/high_rated_articles'
    summaries_dir = 'output/article_summaries'
    summaries_file = 'output/article_summaries.json'

    os.makedirs(summaries_dir, exist_ok=True)

    results = {}

    for filename in os.listdir(high_rated_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(high_rated_dir, filename)
            logger.info(f"Processing {filename}...")

            content = read_file(file_path)
            if not content:
                logger.warning(f"Could not read content from {filename}")
                continue

            # Extract URL and title from content
            url = ''
            title = ''
            for line in content.splitlines():
                if line.startswith('URL:'):
                    url = line.replace('URL:', '').strip()
                elif line.startswith('Title:'):
                    title = line.replace('Title:', '').strip()

            # Remove URL and title lines from content for summarization
            content = '\n'.join(line for line in content.splitlines() if not line.startswith(('URL:', 'Title:')))

            # Summarize article
            file_base_name, summary_data = summarizer.summarize_article(file_path, summaries_dir)

            if summary_data:
                results[filename] = summary_data
                logger.info(f"Summaries for {filename} saved.")
            else:
                logger.warning(f"Failed to get summaries for {filename}")

    # Save results to a JSON file
    with open(summaries_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    logger.info(f"Summaries saved to {summaries_file}")
    logger.info(f"Article summaries saved in {summaries_dir}")

if __name__ == "__main__":
    main()