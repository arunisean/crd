import subprocess
import time
import os

def run_script(script_name):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"Starting {script_name} at {start_time}")
    
    process = subprocess.Popen(['python', script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    
    stdout, stderr = process.communicate()
    returncode = process.returncode
    
    if stdout:
        print(stdout.strip())
    
    if returncode == 0:
        print(f"{script_name} executed successfully.")
    else:
        print(f"Error executing {script_name}:\n{stderr}")

def main():
    scripts = [
        'rss_digest.py',
        'rating-openai.py',
        'summerize-high-rated.py',
        'make_newsletter.py',
        'renderpng.py',
        'cleanup.py'
    ]

    for i, script in enumerate(scripts, start=1):
        print(f"Running script {i}/{len(scripts)}: {script}")
        run_script(script)

import sys
from crd.cli import main as crd_main

if __name__ == "__main__":
    sys.exit(crd_main())