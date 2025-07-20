import sqlite3
import logging
from urllib.parse import urlparse
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.thread_local = threading.local()

    def get_conn(self):
        if not hasattr(self.thread_local, 'conn'):
            self.thread_local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.thread_local.conn.row_factory = sqlite3.Row
        return self.thread_local.conn

    def close_conn(self):
        if hasattr(self.thread_local, 'conn'):
            self.thread_local.conn.close()
            del self.thread_local.conn

    def create_tables(self):
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
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
            conn = self.get_conn()
            cursor = conn.cursor()
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
            conn.commit()
            return cursor.lastrowid > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to add article {article_data.get('link')}: {e}")
            return False

    def get_articles_by_status(self, status, category, date_str):
        sql = "SELECT * FROM articles WHERE status = ? AND category = ? AND fetch_date = ?"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (status, category, date_str))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get articles with status {status}: {e}")
            return []

    def update_article_score_and_reason(self, article_id, score, reason):
        sql = "UPDATE articles SET score = ?, rating_reason = ?, status = 'rated' WHERE id = ?"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (score, reason, article_id))
            conn.commit()
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
            conn = self.get_conn()
            cursor = conn.cursor()
            logger.info(f"Executing select_top_articles_for_summary with params: category={category}, date_str={date_str}, limit={limit}, min_score={min_score}")
            cursor.execute(sql_select, (category, date_str, min_score, limit))
            top_article_ids = [row['id'] for row in cursor.fetchall()]
            logger.info(f"Found {len(top_article_ids)} articles with score >= {min_score}.")
            for article_id in top_article_ids:
                cursor.execute(sql_update, (article_id,))
            conn.commit()
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
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (chinese_title, english_summary, chinese_summary, article_id))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to update summary for article {article_id}: {e}")

    def update_article_thumbnail(self, article_id, thumbnail_path):
        sql = "UPDATE articles SET thumbnail_path = ?, status = 'complete' WHERE id = ?"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (thumbnail_path, article_id))
            conn.commit()
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
            conn = self.get_conn()
            cursor = conn.cursor()
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
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (date_str, category))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get summarized articles for {category} on {date_str}: {e}")
            return []

    def get_available_dates(self):
        sql = "SELECT DISTINCT fetch_date FROM articles WHERE status IN ('complete', 'summarized') AND chinese_summary IS NOT NULL AND chinese_summary != '' ORDER BY fetch_date DESC"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql)
            return [row['fetch_date'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get available dates: {e}")
            return []

    def get_all_categories(self):
        sql = "SELECT DISTINCT category FROM articles ORDER BY category ASC"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql)
            return [row['category'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all categories: {e}")
            return []

    def get_article_by_id(self, article_id):
        sql = "SELECT * FROM articles WHERE id = ?"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get article by ID {article_id}: {e}")
            return None

    def get_stats(self):
        stats = {}
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            
            # Total articles per category
            cursor.execute("SELECT category, COUNT(*) as count FROM articles GROUP BY category")
            stats['articles_per_category'] = {row['category']: row['count'] for row in cursor.fetchall()}
            
            # Average score per category
            cursor.execute("SELECT category, AVG(score) as avg_score FROM articles WHERE score IS NOT NULL GROUP BY category")
            stats['avg_score_per_category'] = {row['category']: row['avg_score'] for row in cursor.fetchall()}
            
            # Articles per day
            cursor.execute("SELECT fetch_date, COUNT(*) as count FROM articles GROUP BY fetch_date ORDER BY fetch_date DESC")
            stats['articles_per_day'] = {row['fetch_date']: row['count'] for row in cursor.fetchall()}
            
            return stats
        except sqlite3.Error as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def finalize_stuck_articles(self, category, date_str):
        sql = "UPDATE articles SET status = 'failed' WHERE category = ? AND fetch_date < ? AND status IN ('fetched', 'rated')"
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute(sql, (category, date_str))
            conn.commit()
            logger.info(f"Finalized {cursor.rowcount} stuck articles for category '{category}' before {date_str}.")
        except sqlite3.Error as e:
            logger.error(f"Failed to finalize stuck articles for category {category}: {e}")

    def close(self):
        self.close_conn()
