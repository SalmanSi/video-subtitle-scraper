import yt_dlp
import logging
import re
import json
import time
import random
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize_channel_url(url: str) -> str:
    """
    Normalize a YouTube channel URL to a standard format.
    
    Args:
        url: YouTube channel URL
        
    Returns:
        Normalized URL
    """
    if not url:
        return url
    
    # Replace mobile and short domains with standard www.youtube.com
    url = url.replace('m.youtube.com', 'www.youtube.com')
    url = url.replace('youtube.com', 'www.youtube.com')
    
    # Ensure https protocol
    if url.startswith('http://'):
        url = url.replace('http://', 'https://')
    elif not url.startswith('https://'):
        url = 'https://' + url
    
    # Fix double www if it got added
    url = url.replace('https://www.www.youtube.com', 'https://www.youtube.com')
    
    return url

def validate_youtube_url(url: str) -> bool:
    """
    Validate if URL is a YouTube channel/playlist URL.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid YouTube URL
    """
    youtube_patterns = [
        r'youtube\.com/(c/|channel/|user/|@)',
        r'youtube\.com/playlist',
        r'youtu\.be/'
    ]
    
    for pattern in youtube_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def extract_video_entries(channel_url: str) -> List[Dict[str, Any]]:
    """
    Extract video entries from a YouTube channel URL using yt-dlp.
    
    Args:
        channel_url (str): The URL of the YouTube channel
        
    Returns:
        List[Dict]: List of video entry dictionaries
        
    Raises:
        Exception: If extraction fails
    """
    ydl_opts = {
        'ignoreerrors': True,
        'skip_download': True,
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
        if not info:
            raise Exception("No information extracted from URL")
            
        # Handle both single video and playlist/channel results
        if 'entries' in info:
            entries = [e for e in info['entries'] if e]
            logging.info(f"Extracted {len(entries)} video entries from {channel_url}")
            return entries
        else:
            # Single video
            logging.info(f"Extracted single video from {channel_url}")
            return [info]
            
    except Exception as e:
        logging.error(f"Failed to extract videos from {channel_url}: {str(e)}")
        raise

def get_channel_info(channel_url: str) -> Dict[str, Any]:
    """
    Get channel information including name.
    
    Args:
        channel_url (str): Channel URL
        
    Returns:
        Dict: Channel information
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False  # We need metadata
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
        return {
            'title': info.get('title', info.get('uploader', 'Unknown Channel')),
            'uploader': info.get('uploader'),
            'uploader_id': info.get('uploader_id'),
            'description': info.get('description')
        }
        
    except Exception as e:
        logging.warning(f"Could not extract channel info from {channel_url}: {str(e)}")
        return {'title': 'Unknown Channel'}

def extract_video_urls(channel_url: str) -> List[str]:
    """
    Extract video URLs from a given YouTube channel URL using yt-dlp.
    Legacy function for backward compatibility.
    
    Args:
        channel_url (str): The URL of the YouTube channel.
        
    Returns:
        list: A list of video URLs extracted from the channel.
    """
    try:
        entries = extract_video_entries(channel_url)
        urls = []
        
        for entry in entries:
            url = entry.get('webpage_url') or entry.get('url')
            if url and 'youtube.com/watch' in url or 'youtu.be/' in url:
                urls.append(url)
            elif entry.get('id'):
                # Construct URL from video ID
                urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                
        logging.info(f"Extracted {len(urls)} video URLs from {channel_url}.")
        return urls
        
    except Exception as e:
        logging.error(f"Error extracting video URLs from {channel_url}: {str(e)}")
        raise

def log_error(video_id: Optional[int], level: str, message: str):
    """
    Log error to console and potentially database.
    
    Args:
        video_id: Video ID if applicable
        level: Log level (INFO, WARN, ERROR)
        message: Error message
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.log(log_level, f"Video {video_id}: {message}" if video_id else message)

def download_subtitles(video_url: str, lang: str = 'en') -> Optional[Dict[str, str]]:
    """
    Download subtitles for a given video URL.
    
    Args:
        video_url (str): Video URL
        lang (str): Language code (default: 'en')
        
    Returns:
        Dict with subtitle content and language, or None if no subtitles
    """
    ydl_opts = {
        'writesubtitles': True,
        'skip_download': True,
        'quiet': True,
        'subtitleslangs': [lang],
        'writeautomaticsub': False,  # Only native subtitles
        'ignoreerrors': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
        subs = info.get('subtitles', {})
        if lang in subs:
            subtitle_url = subs[lang][0]['url']
            raw_content = ydl.urlopen(subtitle_url).read().decode('utf-8', errors='ignore')
            # Basic HTML/XML tag removal
            content = re.sub(r'<[^>]+>', '', raw_content).strip()
            return {'language': lang, 'content': content}
        else:
            return None
            
    except Exception as e:
        logging.error(f"Failed to download subtitles for {video_url}: {str(e)}")
        return None

def _process_subtitle_content(raw_content: str, format_type: str) -> str:
    """
    Process subtitle content based on format type.
    
    Args:
        raw_content: Raw subtitle content from yt-dlp
        format_type: Format type (json3, vtt, srt, etc.)
        
    Returns:
        Processed plain text content
    """
    if not raw_content.strip():
        return ""
    
    try:
        if format_type == 'json3':
            # Parse JSON3 format (YouTube's native format)
            try:
                subtitle_data = json.loads(raw_content)
                logging.debug(f"JSON3 structure keys: {subtitle_data.keys()}")
                
                text_parts = []
                
                # Handle different JSON3 structures
                if 'events' in subtitle_data:
                    for event in subtitle_data['events']:
                        if 'segs' in event:
                            for seg in event['segs']:
                                if 'utf8' in seg:
                                    text = seg['utf8'].strip()
                                    if text and text not in ['\n', ' ', '']:
                                        text_parts.append(text)
                        elif 'dDurationMs' in event and 'tStartMs' in event:
                            # Handle events without segments but with text
                            if 'wsWinStyles' in event or 'wWinStyles' in event:
                                # Look for text in different possible locations
                                for key in ['aAppend', 'segs']:
                                    if key in event:
                                        if isinstance(event[key], list):
                                            for item in event[key]:
                                                if isinstance(item, dict) and 'utf8' in item:
                                                    text = item['utf8'].strip()
                                                    if text and text not in ['\n', ' ', '']:
                                                        text_parts.append(text)
                
                # Alternative structure: look for 'body' or 'transcript'
                elif 'body' in subtitle_data:
                    if isinstance(subtitle_data['body'], list):
                        for item in subtitle_data['body']:
                            if isinstance(item, dict) and 'utf8' in item:
                                text = item['utf8'].strip()
                                if text and text not in ['\n', ' ', '']:
                                    text_parts.append(text)
                
                # Another alternative: direct array of text items
                elif isinstance(subtitle_data, list):
                    for item in subtitle_data:
                        if isinstance(item, dict):
                            if 'utf8' in item:
                                text = item['utf8'].strip()
                                if text and text not in ['\n', ' ', '']:
                                    text_parts.append(text)
                            elif 'text' in item:
                                text = item['text'].strip()
                                if text and text not in ['\n', ' ', '']:
                                    text_parts.append(text)
                
                # Join and clean up
                if text_parts:
                    content = ' '.join(text_parts)
                    # Remove excessive whitespace and normalize
                    content = re.sub(r'\s+', ' ', content)
                    content = content.strip()
                    logging.debug(f"Extracted {len(content)} characters from JSON3")
                    return content
                else:
                    logging.warning("No text segments found in JSON3 structure")
                    logging.debug(f"JSON3 sample: {str(subtitle_data)[:500]}...")
                    return ""
                    
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON3: {e}")
                # Try to extract any text using regex as fallback
                text_matches = re.findall(r'"utf8"\s*:\s*"([^"]*)"', raw_content)
                if text_matches:
                    content = ' '.join(match.strip() for match in text_matches if match.strip())
                    content = re.sub(r'\s+', ' ', content).strip()
                    if content:
                        logging.info(f"Fallback regex extraction successful: {len(content)} characters")
                        return content
                return ""
        
        elif format_type in ['vtt', 'webvtt']:
            # Process WebVTT format
            lines = raw_content.split('\n')
            text_parts = []
            
            for line in lines:
                line = line.strip()
                # Skip WebVTT headers, timestamps, and empty lines
                if (line and 
                    not line.startswith('WEBVTT') and
                    not line.startswith('NOTE') and
                    not '-->' in line and
                    not line.isdigit()):
                    # Remove any remaining HTML-like tags
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    if clean_line.strip():
                        text_parts.append(clean_line.strip())
            
            return ' '.join(text_parts)
        
        elif format_type == 'srt':
            # Process SRT format
            lines = raw_content.split('\n')
            text_parts = []
            
            for line in lines:
                line = line.strip()
                # Skip SRT sequence numbers, timestamps, and empty lines
                if (line and 
                    not line.isdigit() and
                    not '-->' in line):
                    text_parts.append(line)
            
            return ' '.join(text_parts)
        
        else:
            # Fallback: treat as XML/HTML and remove tags
            content = re.sub(r'<[^>]+>', '', raw_content)
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
            
    except json.JSONDecodeError:
        # If JSON parsing fails, fall back to XML/HTML processing
        logging.warning(f"Failed to parse {format_type} format, falling back to generic processing")
        content = re.sub(r'<[^>]+>', '', raw_content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    except Exception as e:
        logging.error(f"Error processing subtitle content: {e}")
        return ""

def fetch_subtitle_text(video_url: str, preferred_langs: List[str] = ['en']) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch subtitle text for a video with language preference fallback.
    
    Args:
        video_url: YouTube video URL
        preferred_langs: List of preferred language codes in order of preference
        
    Returns:
        Tuple of (language, content) or (None, None) if no subtitles available
    """
    ydl_opts = {
        'writesubtitles': True,
        'skip_download': True,
        'quiet': True,
        'subtitleslangs': preferred_langs,
        'writeautomaticsub': False,  # Ensure only provided, not auto-generated
        'ignoreerrors': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
        subs = info.get('subtitles') or {}
        if not subs:
            logging.info(f"No native subtitles available for {video_url}")
            return None, None
        
        # Choose language based on preference
        chosen_lang = None
        for lang in preferred_langs:
            if lang in subs:
                chosen_lang = lang
                break
                
        # Fallback to first available language if preferred not found
        if not chosen_lang and subs:
            chosen_lang = next(iter(subs.keys()))
            logging.info(f"Preferred languages {preferred_langs} not found, using {chosen_lang}")
        
        if not chosen_lang:
            return None, None
            
        # Download subtitle content
        subtitle_info = subs[chosen_lang][0]
        subtitle_url = subtitle_info['url']
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            raw_content = ydl.urlopen(subtitle_url).read().decode('utf-8', errors='ignore')
        
        # Process subtitle content based on format
        content = _process_subtitle_content(raw_content, subtitle_info.get('ext', 'unknown'))
        
        if not content:
            logging.warning(f"Subtitle content is empty after processing for {video_url}")
            return None, None
            
        logging.info(f"Successfully extracted {chosen_lang} subtitles for {video_url} ({len(content)} characters)")
        return chosen_lang, content
        
    except Exception as e:
        logging.error(f"Failed to fetch subtitle text for {video_url}: {str(e)}")
        return None, None

def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient (should retry) or permanent (should fail).
    
    Args:
        error: Exception that occurred
        
    Returns:
        True if error is likely transient, False if permanent
    """
    error_str = str(error).lower()
    
    # Network-related errors that should be retried
    transient_indicators = [
        'timeout',
        'connection',
        'network',
        'temporary',
        'server error',
        'http 5',  # 5xx server errors
        'rate limit',
        'too many requests'
    ]
    
    # Permanent errors that should not be retried
    permanent_indicators = [
        'not found',
        'http 404',
        'forbidden',
        'http 403',
        'private video',
        'video unavailable',
        'removed',
        'deleted'
    ]
    
    # Check for permanent errors first
    for indicator in permanent_indicators:
        if indicator in error_str:
            return False
            
    # Check for transient errors
    for indicator in transient_indicators:
        if indicator in error_str:
            return True
            
    # Default to transient for unknown errors (safer to retry)
    return True

def extract_single_video_subtitles(video_url: str, 
                                 preferred_langs: List[str] = ['en'],
                                 include_auto_generated: bool = False,
                                 max_retries: int = 3,
                                 base_delay: float = 1.0) -> Dict[str, Any]:
    """
    Extract subtitles from a single video URL with comprehensive error handling and rate limiting.
    
    Args:
        video_url: YouTube video URL
        preferred_langs: List of preferred language codes in order of preference
        include_auto_generated: Whether to include auto-generated captions
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        
    Returns:
        Dictionary containing:
        {
            'success': bool,
            'video_title': str,
            'video_id': str,
            'duration': int,
            'language': str,
            'content': str,
            'content_length': int,
            'subtitle_format': str,
            'available_languages': List[str],
            'auto_generated_available': List[str],
            'error': str,
            'is_transient_error': bool
        }
    """
    result = {
        'success': False,
        'video_title': None,
        'video_id': None,
        'duration': None,
        'language': None,
        'content': None,
        'content_length': 0,
        'subtitle_format': None,
        'available_languages': [],
        'auto_generated_available': [],
        'error': None,
        'is_transient_error': False
    }
    
    # Validate URL
    if not validate_youtube_video_url(video_url):
        result['error'] = 'Invalid YouTube video URL'
        return result
    
    # Extract video ID
    video_id = extract_video_id(video_url)
    result['video_id'] = video_id
    
    for attempt in range(max_retries + 1):
        try:
            # Add rate limiting delay
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logging.info(f"Retry attempt {attempt}, waiting {delay:.2f} seconds...")
                time.sleep(delay)
            
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': include_auto_generated,
                'skip_download': True,
                'quiet': True,
                'subtitleslangs': preferred_langs,
                'ignoreerrors': True,
                # Rate limiting options
                'sleep_interval': 1,
                'max_sleep_interval': 5,
                'sleep_interval_subtitles': 1,
                # Anti-bot measures for 2025.08.12
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['webpage'],
                        'comment_sort': ['top'],
                        'max_comments': ['100,100,100,100']
                    }
                },
                # Additional headers and user agent rotation
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip,deflate',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Keep-Alive': '300',
                    'Connection': 'keep-alive',
                }
            }
            
            logging.info(f"Extracting subtitle info for {video_url} (attempt {attempt + 1})")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
            
            if not info:
                result['error'] = 'Failed to extract video information'
                continue
            
            # Extract basic video info
            result['video_title'] = info.get('title', 'Unknown')
            result['duration'] = info.get('duration', 0)
            
            # Get available subtitles
            subs = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            
            result['available_languages'] = list(subs.keys())
            result['auto_generated_available'] = list(auto_subs.keys())
            
            logging.info(f"Found native subtitles: {result['available_languages']}")
            if include_auto_generated:
                logging.info(f"Found auto-generated subtitles: {result['auto_generated_available']}")
            
            # Choose subtitle language
            chosen_lang = None
            chosen_subs = None
            is_auto_generated = False
            
            # First, try native subtitles
            for lang in preferred_langs:
                if lang in subs:
                    chosen_lang = lang
                    chosen_subs = subs[lang]
                    break
            
            # Fallback to first available native subtitle
            if not chosen_lang and subs:
                chosen_lang = next(iter(subs.keys()))
                chosen_subs = subs[chosen_lang]
                logging.info(f"Using fallback language: {chosen_lang}")
            
            # If no native subtitles and auto-generated is allowed
            if not chosen_lang and include_auto_generated:
                for lang in preferred_langs:
                    if lang in auto_subs:
                        chosen_lang = lang
                        chosen_subs = auto_subs[lang]
                        is_auto_generated = True
                        break
                
                # Fallback to first available auto-generated
                if not chosen_lang and auto_subs:
                    chosen_lang = next(iter(auto_subs.keys()))
                    chosen_subs = auto_subs[chosen_lang]
                    is_auto_generated = True
                    logging.info(f"Using auto-generated fallback: {chosen_lang}")
            
            if not chosen_lang:
                result['error'] = f"No subtitles available. Native: {list(subs.keys())}, Auto: {list(auto_subs.keys())}"
                return result
            
            # Download subtitle content
            subtitle_info = chosen_subs[0]
            subtitle_url = subtitle_info['url']
            subtitle_format = subtitle_info.get('ext', 'unknown')
            
            logging.info(f"Downloading {chosen_lang} subtitles in {subtitle_format} format...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                raw_content = ydl.urlopen(subtitle_url).read().decode('utf-8', errors='ignore')
            
            # Process subtitle content
            content = _process_subtitle_content(raw_content, subtitle_format)
            
            if not content:
                result['error'] = f"Subtitle content is empty after processing ({subtitle_format} format)"
                continue
            
            # Success!
            result.update({
                'success': True,
                'language': chosen_lang,
                'content': content,
                'content_length': len(content),
                'subtitle_format': subtitle_format,
                'is_auto_generated': is_auto_generated
            })
            
            logging.info(f"Successfully extracted {chosen_lang} subtitles ({len(content)} characters)")
            return result
            
        except Exception as e:
            error_msg = str(e)
            result['error'] = error_msg
            result['is_transient_error'] = is_transient_error(e)
            
            logging.error(f"Error extracting subtitles (attempt {attempt + 1}): {error_msg}")
            
            # If it's a permanent error, don't retry
            if not result['is_transient_error']:
                logging.info("Permanent error detected, not retrying")
                break
            
            # If this was the last attempt
            if attempt == max_retries:
                logging.error("All retry attempts exhausted")
                break
    
    return result

def validate_youtube_video_url(url: str) -> bool:
    """
    Validate if URL is a YouTube video URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid YouTube video URL
    """
    video_patterns = [
        r'youtube\.com/watch\?v=',
        r'youtu\.be/',
        r'youtube\.com/embed/',
        r'youtube\.com/v/'
    ]
    
    for pattern in video_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID or None if not found
    """
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be/([0-9A-Za-z_-]{11})',
        r'embed/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_info_only(video_url: str) -> Dict[str, Any]:
    """
    Get basic video information without downloading subtitles.
    
    Args:
        video_url: YouTube video URL
        
    Returns:
        Dictionary with video information
    """
    result = {
        'success': False,
        'video_id': None,
        'title': None,
        'duration': None,
        'upload_date': None,
        'uploader': None,
        'view_count': None,
        'like_count': None,
        'description': None,
        'tags': [],
        'available_subtitle_languages': [],
        'auto_caption_languages': [],
        'error': None
    }
    
    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'ignoreerrors': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        
        if not info:
            result['error'] = 'Failed to extract video information'
            return result
        
        result.update({
            'success': True,
            'video_id': info.get('id'),
            'title': info.get('title'),
            'duration': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'uploader': info.get('uploader'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'description': info.get('description'),
            'tags': info.get('tags', []),
            'available_subtitle_languages': list(info.get('subtitles', {}).keys()),
            'auto_caption_languages': list(info.get('automatic_captions', {}).keys())
        })
        
    except Exception as e:
        result['error'] = str(e)
    
    return result