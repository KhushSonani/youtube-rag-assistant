from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import time
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache/transcripts")

def get_transcript(video_id=None):
    if not video_id:
        return {
            "status": "failed",
            "video_id": None,
            "reason": "video_id must be provided",
            "fallback": "Please provide a valid video_id"
        }
        
    cache_file = CACHE_DIR / f"{video_id}.txt"
    
    # -----------------------------------------------------------------------
    # STEP 1: LOCAL CACHE CHECK
    # -----------------------------------------------------------------------
    if cache_file.exists():
        logger.info(f"[{video_id}] CACHE HIT for video_id")
        return cache_file.read_text(encoding="utf-8")
        
    logger.info(f"[{video_id}] CACHE MISS")
    
    # -----------------------------------------------------------------------
    # STEP 2: FETCH FROM YOUTUBE API WITH RETRIES
    # -----------------------------------------------------------------------
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript_obj = None
            source_lang = None
            
            try:
                transcript_obj = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                source_lang = "English"
            except NoTranscriptFound:
                try:
                    transcript_hi = transcript_list.find_transcript(['hi'])
                    if transcript_hi.is_translatable:
                        logger.info(f"[{video_id}] Found Hindi transcript. Translating to English...")
                        transcript_obj = transcript_hi.translate('en')
                        source_lang = "Hindi (Translated to English)"
                    else:
                        logger.info(f"[{video_id}] Found Hindi transcript but it is not translatable. Using as is.")
                        transcript_obj = transcript_hi
                        source_lang = "Hindi"
                except Exception:
                    logger.info(f"[{video_id}] En/Hi translation failed or missing. Grabbing first available transcript.")
                    for t in transcript_list:
                        if t.is_translatable:
                            try:
                                transcript_obj = t.translate('en')
                                source_lang = f"{t.language} (Translated to English)"
                                break
                            except Exception:
                                continue
                    
                    if transcript_obj is None:
                        for t in transcript_list:
                            transcript_obj = t
                            source_lang = t.language
                            break
            
            if transcript_obj is None:
                raise Exception("No transcripts available for this video.")
                
            fetched = transcript_obj.fetch()
            
            logger.info(f"[{video_id}] Transcript source language: {source_lang}")
            logger.info(f"[{video_id}] Number of snippets: {len(fetched)}")
            
            text_with_markers = " ".join(
                f"[[{chunk.start}]]{chunk.text}" for chunk in fetched
            )
            
            logger.info(f"[{video_id}] Final text length: {len(text_with_markers)}")
            logger.info(f"[{video_id}] Transcript fetched successfully")
            
            # -----------------------------------------------------------------------
            # STEP 3: SAVE TO CACHE
            # -----------------------------------------------------------------------
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(text_with_markers, encoding="utf-8")
            
            return text_with_markers

        except Exception as e:
            logger.error(f"[{video_id}] Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                sleep_time = 2 ** (attempt - 1)  # 1s, 2s, 4s...
                time.sleep(sleep_time)
            else:
                # -----------------------------------------------------------------------
                # STEP 4: GRACEFUL FAILURE
                # -----------------------------------------------------------------------
                return {
                    "status": "failed",
                    "video_id": video_id,
                    "reason": "Transcript unavailable due to YouTube blocking or missing captions",
                    "fallback": "Try another video or retry later"
                }