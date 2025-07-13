from flask import Flask, render_template, request
import os
import json
import re

app = Flask(__name__)

# Define the output directory relative to the app's location
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'static', 'output')

@app.route('/')
def home():
    """Serves the main page with the latest newsletter."""
    # Scan for available dated directories
    try:
        dated_dirs = [d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d)) and re.match(r'\d{4}-\d{2}-\d{2}', d)]
        dated_dirs.sort(reverse=True)
    except FileNotFoundError:
        dated_dirs = []

    # Determine which date to show
    available_dates = dated_dirs[:3]
    selected_date_str = request.args.get('date', available_dates[0] if available_dates else None)

    # Load data for the selected date
    summaries = None
    if selected_date_str and selected_date_str in available_dates:
        summaries_path = os.path.join(OUTPUT_DIR, selected_date_str, 'summaries.json')
        if os.path.exists(summaries_path):
            try:
                with open(summaries_path, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
            except json.JSONDecodeError:
                app.logger.error(f"Could not decode JSON from {summaries_path}")

    return render_template(
        'index.html', 
        articles_by_category=summaries,
        available_dates=available_dates,
        selected_date=selected_date_str
    )

if __name__ == '__main__':
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)