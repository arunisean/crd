import argparse
import sys
import logging
import os
import json
from datetime import datetime, timedelta
import tempfile
from .utils.config import Config
from .utils.logging import setup_logger
from .fetcher import ArticleFetcher
from .analyzer import ArticleAnalyzer
from .summarizer import ArticleSummarizer
from .renderer import NewsletterRenderer
from .utils.api_client import APIClient
from .utils.io import write_json

def parse_args():
    parser = argparse.ArgumentParser(description='Content Research Digest - Newsletter Generator')
    
    parser.add_argument('--config', '-c', default='.env',
                        help='Path to configuration file')
    parser.add_argument('--output-dir', '-d', default='crd/web/static/output',
                        help='Directory to store output files')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    # Add template path argument
    parser.add_argument('--template', '-t', default='newsletter_template.html',
                        help='Path to newsletter HTML template')
    parser.add_argument('--feeds-config', default='feeds.json',
                        help='Path to feeds configuration JSON file')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger('crd', level=log_level)
    
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Output directory: {args.output_dir}")

    # Load configuration
    config = Config(args.config, args.feeds_config)
    
    # Setup API client
    api_client = APIClient(config.api_url, config.api_key)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Loop through the last 3 days to ensure data is up-to-date
    for i in range(3):
        target_date = datetime.now().date() - timedelta(days=i)
        date_str = target_date.strftime('%Y-%m-%d')
        output_dir_for_date = os.path.join(args.output_dir, date_str)

        if os.path.exists(output_dir_for_date):
            logger.info(f"Data for {date_str} already exists. Skipping.")
            continue

        logger.info(f"--- Generating data for {date_str} ---")
        os.makedirs(output_dir_for_date, exist_ok=True)

        # Run pipeline for the target date
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.info(f"Using temporary directory: {temp_dir}")
                all_summaries = {}
                all_top_articles = {}

                for category, settings in config.feeds_config.items():
                    try:
                        logger.info(f"--- Processing category: {category} for {date_str} ---")
                        category_slug = category.lower().replace(' ', '_').replace('&', 'and')

                        # Define category-specific paths in temp_dir
                        articles_dir_cat = os.path.join(temp_dir, 'articles_text', category_slug)
                        high_rated_dir_cat = os.path.join(temp_dir, 'high_rated_articles', category_slug)
                        summaries_dir_cat = os.path.join(temp_dir, 'article_summaries', category_slug)
                        ratings_json_cat = os.path.join(temp_dir, f'ratings_{category_slug}.json')

                        # 1. Fetch articles for the specific date
                        fetcher = ArticleFetcher(
                            target_date=target_date,
                            max_workers=config.threads,
                            keywords=config.keywords
                        )
                        articles = fetcher.fetch_all_articles(settings['feeds'])
                        fetcher.process_articles(articles, articles_dir_cat)

                        # 2. Rate articles
                        analyzer = ArticleAnalyzer(
                            api_client=api_client,
                            rating_criteria=settings['rating_criteria'],
                            top_articles=config.top_articles,
                            max_workers=config.threads,
                            model=config.rating_model
                        )
                        top_articles = analyzer.process(articles_dir_cat, high_rated_dir_cat, ratings_json_cat)
                        if top_articles:
                            all_top_articles[category] = top_articles

                            # 3. Summarize high-rated articles
                            summarizer = ArticleSummarizer(
                                api_client=api_client,
                                model=config.summary_model,
                                max_workers=config.threads
                            )
                            summaries = summarizer.process(high_rated_dir_cat, summaries_dir_cat, os.path.join(temp_dir, f'summaries_{category_slug}.json'))
                            if summaries:
                                all_summaries[category] = list(summaries.values())
                    except Exception as e:
                        logger.error(f"Failed to process category '{category}' for {date_str}. Skipping.", exc_info=True)
                        continue

                # 4. Generate assets and final JSON files for the date
                logger.info(f"--- Finalizing data for {date_str} ---")
                thumbnails_dir = os.path.join(output_dir_for_date, 'thumbnails')
                renderer = NewsletterRenderer(
                    title=config.newsletter_title,
                    font=config.newsletter_font,
                    width=config.width
                )
                # Download thumbnails and add local paths to summary data
                all_summaries_with_thumbnails = renderer.download_thumbnails(all_summaries, thumbnails_dir)
                # Generate top news image
                renderer.process(all_summaries_with_thumbnails, thumbnails_dir)

                # Write final JSON files to dated output directory
                write_json(os.path.join(output_dir_for_date, 'summaries.json'), all_summaries_with_thumbnails)
                write_json(os.path.join(output_dir_for_date, 'top_articles.json'), all_top_articles)

                logger.info(f"Successfully generated data for {date_str}")

            except Exception as e:
                logger.error(f"A critical error occurred processing {date_str}: {e}", exc_info=True)
                continue # Continue to the next day

    return 0

if __name__ == "__main__":
    sys.exit(main())