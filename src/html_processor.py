import re
from bs4 import BeautifulSoup, Comment
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HTMLProcessor:
    """
    A class for extracting and processing content from HTML documents,
    particularly optimized for WeChat articles
    """
    
    def __init__(self, html_content, url=None):
        """Initialize with HTML content"""
        self.html = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script, style, and comment elements
        for element in self.soup(["script", "style", "noscript"]):
            element.decompose()
            
        for comment in self.soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
    
    def get_title(self):
        """Extract the title using multiple selector strategies"""
        # Try the most common title selectors
        title_selectors = [
            'h1.rich_media_title', 
            'h1#activity-name',
            'h1.activity-name',
            'div.rich_media_content h1',
            'h2.rich_media_title',
            'h1.title',
            'div.title',
            'meta[property="og:title"]'
        ]
        
        for selector in title_selectors:
            elements = self.soup.select(selector)
            if elements:
                if selector.startswith('meta'):
                    title = elements[0].get('content', '')
                else:
                    title = self._normalize_text(elements[0].get_text())
                if title:
                    return title
        
        # Try looking for the largest header
        headers = self.soup.find_all(['h1', 'h2'])
        if headers:
            # Sort by text length to find the most substantial header
            headers.sort(key=lambda x: len(x.get_text()), reverse=True)
            return self._normalize_text(headers[0].get_text())
        
        # Fallback to document title
        if self.soup.title:
            return self._normalize_text(self.soup.title.string)
        
        return "WeChat Article"
    
    def get_author(self):
        """Extract the author"""
        author_selectors = [
            'a.wx_tap_link',
            'a.rich_media_meta_link',
            'span.rich_media_meta_text',
            'div#js_profile_qrcode strong.profile_nickname',
            'div.profile_nickname',
            'meta[name="author"]',
            'span.author'
        ]
        
        for selector in author_selectors:
            elements = self.soup.select(selector)
            if elements:
                if selector.startswith('meta'):
                    author = elements[0].get('content', '')
                else:
                    author = self._normalize_text(elements[0].get_text())
                if author:
                    return author
        
        return "Unknown Author"
    
    def get_publication_date(self):
        """Extract the publication date"""
        date_selectors = [
            '#publish_time',
            '.publish_time',
            '.post-date',
            '.rich_media_createtime',
            'em.rich_media_meta_text'
        ]
        
        for selector in date_selectors:
            elements = self.soup.select(selector)
            for element in elements:
                date_text = self._normalize_text(element.get_text())
                # Look for date patterns
                if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}', date_text):
                    return date_text
        
        return None
    
    def get_content_element(self):
        """Find the main content element"""
        content_selectors = [
            'div.rich_media_content',
            'div#js_content',
            'div.article-content',
            'div.rich_media_wrp'
        ]
        
        for selector in content_selectors:
            elements = self.soup.select(selector)
            if elements:
                return elements[0]
        
        # Try to find the content by looking for divs with lots of text
        candidates = self.soup.find_all('div')
        if candidates:
            # Get divs with significant text content
            text_divs = [(div, len(div.get_text())) for div in candidates 
                        if len(div.get_text()) > 500]
            
            if text_divs:
                # Sort by text length, assuming largest is the content
                text_divs.sort(key=lambda x: x[1], reverse=True)
                return text_divs[0][0]
        
        return None
    
    def extract_content_blocks(self):
        """
        Extract content blocks (text paragraphs, images, headings)
        in the order they appear in the document
        """
        content_element = self.get_content_element()
        blocks = []
        
        if not content_element:
            logger.warning("No content element found")
            return blocks
        
        # Process direct child elements to maintain structure
        for element in content_element.children:
            if element.name in ['p', 'div', 'section', 'span']:
                text = self._extract_text_from_element(element)
                if text and len(text) > 5:  # Skip very short texts
                    blocks.append({
                        'type': 'paragraph',
                        'content': text
                    })
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                text = self._normalize_text(element.get_text())
                if text:
                    blocks.append({
                        'type': 'heading',
                        'level': int(element.name[1]),
                        'content': text
                    })
            elif element.name == 'img':
                img_url = self._get_image_url(element)
                if img_url:
                    blocks.append({
                        'type': 'image',
                        'url': img_url,
                        'alt': element.get('alt', '')
                    })
            elif element.name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li'):
                    list_text = self._normalize_text(li.get_text())
                    if list_text:
                        list_items.append(list_text)
                
                if list_items:
                    blocks.append({
                        'type': 'list',
                        'style': 'bullet' if element.name == 'ul' else 'numbered',
                        'items': list_items
                    })
            # Handle div with images separately
            elif element.name == 'div':
                # Check for images
                for img in element.find_all('img'):
                    img_url = self._get_image_url(img)
                    if img_url:
                        blocks.append({
                            'type': 'image',
                            'url': img_url,
                            'alt': img.get('alt', '')
                        })
                
                # Check for text
                text = self._extract_text_from_element(element)
                if text and len(text) > 5:
                    blocks.append({
                        'type': 'paragraph',
                        'content': text
                    })
        
        # If we couldn't extract much content from direct children,
        # try a more aggressive approach
        if len(blocks) < 5:
            logger.info("Few blocks found, trying deeper content extraction")
            blocks.extend(self._extract_deep_content(content_element))
        
        return blocks
        
    def _extract_deep_content(self, root_element):
        """Extract content from deeper within the element structure"""
        blocks = []
        
        # Find all paragraphs with substantial text
        paragraphs = root_element.find_all(['p', 'div', 'section', 'span'])
        for p in paragraphs:
            if p.parent.name not in ['li', 'blockquote']:  # Skip nested elements
                text = self._normalize_text(p.get_text())
                if text and len(text) > 20:  # Only include substantial paragraphs
                    blocks.append({
                        'type': 'paragraph',
                        'content': text
                    })
        
        # Find all headers
        headers = root_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
        for h in headers:
            text = self._normalize_text(h.get_text())
            if text:
                blocks.append({
                    'type': 'heading',
                    'level': int(h.name[1]),
                    'content': text
                })
        
        # Find all images that haven't been processed
        images = root_element.find_all('img')
        for img in images:
            img_url = self._get_image_url(img)
            if img_url:
                blocks.append({
                    'type': 'image',
                    'url': img_url,
                    'alt': img.get('alt', '')
                })
        
        return blocks
    
    def _get_image_url(self, img_element):
        """Extract image URL from various possible attributes"""
        for attr in ['data-src', 'src', 'data-url', 'data-backh-src']:
            if img_element.get(attr):
                url = img_element.get(attr)
                # Ensure URL is absolute
                if url.startswith('//'):
                    return 'https:' + url
                return url
        return None
    
    def _normalize_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        # Replace non-breaking spaces
        text = text.replace('\xa0', ' ')
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Trim leading/trailing whitespace
        return text.strip()
    
    def _extract_text_from_element(self, element):
        """Extract text from an element, preserving some structure"""
        if not element:
            return ""
            
        # Handle special elements
        if element.name == 'br':
            return "\n"
            
        # Get text from this element and its children
        text_parts = []
        
        for child in element.children:
            if child.name:
                # It's a tag
                if child.name == 'br':
                    text_parts.append("\n")
                else:
                    child_text = self._extract_text_from_element(child)
                    if child_text:
                        text_parts.append(child_text)
            elif child.string:
                # It's a text node
                text = child.string.strip()
                if text:
                    text_parts.append(text)
        
        # Join with appropriate spacing

















        return "\n".join(content)                            content.append(text)                if text:                text = self._normalize_text(element)            if element.parent.name not in ['script', 'style', 'meta', 'head']:        for element in self.soup.find_all(text=True):                content = []        """Get all visible text from the document"""    def get_all_text(self):        return text.strip()        text = re.sub(r'\s+', ' ', text)        # Normalize spaces        text = " ".join(text_parts)
