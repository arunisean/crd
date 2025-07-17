import logging
from concurrent.futures import ThreadPoolExecutor
import pangu

logger = logging.getLogger(__name__)

class ArticleSummarizer:
    """Summarizes articles using an AI API and updates the database."""
    
    def __init__(self, db_manager, api_client, stats_manager=None, model="gpt-4o", max_workers=10):
        self.db_manager = db_manager
        self.api_client = api_client
        self.model = model
        self.max_workers = max_workers
        self.stats_manager = stats_manager
    
    def get_chinese_title_and_summary(self, title, content, url):
        """Get Chinese title and summary for an article"""
        # Translate title
        title_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a translator. Translate the given title to Chinese (zh-CN). Output only the translated title without any additional text."},
                {"role": "user", "content": f"Translate this title to Chinese:\n\n{title}"}
            ]
        }
        
        # Summarize and translate content
        content_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an AI assistant that summarizes articles in Chinese (zh-CN). Provide a concise summary in about 3-5 sentences in Chinese."},
                {"role": "user", "content": f"Summarize the following article in Chinese (zh-CN),Do not output anything that is irrelevant to the article.:\n\nTitle: {title}\n\nContent:\n{content}"}
            ]
        }
        
        with self.stats_manager.time_block('summarizer_zh_api_call') if self.stats_manager else open(os.devnull, 'w'):
            try:
                # Get translated title
                title_response = self.api_client.request(title_payload)
                chinese_title = title_response['choices'][0]['message']['content'].strip()
                
                # Get Chinese summary
                content_response = self.api_client.request(content_payload)
                chinese_summary = content_response['choices'][0]['message']['content'].strip()
                
                # Apply pangu spacing
                chinese_title = pangu.spacing_text(chinese_title)
                chinese_summary = pangu.spacing_text(chinese_summary)
                
                if self.stats_manager: self.stats_manager.increment('summaries_zh_success')
                return chinese_title, chinese_summary
            except Exception as e:
                logger.error(f"Error getting Chinese title and summary: {e}")
                if self.stats_manager: self.stats_manager.increment('summaries_zh_failed')
                return None, None

    def get_english_summary(self, title, content):
        """Get English summary for an article"""
        content_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an AI assistant that summarizes articles. Provide a concise summary in about 3-5 sentences."},
                {"role": "user", "content": f"Summarize the following article:\n\nTitle: {title}\n\nContent:\n{content}"}
            ]
        }

        with self.stats_manager.time_block('summarizer_en_api_call') if self.stats_manager else open(os.devnull, 'w'):
            try:
                content_response = self.api_client.request(content_payload)
                english_summary = content_response['choices'][0]['message']['content'].strip()
                if self.stats_manager: self.stats_manager.increment('summaries_en_success')
                return english_summary
            except Exception as e:
                logger.error(f"Error getting English summary: {e}")
                if self.stats_manager: self.stats_manager.increment('summaries_en_failed')
                return None

    def summarize_article(self, article):
        """Summarize a single article and update it in the database."""
        try:
            article_id = article['id']
            title = article['title']
            content = article['content']
            url = article['url']

            if not content:
                logger.warning(f"Article {title} (ID: {article_id}) has no content to summarize, skipping.")
                return

            logger.info(f"Summarizing article ID {article_id}: {title}")
            
            chinese_title, chinese_summary = self.get_chinese_title_and_summary(title, content, url)
            english_summary = self.get_english_summary(title, content)

            if chinese_title or chinese_summary or english_summary:
                self.db_manager.update_article_summary(
                    article_id,
                    chinese_title,
                    english_summary,
                    chinese_summary
                )
                if self.stats_manager: self.stats_manager.increment('articles_summarized_in_db')
                logger.info(f"Successfully summarized (possibly partially) and saved to DB: {title}")
            else:
                logger.error(f"All summarization attempts failed for article: {title}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while summarizing article ID {article.get('id')}: {e}", exc_info=True)

    def process(self, category, date_str):
        """
        Fetches articles marked for summarization from the DB, summarizes them,
        and updates the results back to the DB.
        """
        articles_to_summarize = self.db_manager.get_articles_by_status('selected_for_summary', category, date_str)
        
        if not articles_to_summarize:
            logger.info(f"No articles to summarize for category '{category}' on {date_str}.")
            return

        logger.info(f"Found {len(articles_to_summarize)} articles to summarize for '{category}' on {date_str}.")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            list(executor.map(self.summarize_article, articles_to_summarize))
        
        logger.info(f"Finished summarizing articles for '{category}' on {date_str}.")