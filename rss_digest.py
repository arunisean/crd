import sys
import xml.etree.ElementTree as ET
import feedparser
import requests
from concurrent.futures import ThreadPoolExecutor
import csv
import os
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from dotenv import load_dotenv
import opencc



headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}
# 初始化 opencc 转换器
cc = opencc.OpenCC('s2t')  # 简体到繁体
cc_tw = opencc.OpenCC('s2tw')  # 简体到台湾繁体
cc_hk = opencc.OpenCC('s2hk')  # 简体到香港繁体

def extract_urls_from_opml(opml_file):
    tree = ET.parse(opml_file)
    root = tree.getroot()
    
    urls = []
    for outline in root.findall('.//outline'):
        url = outline.get('xmlUrl')
        if url:
            urls.append(url)
    
    return urls

def fetch_articles_from_rss(url):
    articles = []
    try:
        print(f"Fetching articles from {url}...")
        response = requests.get(url,headers=headers, timeout=10)

        feed = feedparser.parse(response.content)
        #print(f"feed from {url}: {feed.entries}")
        date_range = datetime.now() - timedelta(days=DATE_RANGE_DAYS)
        
        for entry in feed.entries:
            published_date = datetime(*entry.published_parsed[:6])
            if published_date > date_range:
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'date': published_date.strftime('%Y-%m-%d')
                }
                articles.append(article)
                print(f"Add {article} to Article list")
    except Exception as e:
        print(f"Error fetching articles from {url}: {e}")
    return articles

def fetch_all_articles(urls):
    articles = []
    # 使用线程池并发获取所有 RSS 源的文章
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        results = executor.map(fetch_articles_from_rss, urls)
        for result in results:
            articles.extend(result)
    return articles

def fetch_html_content(url):
    try:
        # Ensure the URL has a scheme
        if url.startswith('//'):
            url = 'http:' + url  # Add 'http:' prefix to URLs starting with '//'
        elif not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        response = requests.get(url, headers=headers,timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        # 捕获并打印异常
        print(f"Error fetching HTML content from {url}: {e}")
        return None

def extract_article_content(html):
    try:
        
        soup = BeautifulSoup(html, 'html.parser')
        
        article = soup.find('article')
        if article:
            return article.get_text()
        else:
            return None
    except Exception as e:
        
        print(f"Error extracting article content: {e}")
        return None

def save_article_content(title, content, url, date, folder, keywords):

    if not any(keyword.lower() in content.lower() for keyword in keywords):
        print(f"Skipping article: {title} (none of the keywords found)")
        return

    filename = f"{title}.txt".replace('/', '_').replace('\\', '_')
    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(f"Title: {title}\n")
            file.write(f"URL: {url}\n")
            file.write(f"Date: {date}\n\n")
            content = '\n'.join([line for line in content.split('\n') if line.strip()])
            file.write(content)
        print(f"Saved article: {filepath}")
    except Exception as e:
        print(f"Error saving article {title}: {e}")

def get_youtube_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed_url.query).get('v', [None])[0]
    elif parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    return None

def fetch_youtube_subtitles(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"Error fetching subtitles for video {video_id}: {e}")
        return None

def process_single_article(row, output_folder, keywords):
    title = row['Title']
    url = row['URL']
    date = row['Date']
    print(f"Processing article: {title} from {url}")
    
    video_id = get_youtube_video_id(url)
    if video_id:
        content = fetch_youtube_subtitles(video_id)
    else:
        html = fetch_html_content(url)
        content = extract_article_content(html) if html else None
    
    if content:
        save_article_content(title, content, url, date, output_folder, keywords)

def process_articles(csv_file, output_folder, keywords):
    os.makedirs(output_folder, exist_ok=True)
    
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        articles = list(reader)
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(lambda row: process_single_article(row, output_folder, keywords), articles)

import sys
import os
from crd.utils.config import Config
from crd.fetcher import ArticleFetcher
from crd.utils.logging import setup_logger

def main():
    # Setup logging
    logger = setup_logger('crd_fetcher')
    
    # Load configuration
    config = Config()
    
    # Create fetcher with configuration
    fetcher = ArticleFetcher(
        date_range_days=config.date_range_days,
        max_workers=config.threads,
        keywords=config.keywords
    )
    
    # Define output directory
    articles_dir = 'articles_text'
    articles_csv = 'articles.csv'
    
    # Create output directory
    os.makedirs(articles_dir, exist_ok=True)
    
    # Extract URLs from OPML
    logger.info(f"Extracting URLs from {config.opml_file}")
    urls = fetcher.extract_urls_from_opml(config.opml_file)
    
    # Fetch articles
    logger.info(f"Fetching articles from {len(urls)} RSS feeds")
    articles = fetcher.fetch_all_articles(urls)
    
    # Save articles to CSV
    fetcher.save_articles_to_csv(articles, articles_csv)
    
    # Process articles
    fetcher.process_articles(articles, articles_dir)
    
    logger.info(f"Completed fetching and processing articles")
    return 0

if __name__ == "__main__":
    sys.exit(main())

