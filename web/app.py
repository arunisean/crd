import os
from flask import Flask, render_template, g
from datetime import datetime, timedelta
import sys

# Add project root to path to allow importing crd
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crd.database import DatabaseManager

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(project_root, 'crd', 'crd.db')
app.config['OUTPUT_DIR'] = os.path.join(project_root, 'crd', 'web', 'static', 'output')

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = DatabaseManager(app.config['DATABASE'])
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
@app.route('/<date_str>')
def index(date_str=None):
    db = get_db()
    
    # Get available dates from the output directory structure
    output_dir = app.config['OUTPUT_DIR']
    available_dates = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))], reverse=True)
    
    if not date_str:
        date_str = available_dates[0] if available_dates else datetime.now().strftime('%Y-%m-%d')
    
    summaries = db.get_summarized_articles_for_date(date_str)
    
    top_news_image_rel_path = os.path.join('output', date_str, 'top_news.png')
    top_news_image_abs_path = os.path.join(project_root, 'crd', 'web', 'static', top_news_image_rel_path)
    
    top_news_image = top_news_image_rel_path if os.path.exists(top_news_image_abs_path) else None

    # Add relative path to static folder for thumbnails
    for category in summaries:
        for article in summaries[category]:
            if article.get('thumbnail_path'):
                article['thumbnail'] = os.path.join('output', date_str, article['thumbnail_path'])

    return render_template(
        'index.html',
        summaries=summaries,
        top_news_image=top_news_image,
        dates=available_dates,
        selected_date=date_str,
        now=datetime.utcnow()
    )

if __name__ == '__main__':
    app.run(debug=True)