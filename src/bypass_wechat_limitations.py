import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

def get_article_with_selenium(url):
    """
    Use Selenium to render the page with JavaScript and bypass limitations
    Returns the full rendered HTML
    """
    try:
        print("Starting Chrome in headless mode...")
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920x1080')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        print(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for the content to load
        print("Waiting for content to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.rich_media_content, div#js_content'))
        )
        
        # Additional wait to ensure dynamic content loads
        time.sleep(5)
        
        print("Page loaded, extracting content...")
        html_content = driver.page_source
        
        # Save page metadata
        try:
            title = driver.title
            meta_data = {
                'url': url,
                'title': title,
                'timestamp': time.time()
            }
            
            with open('article_metadata.json', 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
                
            print(f"Saved metadata with title: {title}")
        except Exception as meta_e:
            print(f"Error saving metadata: {meta_e}")
        
        # Close browser
        driver.quit()
        return html_content
    
    except Exception as e:
        print(f"Error using Selenium: {e}")
        if 'driver' in locals():
            driver.quit()
        return None

def fetch_wechat_article(url):
    """
    Attempts to fetch a WeChat article using various methods to bypass limitations.
    Returns the article HTML content.
    """
    print("Attempting to fetch article with standard requests...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Check if we got a proper article or an error page
            if 'rich_media_content' in response.text or 'js_content' in response.text:
                print("Successfully fetched article with requests!")
                return response.text
            else:
                print("Got 200 response but content may be incomplete, trying Selenium...")
        else:
            print(f"HTTP error: {response.status_code}, trying Selenium...")
    
    except Exception as req_error:
        print(f"Request error: {req_error}, trying Selenium...")
    
    # Fall back to Selenium if requests failed
    return get_article_with_selenium(url)

if __name__ == "__main__":
    # Example usage
    test_url = "https://mp.weixin.qq.com/s/example_article_url"
    content = fetch_wechat_article(test_url)
    if content:
        with open("test_article.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Saved article HTML to test_article.html")
