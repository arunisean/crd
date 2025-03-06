import os
import logging
import re
import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from .utils.io import write_file

logger = logging.getLogger(__name__)

class NewsletterRenderer:
    """Renders newsletter from article summaries"""
    
    def __init__(self, title="Research Digest", font="Arial, sans-serif"):
        self.title = title
        self.font = font
    
    def get_youtube_thumbnail(self, url):
        """Get thumbnail URL for a YouTube video"""
        parsed_url = urlparse(url)
        if parsed_url.netloc in ['www.youtube.com', 'youtu.be']:
            if parsed_url.netloc == 'youtu.be':
                video_id = parsed_url.path[1:]
            else:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            if video_id:
                return f"https://img.youtube.com/vi/{video_id}/0.jpg"
        return None
    
    def get_og_image(self, url):
        """Get Open Graph image from a URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image:
                return og_image['content']
        except requests.RequestException as e:
            logger.error(f"Error getting OG image from {url}: {e}")
        return None
    
    def get_first_image(self, url):
        """Get first image from a URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            images = soup.find_all('img')
            for img in images:
                if 'src' in img.attrs:
                    src = img['src']
                    # Filter out common ad-related keywords
                    if not any(keyword in src.lower() for keyword in ['ad', 'banner', 'sponsor']):
                        return src
        except requests.RequestException as e:
            logger.error(f"Error getting first image from {url}: {e}")
        return None
    
    def get_thumbnail(self, url):
        """Get thumbnail for an article URL"""
        thumbnail_url = self.get_youtube_thumbnail(url)
        if thumbnail_url and self.is_url_reachable(thumbnail_url):
            return thumbnail_url
        
        thumbnail_url = self.get_og_image(url)
        if thumbnail_url and self.is_url_reachable(thumbnail_url):
            return thumbnail_url
        
        thumbnail_url = self.get_first_image(url)
        if thumbnail_url and self.is_url_reachable(thumbnail_url):
            return thumbnail_url
        
        return None
    
    def sanitize_filename(self, filename):
        """Sanitize filename to be safe for file systems"""
        # Remove or replace special characters
        filename = re.sub(r'[?<>:*|"\\/]', '', filename)
        filename = re.sub(r'[\s]+', '_', filename)  # Replace spaces with underscores
        filename = re.sub(r'[^\w\-_\.]', '', filename)  # Remove any remaining non-word characters
        return filename[:255]  # Truncate to max filename length
    
    def download_thumbnail(self, url, filename):
        """Download thumbnail from URL to file"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(response.content)
            return True
        except requests.RequestException as e:
            logger.error(f"Error downloading thumbnail from {url}: {e}")
            return False
    
    def is_url_reachable(self, url):
        """Check if a URL is reachable"""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def write_titles_and_links(self, summaries, output_file):
        """Write titles and links to a text file"""
        content = ""
        for data in summaries.values():
            content += f"{data['chinese_title']}\n{data['url']}\n\n"
        
        return write_file(output_file, content)
    
    def process_thumbnails(self, summaries, thumbnails_dir):
        """Process thumbnails for all articles"""
        os.makedirs(thumbnails_dir, exist_ok=True)
        
        for filename, data in summaries.items():
            url = data['url']
            thumbnail_url = self.get_thumbnail(url)
            
            if thumbnail_url:
                safe_filename = self.sanitize_filename(filename)
                thumbnail_filename = os.path.join(thumbnails_dir, f"{safe_filename.replace('.txt', '.jpg')}")
                if self.download_thumbnail(thumbnail_url, thumbnail_filename):
                    data['thumbnail'] = os.path.relpath(thumbnail_filename)
                else:
                    data['thumbnail'] = None
            else:
                data['thumbnail'] = None
            
            # Add source to data
            data['source'] = urlparse(url).netloc
    
    def render_newsletter(self, summaries, template_path, output_file):
        """Render newsletter HTML using Jinja2 template"""
        # Setup Jinja2 environment
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_file)
        
        # Render template
        newsletter_html = template.render(
            articles=summaries.values(),
            title=self.title,
            font=self.font
        )
        
        # Save the newsletter
        return write_file(output_file, newsletter_html)
    
    def process(self, summaries_data, template_path, output_html, output_txt, thumbnails_dir):
        """Process all steps to render the newsletter"""
        # Process thumbnails
        self.process_thumbnails(summaries_data, thumbnails_dir)
        
        # Render newsletter
        if self.render_newsletter(summaries_data, template_path, output_html):
            logger.info(f"Newsletter created: {output_html}")
        
        # Write titles and links
        if self.write_titles_and_links(summaries_data, output_txt):
            logger.info(f"Titles and links saved: {output_txt}")
        
        return True