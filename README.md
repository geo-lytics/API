# News Article Downloader and Converter

A Python script that downloads news articles from the Siemens API and converts them to clean Markdown files with automatic change detection and logging.

## Features

- 🔄 **Dual Batch Download**: Downloads articles in 2 batches (limit=5, offset=0 and limit=5, offset=5) to get more articles
- 📝 **Markdown Conversion**: Converts rich text content to clean Markdown format
- 🔍 **Change Detection**: Only processes new or updated articles
- 📊 **Detailed Logging**: Maintains a complete log of all operations
- 🏷️ **Smart Categorization**: Organizes articles with tags, countries, and authors

## Installation

1. **Clone or download** this repository to your local machine

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API settings**:
   ```bash
   # Copy the example config file
   cp config.example.py config.py
   
   # Edit config.py with your API credentials
   # Update API_BASE_URL and API_KEY
   ```

4. **Verify installation**:
   ```bash
   python download_and_convert.py --help
   ```

## Quick Start

### Basic Usage

```bash
# Download and convert articles (2 batches of 5 articles each)
python download_and_convert.py

# Skip download and only convert existing raw.json
python download_and_convert.py --skip-download

# Custom batch configuration
python download_and_convert.py --batch-size 3 --num-batches 4
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Input JSON file path | `raw.json` |
| `--out` | Output directory | `md_export` |
| `--batch-size` | Articles per batch | `5` |
| `--num-batches` | Number of batches to download | `2` |
| `--skip-download` | Skip API download | `False` |

## File Structure

```
project/
├── download_and_convert.py    # Main script
├── config.py                  # API configuration (create from config.example.py)
├── config.example.py          # Example configuration file
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation
├── log.md                     # Operation log (created automatically)
├── raw.json                   # Downloaded API data (created automatically)
└── md_export/                 # Output directory
    ├── index.md              # Current articles index
    └── *.md                  # Individual article files
```

## Output Files

### Individual Article Files
Each article is saved as a Markdown file with the format: `{id}-{title-slug}.md`

**Structure:**
```markdown
# Article Title

## Basic Information
- **Author**: Author Name
- **Last Edited**: 2025-09-26

## Categories
- **Channels**: geopolitics, trade
- **Tags**: `Diplomacy` | `taiwan` | `us-china`
- **Countries**: **CHINA** | **USA**

## Key Takeaways
Key points from the article...

## Article Content
Full article content in Markdown format...
```

### Index File (`md_export/index.md`)
Simple list of all current articles with links.

### Log File (`log.md`)
Complete operation history with timestamps and statistics.

## Daily Automation

To run this script daily, you can set up a scheduled task:

### Windows Task Scheduler
1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task
3. Set trigger to "Daily"
4. Set action to start program: `python`
5. Add arguments: `download_and_convert.py`
6. Set start in directory to your project folder

### Linux/Mac Cron
```bash
# Add to crontab to run daily at 9 AM
0 9 * * * cd /path/to/project && python download_and_convert.py
```

## API Configuration

The script uses API settings from `config.py`:
- **Base URL**: Configured in `config.py`
- **Endpoint**: `/v1/topics/export`
- **Authentication**: API key in headers

To modify the API settings, edit `config.py`:
```python
API_BASE_URL = "your-api-url"
API_KEY = "your-api-key"
```

**Security Note**: Never commit `config.py` to version control. Use `config.example.py` as a template.

## Change Detection

The script intelligently detects changes:

- **New Articles**: 🆕 marker in log and index
- **Updated Articles**: 🔄 marker in log and index  
- **Unchanged Articles**: No marker, no file rewrite

Only new or changed articles trigger file updates, making subsequent runs efficient.

## Logging

### Log Entry Format
```markdown
## Log Entry - 2025-09-26 11:25:36
> Total articles: 10
> New articles: 2
> Updated articles: 1

## Current Articles
- [Article Title](filename.md) — Author (Date) 🆕
```

### Log Features
- **Complete History**: All operations are preserved
- **Timestamps**: Each entry includes exact time
- **Statistics**: New, updated, and total article counts
- **Status Markers**: Visual indicators for article status

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Check internet connection
   - Verify API key is correct
   - Check if API endpoint is accessible

2. **Permission Errors**
   - Ensure write permissions in the project directory
   - Run as Administrator if needed for scheduled tasks

3. **Python Import Errors**
   - Install requirements: `pip install -r requirements.txt`
   - Check Python version (3.6+ required)

4. **Duplicate Articles**
   - This is normal if the API returns overlapping results
   - The script handles duplicates automatically

### Debug Mode

For detailed debugging, check the console output which shows:
- API request details
- Article processing status
- File operation results
- Error messages with stack traces

## Examples

### Daily Workflow
```bash
# Download latest articles
python download_and_convert.py

# Check results
cat log.md | head -20  # View latest log entry
```

### Custom Batch Processing
```bash
# Download 3 batches of 10 articles each
python download_and_convert.py --batch-size 10 --num-batches 3

# Process only existing data
python download_and_convert.py --skip-download
```

### Testing
```bash
# Test with single batch
python download_and_convert.py --num-batches 1

# Test conversion only
python download_and_convert.py --skip-download
```

## Requirements

- **Python**: 3.6 or higher
- **Dependencies**: requests library
- **OS**: Windows, Linux, or macOS
- **Network**: Internet connection for API access

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the log files for error details
3. Verify API connectivity and permissions

---

**Happy article downloading! 📰✨**
