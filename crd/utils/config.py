import os
from dotenv import load_dotenv

class Config:
    """Configuration management class"""
    
    def __init__(self, env_file='.env'):
        load_dotenv(env_file)
        
        # API settings
        self.api_url = os.getenv("CUSTOM_API_URL", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.getenv("API_KEY", "")
        
        # Model settings
        self.rating_model = os.getenv("RATING_MODEL", "gpt-3.5-turbo")
        self.summary_model = os.getenv("SUMMARY_MODEL", "gpt-4o")
        self.translation_model = os.getenv("TRANSLATION_MODEL", "gpt-4o")
        
        # Content settings
        rating_criteria_path = os.getenv("RATING_CRITERIA", "")
        if os.path.isfile(rating_criteria_path):
            with open(rating_criteria_path, 'r', encoding='utf-8') as f:
                self.rating_criteria = f.read().strip()
        else:
            self.rating_criteria = rating_criteria_path
        self.top_articles = int(os.getenv("TOP_ARTICLES", 5))
        self.keywords = os.getenv("KEYWORDS", "").split(',')
        self.opml_file = os.getenv("OPML_FILE", "feeds.opml")
        
        # Newsletter settings
        self.newsletter_title = os.getenv("NEWSLETTER_TITLE", "Article Summary Newsletter")
        self.newsletter_font = "Arial, sans-serif"
        self.newsletter_template = os.getenv("NEWSLETTER_TEMPLATE", "newsletter_template.html")
        self.width = int(os.getenv("WIDTH", 800))
        
        # Processing settings
        self.threads = int(os.getenv("THREADS", 10))
        self.date_range_days = int(os.getenv("DATE_RANGE_DAYS", 7))