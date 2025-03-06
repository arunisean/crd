import requests
import logging
import time

logger = logging.getLogger(__name__)

class APIClient:
    """Client for interacting with OpenAI-compatible APIs"""
    
    def __init__(self, api_url, api_key, max_retries=3, retry_delay=2):
        self.api_url = api_url
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def request(self, payload, timeout=30):
        """Make a request to the API with retry logic"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"API request failed after {self.max_retries} attempts")
                    raise