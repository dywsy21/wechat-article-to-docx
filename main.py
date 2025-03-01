import os
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Inches
import tempfile
import argparse
from urllib.parse import urlparse
import traceback
import re
import time
import random

def is_valid_url(url):
    """Check if the URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def download_image(img_url, temp_dir):
    """Download image from URL and save to temp directory"""
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
            # Generate a more reliable filename
            img_filename = f"img_{abs(hash(img_url)) % 10000}_{int(time.time())}_{random.randint(1000, 9999)}.jpg"
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
    """Convert WeChat article to docx document"""
    if not is_valid_url(url):
        print("Invalid URL provided")
        return False
    
    try:
        print(f"Fetching article from {url}...")
        # Fetch the webpage content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print("Parsing HTML content...")
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug HTML structure
        with open('debug_html.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("Saved debug HTML to debug_html.html")
        
        # Extract title - try different possible class names
        title = None
        possible_title_selectors = [
            'h1.rich_media_title', 
            'h1#activity-name',
            'h1.activity-name',
            'div.rich_media_content h1',
            'div.rich_media_content h2:first-of-type'
        ]
        
        for selector in possible_title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                print(f"Found title: {title}")
                break
        
        if not title:
            print("Could not find title, using default")
            title = "WeChat Article"
        
        # Extract author - try different possible selectors
        author = None
        possible_author_selectors = [
            'a.wx_tap_link',
            'a.rich_media_meta_link',
            'span.rich_media_meta_text',
            'div#js_profile_qrcode strong.profile_nickname',
            'div.profile_nickname'
        ]
        
        for selector in possible_author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                print(f"Found author: {author}")
                break
        
        if not author:
            print("Could not find author, using default")
            author = "Unknown Author"
        
        # Extract article content - try different possible content containers
        content_div = None
        possible_content_selectors = [
            'div.rich_media_content',
            'div#js_content',
            'div.rich_media_wrp'
        ]
        
        for selector in possible_content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                print(f"Found content using selector: {selector}")
                break
        
        if not content_div:
            print("Could not find article content")
            return False
        
        print("Creating document...")
        # Create document
        doc = Document()
        doc.add_heading(title, level=1)
        doc.add_paragraph(f"Author: {author}")
        
        # Create temporary directory for images
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory for images: {temp_dir}")
        
        # Process paragraphs and images
        print("Processing content elements...")
        for element in content_div.find_all(['p', 'img', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol', 'div']):
            try:
                if element.name == 'img':
                    # Try different image URL attributes that WeChat might use
                    img_url = None
                    for attr in ['data-src', 'src', 'data-url', 'data-backh-src']:
                        if element.get(attr):
                            img_url = element.get(attr)
                            break
                    
                    if img_url:
                        print(f"Found image: {img_url[:50]}...")
                        img_path = download_image(img_url, temp_dir)
                        if img_path:
                            try:
                                doc.add_picture(img_path, width=Inches(6))
                                print(f"Added image to document")
                            except Exception as img_ex:
                                print(f"Error adding image to document: {img_ex}")
                
                # Handle div elements that might contain images
                elif element.name == 'div' and element.find('img'):
                    for img in element.find_all('img'):
                        img_url = None
                        for attr in ['data-src', 'src', 'data-url', 'data-backh-src']:
                            if img.get(attr):
                                img_url = img.get(attr)
                                break
                        
                        if img_url:
                            print(f"Found image in div: {img_url[:50]}...")
                            img_path = download_image(img_url, temp_dir)
                            if img_path:
                                try:
                                    doc.add_picture(img_path, width=Inches(6))
                                    print(f"Added image to document")
                                except Exception as img_ex:
                                    print(f"Error adding image to document: {img_ex}")
                
                elif element.name in ['h2', 'h3', 'h4']:
                    level = int(element.name[1])
                    heading_text = element.get_text().strip()
                    if heading_text:
                        doc.add_heading(heading_text, level=level)
                        print(f"Added heading: {heading_text[:30]}...")
                
                elif element.name == 'blockquote':
                    quote_text = element.get_text().strip()
                    if quote_text:
                        p = doc.add_paragraph(quote_text)
                        p.style = 'Quote'
                        print(f"Added blockquote: {quote_text[:30]}...")
                
                elif element.name in ['ul', 'ol']:
                    for li in element.find_all('li'):
                        li_text = li.get_text().strip()
                        if li_text:
                            doc.add_paragraph(li_text, style='List Bullet' if element.name == 'ul' else 'List Number')
                            print(f"Added list item: {li_text[:30]}...")
                
                elif element.name == 'p' or (element.name == 'div' and not element.find(['img', 'div'])):
                    text = element.get_text().strip()
                    if text:
                        doc.add_paragraph(text)
                        print(f"Added paragraph: {text[:30]}...")
            
            except Exception as elem_ex:
                print(f"Error processing element {element.name}: {elem_ex}")
        
        # Save document
        if not output_path:
            # Sanitize filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
            output_path = f"{safe_title.replace(' ', '_')[:30]}.docx"
        
        print(f"Saving document to {output_path}...")
        doc.save(output_path)
        print(f"Document saved as: {output_path}")
        return True
    
    except Exception as e:
        print(f"Error converting article: {e}")
        print("Detailed traceback:")
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert WeChat article to Word document')
    parser.add_argument('url', help='URL of the WeChat article')
    parser.add_argument('--output', '-o', help='Output document path')
    args = parser.parse_args()
    args.output = args.output + '.docx'


    success = wechat_to_docx(args.url, args.output)
    if success:
        print("Conversion completed successfully!")
    else:
        print("Conversion failed.")

if __name__ == "__main__":
    main()

