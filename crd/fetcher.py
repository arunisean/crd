import xml.etree.ElementTree as ET
import feedparser
import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import os
import logging
import csv
from .utils.io import write_file
from tqdm import tqdm

logger = logging.getLogger(__name__)

class ArticleFetcher:
    """Fetches articles from RSS feeds"""
    
    def __init__(self, http_client=None, date_range_days=7, max_workers=10, keywords=None):
        self.http_client = http_client or requests
        self.date_range_days = date_range_days
        self.max_workers = max_workers
        self.keywords = keywords or []
    
    def extract_urls_from_opml(self, opml_file):
        """Extract RSS feed URLs from an OPML file"""
        try:
            tree = ET.parse(opml_file)
            root = tree.getroot()
            
            urls = []
            for outline in root.findall('.//outline'):
                url = outline.get('xmlUrl')
                if url:
                    urls.append(url)
            
            logger.info(f"Extracted {len(urls)} URLs from {opml_file}")
            return urls
        except Exception as e:
            logger.error(f"Error extracting URLs from {opml_file}: {e}")
            return []
    
    def fetch_articles_from_rss(self, url):
        """Fetch articles from a single RSS feed"""
        articles = []
        try:
            logger.info(f"Fetching articles from {url}...")
            response = self.http_client.get(url, timeout=10)
            feed = feedparser.parse(response.content)
            date_range = datetime.now() - timedelta(days=self.date_range_days)
            
            for entry in feed.entries:
                try:
                    published_date = datetime(*entry.published_parsed[:6])
                    if published_date > date_range:
                        article = {
                            'title': entry.title,
                            'link': entry.link,
                            'date': published_date.strftime('%Y-%m-%d')
                        }
                        articles.append(article)
                except AttributeError:
                    # Skip entries without required attributes
                    continue
                    
            logger.info(f"Found {len(articles)} articles from {url}")
        except Exception as e:
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
            # Ensure the URL has a scheme
            if url.startswith('//'):
                url = 'http:' + url  # Add 'http:' prefix to URLs starting with '//'
            elif not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            response = self.http_client.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching HTML content from {url}: {e}")
            return None
    
    def extract_article_content(self, html):
        """Extract article content from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            article = soup.find('article')
            if article:
                return article.get_text()
            else:
                return None
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
    
    def save_article_content(self, title, content, url, date, folder):
        """Save article content to a file if it contains keywords"""
        if self.keywords and not any(keyword.lower() in content.lower() for keyword in self.keywords):
            logger.info(f"Skipping article: {title} (none of the keywords found)")
            return False
        
        filename = f"{title}.txt".replace('/', '_').replace('\\', '_')
        filepath = os.path.join(folder, filename)
        
        article_content = f"Title: {title}\nURL: {url}\nDate: {date}\n\n"
        article_content += '\n'.join([line for line in content.split('\n') if line.strip()])
        
        if write_file(filepath, article_content):
            logger.info(f"Saved article: {filepath}")
            return True
        return False
    
    def process_single_article(self, article, output_folder):
        """Process a single article"""
        title = article['title']
        url = article['link']
        date = article['date']
        logger.info(f"Processing article: {title} from {url}")
        
        video_id = self.get_youtube_video_id(url)
        if video_id:
            content = self.fetch_youtube_subtitles(video_id)
        else:
            html = self.fetch_html_content(url)
            content = self.extract_article_content(html) if html else None
        
        if content:
            return self.save_article_content(title, content, url, date, output_folder)
        return False
    def process_articles(self, articles, output_folder):
        """Process multiple articles concurrently"""
        os.makedirs(output_folder, exist_ok=True)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(
                lambda article: self.process_single_article(article, output_folder), 
                articles
            ))
        
        processed_count = sum(1 for result in results if result)
        logger.info(f"Processed {processed_count} articles out of {len(articles)}")
        return processed_count  # Add this return statement
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