# API Handbook

## 1. Introduction

This API allows clients to bulk download the latest analysis along with their associated metadata, including last edited time, authors, channels, tags, countries, and key takeaways. 

The primary target users are clients' IT teams, who can:
- Retrieve report lists and detailed content;
- Convert the downloaded JSON content into Markdown files using the provided Python converter, making it easy to store, archive, and display in internal systems.

### Update Cycle
- All analysis and research are finalized by Friday each week.
- The latest reports become available through the API after Friday EOB (18:00 Central European Time, CET/CEST).
- Clients can fetch the complete set of new reports after this time.

### API Features
- Standardized JSON interface: all responses follow a unified JSON format (and then converted to Markdown by Python);
- Basic pagination support: by default, 5 records are returned per request, with paging supported via the offset parameter; 
- Secure access: API Key.

## 2. How To Use

### 2.1 Installation

(1) Clone or download this repository to your local machine
```
https://github.com/geo-lytics/API
```

(2) Install Python dependencies: (Python: 3.6 or higher)

```bash
pip install -r requirements.txt
```

(3) Configure API settings:

```bash
# Copy the example config file
cp config.example.py config.py

# Edit config.py with your API credentials
# Update API_BASE_URL and API_KEY
API_BASE_URL = "https://zlegl6sgdl.execute-api.eu-central-1.amazonaws.com/prod"
API_KEY is provided separately.
```

### 2.2 Quick Start

```bash
python download_and_convert.py
```

By default, the script retrieves the latest 10 articles, fetching 5 at a time in accordance with the API limit. This volume is sufficient to cover all weekly updates now and daily updates in the future.

All exported articles can be found in the md_export folder.

An operation log is maintained in the log.md file, which automatically tracks newly added or updated article headlines. Please refer to the sections below for more details.

**Other options:**
- `--batch-size`: Articles per batch, default 5
- `--num-batches`: Number of batches to download, default 2
- `--skip-download`: Skip download and only convert from json, default False 

**Example:** 
```bash
python download_and_convert.py --batch-size 2 --num-batches 1 
python download_and_convert.py --skip-download
```

### 2.3 Output Files

Only new or changed articles trigger file updates.

**(1) Individual Article Files (in the md_export folder):**

Each article is saved as a Markdown file with the format: `{id}-{title}.md`

**(2) Log File (log.md):**

Complete operation history with timestamps and statistics.

### 2.4 File Structure:

```
project/
├── download_and_convert.py     # Main script
├── config.py                  		# API configuration (create from config.example.py)
├── config.example.py          	# Example configuration file
├── requirements.txt           	# Python dependencies
├── README.md                  	# Documentation
├── log.md                     		# Operation log (created automatically)
├── raw.json                   		# Downloaded API data (created automatically)
└── md_export/                 		# Output directory 
    └── *.md                  		# Individual article files
```

### 2.5 Daily Automation 

Since new analysis and reports are finalized every Friday and made available via the API after Friday EOB (18:00 CET/CEST), we recommend scheduling the script to run once per week after this time.

**Windows Task Scheduler:**
- Open Task Scheduler (taskschd.msc)
- Create Basic Task
- Set trigger to Weekly, choose Friday at e.g. 19:00 CET/CEST
- Set action to start program: python
- Add arguments: download_and_convert.py
- Set "Start in" directory to your project folder

**Linux/Mac Cron:**
Add the following to your crontab to run every Friday at 19:00:
```bash
0 19 * * FRI cd /path/to/project && python download_and_convert.py
```

## 3. API Additional Information

### 3.1 API Parameters

**Endpoint:**
```
/v1/topics/export
```

**Query Parameters:**
- `limit` (integer, optional):
  Maximum number of topics to return. Default and maximum value: 5.

- `offset` (integer, optional):
  Number of topics to skip before starting to return results. Default: 0. 

### 3.2 API Setup & Security

- **Authentication**: Access is secured with an API key in the HTTP headers. Each client receives a unique key for tracking and access control.

- **IP Whitelisting**: Not enabled by default. This can be configured upon request to restrict API access to specific server IPs.

- **Encryption**: All traffic is served over HTTPS (TLS 1.2+), ensuring that data in transit is fully encrypted.

- **Data Access**: The API is strictly read-only. No write or modification operations are supported.

### 3.3 Rate Limits & Quotas

- **Rate limit**: 1 request per second, with a short burst allowance of 2 requests.

- **Quota**: 5 requests per week (temporarily adjusted to 20 per day for testing purposes).

- **Exceeding limits**: Requests over the quota or rate limit will return an error response.