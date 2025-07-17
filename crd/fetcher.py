import xml.etree.ElementTree as ET
import feedparser
import requests
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import time
import os
import logging
import csv
import json
from tqdm import tqdm

logger = logging.getLogger(__name__)

class ArticleFetcher:
    """Fetches articles from RSS feeds"""

    def __init__(self, db_manager, feeds_path, stats_manager=None, http_client=None, target_date=None, max_workers=10, keywords=None):
        self.http_client = http_client or requests
        self.db_manager = db_manager
        self.feeds_path = feeds_path
        self.target_date = target_date or datetime.now().date()
        self.max_workers = max_workers
        self.stats_manager = stats_manager
        self.keywords = keywords or []
        self.feeds = self._load_feeds()

    def _load_feeds(self):
        """Loads the feeds from the JSON file."""
        try:
            with open(self.feeds_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Feeds file not found at {self.feeds_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.feeds_path}")
            return {}

    def fetch_articles_from_rss(self, url):
        """Fetch articles from a single RSS feed"""
        articles = []
        try:
            logger.info(f"Fetching articles from {url}...")
            if self.stats_manager:
                self.stats_manager.increment('rss_feeds_fetched')
            response = self.http_client.get(url, timeout=30)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                try:
                    date_tuple = entry.get('published_parsed') or entry.get('updated_parsed')
                    if not date_tuple:
                        continue

                    published_date = datetime(*date_tuple[:6])
                    if published_date.date() == self.target_date:
                        article = {
                            'title': entry.title,
                            'link': entry.link,
                            'date': published_date.strftime('%Y-%m-%d')
                        }
                        articles.append(article)
                except AttributeError:
                    continue
                    
            logger.info(f"Found {len(articles)} articles from {url}")
        except Exception as e:
            if self.stats_manager:
                self.stats_manager.increment('rss_feeds_failed')
            logger.error(f"Error fetching articles from {url}: {e}")
        return articles
    
    def fetch_all_articles(self, urls):
        """Fetch articles from multiple RSS feeds concurrently"""
        articles = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.fetch_articles_from_rss, tqdm(urls, desc="Fetching RSS feeds")))
            for result in results:
                articles.extend(result)
        logger.info(f"Fetched a total of {len(articles)} articles")
        return articles
    
    def fetch_html_content(self, url):
        """Fetch HTML content from a URL"""
        try:
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            logger.info(f"Fetching HTML content from {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = self.http_client.get(url, timeout=30, headers=headers)
            if self.stats_manager:
                self.stats_manager.increment('http_fetches_success')
            response.raise_for_status()
            logger.info(f"Response status code: {response.status_code}")
            return response.text
        except Exception as e:
            if self.stats_manager:
                self.stats_manager.increment('http_fetches_failed')
            logger.error(f"Error fetching HTML content from {url}: {e}, URL: {url}")
            return None
    
    def fetch_html_with_playwright(self, url):
        """Fetch HTML content from a URL using Playwright for JS-heavy sites."""
        with self.stats_manager.time_block('fetcher_playwright_fetch') if self.stats_manager else open(os.devnull, 'w'):
            try:
                logger.info(f"Fetching HTML with Playwright from {url}")
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page()
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    content = page.content()
                    browser.close()
                    if self.stats_manager:
                        self.stats_manager.increment('playwright_fetches_success')
                    return content
            except PlaywrightError as e:
                if self.stats_manager:
                    self.stats_manager.increment('playwright_fetches_failed')
                logger.error(f"Error fetching HTML with Playwright from {url}: {e}")
                return None

    def extract_article_content(self, html):
        """Extract article content from HTML"""
        if not html:
            return None
        try:
            soup = BeautifulSoup(html, 'html.parser')
            selectors = [
                'article',
                'main',
                '[role="main"]',
                '.post-content',
                '.entry-content',
                '.td-post-content',
                '#content',
                '.content',
                '#main-content',
                '.main-content',
                '#article-body',
                '.article-body'
            ]
            content_element = None
            for selector in selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    logger.debug(f"Found content with selector: '{selector}'")
                    break
            if not content_element:
                content_element = soup.body
                if not content_element:
                    return None
                logger.debug("No specific content container found, falling back to body.")
                for tag_name in ['nav', 'header', 'footer', 'aside', 'script', 'style', '.sidebar', '#sidebar']:
                    for tag in content_element.select(tag_name):
                        tag.decompose()
            return content_element.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.error(f"Error extracting article content: {e}")
            return None
    
    def get_youtube_video_id(self, url):
        """Extract YouTube video ID from URL"""
        parsed_url = urlparse(url)
        if parsed_url.netloc in ['www.youtube.com', 'youtube.com']:
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.netloc == 'youtu.be':
            return parsed_url.path[1:]
        return None
    
    def fetch_youtube_subtitles(self, video_id):
        """Fetch subtitles from a YouTube video"""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join([entry['text'] for entry in transcript])
        except Exception as e:
            logger.error(f"Error fetching subtitles for video {video_id}: {e}")
            return None

    def process_single_article(self, article_info, use_playwright=False):
        """Process a single article"""
        article, category = article_info
        title = article.get('title')
        url = article.get('link')
        date = article.get('date')

        if not all([title, url, date]):
            logger.warning(f"Skipping article with missing data: {article}")
            return False

        logger.info(f"Processing article: {title} from {url}")

        content = None
        video_id = self.get_youtube_video_id(url)
        if video_id:
            content = self.fetch_youtube_subtitles(video_id)
        else:
            if use_playwright:
                html = self.fetch_html_with_playwright(url)
            else:
                html = self.fetch_html_content(url)
            content = self.extract_article_content(html) if html else None

        if content:
            if self.keywords and not any(keyword.lower() in content.lower() for keyword in self.keywords):
                logger.info(f"Skipping article: {title} (none of the keywords found)")
                return False

            article_data = {
                'link': url,
                'title': title,
                'date': date,
                'fetch_date': self.target_date.strftime('%Y-%m-%d'),
                'category': category,
                'content': content
            }
            if self.db_manager.add_article(article_data):
                logger.info(f"Saved article to DB: {title}")
                if self.stats_manager:
                    self.stats_manager.increment('articles_saved_to_db')
                return True
        return False

    def process_articles(self, articles_with_category, use_playwright=False):
        """Process multiple articles concurrently"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(
                lambda article_info: self.process_single_article(article_info, use_playwright),
                articles_with_category
            ))

        processed_count = sum(1 for result in results if result)
        logger.info(f"Processed and saved {processed_count} articles to DB out of {len(articles_with_category)}")
        return processed_count

    def process(self, category, date_str):
        """Process all articles for a category: fetch and save them"""
        if category not in self.feeds:
            logger.warning(f"Category '{category}' not found in feeds file.")
            return

        category_info = self.feeds[category]
        urls = category_info.get('feeds', [])
        use_playwright = category_info.get('use_playwright', False)

        if not urls:
            logger.warning(f"No feeds found for category '{category}'.")
            return

        articles = self.fetch_all_articles(urls)
        articles_with_category = [(article, category) for article in articles]
        self.process_articles(articles_with_category, use_playwright)

    def save_articles_to_csv(self, articles, csv_file):
        """Save articles to a CSV file"""
        try:
            with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Title', 'URL', 'Date'])
                for article in articles:
                    writer.writerow([article['title'], article['link'], article['date']])
            logger.info(f"Articles have been written to {csv_file}")
            return True
        except Exception as e:
            logger.error(f"Error writing articles to CSV: {e}")
            return