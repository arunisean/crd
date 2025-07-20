from flask import Flask, render_template, request, g, jsonify, url_for
import os
from datetime import datetime

from ..database import DatabaseManager
from ..renderer import NewsletterRenderer

app = Flask(__name__)
app.secret_key = 'a_temp_secret_key_for_flashing'

# --- Configuration ---
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crd.db'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'output'))
NEWSLETTER_TITLE = "Research Digest"
NEWSLETTER_FONT = "Arial, sans-serif"

# --- Database Handling ---
def get_db():
    if 'db' not in g:
        g.db = DatabaseManager(DATABASE_PATH)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/articles')
def api_articles():
    db = get_db()
    date_str = request.args.get('date')
    category = request.args.get('category')

    # If no date is specified, default to the most recent date available.
    if not date_str:
        available_dates = db.get_available_dates()
        if available_dates:
            date_str = available_dates[0]

    articles = db.get_summarized_articles_for_date(date_str=date_str, category_filter=category)
    return jsonify(articles)

@app.route('/api/categories')
def api_categories():
    db = get_db()
    categories = db.get_all_categories()
    return jsonify(categories)

@app.route('/api/available_dates')
def api_available_dates():
    db = get_db()
    dates = db.get_available_dates()
    return jsonify(dates)

@app.route('/share/<int:article_id>')
def share_article(article_id):
    db = get_db()
    article = db.get_article_by_id(article_id)
    if not article:
        return "Article not found", 404

    date_str = article['fetch_date']
    output_dir_for_date = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir_for_date, exist_ok=True)

    safe_filename = "".join([c for c in article['title'] if c.isalpha() or c.isdigit() or c.isspace()]).rstrip().replace(' ', '_')
    image_filename = f"analysis_{safe_filename}.png"
    image_path = os.path.join(output_dir_for_date, image_filename)
    image_url_for_template = url_for('static', filename=f'output/{date_str}/{image_filename}')

    # Generate the image if it doesn't exist
    if not os.path.exists(image_path):
        renderer = NewsletterRenderer(
            db_manager=db,
            title=NEWSLETTER_TITLE,
            font=NEWSLETTER_FONT,
            width=600
        )
        try:
            renderer.generate_article_analysis_image(article, image_path)
        except Exception as e:
            app.logger.error(f"Error generating image for sharing article {article_id}: {e}", exc_info=True)
            # Optionally, redirect to the original article anyway or show a generic error page
            return "Could not generate analysis image.", 500

    # For meta tags, we need the full URL
    image_full_url = url_for('static', filename=f'output/{date_str}/{image_filename}', _external=True)

    return render_template(
        'share.html',
        article=article,
        image_full_url=image_full_url,
        image_url_for_template=image_url_for_template
    )


@app.route('/generate_image/<int:article_id>', methods=['POST'])
def generate_image(article_id):
    db = get_db()
    article = db.get_article_by_id(article_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    date_str = article['fetch_date']
    output_dir_for_date = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir_for_date, exist_ok=True)
    
    safe_filename = "".join([c for c in article['title'] if c.isalpha() or c.isdigit() or c.isspace()]).rstrip()
    image_filename = f"analysis_{safe_filename}.png"
    image_path = os.path.join(output_dir_for_date, image_filename)
    
    renderer = NewsletterRenderer(
        db_manager=db,
        title=NEWSLETTER_TITLE,
        font=NEWSLETTER_FONT,
        width=600
    )
    
    try:
        renderer.generate_article_analysis_image(article, image_path)
        image_url = f'/static/output/{date_str}/{image_filename}'
        return jsonify({'image_url': image_url})
    except Exception as e:
        app.logger.error(f"Error generating image for article {article_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate image'}), 500

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)