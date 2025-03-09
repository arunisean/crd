import argparse
import sys
import logging
import os
from .utils.config import Config
from .utils.logging import setup_logger
from .fetcher import ArticleFetcher
from .analyzer import ArticleAnalyzer
from .summarizer import ArticleSummarizer
from .renderer import NewsletterRenderer
from .cleanup import Cleanup
from .utils.api_client import APIClient

def parse_args():
    parser = argparse.ArgumentParser(description='Content Research Digest - Newsletter Generator')
    
    parser.add_argument('--config', '-c', default='.env',
                        help='Path to configuration file')
    parser.add_argument('--output-dir', '-d', default='output',
                        help='Directory to store output files')
    parser.add_argument('--skip-cleanup', action='store_true',
                        help='Skip cleanup step')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    # Add template path argument
    parser.add_argument('--template', '-t', default='newsletter_template.html',
                        help='Path to newsletter HTML template')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger('crd', level=log_level)
    
    # Load configuration
    config = Config(args.config)
    
    # Setup API client
    api_client = APIClient(config.api_url, config.api_key)
    
    # Define directories and files
    articles_dir = os.path.join(args.output_dir, 'articles_text')
    high_rated_dir = os.path.join(args.output_dir, 'high_rated_articles')
    summaries_dir = os.path.join(args.output_dir, 'article_summaries')
    thumbnails_dir = os.path.join(args.output_dir, 'thumbnails')
    
    articles_csv = os.path.join(args.output_dir, 'articles.csv')
    ratings_json = os.path.join(args.output_dir, 'article_ratings.json')
    summaries_json = os.path.join(args.output_dir, 'article_summaries.json')
    newsletter_html = os.path.join(args.output_dir, 'newsletter.html')
    titles_links_txt = os.path.join(args.output_dir, 'titles_and_links.txt')
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run pipeline
    try:
        logger.info("Starting Content Research Digest pipeline")
        
        # 1. Fetch articles
        logger.info("Step 1: Fetching articles from RSS feeds")
        fetcher = ArticleFetcher(
            date_range_days=config.date_range_days,
            max_workers=config.threads,
            keywords=config.keywords
        )
        urls = fetcher.extract_urls_from_opml(config.opml_file)
        articles = fetcher.fetch_all_articles(urls)
        
        # Save articles to CSV
        fetcher.save_articles_to_csv(articles, articles_csv)
        
        # Process articles
        fetcher.process_articles(articles, articles_dir)
        
        # 2. Rate articles
        logger.info("Step 2: Rating articles")
        analyzer = ArticleAnalyzer(
            api_client=api_client,
            config=config,
            top_articles=config.top_articles,
            max_workers=config.threads,
            model=config.rating_model  # Use model from config
        )
        top_articles = analyzer.process(articles_dir, high_rated_dir, ratings_json)
        
        # 3. Summarize high-rated articles
        logger.info("Step 3: Summarizing high-rated articles")
        summarizer = ArticleSummarizer(
            api_client=api_client,
            model=config.summary_model,  # Use model from config
            max_workers=config.threads
        )
        summaries = summarizer.process(high_rated_dir, summaries_dir, summaries_json)
        
        # 4. Generate newsletter
        logger.info("Step 4: Generating newsletter")
        renderer = NewsletterRenderer(
            title=config.newsletter_title,
            font=config.newsletter_font
        )
        
        # Use the template path from args
        renderer.process(
            summaries_data=summaries,
            template_path=args.template,
            output_html=newsletter_html,
            output_txt=titles_links_txt,
            thumbnails_dir=thumbnails_dir
        )
        
        # 5. Cleanup
        if not args.skip_cleanup:
            logger.info("Step 5: Cleaning up and archiving files")
            items_to_archive = [
                articles_dir,
                high_rated_dir,
                summaries_dir,
                thumbnails_dir,
                ratings_json,
                summaries_json,
                articles_csv,
                newsletter_html,
                titles_links_txt
            ]
            
            items_to_copy = [
                newsletter_html,
                thumbnails_dir,
                titles_links_txt
            ]
            
            cleanup = Cleanup()
            cleanup.process(items_to_archive, items_to_copy)
        
        logger.info("Content Research Digest pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Error in pipeline: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())