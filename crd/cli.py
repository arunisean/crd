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
from .utils.stats import StatsManager
from .utils.api_client import APIClient

def create_parser():
    parser = argparse.ArgumentParser(description='Content Research Digest - Newsletter Generator')
    parser.add_argument('--config', '-c', default='.env', help='Path to configuration file')
    parser.add_argument('--output-dir', '-d', default='crd/web/static/output', help='Directory to store output files')
    parser.add_argument('--db-path', default='crd/crd.db', help='Path to SQLite database file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--feeds-config', default='feeds.json', help='Path to feeds configuration JSON file')
    parser.add_argument('--news-criteria', default='news_criteria.json', help='Path to news criteria JSON file')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Process command
    process_parser = subparsers.add_parser('process', help='Run the full pipeline for a category')
    process_parser.add_argument('category', help='Category to process')
    process_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD). Defaults to today.')
    process_parser.add_argument('--force', action='store_true', help='Force re-processing by clearing existing data for the category and date.')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch articles for a category')
    fetch_parser.add_argument('category', help='Category to fetch')
    fetch_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD). Defaults to today.')
    fetch_parser.add_argument('--force', action='store_true', help='Force re-fetching by clearing existing data for the category and date.')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze articles for a category')
    analyze_parser.add_argument('category', help='Category to analyze')
    analyze_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD). Defaults to today.')

    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Summarize articles for a category')
    summarize_parser.add_argument('category', help='Category to summarize')
    summarize_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD). Defaults to today.')

    # Render command
    render_parser = subparsers.add_parser('render', help='Render assets for a category')
    render_parser.add_argument('category', help='Category to render')
    render_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD). Defaults to today.')

    # Finalize command
    finalize_parser = subparsers.add_parser('finalize', help='Manually finalize articles.')
    finalize_parser.add_argument('--date', '-t', help='Target date (YYYY-MM-DD) to finalize.')
    finalize_parser.add_argument('--category', '-c', help='Category to finalize.')
    finalize_parser.add_argument('--all-stuck', action='store_true', help='Force finalize all articles stuck in intermediate states.')

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger('crd', level=log_level)

    config = Config(args.config, args.feeds_config)
    api_client = APIClient(config.api_url, config.api_key)
    stats_manager = StatsManager()

    os.makedirs(args.output_dir, exist_ok=True)

    db_manager = None
    try:
        db_manager = DatabaseManager(args.db_path)
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date() if args.date else datetime.now().date()
        date_str = target_date.strftime('%Y-%m-%d')
        output_dir_for_date = os.path.join(args.output_dir, date_str)
        os.makedirs(output_dir_for_date, exist_ok=True)

        if args.command == 'process':
            if args.force:
                logger.info(f"Force-updating category '{args.category}' for {date_str}.")
                db_manager.clear_category_for_date(args.category, date_str)
            
            run_fetch(logger, db_manager, config, args, stats_manager, target_date, date_str)
            run_analyze(logger, db_manager, api_client, config, args, stats_manager, date_str)
            run_summarize(logger, db_manager, api_client, config, args, stats_manager, date_str)
            run_render(logger, db_manager, args, stats_manager, date_str, output_dir_for_date)

        elif args.command == 'fetch':
            if args.force:
                logger.info(f"Force-fetching category '{args.category}' for {date_str}.")
                db_manager.clear_category_for_date(args.category, date_str)
            run_fetch(logger, db_manager, config, args, stats_manager, target_date, date_str)
        elif args.command == 'analyze':
            run_analyze(logger, db_manager, api_client, config, args, stats_manager, date_str)
        elif args.command == 'summarize':
            run_summarize(logger, db_manager, api_client, config, args, stats_manager, date_str)
        elif args.command == 'render':
            run_render(logger, db_manager, args, stats_manager, date_str, output_dir_for_date)
        elif args.command == 'finalize':
            if args.all_stuck:
                logger.info("Forcibly finalizing all stuck articles across all dates.")
                db_manager.force_finalize_all_articles()
            elif args.date and args.category:
                logger.info(f"Finalizing articles for category '{args.category}' on {args.date}.")
                db_manager.finalize_stuck_articles(args.category, args.date)
            else:
                logger.warning("Please provide --date and --category to finalize, or use --all-stuck.")

    finally:
        if db_manager:
            db_manager.close()
        stats_manager.report()

    return 0

def run_fetch(logger, db_manager, config, args, stats_manager, target_date, date_str):
    logger.info(f"--- Fetching category: {args.category} for {date_str} ---")
    fetcher = ArticleFetcher(
        db_manager=db_manager,
        feeds_path=args.feeds_config,
        stats_manager=stats_manager,
        target_date=target_date,
        max_workers=config.threads,
        keywords=config.keywords
    )
    fetcher.process(args.category, date_str)

def run_analyze(logger, db_manager, api_client, config, args, stats_manager, date_str):
    logger.info(f"--- Analyzing category: {args.category} for {date_str} ---")
    analyzer = ArticleAnalyzer(
        db_manager=db_manager,
        api_client=api_client,
        criteria_path=args.news_criteria,
        stats_manager=stats_manager,
        top_articles=config.top_articles,
        min_score_map=config.minimum_score_map,
        max_workers=config.threads,
        model=config.rating_model
    )
    analyzer.process(args.category, date_str)

def run_summarize(logger, db_manager, api_client, config, args, stats_manager, date_str):
    logger.info(f"--- Summarizing category: {args.category} for {date_str} ---")
    summarizer = ArticleSummarizer(
        db_manager=db_manager,
        api_client=api_client,
        stats_manager=stats_manager,
        model=config.summary_model,
        max_workers=config.threads
    )
    summarizer.process(args.category, date_str)

def run_render(logger, db_manager, args, stats_manager, date_str, output_dir_for_date):
    logger.info(f"--- Rendering category: {args.category} for {date_str} ---")
    renderer = NewsletterRenderer(db_manager=db_manager, stats_manager=stats_manager)
    renderer.process(args.category, date_str, output_dir_for_date)

if __name__ == "__main__":
    sys.exit(main())