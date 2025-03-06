import os
import json
import shutil
import zipfile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def read_file(file_path, encoding='utf-8'):
    """Read content from a file"""
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def write_file(file_path, content, encoding='utf-8'):
    """Write content to a file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(content)
        return True
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        return False

def read_json(file_path, encoding='utf-8'):
    """Read JSON from a file"""
    content = read_file(file_path, encoding)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {file_path}: {e}")
    return None

def write_json(file_path, data, encoding='utf-8', indent=4):
    """Write JSON to a file"""
    try:
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        return write_file(file_path, content, encoding)
    except Exception as e:
        logger.error(f"Error writing JSON to {file_path}: {e}")
        return False

def zip_files_and_folders(zip_filename, items_to_zip):
    """Zip files and folders"""
    try:
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
        return True
    except Exception as e:
        logger.error(f"Error creating zip file {zip_filename}: {e}")
        return False

def remove_items(items_to_remove):
    """Remove files and folders"""
    for item in items_to_remove:
        try:
            if os.path.isdir(item):
                shutil.rmtree(item)
            elif os.path.isfile(item):
                os.remove(item)
        except Exception as e:
            logger.error(f"Error removing {item}: {e}")

def update_gitignore(content):
    """Update .gitignore file"""
    try:
        with open('.gitignore', 'a+') as gitignore_file:
            gitignore_file.seek(0)
            existing_content = gitignore_file.read()
            if content not in existing_content:
                gitignore_file.write(f"\n{content}")
        return True
    except Exception as e:
        logger.error(f"Error updating .gitignore: {e}")
        return False