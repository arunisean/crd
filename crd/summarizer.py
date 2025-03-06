import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor
import pangu
from .utils.io import read_file, write_file, write_json

logger = logging.getLogger(__name__)

class ArticleSummarizer:
    """Summarizes articles using an AI API"""
    
    def __init__(self, api_client, model="gpt-4o", max_workers=10):
        self.api_client = api_client
        self.model = model
        self.max_workers = max_workers
    
    def extract_url_and_title(self, content):
        """Extract URL and title from article content"""
        lines = content.split('\n')
        url = ''
        title = ''
        
        for line in lines:
            if line.startswith('URL:'):
                url = line.replace('URL:', '').strip()
            elif line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
            
            if url and title:
                break
        
        return url, title
    
    def get_chinese_title_and_summary(self, title, content, url):
        """Get Chinese title and summary for an article"""
        # Translate title
        title_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a translator. Translate the given title to Chinese (zh-CN). Output only the translated title without any additional text."},
                {"role": "user", "content": f"Translate this title to Chinese:\n\n{title}"}
            ]
        }
        
        # Summarize and translate content
        content_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an AI assistant that summarizes articles in Chinese (zh-CN). Provide a concise summary in about 3-5 sentences in Chinese."},
                {"role": "user", "content": f"Summarize the following article in Chinese (zh-CN):\n\nTitle: {title}\n\nContent:\n{content}"}
            ]
        }
        
        try:
            # Get translated title
            title_response = self.api_client.request(title_payload)
            chinese_title = title_response['choices'][0]['message']['content'].strip()
            
            # Get Chinese summary
            content_response = self.api_client.request(content_payload)
            chinese_summary = content_response['choices'][0]['message']['content'].strip()
            
            # Apply pangu spacing
            chinese_title = pangu.spacing_text(chinese_title)
            chinese_summary = pangu.spacing_text(chinese_summary)
            
            return chinese_title, chinese_summary
        except Exception as e:
            logger.error(f"Error getting Chinese title and summary: {e}")
            return None, None
    
    def summarize_article(self, file_path, output_dir):
        """Summarize a single article"""
        filename = os.path.basename(file_path)
        logger.info(f"Summarizing article: {filename}")
        
        content = read_file(file_path)
        if not content:
            return filename, None
        
        url, title = self.extract_url_and_title(content)
        
        # Remove URL and title lines from content
        content = '\n'.join(line for line in content.split('\n') 
                           if not line.startswith(('URL:', 'Title:')))
        
        chinese_title, chinese_summary = self.get_chinese_title_and_summary(title, content, url)
        
        if chinese_summary and chinese_title:
            summary_filename = f"summary_{filename}"
            summary_path = os.path.join(output_dir, summary_filename)
            
            summary_content = f"标题：{chinese_title}\n\nURL: {url}\n\n{chinese_summary}"
            
            if write_file(summary_path, summary_content):
                logger.info(f"Chinese title and summary for {filename} saved")
                
                return filename, {
                    "url": url,
                    "original_title": title,
                    "chinese_title": chinese_title,
                    "chinese_summary": chinese_summary
                }
        
        logger.warning(f"Failed to get Chinese title and summary for {filename}")
        return filename, None
    
    def summarize_articles(self, articles_dir, summaries_dir):
        """Summarize multiple articles concurrently"""
        os.makedirs(summaries_dir, exist_ok=True)
        results = {}
        
        # Get all article files
        article_files = []
        for filename in os.listdir(articles_dir):
            if filename.endswith('.txt'):
                article_files.append(os.path.join(articles_dir, filename))
        
        # Summarize articles concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for filename, summary_data in executor.map(
                lambda file_path: self.summarize_article(file_path, summaries_dir),
                article_files
            ):
                if summary_data:
                    results[filename] = summary_data
        
        return results
    
    def process(self, articles_dir, summaries_dir, summaries_file):
        """Process all articles: summarize them and save results"""
        # Summarize all articles
        results = self.summarize_articles(articles_dir, summaries_dir)
        
        # Save summaries to file
        if write_json(summaries_file, results):
            logger.info(f"Summaries saved to {summaries_file}")
        
        return results