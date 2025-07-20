import sqlite3
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to database at {db_path}")
            self.create_tables()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

    def create_tables(self):
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
                    rating_reason TEXT,
                    source TEXT
                )
            """)
            logger.info("Tables created or already exist.")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

    def add_article(self, article_data):
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
        sql = "SELECT * FROM articles WHERE status = ? AND category = ? AND fetch_date = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (status, category, date_str))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get articles with status {status}: {e}")
            return []

    def update_article_score_and_reason(self, article_id, score, reason):
        sql = "UPDATE articles SET score = ?, rating_reason = ?, status = 'rated' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (score, reason, article_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update score and reason for article {article_id}: {e}")

    def select_top_articles_for_summary(self, category, date_str, limit, min_score):
        sql_select = """
            SELECT id FROM articles 
            WHERE category = ? AND fetch_date = ? AND status = 'rated' AND score >= ?
            ORDER BY score DESC 
            LIMIT ?
        """
        sql_update = "UPDATE articles SET status = 'selected_for_summary' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_select, (category, date_str, min_score, limit))
            top_article_ids = [row['id'] for row in cursor.fetchall()]
            for article_id in top_article_ids:
                cursor.execute(sql_update, (article_id,))
            self.conn.commit()
            return top_article_ids
        except sqlite3.Error as e:
            logger.error(f"Failed to select top articles for {category}: {e}")
            return []

    def update_article_summary(self, article_id, chinese_title, english_summary, chinese_summary):
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
        sql = "UPDATE articles SET thumbnail_path = ?, status = 'complete' WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (thumbnail_path, article_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update thumbnail for article {article_id}: {e}")

    def _row_to_dict(self, row):
        return dict(row) if row else None

    def get_summarized_articles_for_date(self, date_str=None, category_filter=None):
        """Get all completed or summarized articles, optionally filtered by date and/or category."""
        sql = "SELECT * FROM articles WHERE status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != ''"
        params = []

        if date_str:
            sql += " AND fetch_date = ?"
            params.append(date_str)

        if category_filter and category_filter != 'all':
            sql += " AND category = ?"
            params.append(category_filter)

        sql += " ORDER BY fetch_date DESC, score DESC"

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, tuple(params))
            articles_by_date = {}
            for row in cursor.fetchall():
                article_dict = self._row_to_dict(row)
                fetch_date = article_dict['fetch_date']
                if fetch_date not in articles_by_date:
                    articles_by_date[fetch_date] = {}
                category = article_dict['category']
                if category not in articles_by_date[fetch_date]:
                    articles_by_date[fetch_date][category] = []
                articles_by_date[fetch_date][category].append(article_dict)
            return articles_by_date
        except sqlite3.Error as e:
            logger.error(f"Failed to get summarized articles: {e}")
            return {}

    def get_summarized_articles_for_category_and_date(self, category, date_str):
        sql = "SELECT * FROM articles WHERE fetch_date = ? AND category = ? AND status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY score DESC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (date_str, category))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get summarized articles for {category} on {date_str}: {e}")
            return []

    def get_available_dates(self):
        sql = "SELECT DISTINCT fetch_date FROM articles WHERE status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY fetch_date DESC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            return [row['fetch_date'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get available dates: {e}")
            return []

    def get_all_categories(self):
        sql = "SELECT DISTINCT category FROM articles ORDER BY category ASC"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            return [row['category'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all categories: {e}")
            return []

    def get_article_by_id(self, article_id):
        sql = "SELECT * FROM articles WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get article by ID {article_id}: {e}")
            return None

    def finalize_stuck_articles(self, category, date_str):
        sql = "UPDATE articles SET status = 'failed' WHERE category = ? AND fetch_date < ? AND status IN ('fetched', 'rated')"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (category, date_str))
            self.conn.commit()
            logger.info(f"Finalized {cursor.rowcount} stuck articles for category '{category}' before {date_str}.")
        except sqlite3.Error as e:
            logger.error(f"Failed to finalize stuck articles for category {category}: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")