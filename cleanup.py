import os
import shutil
import zipfile
from datetime import datetime

def zip_files_and_folders(zip_filename, items_to_zip):
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in items_to_zip:
            if os.path.isdir(item):
                for root, _, files in os.walk(item):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=os.path.dirname(item))
                        zipf.write(file_path, arcname)
            elif os.path.isfile(item):
                zipf.write(item, os.path.basename(item))

def remove_items(items_to_remove):
    for item in items_to_remove:
        if os.path.isdir(item):
            shutil.rmtree(item)
        elif os.path.isfile(item):
            os.remove(item)

def update_gitignore():
    gitignore_content = "\n# Archive folder\narchives/"
    with open('.gitignore', 'a+') as gitignore_file:
        gitignore_file.seek(0)
        existing_content = gitignore_file.read()
        if "archives/" not in existing_content:
            gitignore_file.write(gitignore_content)

def copy_to_output_folder(output_folder, items_to_copy):
    os.makedirs(output_folder, exist_ok=True)
    for item in items_to_copy:
        if os.path.isdir(item):
            shutil.copytree(item, os.path.join(output_folder, os.path.basename(item)))
        elif os.path.isfile(item):
            shutil.copy2(item, output_folder)

import sys
from crd.cleanup import Cleanup
from crd.utils.logging import setup_logger

def main():
    # Setup logging
    logger = setup_logger('crd_cleanup')
    
    # Define items to archive and copy
    items_to_archive = [
        "article_summaries",
        "articles_text",
        "high_rated_articles",
        "articles.csv",
    ]
    
    items_to_copy = [
        "newsletter.html",
        "thumbnails",
        "titles_and_links.txt",
        "newsletter.png"
    ]
    
    # Create cleanup handler
    cleanup = Cleanup()
    
    # Process cleanup
    logger.info("Cleaning up and archiving files")
    cleanup.process(items_to_archive, items_to_copy)
    
    logger.info("Cleanup complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())