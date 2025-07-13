import os
import logging
import re
import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from PIL import Image
from .utils.io import write_file

logger = logging.getLogger(__name__)

class NewsletterRenderer:
    """Renders newsletter from article summaries"""
    
    def __init__(self, title="Research Digest", font="Arial, sans-serif", width=800):
        self.title = title
        self.font = font
        self.width = width

    def _render_html_to_png(self, html_file_path, output_png_path):
        """Renders an HTML file to a PNG image using Playwright."""
        device_pixel_ratio = 2  # For HiDPI
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=device_pixel_ratio)
            
            page.set_viewport_size({"width": self.width, "height": 1000})
            
            page.goto(f"file://{os.path.abspath(html_file_path)}")
            
            page.evaluate("""() => {
                document.body.style.padding = '40px';
                document.body.style.fontSize = '24px';
                document.body.style.boxSizing = 'border-box';
            }""")
            
            page.wait_for_load_state("networkidle")
            
            height = page.evaluate("document.documentElement.scrollHeight")
            
            page.set_viewport_size({"width": self.width, "height": height})
            
            screenshot = page.screenshot(full_page=True)
            
            browser.close()
        
        with open(output_png_path, 'wb') as f:
            f.write(screenshot)
        
        image = Image.open(output_png_path)
        image = image.crop((0, 0, self.width * device_pixel_ratio, height * device_pixel_ratio))
        image.save(output_png_path)
        logger.info(f"Rendered {html_file_path} to {output_png_path}")
    
    def get_youtube_thumbnail(self, url):
        """Get thumbnail URL for a YouTube video"""
        parsed_url = urlparse(url)
        if parsed_url.netloc in ['www.youtube.com', 'youtu.be']:
            if parsed_url.netloc == 'youtu.be':
                video_id = parsed_url.path[1:]
            else:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            if video_id:
                logger.info(f"YouTube thumbnail found: https://img.youtube.com/vi/{video_id}/0.jpg")
                return f"https://img.youtube.com/vi/{video_id}/0.jpg"
        logger.info("No YouTube thumbnail found")
        return None
    
    def get_og_image(self, url):
        """Get Open Graph image from a URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find('meta', property='og:image')
            if og_image:
                logger.info(f"OG image found: {og_image['content']}")
                return og_image['content']
        except requests.RequestException as e:
            logger.error(f"Error getting OG image from {url}: {e}")
        logger.info("No OG image found")
        return None
    
    def get_first_image(self, url):
        """Get first image from a URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            images = soup.find_all('img')
            for img in images:
                if 'src' in img.attrs:
                    src = img['src']
                    # Filter out common ad-related keywords
                    if not any(keyword in src.lower() for keyword in ['ad', 'banner', 'sponsor']):
                        # Filter out small images
                        if 'width' in img.attrs and 'height' in img.attrs:
                            width = int(img['width'])
                            height = int(img['height'])
                            if width > 100 and height > 100:
                                logger.info(f"First image found: {src}")
                                return src
                        else:
                            logger.info(f"First image found: {src}")
                            return src
                    # Filter out images with extensions like .svg or .png
                    elif not src.lower().endswith(('.svg', '.png')):
                        logger.info(f"First image found: {src}")
                        return src
        except requests.RequestException as e:
            logger.error(f"Error getting first image from {url}: {e}")
        logger.info("No first image found")
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
            logger.info(f"get_first_image returned: {thumbnail_url}")
            return thumbnail_url
        
        logger.warning("No thumbnail found")
        return None
    
    def download_thumbnails(self, summaries_data, thumbnails_dir):
        """Finds and downloads thumbnails for articles, updating the data dictionary."""
        os.makedirs(thumbnails_dir, exist_ok=True)
        for category, articles in summaries_data.items():
            for article in articles:
                thumbnail_url = self.get_thumbnail(article['url'])
                if thumbnail_url:
                    # Sanitize title for filename
                    safe_filename = self.sanitize_filename(article['original_title'])
                    # Get extension
                    ext = os.path.splitext(urlparse(thumbnail_url).path)[1]
                    if not ext or len(ext) > 5: # basic check for valid extension
                        ext = '.jpg'
                    thumbnail_filename = f"{safe_filename}{ext}"
                    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                    
                    if self.download_thumbnail(thumbnail_url, thumbnail_path):
                        # Store relative path for web app
                        article['thumbnail'] = os.path.join('thumbnails', thumbnail_filename)
                    else:
                        article['thumbnail'] = None
                else:
                    article['thumbnail'] = None
        return summaries_data
    
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
    
    def generate_top_news_image(self, summaries_data, output_path):
        """Generate a single PNG image with the top news content."""
        # Create HTML content for the image
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Top News</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}
                h1 {{
                    font-size: 24px;
                }}
                p {{
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <h1>Top News</h1>
        """
        for category, articles in summaries_data.items():
            for data in articles:
                logger.info(f"URL: {data['url']}")
                html_content += f"""
                <div>
                    <h2>{data['chinese_title']}</h2>
                    <p>{data['chinese_summary']}</p>
                    <p>Source: <a href="{data['source']}">{data['source'].replace("www.", "")}</a></p>
                </div>
                """
        html_content += """
        </body>
        </html>
        """

        # Create a temporary HTML file
        html_filename = os.path.join(os.path.dirname(output_path), "top_news.html")
        if write_file(html_filename, html_content):
            try:
                self._render_html_to_png(html_filename, output_path)
                logger.info(f"Top news image generated and saved to {output_path}")
            except Exception as e:
                logger.error(f"Error generating top news image: {e}", exc_info=True)
            finally:
                # Clean up temporary HTML file
                if os.path.exists(html_filename):
                    os.remove(html_filename)
        else:
            logger.error("Failed to create temporary HTML file for top news image")

        return
    
    def process(self, summaries_data, thumbnails_dir):
        """Process all steps to render newsletter assets like images."""
        # Generate top news image only if there are summaries
        if summaries_data:
            os.makedirs(thumbnails_dir, exist_ok=True)
            top_news_image_path = os.path.join(thumbnails_dir, "top_news.png")
            self.generate_top_news_image(summaries_data, top_news_image_path)
            return True
        return False
