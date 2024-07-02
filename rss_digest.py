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


load_dotenv()
KEYWORDS = os.getenv("KEYWORDS").split(',')
THREADS = int(os.getenv("THREADS", 10))
DATE_RANGE_DAYS = int(os.getenv("DATE_RANGE_DAYS", 7))

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
        response = requests.get(url, timeout=10)
        feed = feedparser.parse(response.content)
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
        
        # 发送 HTTP 请求获取 HTML 内容
        response = requests.get(url, timeout=10)
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

if __name__ == "__main__":
    opml_file = 'feeds.opml'
    urls = extract_urls_from_opml(opml_file)
    articles = fetch_all_articles(urls)
    

    with open('articles.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'URL', 'Date'])
        for article in articles:
            writer.writerow([article['title'], article['link'], article['date']])
    
    print("Articles have been written to articles.csv")
    

    process_articles('articles.csv', 'articles_text', KEYWORDS)

