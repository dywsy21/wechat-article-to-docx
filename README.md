# WeChat Article to DOCX Converter

A simple Python tool that converts WeChat articles to Microsoft Word (.docx) documents.

## Installation

### Run from source

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

### Download binary

Alternatively, directly download binary release.

## Usage

### Command Line

```
python main.py [WeChat Article URL] --output [output_file.docx]
```

Example:
```
python main.py https://mp.weixin.qq.com/s/example_article_url --output article.docx
```

If no output path is specified, the document will be saved with a name based on the article title.

### As a Module

```python
from main import wechat_to_docx

wechat_to_docx("https://mp.weixin.qq.com/s/example_article_url", "output.docx")
```

## Notes

- This tool may not work if the WeChat article structure changes
- Some complex formatting or dynamic content might not be preserved
- Requires internet connection to download the article and its images
