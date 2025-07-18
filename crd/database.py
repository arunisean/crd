import sqlite3
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all interactions with the SQLite database."""
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        try:
            # `check_same_thread=False` is needed for multi-threaded access in the pipeline.
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to database at {db_path}")
            self.create_tables()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

    def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    fetch_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT,
                    score REAL,
                    status TEXT NOT NULL DEFAULT 'fetched',
                    chinese_title TEXT,
                    english_summary TEXT,
                    chinese_summary TEXT,
                    thumbnail_path TEXT,
                    source TEXT
                )
            """)

            logger.info("Tables created or already exist.")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

    def add_article(self, article_data):
        """Add a new article to the database, ignoring if URL already exists."""
        sql = ''' INSERT OR IGNORE INTO articles(url, title, publication_date, fetch_date, category, content, source, status)
                  VALUES(?,?,?,?,?,?,?,?) '''
        try:
            cursor = self.conn.cursor()
            source = urlparse(article_data['link']).netloc.replace('www.', '')
            cursor.execute(sql, (
                article_data['link'],
                article_data['title'],
                article_data['date'],
                article_data['fetch_date'],
                article_data['category'],
                article_data['content'],
                source,
                'fetched'
            ))
            self.conn.commit()
            return cursor.lastrowid > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to add article {article_data.get('link')}: {e}")
            return False

    def get_articles_by_status(self, status, category, date_str):
        """Get articles with a specific status for a given category and date."""
        sql = "SELECT * FROM articles WHERE status = ? AND category = ? AND fetch_date = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (status, category, date_str))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get articles with status {status}: {e}")
            return []

    def update_article_score(self, article_id, score):
        """Update the score and status of an article."""
        sql = "UPDATE articles SET score = ?, status = 'rated' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (score, article_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update score for article {article_id}: {e}")

    def select_top_articles_for_summary(self, category, date_str, limit):
        """Select top articles and update their status for summarization."""
        sql_select = """
            SELECT id FROM articles 
            WHERE category = ? AND fetch_date = ? AND status = 'rated'
            ORDER BY score DESC 
            LIMIT ?
        """
        sql_update = "UPDATE articles SET status = 'selected_for_summary' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_select, (category, date_str, limit))
            top_article_ids = [row['id'] for row in cursor.fetchall()]
            for article_id in top_article_ids:
                cursor.execute(sql_update, (article_id,))
            self.conn.commit()
            return top_article_ids
        except sqlite3.Error as e:
            logger.error(f"Failed to select top articles for {category}: {e}")
            return []

    def update_article_summary(self, article_id, chinese_title, english_summary, chinese_summary):
        """Update summary details and status of an article."""
        sql = """
            UPDATE articles 
            SET chinese_title = ?, english_summary = ?, chinese_summary = ?, status = 'summarized' 
            WHERE id = ?
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (chinese_title, english_summary, chinese_summary, article_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update summary for article {article_id}: {e}")

    def update_article_thumbnail(self, article_id, thumbnail_path):
        """Update thumbnail path and status of an article."""
        sql = "UPDATE articles SET thumbnail_path = ?, status = 'complete' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (thumbnail_path, article_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update thumbnail for article {article_id}: {e}")

    def _row_to_dict(self, row):
        """Converts a sqlite3.Row object to a dictionary."""
        return dict(row) if row else None

    def get_summarized_articles_for_date(self, date_str):
        """Get all completed or summarized articles for a specific date, grouped by category."""
        sql = "SELECT * FROM articles WHERE fetch_date = ? AND status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY category, score DESC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (date_str,))
            articles_by_category = {}
            for row in cursor.fetchall():
                article_dict = self._row_to_dict(row)
                category = article_dict['category']
                if category not in articles_by_category:
                    articles_by_category[category] = []
                articles_by_category[category].append(article_dict)
            return articles_by_category
        except sqlite3.Error as e:
            logger.error(f"Failed to get summarized articles for {date_str}: {e}")
            return {}

    def get_summarized_articles_for_category_and_date(self, category, date_str):
        """Get all completed or summarized articles for a specific category and date."""
        sql = "SELECT * FROM articles WHERE fetch_date = ? AND category = ? AND status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY score DESC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (date_str, category))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get summarized articles for {category} on {date_str}: {e}")
            return []

    def get_available_dates(self):
        """Get a sorted list of distinct dates that have completed or summarized articles."""
        sql = "SELECT DISTINCT fetch_date FROM articles WHERE status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY fetch_date DESC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            return [row['fetch_date'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get available dates: {e}")
            return []

    def has_complete_articles(self, date_str):
        """Check if there are any articles with status 'complete' for a given date."""
        # We check for at least one 'complete' article as a sign that the day's run finished.
        sql = "SELECT 1 FROM articles WHERE fetch_date = ? AND status = 'complete' LIMIT 1"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (date_str,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Failed to check for complete articles on {date_str}: {e}")
            return False # Assume not complete on error

    def finalize_articles_status(self, category, date_str):
        """Mark all summarized articles as complete for a given category and date."""
        # This ensures articles are displayed even if thumbnail generation fails.
        sql = "UPDATE articles SET status = 'complete' WHERE status = 'summarized' AND category = ? AND fetch_date = ?"
        try:
            cursor = self.conn.cursor()
            updated_rows = cursor.execute(sql, (category, date_str)).rowcount
            self.conn.commit()
            if updated_rows > 0:
                logger.info(f"Finalized status for {updated_rows} articles in '{category}' on {date_str}.")
        except sqlite3.Error as e:
            logger.error(f"Failed to finalize article status for {category} on {date_str}: {e}")

    def clear_category_for_date(self, category, date_str):
        """Delete all articles for a specific category and date."""
        sql = "DELETE FROM articles WHERE category = ? AND fetch_date = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (category, date_str))
            self.conn.commit()
            logger.info(f"Cleared data for category '{category}' on {date_str}.")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear category {category} for date {date_str}: {e}")

    def get_article_by_id(self, article_id):
        """Get a single article by its primary key ID."""
        sql = "SELECT * FROM articles WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get article by ID {article_id}: {e}")
            return None

    def force_finalize_all_articles(self):
        """Forces all articles that have been summarized or rated into the 'complete' state."""
        sql = "UPDATE articles SET status = 'complete' WHERE status IN ('summarized', 'rated', 'selected_for_summary')"
        try:
            cursor = self.conn.cursor()
            updated_rows = cursor.execute(sql).rowcount
            self.conn.commit()
            logger.info(f"Force-finalized {updated_rows} articles.")
            return updated_rows
        except sqlite3.Error as e:
            logger.error(f"Failed to force-finalize articles: {e}")
            return 0

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")