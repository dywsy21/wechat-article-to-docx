import argparse
import os
import tempfile
import time
import traceback
from urllib.parse import urlparse
import requests
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import re

from bypass_wechat_limitations import fetch_wechat_article
from html_processor import HTMLProcessor

def is_valid_url(url):
    """Check if the URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def download_image(img_url, temp_dir):
    """Download image from URL and save to temporary directory"""
    try:
        # Ensure the URL is absolute
        if not img_url.startswith(('http://', 'https://')):
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            else:
                print(f"Skipping image with invalid URL: {img_url}")
                return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://mp.weixin.qq.com/'
        }
        response = requests.get(img_url, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            # Generate a unique filename
            img_filename = f"img_{abs(hash(img_url)) % 10000}_{int(time.time())}_{hash(img_url) % 1000}.jpg"
            img_path = os.path.join(temp_dir, img_filename)
            with open(img_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            # Wait a moment to avoid being blocked
            time.sleep(0.2)
            return img_path
    except Exception as e:
        print(f"Failed to download image: {e} - URL: {img_url}")
    return None

def wechat_to_docx(url, output_path=None):
    """Convert WeChat article to docx document using enhanced HTML processor"""
    if not is_valid_url(url):
        print("Invalid URL provided")
        return False
    
    try:
        print(f"Fetching article from {url}...")
        
        # Use our bypass function to get the HTML content
        html_content = fetch_wechat_article(url)
        
        if not html_content:
            print("Failed to retrieve the article content")
            return False
        
        # Save HTML for debugging
        with open('debug_html.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Saved HTML to debug_html.html for debugging")
        