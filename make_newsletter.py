import json
import os
import requests
import re
from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from crd.utils.config import Config
from crd.renderer import NewsletterRenderer
from crd.utils.logging import setup_logger

logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

def get_youtube_thumbnail(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['www.youtube.com', 'youtu.be']:
        if parsed_url.netloc == 'youtu.be':
            video_id = parsed_url.path[1:]
        else:
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/0.jpg"
    return None

def get_og_image(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        if og_image:
            return og_image['content']
    except requests.RequestException:
        pass
    return None

def get_first_image(url):
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
    except requests.RequestException:
        pass
    return None

def get_thumbnail(url):
    thumbnail_url = get_youtube_thumbnail(url)
    if thumbnail_url and is_url_reachable(thumbnail_url):
        return thumbnail_url

    thumbnail_url = get_og_image(url)
    if thumbnail_url and is_url_reachable(thumbnail_url):
        return thumbnail_url

    thumbnail_url = get_first_image(url)
    if thumbnail_url and is_url_reachable(thumbnail_url):
        return thumbnail_url

    return None

def sanitize_filename(filename):
    # Remove or replace special characters
    filename = re.sub(r'[?<>:*|"\\/]', '', filename)
    filename = re.sub(r'[\s]+', '_', filename)  # Replace spaces with underscores
    filename = re.sub(r'[^\w\-_\.]', '', filename)  # Remove any remaining non-word characters
    return filename[:255]  # Truncate to max filename length

def download_thumbnail(url, filename):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True
    except requests.RequestException:
        return False

def is_url_reachable(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def write_titles_and_links(summaries, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for data in summaries.values():
            f.write(f"{data['chinese_title']}\\n{data['url']}\\n\\n")

def main():
    logger.info("Starting make_newsletter.py")
    # Load article summaries
    try:
        with open('output/article_summaries.json', 'r', encoding='utf-8') as f:
            summaries = json.load(f)
        logger.info("Successfully loaded article summaries from output/article_summaries.json")
    except Exception as e:
        logger.error(f"Failed to load article summaries: {e}")
        return

    # Create thumbnails directory
    thumbnails_dir = 'thumbnails'
    os.makedirs(thumbnails_dir, exist_ok=True)

    # Process each article
    for filename, data in summaries.items():
        url = data['url']
        thumbnail_url = get_thumbnail(url)
        
        if thumbnail_url:
            safe_filename = sanitize_filename(filename)
            thumbnail_filename = os.path.join(thumbnails_dir, f"{safe_filename.replace('.txt', '.jpg')}")
            if download_thumbnail(thumbnail_url, thumbnail_filename):
                logger.info(f"Thumbnail downloaded: {thumbnail_filename}")
                data['thumbnail'] = os.path.relpath(thumbnail_filename)
            else:
                logger.warning(f"Failed to download thumbnail from {thumbnail_url}")
                data['thumbnail'] = None
        else:
            logger.info(f"No thumbnail found for {url}")
            data['thumbnail'] = None

        # Add source to data
        data['source'] = urlparse(url).netloc

    # Get title and font from environment variables
    title = os.getenv('NEWSLETTER_TITLE', 'Reserch Digest')
    font = os.getenv('NEWSLETTER_FONT', 'Arial, sans-serif')

    # Create newsletter using Jinja2 template
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('newsletter_template.html')

    try:
        newsletter_html = template.render(articles=summaries.values(), title=title, font=font)
        logger.info("Successfully rendered newsletter template")
    except Exception as e:
        logger.error(f"Failed to render newsletter template: {e}")
        return

    # Save the newsletter
    logger.info("Saving newsletter to newsletter.html")
    with open('newsletter.html', 'w', encoding='utf-8') as f:
        f.write(newsletter_html)
    logger.info("Newsletter saved to newsletter.html")

    # Write titles and links to a text file
    write_titles_and_links(summaries, 'titles_and_links.txt')

    print("Newsletter created: newsletter.html")
    logger.info(f"NEWSLETTER_TITLE: {title}, NEWSLETTER_FONT: {font}")
    print("Titles and links saved: titles_and_links.txt")

if __name__ == "__main__":
    main()