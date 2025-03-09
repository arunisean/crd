import os
import json
import requests
import shutil
from dotenv import load_dotenv
from datetime import datetime
import re
from crd.utils.config import Config
from crd.analyzer import ArticleAnalyzer
from crd.utils.api_client import APIClient
from crd.utils.logging import setup_logger
import sys

def main():
    # Setup logging
    logger = setup_logger('crd_analyzer')
    
    # Load configuration
    config = Config()
    
    # Setup API client
    api_client = APIClient(config.api_url, config.api_key)
    
    # Define directories and files
    articles_dir = 'articles_text'
    high_rated_dir = 'high_rated_articles'
    ratings_json = 'article_ratings.json'
    
    # Create output directory
    os.makedirs(high_rated_dir, exist_ok=True)
    
    # Create analyzer
    analyzer = ArticleAnalyzer(
        api_client=api_client,
        rating_criteria=config.rating_criteria,
        top_articles=config.top_articles,
        max_workers=config.threads,
        model=config.rating_model
    )
    
    # Process articles
    logger.info("Rating articles")
    analyzer.process(articles_dir, high_rated_dir, ratings_json)
    
    logger.info("Completed rating articles")
    return 0

if __name__ == "__main__":
    sys.exit(main())