import os
import json
from dotenv import load_dotenv

class Config:
    """Configuration management class"""
    
    def __init__(self, env_file='.env', feeds_config='feeds.json'):
        load_dotenv(env_file)
        
        # API settings
        self.api_url = os.getenv("CUSTOM_API_URL", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.getenv("API_KEY", "")
        
        # Model settings
        self.rating_model = os.getenv("RATING_MODEL", "gpt-3.5-turbo")
        self.summary_model = os.getenv("SUMMARY_MODEL", "gpt-4o")
        self.translation_model = os.getenv("TRANSLATION_MODEL", "gpt-4o")
        
        self.feeds_config = self.load_feeds_config(feeds_config)
        
        # Newsletter settings
        self.newsletter_title = os.getenv("NEWSLETTER_TITLE", "Article Summary Newsletter")
        self.newsletter_font = "Arial, sans-serif"
        self.newsletter_template = os.getenv("NEWSLETTER_TEMPLATE", "newsletter_template.html")
        self.width = int(os.getenv("WIDTH", 800))
        
        # Processing settings
        self.threads = int(os.getenv("THREADS", 10))
        self.date_range_days = int(os.getenv("DATE_RANGE_DAYS", 7))
        self.top_articles = int(os.getenv("TOP_ARTICLES", 10))
        
        # Minimum score settings
        self.minimum_score_map = {
            "AI & Tech": float(os.getenv("MINIMUM_SCORE_AI_TECH", 6.5)),
            "Crypto": float(os.getenv("MINIMUM_SCORE_CRYPTO", 6.5)),
            "Academic": float(os.getenv("MINIMUM_SCORE_ACADEMIC", 6.5)),
        }
        self.minimum_score = float(os.getenv("MINIMUM_SCORE", 6.5)) # Default
        
        self.keywords = os.getenv("KEYWORDS", "").split(',') if os.getenv("KEYWORDS") else []

    def load_feeds_config(self, config_path):
        """Loads the feeds configuration from a JSON file."""
        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading feeds config '{config_path}': {e}")
                return {}
        return {}