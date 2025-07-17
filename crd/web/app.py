from flask import Flask, render_template, request, g, jsonify, send_file, flash, redirect, url_for
import os
from datetime import datetime, timedelta
import sys

from ..database import DatabaseManager
from ..renderer import NewsletterRenderer

app = Flask(__name__)
app.secret_key = 'a_temp_secret_key_for_flashing' # Required for flash messages

# --- Configuration ---
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crd.db'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'output'))
NEWSLETTER_TITLE = "Research Digest"
NEWSLETTER_FONT = "Arial, sans-serif"
WIDTH = 800

# --- Database Handling ---
def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = DatabaseManager(DATABASE_PATH)
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Routes ---
@app.route('/')
def home():
    """Serves the main page shell, which will be populated by JavaScript."""
    return render_template('index.html')

@app.route('/api/articles')
def api_articles():
    """Returns articles for a given date as JSON."""
    db = get_db()
    date_str = request.args.get('date', datetime.now().date().strftime('%Y-%m-%d'))
    articles_by_category = db.get_summarized_articles_for_date(date_str)
    return jsonify(articles_by_category)

@app.route('/api/latest_article_date')
def api_latest_article_date():
    """Returns the most recent date that has articles."""
    db = get_db()
    # Assuming get_available_dates() returns a sorted list of dates DESC
    available_dates = db.get_available_dates()
    latest_date = available_dates[0] if available_dates else None
    return jsonify({'latest_date': latest_date})

@app.route('/stats')
def stats():
    """Shows data health statistics."""
    db = get_db()
    cursor = db.conn.cursor()
    query = """
        SELECT fetch_date, category, status, COUNT(*) as count 
        FROM articles 
        GROUP BY fetch_date, category, status
        ORDER BY fetch_date DESC, category ASC, status ASC
    """
    cursor.execute(query)
    stats_data = cursor.fetchall()
    return render_template('stats.html', stats=stats_data)

@app.route('/generate_image/<int:article_id>', methods=['POST'])
def generate_image(article_id):
    """Generates an analysis image for a single article."""
    db = get_db()
    article = db.get_article_by_id(article_id)
    
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    # Define output path for the generated image
    date_str = article['fetch_date']
    output_dir_for_date = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir_for_date, exist_ok=True)
    
    # Sanitize title for filename
    safe_filename = "".join([c for c in article['title'] if c.isalpha() or c.isdigit() or c.isspace()]).rstrip()
    image_filename = f"analysis_{safe_filename}.png"
    image_path = os.path.join(output_dir_for_date, image_filename)
    
    # Create a renderer instance
    renderer = NewsletterRenderer(
        db_manager=db,
        title=NEWSLETTER_TITLE,
        font=NEWSLETTER_FONT,
        width=WIDTH
    )
    
    # Generate the image using a simplified HTML structure for a single article
    try:
        # This function expects a dictionary of {category: [articles]}
        single_article_data = {article['category']: [article]}
        renderer.generate_top_news_image(single_article_data, image_path)
        
        # Return the path to the generated image
        image_url = f'/static/output/{date_str}/{image_filename}'
        return jsonify({'image_url': image_url})
        
    except Exception as e:
        app.logger.error(f"Error generating image for article {article_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate image'}), 500



if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
