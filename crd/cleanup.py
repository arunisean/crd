import os
import logging
import shutil  # Add this import
from datetime import datetime
from .utils.io import zip_files_and_folders, remove_items, update_gitignore

logger = logging.getLogger(__name__)

class Cleanup:
    """Handles cleanup and archiving of files"""
    
    def __init__(self, archives_dir="archives", output_dir="output"):
        self.archives_dir = archives_dir
        self.output_dir = output_dir
    
    def copy_to_output_folder(self, output_folder, items_to_copy):
        """Copy items to output folder"""
        os.makedirs(output_folder, exist_ok=True)
        
        for item in items_to_copy:
            try:
                if os.path.isdir(item):
                    shutil.copytree(item, os.path.join(output_folder, os.path.basename(item)))
                elif os.path.isfile(item):
                    shutil.copy2(item, output_folder)
                logger.info(f"Copied {item} to {output_folder}")
            except Exception as e:
                logger.error(f"Error copying {item} to {output_folder}: {e}")
    
    def process(self, items_to_archive, items_to_copy=None):
        """Process cleanup: archive files, copy to output, and remove originals"""
        # Create archives directory
        os.makedirs(self.archives_dir, exist_ok=True)
        
        # Create current timestamp
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create zip filename with current date and time
        zip_filename = os.path.join(self.archives_dir, f"archive_{current_time}.zip")
        
        # Create output folder with current date and time
        if items_to_copy:
            output_folder = os.path.join(self.output_dir, current_time)
            self.copy_to_output_folder(output_folder, items_to_copy)
        
        # Zip files and folders
        logger.info(f"Creating zip file: {zip_filename}")
        if zip_files_and_folders(zip_filename, items_to_archive):
            # Remove original files and folders
            logger.info("Removing original files and folders")
            remove_items(items_to_archive)
            
            # Update .gitignore
            update_gitignore("# Archive folder\narchives/")
            
            logger.info(f"Cleanup complete. Archive created: {zip_filename}")
            return True
        
        logger.error("Failed to create archive")
        return False