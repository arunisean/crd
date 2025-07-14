import os
import logging
import re
import requests
from urllib.parse import urlparse, parse_qs, urljoin
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from PIL import Image
from .utils.io import write_file

logger = logging.getLogger(__name__)

class NewsletterRenderer:
    """Renders newsletter from article summaries"""

    def __init__(self, db_manager, stats_manager=None, title="Research Digest", font="Arial, sans-serif", width=800):
        self.db_manager = db_manager
        self.title = title
        self.font = font
        self.stats_manager = stats_manager
        self.width = width

    def _render_html_to_png(self, html_file_path, output_png_path):
        """Renders an HTML file to a PNG image using Playwright."""
        device_pixel_ratio = 2  # For HiDPI
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=device_pixel_ratio)
            
            page.set_viewport_size({"width": self.width, "height": 1000})
            
            page.goto(f"file://{os.path.abspath(html_file_path)}", wait_until='networkidle', timeout=60000)
            
            page.evaluate("""() => {
                document.body.style.padding = '40px';
                document.body.style.fontSize = '24px';
                document.body.style.boxSizing = 'border-box';
            }""")
            
            page.wait_for_load_state("networkidle", timeout=60000)
            
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
        """Get first meaningful image from a URL."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all images and check them
            for img in soup.find_all('img'):
                if 'src' not in img.attrs:
                    continue
                
                src = img['src']
                
                # 1. Basic validation and filtering
                if not src or src.startswith('data:image'):
                    continue
                
                # 2. Filter out common non-content images by keywords in src
                non_content_keywords = ['ad', 'banner', 'sponsor', 'logo', 'avatar', 'icon', 'spinner', 'loading', 'pixel']
                if any(keyword in src.lower() for keyword in non_content_keywords):
                    continue

                # 3. Filter out tiny images based on attributes
                try:
                    width = int(img.get('width', 0))
                    height = int(img.get('height', 0))
                    if (width > 0 and width < 100) or (height > 0 and height < 100):
                        continue
                except (ValueError, TypeError):
                    pass # Ignore if width/height are not valid integers

                # 4. Prioritize common image formats
                if not src.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue

                # 5. Construct absolute URL if src is relative
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)

                logger.info(f"First meaningful image found: {src}")
                return src
                
        except requests.RequestException as e:
            logger.error(f"Error getting first image from {url}: {e}")
        logger.info(f"No meaningful first image found for {url}")
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

    def process_thumbnails(self, category, date_str, thumbnails_dir):
        """Finds, downloads, or screenshots thumbnails for articles."""
        os.makedirs(thumbnails_dir, exist_ok=True)
        articles_to_process = self.db_manager.get_articles_by_status('summarized', category, date_str)

        for article in articles_to_process:
            thumbnail_rel_path = None
            safe_filename = self.sanitize_filename(article['title'])

            thumbnail_url = self.get_thumbnail(article['url'])
            if thumbnail_url:
                ext = os.path.splitext(urlparse(thumbnail_url).path)[1]
                if not ext or len(ext) > 5:
                    ext = '.jpg'
                thumbnail_filename = f"{safe_filename}{ext}"
                thumbnail_abs_path = os.path.join(thumbnails_dir, thumbnail_filename)
                if self.download_thumbnail(thumbnail_url, thumbnail_abs_path):
                    thumbnail_rel_path = os.path.join('thumbnails', thumbnail_filename)
                    if self.stats_manager:
                        self.stats_manager.increment('thumbnails_downloaded')
            else:
                logger.info(f"No thumbnail found for {article['url']}. Attempting to take a screenshot.")
                screenshot_filename = f"{safe_filename}.png"
                screenshot_abs_path = os.path.join(thumbnails_dir, screenshot_filename)
                if self.screenshot_article(article['url'], screenshot_abs_path):
                    thumbnail_rel_path = os.path.join('thumbnails', screenshot_filename)
                    if self.stats_manager:
                        self.stats_manager.increment('thumbnails_screenshotted')

            if thumbnail_rel_path:
                self.db_manager.update_article_thumbnail(article['id'], thumbnail_rel_path)

    def screenshot_article(self, url, output_path):
        """Takes a screenshot of the top part of a webpage."""
        try:
            with self.stats_manager.time_block('renderer_screenshot_article') if self.stats_manager else open(os.devnull, 'w'):
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={'width': 1200, 'height': 800})
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    page.screenshot(path=output_path)
                    browser.close()
                logger.info(f"Successfully took screenshot for {url} at {output_path}")
                if self.stats_manager:
                    self.stats_manager.increment('screenshots_success')
                return True
        except Exception as e:
            logger.error(f"Failed to take screenshot for {url}: {e}")
            if self.stats_manager:
                self.stats_manager.increment('screenshots_failed')
            return False

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
                if self.stats_manager:
                    self.stats_manager.increment('top_news_image_generated')
            except Exception as e:
                logger.error(f"Error generating top news image: {e}", exc_info=True)
            finally:
                # Clean up temporary HTML file
                if os.path.exists(html_filename):
                    os.remove(html_filename)
        else:
            logger.error("Failed to create temporary HTML file for top news image")

        return

    def process(self, date_str, output_dir_for_date):
        """Process all steps to render newsletter assets like images."""
        summaries_data = self.db_manager.get_summarized_articles_for_date(date_str)
        # Generate top news image only if there are summaries
        if summaries_data:
            thumbnails_dir = os.path.join(output_dir_for_date, 'thumbnails')
            os.makedirs(thumbnails_dir, exist_ok=True)
            top_news_image_path = os.path.join(output_dir_for_date, "top_news.png")
            self.generate_top_news_image(summaries_data, top_news_image_path)
            return True
        return False
