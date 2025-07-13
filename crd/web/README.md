# Web Module

This directory contains a simple Flask web application to display the output of the Content Research Digest pipeline.

## Structure

- `app.py`: The main Flask application file containing the routes.
- `templates/`: Contains the Jinja2 HTML templates for the website.
- `static/`: Contains static assets like CSS files. The generated output from the CLI (`newsletter.html`, etc.) is also placed here in an `output` subdirectory.

## Running the Server

To start the web server, run the following command from the project root:
```bash
python -m crd.web.app
```