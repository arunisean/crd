import os
import logging
import re
import json
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ArticleAnalyzer:
    """Analyzes and rates articles"""

    def __init__(self, db_manager, api_client, criteria_path, stats_manager=None, top_articles=10, min_score_map=None, max_workers=10, model="gpt-3.5-turbo"):
        self.api_client = api_client
        self.db_manager = db_manager
        self.criteria_path = criteria_path
        self.top_articles = top_articles
        self.min_score_map = min_score_map if min_score_map is not None else {}
        self.max_workers = max_workers
        self.stats_manager = stats_manager
        self.model = model
        self.rating_criteria = self._load_criteria()

    def _load_criteria(self):
        """Loads the rating criteria from the JSON file."""
        try:
            with open(self.criteria_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Criteria file not found at {self.criteria_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.criteria_path}")
            return {}

    def get_article_rating(self, content, category):
        """Get rating for an article using the API"""
        criteria = self.rating_criteria.get('default', {})
        criteria.update(self.rating_criteria.get(category, {}))
        
        if not criteria:
            logger.warning(f"No rating criteria found for category: {category}")
            return None

        criteria_prompt = ", ".join([f"{k} ({v} points)" for k, v in criteria.items()])
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"You are an AI assistant that rates articles strictly based on the criteria: '{criteria_prompt}'. First, determine if the article strictly matches the criteria. If it does not, respond with 'Not relevant'. If it matches, you must first provide a one-sentence reason for your rating, followed by the rating itself in the format 'Rating: X/10', where X is a number from 1 to 10."},
                {"role": "user", "content": f"Rate the following article:\n\n{content}"}
            ]
        }
        
        with self.stats_manager.time_block('analyzer_api_call') if self.stats_manager else open(os.devnull, 'w'):
            try:
                response = self.api_client.request(payload)
                raw_rating = response['choices'][0]['message']['content'].strip()
                logger.debug(f"Raw rating response: {raw_rating}")
                
                if raw_rating.lower() == "not relevant":
                    if self.stats_manager: self.stats_manager.increment('articles_rated_irrelevant')
                    return None, None
                    
                match = re.search(r'Rating:\s*(\d+(\.\d+)?)/10', raw_rating, re.IGNORECASE)
                
                if match:
                    score = match.group(1)
                    reason_match = re.match(r'(.*?)Rating:', raw_rating, re.DOTALL | re.IGNORECASE)
                    reason = reason_match.group(1).strip() if reason_match else "No reason provided."
                    if self.stats_manager: self.stats_manager.increment('articles_rated_success')
                    return score, reason
                else:
                    logger.warning(f"Unexpected rating format: {raw_rating}")
                    if self.stats_manager: self.stats_manager.increment('articles_rated_failed_format')
                    return None, None
            except Exception as e:
                logger.error(f"Error getting rating: {e}")
                return None

    def rate_single_article(self, article):
        """Rate a single article"""
        article_id = article['id']
        title = article['title']
        category = article['category']
        logger.info(f"Rating article: {title}")

        if not article['content']:
            return article_id, None, None

        score, reason = self.get_article_rating(article['content'], category)
        if score:
            self.db_manager.update_article_score_and_reason(article_id, float(score), reason)
            logger.info(f"Rating for {title}: {score}/10. Reason: {reason}")
            return article_id, score, reason

        logger.warning(f"Failed to get rating for {title}")
        return article_id, None, None

    def process(self, category, date_str):
        """Process all articles for a category: rate them and select top ones"""
        articles_to_rate = self.db_manager.get_articles_by_status('fetched', category, date_str)
        if not articles_to_rate:
            logger.warning(f"No articles found with status 'fetched' for category '{category}' on {date_str}.")
            return []

        # Rate articles concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.rate_single_article, article) for article in articles_to_rate]
            for future in futures:
                future.result()  # Wait for all futures to complete

        # Get the minimum score for the current category
        min_score = self.min_score_map.get(category, 6.5)

        # Select top articles and mark them for summarization
        top_article_ids = self.db_manager.select_top_articles_for_summary(
            category, date_str, self.top_articles, min_score
        )
        logger.info(f"Selected {len(top_article_ids)} top articles for category '{category}' for summarization.")

        return top_article_ids
