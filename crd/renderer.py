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
            safe_filename = self.sanitize_filename(filename)
            thumbnail_filename = os.path.join(thumbnails_dir, f"{safe_filename.replace('.txt', '.png')}")
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{data['chinese_title']}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        padding: 20px;
                    }}
                </style>
            </head>
            <body>
                <h1>{data['chinese_title']}</h1>
                <p>{data['chinese_summary']}</p>
            </body>
            </html>
            """
            html_filename = os.path.join(thumbnails_dir, f"{safe_filename.replace('.txt', '.html')}")
            if write_file(html_filename, html_content):
                import subprocess
                result = subprocess.run(['python', 'renderpng.py', html_filename, thumbnail_filename], capture_output=True, text=True)
                if result.returncode == 0:
                    data['thumbnail'] = os.path.relpath(thumbnail_filename)
                    logger.info(f"Thumbnail generated and saved to {thumbnail_filename}")
                else:
                    logger.error(f"Error generating thumbnail: {result.stderr}")
                    data['thumbnail'] = None
                    logger.warning(f"Failed to generate thumbnail for {url}")
            else:
                data['thumbnail'] = None
                logger.warning(f"Failed to generate thumbnail for {url}")
            
            # Add source to data
            data['source'] = urlparse(url).netloc
    
    def render_newsletter(self, summaries, template_path, output_file):
        """Render newsletter HTML using Jinja2 template"""
        try:
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            newsletter_html = template.render(articles=summaries.values(), title=self.title, font=self.font)
            write_file(output_file, newsletter_html)
            logger.info(f"Newsletter rendered successfully to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error rendering newsletter: {e}")
            return False

    def generate_top_news_image(self, summaries_data, output_path, template_path):
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
        for data in summaries_data.values():
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
            # Generate the PNG image using renderpng.py
            import subprocess
            result = subprocess.run(['python', 'renderpng.py', html_filename, output_path], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Top news image generated and saved to {output_path}")
            else:
                logger.error(f"Error generating top news image: {result.stderr}")
        else:
            logger.error("Failed to create temporary HTML file for top news image")

        # End of generate_top_news_image; the newsletter rendering is handled separately.
        return
    
    def process(self, summaries_data, template_path, output_html, output_txt, thumbnails_dir):
        """Process all steps to render the newsletter"""
        # Generate top news image
        top_news_image_path = os.path.join(thumbnails_dir, "top_news.png")
        self.generate_top_news_image(summaries_data, top_news_image_path, template_path)

        # Render newsletter
        if self.render_newsletter(summaries_data, template_path, output_html):
            logger.info(f"Newsletter created: {output_html}")

        # Write titles and links
        if self.write_titles_and_links(summaries_data, output_txt):
            logger.info(f"Titles and links saved: {output_txt}")

        return True
        """Process all steps to render the newsletter"""
        # Generate top news image
        top_news_image_path = os.path.join(thumbnails_dir, "top_news.png")
        self.generate_top_news_image(summaries_data, top_news_image_path, template_path)

        # Render newsletter
        if self.render_newsletter(summaries_data, template_path, output_html):
            logger.info(f"Newsletter created: {output_html}")

        # Write titles and links
        if self.write_titles_and_links(summaries_data, output_txt):
            logger.info(f"Titles and links saved: {output_txt}")

        return True
