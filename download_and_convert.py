#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combined script for downloading data from Siemens API and converting to Markdown
Downloads news article data from API and generates formatted Markdown files

Requirements:
- requests library: pip install requests

Features:
- Downloads latest 5 articles by default (configurable)
- Detects new vs existing articles on subsequent runs
- Reports how many new articles were downloaded
- Generates clean Markdown files with proper structure
"""

import json
import re
import unicodedata
import requests
from datetime import datetime
from typing import Dict, List, Any
import os
import argparse
from config import API_BASE_URL, API_KEY, DEFAULT_BATCH_SIZE, DEFAULT_NUM_BATCHES, DEFAULT_OUTPUT_DIR, DEFAULT_INPUT_FILE

def download_raw_data(output_file="raw.json", limit=5, offset=0):
    """
    Download raw data from Siemens API
    """
    url = f"{API_BASE_URL}/v1/topics/export?limit={limit}&offset={offset}"
    headers = {"x-api-key": API_KEY}
    
    try:
        print(f"Downloading data from API...")
        print(f"URL: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse response to check actual article count
        try:
            response_data = response.json()
            # Check if data is nested in 'body' field
            if 'body' in response_data and isinstance(response_data['body'], str):
                body_data = json.loads(response_data['body'])
                actual_articles = body_data.get('topics', [])
                meta_info = body_data.get('meta', {})
                api_limit = meta_info.get('limit', 'unknown')
                print(f"API returned {len(actual_articles)} articles (requested: {limit}, API limit: {api_limit})")
            else:
                actual_articles = response_data.get('topics', [])
                print(f"API returned {len(actual_articles)} articles (requested: {limit})")
            
            if len(actual_articles) != limit:
                print(f"⚠️  Note: API returned different number of articles than requested. This might be due to:")
                print(f"   - API returning all available articles if less than requested")
                print(f"   - API having a different default behavior")
                print(f"   - API pagination or caching behavior")
        except Exception as e:
            print(f"Could not parse response to count articles: {e}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✅ Successfully downloaded data to {output_file}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def download_multiple_batches(output_file="raw.json", batch_size=5, num_batches=2):
    """
    Download data from multiple API batches and combine them
    """
    all_articles = []
    all_meta = {}
    
    print(f"🔄 Downloading {num_batches} batches of {batch_size} articles each...")
    
    for batch in range(num_batches):
        offset = batch * batch_size
        print(f"\n--- Batch {batch + 1}/{num_batches} (offset: {offset}) ---")
        
        url = f"{API_BASE_URL}/v1/topics/export?limit={batch_size}&offset={offset}"
        headers = {"x-api-key": API_KEY}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Check if data is nested in 'body' field
            if 'body' in response_data and isinstance(response_data['body'], str):
                body_data = json.loads(response_data['body'])
                articles = body_data.get('topics', [])
                meta = body_data.get('meta', {})
            else:
                articles = response_data.get('topics', [])
                meta = response_data.get('meta', {})
            
            print(f"Batch {batch + 1}: Got {len(articles)} articles")
            all_articles.extend(articles)
            
            # Update meta info (use the latest batch's meta)
            all_meta.update(meta)
            
            # If we got fewer articles than requested, we've reached the end
            if len(articles) < batch_size:
                print(f"⚠️  Batch {batch + 1} returned fewer articles than requested. This might be the last batch.")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading batch {batch + 1}: {e}")
            continue
        except Exception as e:
            print(f"❌ Unexpected error in batch {batch + 1}: {e}")
            continue
    
    # Combine all articles into a single response
    combined_response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps({
            "meta": {
                **all_meta,
                "limit": len(all_articles),
                "offset": 0,
                "total_fetched": len(all_articles)
            },
            "topics": all_articles
        })
    }
    
    # Save combined data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_response, f, indent=2)
    
    print(f"\n✅ Successfully downloaded {len(all_articles)} total articles to {output_file}")
    return len(all_articles) > 0

def slugify(value, allow_unicode=True):
    """
    Convert text to URL-friendly slug format
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")

def to_yaml_like(value):
    """
    Convert Python/JSON values to YAML-style text (simple and safe version)
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Wrap with double quotes and escape internal quotes
        return '"' + value.replace('"', '\\"') + '"'
    if isinstance(value, (list, tuple)):
        items = ", ".join(to_yaml_like(v) for v in value)
        return f"[{items}]"
    if isinstance(value, dict):
        # Dict not expected; fallback to JSON
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)

def clean_text(text: str) -> str:
    """
    Clean text content, remove extra whitespace and special characters
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove newlines and tabs
    text = text.replace('\n', ' ').replace('\t', ' ')
    # Remove HTML tags (if any)
    text = re.sub(r'<[^>]+>', '', text)
    # Clean leading and trailing whitespace
    text = text.strip()
    
    return text

def parse_content(content_data: Any) -> str:
    """
    Parse rich text content from content field and convert to Markdown format
    """
    if not content_data:
        return ""
    
    # If content is a string, try to parse as JSON
    if isinstance(content_data, str):
        try:
            content_data = json.loads(content_data)
        except:
            return clean_text(content_data)
    
    # If content is a dict, extract and convert to Markdown
    if isinstance(content_data, dict):
        return convert_to_markdown(content_data)
    
    return str(content_data)

def convert_to_markdown(content_obj: dict) -> str:
    """
    Convert rich text content object to Markdown format
    """
    if not isinstance(content_obj, dict) or 'content' not in content_obj:
        return ""
    
    markdown_parts = []
    
    for item in content_obj['content']:
        if isinstance(item, dict):
            markdown_item = convert_node_to_markdown(item)
            if markdown_item.strip():
                markdown_parts.append(markdown_item)
    
    return '\n\n'.join(markdown_parts)

def convert_node_to_markdown(node: dict) -> str:
    """
    Convert a single node to Markdown format
    """
    node_type = node.get('type', '')
    
    if node_type == 'paragraph':
        return convert_paragraph_to_markdown(node)
    elif node_type == 'heading':
        return convert_heading_to_markdown(node)
    elif node_type == 'bulletList':
        return convert_bullet_list_to_markdown(node)
    elif node_type == 'orderedList':
        return convert_ordered_list_to_markdown(node)
    elif node_type == 'listItem':
        return convert_list_item_to_markdown(node)
    elif node_type == 'blockquote':
        return convert_blockquote_to_markdown(node)
    elif node_type == 'codeBlock':
        return convert_code_block_to_markdown(node)
    elif node_type == 'table':
        return convert_table_to_markdown(node)
    elif node_type == 'image':
        return convert_image_to_markdown(node)
    elif node_type == 'horizontalRule':
        return '---'
    else:
        # For other types, try recursive processing
        if 'content' in node:
            return convert_to_markdown(node)
        return ""

def convert_paragraph_to_markdown(node: dict) -> str:
    """
    Convert paragraph node
    """
    if 'content' not in node:
        return ""
    
    text_parts = []
    for item in node['content']:
        if isinstance(item, dict):
            text_parts.append(convert_text_node_to_markdown(item))
    
    return ''.join(text_parts)

def convert_text_node_to_markdown(node: dict) -> str:
    """
    Convert text node, handle bold, italic, links and other formats
    """
    if node.get('type') != 'text':
        return ""
    
    text = node.get('text', '')
    marks = node.get('marks', [])
    
    # Apply all marks
    for mark in marks:
        if isinstance(mark, dict):
            mark_type = mark.get('type', '')
            if mark_type == 'bold':
                text = f"**{text}**"
            elif mark_type == 'italic':
                text = f"*{text}*"
            elif mark_type == 'code':
                text = f"`{text}`"
            elif mark_type == 'link':
                attrs = mark.get('attrs', {})
                href = attrs.get('href', '#')
                text = f"[{text}]({href})"
            elif mark_type == 'strike':
                text = f"~~{text}~~"
    
    return text

def convert_heading_to_markdown(node: dict) -> str:
    """
    Convert heading node
    """
    level = node.get('attrs', {}).get('level', 1)
    if 'content' not in node:
        return ""
    
    text_parts = []
    for item in node['content']:
        if isinstance(item, dict):
            text_parts.append(convert_text_node_to_markdown(item))
    
    heading_text = ''.join(text_parts)
    return f"{'#' * level} {heading_text}"

def convert_bullet_list_to_markdown(node: dict) -> str:
    """
    Convert unordered list
    """
    if 'content' not in node:
        return ""
    
    list_items = []
    for item in node['content']:
        if isinstance(item, dict) and item.get('type') == 'listItem':
            list_item_text = convert_list_item_to_markdown(item)
            if list_item_text.strip():
                list_items.append(f"- {list_item_text}")
    
    return '\n'.join(list_items)

def convert_ordered_list_to_markdown(node: dict) -> str:
    """
    Convert ordered list
    """
    if 'content' not in node:
        return ""
    
    list_items = []
    for i, item in enumerate(node['content'], 1):
        if isinstance(item, dict) and item.get('type') == 'listItem':
            list_item_text = convert_list_item_to_markdown(item)
            if list_item_text.strip():
                list_items.append(f"{i}. {list_item_text}")
    
    return '\n'.join(list_items)

def convert_list_item_to_markdown(node: dict) -> str:
    """
    Convert list item
    """
    if 'content' not in node:
        return ""
    
    text_parts = []
    for item in node['content']:
        if isinstance(item, dict):
            if item.get('type') == 'paragraph':
                text_parts.append(convert_paragraph_to_markdown(item))
            else:
                text_parts.append(convert_node_to_markdown(item))
    
    return ' '.join(text_parts)

def convert_blockquote_to_markdown(node: dict) -> str:
    """
    Convert blockquote
    """
    if 'content' not in node:
        return ""
    
    text_parts = []
    for item in node['content']:
        if isinstance(item, dict):
            text_parts.append(convert_node_to_markdown(item))
    
    quote_text = '\n'.join(text_parts)
    return f"> {quote_text}"

def convert_code_block_to_markdown(node: dict) -> str:
    """
    Convert code block
    """
    if 'content' not in node:
        return ""
    
    text_parts = []
    for item in node['content']:
        if isinstance(item, dict) and item.get('type') == 'text':
            text_parts.append(item.get('text', ''))
    
    code_text = ''.join(text_parts)
    language = node.get('attrs', {}).get('language', '')
    return f"```{language}\n{code_text}\n```"

def convert_table_to_markdown(node: dict) -> str:
    """
    Convert table
    """
    if 'content' not in node:
        return ""
    
    table_rows = []
    for row in node['content']:
        if isinstance(row, dict) and row.get('type') == 'tableRow':
            row_cells = []
            for cell in row.get('content', []):
                if isinstance(cell, dict) and cell.get('type') == 'tableCell':
                    # Table cells may contain paragraphs, need recursive processing
                    cell_text = convert_table_cell_to_markdown(cell)
                    row_cells.append(cell_text)
            if row_cells:
                table_rows.append('| ' + ' | '.join(row_cells) + ' |')
    
    if not table_rows:
        return ""
    
    # Add table header separator line
    if len(table_rows) > 0:
        # Calculate number of columns
        first_row = table_rows[0]
        col_count = len([col for col in first_row.split('|') if col.strip()])
        separator = '| ' + ' | '.join(['---'] * col_count) + ' |'
        table_rows.insert(1, separator)
    
    return '\n'.join(table_rows)

def convert_table_cell_to_markdown(cell: dict) -> str:
    """
    Convert table cell
    """
    if 'content' not in cell:
        return ""
    
    text_parts = []
    for item in cell['content']:
        if isinstance(item, dict):
            if item.get('type') == 'paragraph':
                # Paragraph content, extract text
                paragraph_text = convert_paragraph_to_markdown(item)
                text_parts.append(paragraph_text)
            else:
                # Other types, recursive processing
                text_parts.append(convert_node_to_markdown(item))
    
    return ' '.join(text_parts)

def convert_image_to_markdown(node: dict) -> str:
    """
    Convert image
    """
    attrs = node.get('attrs', {})
    src = attrs.get('src', '')
    alt = attrs.get('alt', '')
    title = attrs.get('title', '')
    
    if title:
        return f"![{alt}]({src} \"{title}\")"
    else:
        return f"![{alt}]({src})"

def format_date(date_str: str) -> str:
    """
    Format date string
    """
    if not date_str:
        return "Unknown date"
    
    try:
        # Try to parse date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except:
        return date_str

def format_authors(authors: List[str]) -> str:
    """
    Format author list
    """
    if not authors:
        return "Unknown author"
    
    if len(authors) == 1:
        return authors[0]
    elif len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    else:
        return f"{', '.join(authors[:-1])} and {authors[-1]}"

def format_tags(tags: List[str]) -> str:
    """
    Format tag list
    """
    if not tags:
        return ""
    
    return " | ".join([f"`{tag}`" for tag in tags])

def format_countries(countries: List[str]) -> str:
    """
    Format country list
    """
    if not countries:
        return ""
    
    return " | ".join([f"**{country.upper()}**" for country in countries])

def load_payload(path):
    """
    Load JSON data, compatible with raw.json format
    """
    with open(path, "r", encoding="utf-8") as f:
        top = json.load(f)
    # Compatible with raw.json (body is JSON string) case
    if isinstance(top.get("body"), str):
        try:
            return json.loads(top["body"])
        except json.JSONDecodeError:
            pass
    return top

def generate_article_markdown(article: Dict[str, Any]) -> str:
    """
    Generate Markdown content for a single article
    """
    # Article basic information
    title = article.get('title', 'Untitled')
    authors = article.get('authors', [])
    publisher = article.get('publisher', '')
    last_edited = article.get('last_edited_date', '')
    tags = article.get('tags', [])
    countries = article.get('countries', [])
    channels = article.get('channels', [])
    key_takeaways = article.get('key_takeaways', '')
    article_id = article.get('id', '')
    
    # Parse article content
    content = article.get('content', '')
    if content:
        parsed_content = parse_content(content)
    else:
        parsed_content = ""
    
    # Generate Markdown content
    md_content = []
    md_content.append(f"# {title}")
    md_content.append("")
    
    # Basic information
    md_content.append("## Basic Information")
    md_content.append(f"- **Author**: {format_authors(authors)}")
    md_content.append(f"- **Last Edited**: {format_date(last_edited)}")
    md_content.append("")
    
    # Categories and tags
    if channels:
        md_content.append("## Categories")
        md_content.append(f"- **Channels**: {', '.join(channels)}")
    
    if tags:
        md_content.append(f"- **Tags**: {format_tags(tags)}")
    
    if countries:
        md_content.append(f"- **Countries**: {format_countries(countries)}")
    
    md_content.append("")
    
    # Key takeaways
    if key_takeaways:
        md_content.append("## Key Takeaways")
        md_content.append(clean_text(key_takeaways))
        md_content.append("")
    
    # Article content
    if parsed_content.strip():
        md_content.append("## Article Content")
        md_content.append(parsed_content)
        md_content.append("")
    
    return "\n".join(md_content)

def get_existing_article_ids(out_dir="md_export"):
    """
    Get list of existing article IDs from the output directory
    """
    existing_ids = set()
    if not os.path.exists(out_dir):
        return existing_ids
    
    for filename in os.listdir(out_dir):
        if filename.endswith('.md') and filename != 'index.md':
            # Extract ID from filename (format: {id}-{slug}.md)
            if '-' in filename:
                article_id = filename.split('-')[0]
                existing_ids.add(article_id)
    
    return existing_ids

def get_existing_article_content(out_dir="md_export", article_id=""):
    """
    Get existing article content for comparison
    """
    if not article_id:
        return None
    
    # Find the file with this ID
    if not os.path.exists(out_dir):
        return None
    
    for filename in os.listdir(out_dir):
        if filename.endswith('.md') and filename != 'index.md' and filename.startswith(article_id[:8]):
            file_path = os.path.join(out_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return None
    
    return None

def convert_json_to_markdown(input_path="raw.json", out_dir="md_export"):
    """
    Convert JSON data to Markdown files
    """
    try:
        # Read JSON file
        print(f"Reading {input_path} file...")
        data = load_payload(input_path)
        articles = data.get('topics', [])
        
        print(f"Found {len(articles)} articles")
        
        # Get existing article IDs to detect new ones
        existing_ids = get_existing_article_ids(out_dir)
        print(f"Found {len(existing_ids)} existing articles in {out_dir}")
        
        # Create output directory (only if it doesn't exist)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            print(f"Created output directory: {out_dir}")
        
        new_articles_count = 0
        updated_articles_count = 0
        unchanged_articles_count = 0
        
        # Process each article
        for i, article in enumerate(articles, 1):
            article_id = article.get('id', '')
            safe_id = (article_id or "")[:8]
            
            # Check if this is a new article
            is_new = safe_id not in existing_ids if safe_id else True
            
            # Generate filename
            title = article.get('title', f'Article {i}')
            slug = slugify(title) or f"article-{i}"
            filename = f"{safe_id}-{slug}.md" if safe_id else f"{slug}.md"
            
            # Generate article Markdown
            article_md = generate_article_markdown(article)
            
            # Check if content has changed for existing articles
            content_changed = True
            if not is_new:
                existing_content = get_existing_article_content(out_dir, safe_id)
                if existing_content == article_md:
                    content_changed = False
                    unchanged_articles_count += 1
                    print(f"Processing existing article {i} (ID: {safe_id}) - No changes")
                else:
                    updated_articles_count += 1
                    print(f"Processing existing article {i} (ID: {safe_id}) - Updated")
            else:
                new_articles_count += 1
                print(f"Processing NEW article {i} (ID: {safe_id})...")
            
            # Save article file (only if new or content changed)
            if is_new or content_changed:
                article_path = os.path.join(out_dir, filename)
                with open(article_path, 'w', encoding='utf-8') as f:
                    f.write(article_md)
        
        # Read existing log file to preserve history
        log_path = "log.md"
        existing_log_lines = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                existing_log_lines = f.readlines()
        
        # Generate new log entry
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_log_entry = [
            f"## Log Entry - {current_time}\n",
            f"> Total articles: {len(articles)}\n",
            f"> New articles: {new_articles_count}\n",
            f"> Updated articles: {updated_articles_count}\n",
            "\n"
        ]
        
        # Generate current articles list
        articles_section = ["## Current Articles\n"]
        for i, article in enumerate(articles, 1):
            article_id = article.get('id', '')
            safe_id = (article_id or "")[:8]
            is_new = safe_id not in existing_ids if safe_id else True
            
            # Generate filename
            title = article.get('title', f'Article {i}')
            slug = slugify(title) or f"article-{i}"
            filename = f"{safe_id}-{slug}.md" if safe_id else f"{slug}.md"
            
            # Check if content changed
            content_changed = True
            if not is_new:
                existing_content = get_existing_article_content(out_dir, safe_id)
                article_md = generate_article_markdown(article)
                if existing_content == article_md:
                    content_changed = False
            
            # Add to index
            authors = article.get('authors', [])
            last_edited = article.get('last_edited_date', '')
            author_line = ", ".join(authors) if authors else "Unknown author"
            
            if is_new:
                status_marker = " 🆕"
            elif content_changed:
                status_marker = " 🔄"
            else:
                status_marker = ""
            
            articles_section.append(f"- [{title}]({filename}) — {author_line} ({format_date(last_edited)}){status_marker}\n")
        
        articles_section.append("\n")
        
        # Combine new log entry + current articles + existing history
        all_lines = []
        all_lines.extend(new_log_entry)
        all_lines.extend(articles_section)
        
        # Add existing log content
        if existing_log_lines:
            all_lines.extend(existing_log_lines)
        
        # Save updated log file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.writelines(all_lines)
        
        # Also save a simple index.md in md_export folder
        index_path = os.path.join(out_dir, "index.md")
        simple_index_lines = ["# News Articles Summary\n\n"]
        simple_index_lines.extend(articles_section)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.writelines(simple_index_lines)
        
        print(f"✅ Successfully processed {out_dir} directory")
        print(f"📊 Processed {len(articles)} articles")
        print(f"🆕 New articles: {new_articles_count}")
        print(f"🔄 Updated articles: {updated_articles_count}")
        print(f"✅ Unchanged articles: {unchanged_articles_count}")
        
        # Display statistics
        print("\n📈 Statistics:")
        print(f"- Total articles: {len(articles)}")
        print(f"- New articles downloaded: {new_articles_count}")
        print(f"- Existing articles updated: {updated_articles_count}")
        print(f"- Unchanged articles: {unchanged_articles_count}")
        
        # Count tags
        all_tags = []
        for article in articles:
            all_tags.extend(article.get('tags', []))
        unique_tags = list(set(all_tags))
        print(f"- Unique tags: {len(unique_tags)}")
        
        # Count countries
        all_countries = []
        for article in articles:
            all_countries.extend(article.get('countries', []))
        unique_countries = list(set(all_countries))
        print(f"- Countries involved: {len(unique_countries)}")
        
        # Count authors
        all_authors = []
        for article in articles:
            all_authors.extend(article.get('authors', []))
        unique_authors = list(set(all_authors))
        print(f"- Unique authors: {len(unique_authors)}")
        
        return True, new_articles_count
        
    except FileNotFoundError:
        print(f"❌ Error: Cannot find {input_path} file")
        return False, 0
    except json.JSONDecodeError as e:
        print(f"❌ Error: JSON parsing failed - {e}")
        return False, 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def main():
    """
    Main function - download data and convert to Markdown
    """
    parser = argparse.ArgumentParser(description="Download data from Siemens API and convert to Markdown")
    parser.add_argument("--input", default=DEFAULT_INPUT_FILE, help=f"Input JSON file path (default: {DEFAULT_INPUT_FILE})")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_DIR, help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Articles per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--num-batches", type=int, default=DEFAULT_NUM_BATCHES, help=f"Number of batches to download (default: {DEFAULT_NUM_BATCHES})")
    parser.add_argument("--skip-download", action="store_true", help="Skip download and use existing raw.json file")
    args = parser.parse_args()
    
    # Download data if not skipping
    if not args.skip_download:
        print("🔄 Step 1: Downloading data from API...")
        if args.num_batches > 1:
            if not download_multiple_batches(args.input, args.batch_size, args.num_batches):
                print("❌ Failed to download data. Exiting.")
                return
        else:
            if not download_raw_data(args.input, args.batch_size, 0):
                print("❌ Failed to download data. Exiting.")
                return
        print()
    
    # Convert to Markdown
    print("🔄 Step 2: Converting to Markdown...")
    success, new_count = convert_json_to_markdown(args.input, args.out)
    
    if success:
        print(f"\n✅ All done! Downloaded {new_count} new articles.")
    else:
        print("\n❌ Conversion failed!")

if __name__ == "__main__":
    main()
