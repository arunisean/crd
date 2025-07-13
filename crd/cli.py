import argparse
import sys
import logging
import os
import json
from datetime import datetime, timedelta
from .utils.config import Config
from .utils.logging import setup_logger
from .database import DatabaseManager
from .fetcher import ArticleFetcher
from .analyzer import ArticleAnalyzer
from .summarizer import ArticleSummarizer
from .renderer import NewsletterRenderer
from .utils.api_client import APIClient

def parse_args():
    parser = argparse.ArgumentParser(description='Content Research Digest - Newsletter Generator')
    
    parser.add_argument('--config', '-c', default='.env',
                        help='Path to configuration file')
    parser.add_argument('--output-dir', '-d', default='crd/web/static/output',
                        help='Directory to store output files')
    parser.add_argument('--db-path', default='crd/crd.db', help='Path to SQLite database file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--feeds-config', default='feeds.json',
                        help='Path to feeds configuration JSON file')
    parser.add_argument('--force', action='store_true',
                        help='Force re-processing of dates even if output data already exists')
    parser.add_argument('--force-category',
                        help='Force re-processing of a specific category even if output data already exists')
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
    
    # Setup Database
    db_manager = DatabaseManager(args.db_path)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Loop through the last 3 days to ensure data is up-to-date
    for i in range(3):
        try:
            target_date = datetime.now().date() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            output_dir_for_date = os.path.join(args.output_dir, date_str)
            os.makedirs(output_dir_for_date, exist_ok=True)

            # Check for forced category
            is_force_category = args.force_category and args.force_category.lower() in [c.lower() for c in config.feeds_config.keys()]

            # If not forcing, check if we can skip
            if not args.force and not is_force_category:
                if os.path.exists(output_dir_for_date) and os.listdir(output_dir_for_date):
                    logger.info(f"Data for {date_str} already exists. Skipping.")
                    continue

            if args.force:
                logger.info(f"Force-processing all categories for {date_str}.")

            logger.info(f"--- Generating data for {date_str} ---")

            for category, settings in config.feeds_config.items():
                try:
                    # If forcing a specific category, clear its old data for the day
                    if is_force_category and category.lower() == args.force_category.lower():
                        logger.info(f"Force-updating category '{category}' for {date_str}.")
                        db_manager.clear_category_for_date(category, date_str)
                    elif is_force_category and category.lower() != args.force_category.lower():
                        continue

                    logger.info(f"--- Processing category: {category} for {date_str} ---")

                    # 1. Fetch articles
                    fetcher = ArticleFetcher(
                        db_manager=db_manager,
                        target_date=target_date,
                        max_workers=config.threads,
                        keywords=config.keywords
                    )
                    articles = fetcher.fetch_all_articles(settings['feeds'])
                    articles_with_category = [(art, category) for art in articles]
                    use_playwright = settings.get('use_playwright', False)
                    fetcher.process_articles(articles_with_category, use_playwright=use_playwright)

                    # 2. Rate articles and select top ones
                    analyzer = ArticleAnalyzer(
                        db_manager=db_manager,
                        api_client=api_client,
                        rating_criteria=settings['rating_criteria'],
                        top_articles=config.top_articles,
                        max_workers=config.threads,
                        model=config.rating_model
                    )
                    analyzer.process(category, date_str)

                    # 3. Summarize high-rated articles
                    summarizer = ArticleSummarizer(
                        api_client=api_client,
                        model=config.summary_model,
                        max_workers=config.threads
                    )
                    summarizer.process(category, date_str)

                    # 4. Process thumbnails
                    thumbnails_dir = os.path.join(output_dir_for_date, 'thumbnails')
                    renderer = NewsletterRenderer(db_manager=db_manager)
                    renderer.process_thumbnails(category, date_str, thumbnails_dir)

                except Exception as e:
                    logger.error(f"Failed to process category '{category}' for {date_str}. Skipping.", exc_info=True)
                    continue

            # 5. Generate final assets for the date (e.g., top news image)
            logger.info(f"--- Finalizing assets for {date_str} ---")
            renderer = NewsletterRenderer(
                db_manager=db_manager,
                title=config.newsletter_title,
                font=config.newsletter_font,
                width=config.width
            )
            renderer.process(date_str, output_dir_for_date)

            logger.info(f"Successfully generated data for {date_str}")

        except Exception as e:
            logger.error(f"A critical error occurred processing date index {i}: {e}", exc_info=True)
            continue # Continue to the next day
    
    db_manager.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())