import os
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import shutil
from .utils.io import read_file, write_file, write_json

logger = logging.getLogger(__name__)

class ArticleAnalyzer:
    """Analyzes and rates articles"""
    
    def __init__(self, api_client, config, top_articles=5, max_workers=10, model="gpt-3.5-turbo"):
        self.api_client = api_client
        self.rating_criteria = config.rating_criteria
        self.top_articles = top_articles
        self.max_workers = max_workers
        self.model = model  # Store model parameter
    
    def get_article_rating(self, content):
        """Get rating for an article using the API"""
        payload = {
            "model": self.model,  # Use the model from instance
            "messages": [
                {"role": "system", "content": f"You are an AI assistant that rates articles strictly based on the criteria: '{self.rating_criteria}'. First, determine if the article strictly matches the criteria. If it does not, respond with 'Not relevant'. If it matches, rate the article based on its value in 'X out of 10' format, where X is a number from 1 to 10."},
                {"role": "user", "content": f"Rate the following article:\n\n{content}"}
            ]
        }
        
        try:
            response = self.api_client.request(payload)
            raw_rating = response['choices'][0]['message']['content'].strip()
            logger.debug(f"Raw rating response: {raw_rating}")
            
            if raw_rating.lower() == "not relevant":
                return None
                
            match = re.search(r'(\d+(\.\d+)?)\s*out of 10', raw_rating)
            if match:
                return match.group(1)
            else:
                logger.warning(f"Unexpected rating format: {raw_rating}")
                return None
        except Exception as e:
            logger.error(f"Error getting rating: {e}")
            return None
    
    def replace_score(self, content, new_score):
        """Replace or add score to article content"""
        score_pattern = re.compile(r'Article Score: (\d+(\.\d+)?)\s*out of 10\nRated on: [^\n]+')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_score_line = f"Article Score: {new_score} out of 10\nRated on: {timestamp}"
        
        if score_pattern.search(content):
            return score_pattern.sub(new_score_line, content)
        else:
            return content + f"\n\n{new_score_line}"
    
    def rate_single_article(self, file_path):
        """Rate a single article"""
        filename = os.path.basename(file_path)
        logger.info(f"Rating article: {filename}")
        
        content = read_file(file_path)
        if not content:
            return filename, None
        
        rating = self.get_article_rating(content)
        if rating:
            score = float(rating)
            updated_content = self.replace_score(content, rating)
            if write_file(file_path, updated_content):
                logger.info(f"Rating for {filename}: {rating} out of 10")
                return filename, score
        
        logger.warning(f"Failed to get rating for {filename}")
        return filename, None
    
    def rate_articles(self, articles_dir):
        """Rate multiple articles concurrently"""
        results = {}
        scores = []
        
        # Get all article files
        article_files = []
        for filename in os.listdir(articles_dir):
            if filename.endswith('.txt'):
                article_files.append(os.path.join(articles_dir, filename))
        
        # Rate articles concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for filename, score in executor.map(self.rate_single_article, article_files):
                if score is not None:
                    results[filename] = score
                    scores.append((filename, score))
        
        return results, scores
    
    def select_top_articles(self, scores, articles_dir, high_rated_dir):
        """Select top-rated articles and copy them to a directory"""
        os.makedirs(high_rated_dir, exist_ok=True)
        
        # Sort by score and select top articles
        scores.sort(key=lambda x: x[1], reverse=True)
        top_articles = scores[:self.top_articles]
        
        # Copy top articles to high_rated_dir
        for filename, score in top_articles:
            src = os.path.join(articles_dir, filename)
            dst = os.path.join(high_rated_dir, filename)
            shutil.copy2(src, dst)
            logger.info(f"Copied {filename} to {high_rated_dir} (Score: {score})")
        
        return top_articles
    
    def process(self, articles_dir, high_rated_dir, ratings_file):
        """Process all articles: rate them and select top ones"""
        # Rate all articles
        results, scores = self.rate_articles(articles_dir)
        
        # Select top articles
        top_articles = self.select_top_articles(scores, articles_dir, high_rated_dir)
        
        # Save ratings to file
        if write_json(ratings_file, results):
            logger.info(f"Ratings saved to {ratings_file}")
        
        # Save top articles with scores to a file
        top_articles_file = os.path.join(os.path.dirname(ratings_file), "top_articles.json")
        top_articles_with_scores = [{"filename": filename, "score": score} for filename, score in top_articles]
        if write_json(top_articles_file, top_articles_with_scores):
            logger.info(f"Top articles saved to {top_articles_file}")
        
        return top_articles