# Individual Video Subtitle Extraction

## Overview

The Video Subtitle Scraper now supports extracting subtitles from individual YouTube videos without requiring channel ingestion or queue management. This feature provides direct API access for on-demand subtitle extraction with comprehensive rate limiting and error handling.

## Key Features

### 🚀 **Core Capabilities**
- **Direct video URL processing** - Extract subtitles from any YouTube video instantly
- **Multi-language support** - Prefer specific languages with intelligent fallback
- **Rate limiting protection** - Built-in safeguards against YouTube API limits
- **Batch processing** - Handle multiple videos efficiently with parallel execution
- **Download functionality** - Get subtitles as downloadable .txt files
- **Video metadata** - Extract title, duration, uploader, and available languages
- **Format flexibility** - Support for JSON3, WebVTT, SRT, and XML subtitle formats

### ⚡ **Performance & Protection**
- **Exponential backoff** - Smart retry logic for transient failures
- **Random jitter** - Prevents thundering herd problems
- **Error classification** - Distinguishes permanent vs temporary issues
- **Transaction safety** - Atomic database operations
- **Resource management** - Efficient memory and network usage

## API Endpoints

### 1. Extract Subtitles

Extract subtitles from a single video with full metadata.

**Endpoint:** `POST /api/subtitles/extract`

**Request Body:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "preferred_languages": ["en", "es", "fr"],
  "include_auto_generated": false
}
```

**Response:**
```json
{
  "success": true,
  "video_info": {
    "title": "Video Title",
    "video_id": "VIDEO_ID",
    "duration": 259,
    "uploader": "Channel Name"
  },
  "subtitle_info": {
    "language": "en",
    "content": "Full subtitle text...",
    "content_length": 4063,
    "format": "json3",
    "is_auto_generated": false
  }
}
```

### 2. Download Subtitles

Get subtitles as a downloadable .txt file.

**Endpoint:** `POST /api/subtitles/extract/download`

**Request Body:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "preferred_languages": ["en"]
}
```

**Response:** Plain text file with subtitle content

### 3. Video Information

Get video metadata and available subtitle languages.

**Endpoint:** `POST /api/subtitles/info`

**Request Body:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "success": true,
  "video_info": {
    "title": "Video Title",
    "video_id": "VIDEO_ID",
    "duration": 259,
    "uploader": "Channel Name"
  },
  "subtitle_availability": {
    "native_languages": ["en", "es", "fr", "de"],
    "auto_generated_languages": ["ar", "zh", "ja", "ko"],
    "total_native": 4,
    "total_auto_generated": 160
  }
}
```

### 4. Batch Processing

Process multiple videos in a single request.

**Endpoint:** `POST /api/subtitles/batch-extract`

**Request Body:**
```json
{
  "video_urls": [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.youtube.com/watch?v=VIDEO2",
    "https://www.youtube.com/watch?v=VIDEO3"
  ],
  "preferred_languages": ["en"],
  "include_auto_generated": false
}
```

**Response:**
```json
{
  "total_requested": 3,
  "successful_extractions": 2,
  "failed_extractions": 1,
  "results": [
    {
      "video_url": "https://www.youtube.com/watch?v=VIDEO1",
      "index": 0,
      "success": true,
      "video_title": "First Video Title",
      "video_id": "VIDEO1",
      "language": "en",
      "content_length": 4063,
      "error": null
    },
    {
      "video_url": "https://www.youtube.com/watch?v=VIDEO2",
      "index": 1,
      "success": true,
      "video_title": "Second Video Title",
      "video_id": "VIDEO2",
      "language": "en",
      "content_length": 12360,
      "error": null
    },
    {
      "video_url": "https://www.youtube.com/watch?v=VIDEO3",
      "index": 2,
      "success": false,
      "video_title": "Third Video Title",
      "video_id": "VIDEO3",
      "language": null,
      "content_length": 0,
      "error": "No native subtitles available in preferred languages"
    }
  ]
}
```

## Usage Examples

### Command Line Examples

**1. Extract Subtitles**
```bash
curl -X POST http://localhost:8003/api/subtitles/extract \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
    "preferred_languages": ["en"]
  }'
```

**2. Download as File**
```bash
curl -X POST http://localhost:8003/api/subtitles/extract/download \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
    "preferred_languages": ["en"]
  }' \
  --output subtitles.txt
```

**3. Get Video Info**
```bash
curl -X POST http://localhost:8003/api/subtitles/info \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo"
  }'
```

**4. Batch Process**
```bash
curl -X POST http://localhost:8003/api/subtitles/batch-extract \
  -H 'Content-Type: application/json' \
  -d '{
    "video_urls": [
      "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
      "https://www.youtube.com/watch?v=8jPQjjsBbIc"
    ],
    "preferred_languages": ["en"]
  }'
```

### Python Examples

**1. Simple Extraction**
```python
import requests

response = requests.post(
    "http://localhost:8003/api/subtitles/extract",
    json={
        "video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
        "preferred_languages": ["en"]
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Title: {data['video_info']['title']}")
    print(f"Language: {data['subtitle_info']['language']}")
    print(f"Length: {data['subtitle_info']['content_length']} characters")
```

**2. Download to File**
```python
import requests

response = requests.post(
    "http://localhost:8003/api/subtitles/extract/download",
    json={
        "video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
        "preferred_languages": ["en"]
    }
)

if response.status_code == 200:
    with open("subtitles.txt", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Subtitles saved to subtitles.txt")
```

**3. Batch Processing**
```python
import requests

video_urls = [
    "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",
    "https://www.youtube.com/watch?v=8jPQjjsBbIc"
]

response = requests.post(
    "http://localhost:8003/api/subtitles/batch-extract",
    json={
        "video_urls": video_urls,
        "preferred_languages": ["en"]
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Processed {data['total_requested']} videos")
    print(f"Successful: {data['successful_extractions']}")
    print(f"Failed: {data['failed_extractions']}")
    
    for result in data['results']:
        if result['success']:
            print(f"✅ {result['video_title']}: {result['content_length']} chars")
        else:
            print(f"❌ {result['video_title']}: {result['error']}")
```

## Rate Limiting

### Protection Strategy

The system implements comprehensive rate limiting to prevent YouTube API blocks:

**Base Delays:**
- 1-3 seconds between requests
- Random jitter: 0.5-1.5x multiplier
- Prevents predictable patterns

**Failure Handling:**
- Exponential backoff: 2^attempt
- Maximum 3 retry attempts
- Smart transient error detection

**Batch Processing:**
- 2-4 second delays between videos
- Parallel execution with throttling
- Graceful degradation on limits

### Configuration

Rate limiting parameters can be adjusted in the code:

```python
# Base delay range (seconds)
BASE_DELAY_MIN = 1.0
BASE_DELAY_MAX = 3.0

# Jitter multiplier range
JITTER_MIN = 0.5
JITTER_MAX = 1.5

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2

# Batch processing delays
BATCH_DELAY_MIN = 2.0
BATCH_DELAY_MAX = 4.0
```

## Error Handling

### Error Types

**Permanent Errors** (no retry):
- Video not found (404)
- Private/unavailable video
- No subtitles available
- Invalid video URL format

**Transient Errors** (retry with backoff):
- Network timeouts
- HTTP 503 Service Unavailable
- Connection failures
- Rate limit responses (429)

### Error Response Format

```json
{
  "success": false,
  "error": "Descriptive error message",
  "error_type": "permanent|transient",
  "video_info": {
    "video_id": "VIDEO_ID",
    "title": "Video Title (if available)"
  },
  "retry_info": {
    "attempt": 2,
    "max_retries": 3,
    "next_retry_delay": 4.5
  }
}
```

## Technical Implementation

### Core Functions

**1. `extract_single_video_subtitles()`**
- Main extraction function with full error handling
- Rate limiting and retry logic
- Multi-language preference support
- Comprehensive response formatting

**2. `get_video_info_only()`**
- Metadata extraction without subtitle download
- Available language detection
- Lightweight operation for information gathering

**3. `_process_subtitle_content()`**
- Multi-format subtitle processing
- JSON3, WebVTT, SRT, XML support
- Clean text extraction with timestamp removal
- Error-tolerant parsing

### Database Integration

While individual video extraction doesn't require database storage, it can optionally save results:

```python
# Optional database saving
if save_to_db:
    from utils.subtitle_processor import SubtitleProcessor
    processor = SubtitleProcessor()
    processor.save_subtitle_to_db(
        video_url=video_url,
        language=language,
        content=content,
        video_title=title
    )
```

### Performance Characteristics

**Response Times:**
- Video info: < 2 seconds
- Single extraction: 3-8 seconds
- Batch processing: 5-15 seconds per video

**Memory Usage:**
- Minimal memory footprint
- Streaming subtitle processing
- No temporary file storage

**Throughput:**
- Single videos: 8-20 per minute (with rate limiting)
- Batch processing: 4-12 per minute (depends on size)
- Parallel workers: Configurable (default: 3)

## Troubleshooting

### Common Issues

**1. Rate Limiting**
```
Error: HTTP 429 Too Many Requests
Solution: Wait 5-10 minutes, increase delays, reduce batch size
```

**2. No Subtitles Available**
```
Error: No native subtitles available in preferred languages
Solution: Check include_auto_generated=true or try different languages
```

**3. Video Unavailable**
```
Error: Video is private or unavailable
Solution: Verify URL, check if video is public
```

**4. Network Timeouts**
```
Error: Connection timeout
Solution: Check internet connection, retry after delay
```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed yt-dlp operations and rate limiting decisions
```

### Health Check

Test system health with a known working video:

```bash
curl -X POST http://localhost:8003/api/subtitles/info \
  -H 'Content-Type: application/json' \
  -d '{"video_url": "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo"}'
```

## Integration Examples

### Webhook Integration

```python
@app.route('/webhook/subtitle-extract', methods=['POST'])
def handle_subtitle_webhook():
    data = request.json
    video_url = data.get('video_url')
    
    # Extract subtitles
    result = requests.post(
        "http://localhost:8003/api/subtitles/extract",
        json={"video_url": video_url, "preferred_languages": ["en"]}
    )
    
    if result.status_code == 200:
        # Process subtitles
        subtitle_data = result.json()
        # Send to downstream systems
        return {"status": "success"}
    else:
        return {"status": "error", "message": result.text}, 400
```

### Background Job Processing

```python
from celery import Celery

@celery.task
def extract_video_subtitles(video_url, callback_url=None):
    result = requests.post(
        "http://localhost:8003/api/subtitles/extract",
        json={"video_url": video_url, "preferred_languages": ["en"]}
    )
    
    if callback_url and result.status_code == 200:
        # Notify completion
        requests.post(callback_url, json=result.json())
    
    return result.json()
```

### API Gateway Integration

```yaml
# api-gateway.yml
paths:
  /extract-subtitles:
    post:
      summary: Extract YouTube video subtitles
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                video_url:
                  type: string
                  format: uri
                preferred_languages:
                  type: array
                  items:
                    type: string
      responses:
        200:
          description: Subtitles extracted successfully
        400:
          description: Invalid request
        429:
          description: Rate limit exceeded
```

## Conclusion

The individual video extraction feature provides a powerful, flexible way to extract YouTube subtitles with enterprise-grade reliability and performance. It complements the existing channel-based processing workflow and opens up new integration possibilities for real-time subtitle extraction needs.

Key benefits:
- **Immediate results** - No queue management required
- **Rate limit protection** - Built-in safeguards against API limits  
- **Flexible integration** - REST API suitable for any platform
- **Comprehensive error handling** - Clear feedback for troubleshooting
- **Production ready** - Tested with real YouTube content
- **Batch support** - Efficient processing of multiple videos
- **Download functionality** - Direct file access for easy consumption

The system is ready for production use and can handle both individual extractions and high-volume batch processing scenarios.
