import os
from dotenv import load_dotenv

class Config:
    """Configuration management class"""
    
    def __init__(self, env_file='.env'):
        load_dotenv(env_file)
        
        # API settings
        self.api_url = os.getenv("CUSTOM_API_URL", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.getenv("API_KEY", "")
        
        # Content settings
        self.rating_criteria = os.getenv("RATING_CRITERIA", "")
        self.top_articles = int(os.getenv("TOP_ARTICLES", 5))
        self.keywords = os.getenv("KEYWORDS", "").split(',')
        
        # Newsletter settings
        self.newsletter_title = os.getenv("NEWSLETTER_TITLE", "Article Summary Newsletter")
        self.newsletter_font = os.getenv("NEWSLETTER_FONT", "Arial, sans-serif")
        self.newsletter_template = os.getenv("NEWSLETTER_TEMPLATE", "newsletter_template.html")
        self.width = int(os.getenv("WIDTH", 800))
        
        # Processing settings
        self.threads = int(os.getenv("THREADS", 10))
        self.date_range_days = int(os.getenv("DATE_RANGE_DAYS", 7))