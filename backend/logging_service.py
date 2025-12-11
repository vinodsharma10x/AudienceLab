"""
Comprehensive Logging Service for Sucana v4
Handles both console and database logging with configurable levels and batching
"""

import os
import sys
import json
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from contextlib import contextmanager
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LogLevel(Enum):
    """Log levels matching Python's logging module"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class LoggingService:
    """Centralized logging service for application-wide logging"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure single instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logging service"""
        if not self._initialized:
            # Configuration from environment
            self.db_logging_enabled = os.getenv('ENABLE_DB_LOGGING', 'true').lower() == 'true'
            self.log_level = getattr(LogLevel, os.getenv('LOG_LEVEL', 'INFO').upper())
            self.batch_size = int(os.getenv('LOG_BATCH_SIZE', '10'))
            self.flush_interval = int(os.getenv('LOG_FLUSH_INTERVAL', '5'))
            
            print(f"🔧 Logging Service Config: db_enabled={self.db_logging_enabled}, level={self.log_level.name}, batch={self.batch_size}, flush={self.flush_interval}s")
            
            # Initialize Supabase client if DB logging is enabled
            self.supabase_client = None
            if self.db_logging_enabled:
                try:
                    supabase_url = os.getenv('SUPABASE_URL')
                    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')
                    if supabase_url and supabase_key:
                        self.supabase_client = create_client(supabase_url, supabase_key)
                        print(f"✅ Database logging initialized")
                    else:
                        print(f"⚠️ Database logging disabled: Missing Supabase credentials")
                        self.db_logging_enabled = False
                except Exception as e:
                    print(f"⚠️ Database logging disabled: {e}")
                    self.db_logging_enabled = False
            
            # Initialize Python logger
            self.logger = logging.getLogger('sucana_v4')
            self.logger.setLevel(self.log_level.value)
            
            # Console handler with formatting
            if not self.logger.handlers:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(self.log_level.value)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            
            # Log buffer for batching
            self.log_buffer: List[Dict] = []
            self.buffer_lock = asyncio.Lock() if asyncio.get_event_loop_policy() else None
            
            # Context storage for request-scoped data
            self.context = {}
            
            # Start background task for flushing logs
            if self.db_logging_enabled:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._periodic_flush())
                except RuntimeError:
                    # No event loop running, will flush synchronously
                    pass
            
            self._initialized = True
    
    def set_context(self, **kwargs):
        """Set context that will be included in all subsequent logs"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear the logging context"""
        self.context = {}
    
    @contextmanager
    def with_context(self, **kwargs):
        """Context manager for temporary context"""
        old_context = self.context.copy()
        self.context.update(kwargs)
        try:
            yield
        finally:
            self.context = old_context
    
    async def _periodic_flush(self):
        """Background task to periodically flush log buffer"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
    
    async def flush(self):
        """Flush log buffer to database"""
        if not self.db_logging_enabled or not self.supabase_client:
            return
        
        if self.buffer_lock:
            async with self.buffer_lock:
                if self.log_buffer:
                    logs_to_flush = self.log_buffer.copy()
                    self.log_buffer.clear()
                else:
                    return
        else:
            if self.log_buffer:
                logs_to_flush = self.log_buffer.copy()
                self.log_buffer.clear()
            else:
                return
        
        try:
            # Insert logs in batch
            print(f"📝 Flushing {len(logs_to_flush)} logs to database...")
            result = self.supabase_client.table('simple_logs').insert(logs_to_flush).execute()
            if not result.data:
                print(f"⚠️ Failed to flush {len(logs_to_flush)} logs to database")
            else:
                print(f"✅ Successfully flushed {len(logs_to_flush)} logs to database")
        except Exception as e:
            print(f"❌ Error flushing logs to database: {e}")
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if the given level should be logged"""
        return level.value >= self.log_level.value
    
    async def _add_to_buffer(self, log_entry: Dict):
        """Add log entry to buffer and flush if needed"""
        if not self.db_logging_enabled or not self.supabase_client:
            return
        
        if self.buffer_lock:
            async with self.buffer_lock:
                self.log_buffer.append(log_entry)
                if len(self.log_buffer) >= self.batch_size:
                    await self.flush()
        else:
            self.log_buffer.append(log_entry)
            if len(self.log_buffer) >= self.batch_size:
                # Synchronous flush
                try:
                    result = self.supabase_client.table('simple_logs').insert(self.log_buffer).execute()
                    self.log_buffer.clear()
                except Exception as e:
                    print(f"❌ Error flushing logs: {e}")
    
    def log(self, 
            event_name: str,
            event_value: str = None,
            level: LogLevel = LogLevel.INFO,
            user_id: str = None,
            session_id: str = None,
            thread_id: str = None,
            metadata: Dict = None,
            **kwargs):
        """
        Main logging method
        
        Args:
            event_name: Standardized event name (e.g., 'workflow.started')
            event_value: Detailed message or description
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            user_id: User ID associated with the event
            session_id: Session ID for tracking
            thread_id: Thread/Conversation ID
            metadata: Additional context as dictionary
            **kwargs: Additional key-value pairs to add to metadata
        """
        if not self._should_log(level):
            return
        
        # Merge context with provided values
        user_id = user_id or self.context.get('user_id')
        session_id = session_id or self.context.get('session_id')
        thread_id = thread_id or self.context.get('thread_id') or self.context.get('conversation_id')
        
        # Build metadata
        full_metadata = {}
        if metadata:
            full_metadata.update(metadata)
        if kwargs:
            full_metadata.update(kwargs)
        
        # Add context metadata
        if self.context.get('metadata'):
            full_metadata.update(self.context['metadata'])
        
        # Add level to metadata
        full_metadata['level'] = level.name
        
        # Console logging
        log_message = f"[{event_name}] {event_value or ''}"
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
        
        # Database logging
        if self.db_logging_enabled:
            # Validate UUIDs - only include if they look like valid UUIDs
            import re
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
            
            log_entry = {
                'event_name': event_name,
                'event_value': event_value,
                'metadata': full_metadata if full_metadata else None
            }
            
            # Only add UUID fields if they're valid UUIDs
            if user_id and uuid_pattern.match(str(user_id)):
                log_entry['user_id'] = user_id
            if session_id and uuid_pattern.match(str(session_id)):
                log_entry['session_id'] = session_id
            if thread_id and uuid_pattern.match(str(thread_id)):
                log_entry['thread_id'] = thread_id
            
            # Immediate write for batch_size = 1
            if self.batch_size == 1 and self.supabase_client:
                try:
                    result = self.supabase_client.table('simple_logs').insert([log_entry]).execute()
                    if not result.data:
                        print(f"⚠️ Failed to insert log: {event_name}")
                except Exception as e:
                    print(f"❌ Error logging to database: {e}")
            else:
                # Try async first, fall back to sync
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._add_to_buffer(log_entry))
                    else:
                        # Synchronous fallback
                        self.log_buffer.append(log_entry)
                        if len(self.log_buffer) >= self.batch_size:
                            if self.supabase_client:
                                try:
                                    self.supabase_client.table('simple_logs').insert(self.log_buffer).execute()
                                    self.log_buffer.clear()
                                except Exception as e:
                                    print(f"❌ Error logging to database: {e}")
                except RuntimeError:
                    # No event loop, use synchronous approach
                    self.log_buffer.append(log_entry)
                    if len(self.log_buffer) >= self.batch_size:
                        if self.supabase_client:
                            try:
                                self.supabase_client.table('simple_logs').insert(self.log_buffer).execute()
                                self.log_buffer.clear()
                            except Exception as e:
                                print(f"❌ Error logging to database: {e}")
    
    # Convenience methods for different log levels
    def debug(self, event_name: str, event_value: str = None, **kwargs):
        """Log debug message"""
        self.log(event_name, event_value, LogLevel.DEBUG, **kwargs)
    
    def info(self, event_name: str, event_value: str = None, **kwargs):
        """Log info message"""
        self.log(event_name, event_value, LogLevel.INFO, **kwargs)
    
    def warning(self, event_name: str, event_value: str = None, **kwargs):
        """Log warning message"""
        self.log(event_name, event_value, LogLevel.WARNING, **kwargs)
    
    def error(self, event_name: str, event_value: str = None, exception: Exception = None, **kwargs):
        """Log error message with optional exception"""
        if exception:
            kwargs['error_type'] = type(exception).__name__
            kwargs['error_message'] = str(exception)
            kwargs['stack_trace'] = traceback.format_exc()
        self.log(event_name, event_value, LogLevel.ERROR, **kwargs)
    
    def critical(self, event_name: str, event_value: str = None, **kwargs):
        """Log critical message"""
        self.log(event_name, event_value, LogLevel.CRITICAL, **kwargs)
    
    @contextmanager
    def timer(self, event_name: str, **kwargs):
        """Context manager to time operations"""
        start_time = time.time()
        self.info(f"{event_name}.started", **kwargs)
        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)
            self.info(f"{event_name}.completed", duration_ms=duration_ms, **kwargs)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.error(f"{event_name}.failed", exception=e, duration_ms=duration_ms, **kwargs)
            raise
    
    async def query_logs(self, 
                        event_name: str = None,
                        user_id: str = None,
                        thread_id: str = None,
                        start_date: datetime = None,
                        end_date: datetime = None,
                        limit: int = 100) -> List[Dict]:
        """Query logs from database"""
        if not self.supabase_client:
            return []
        
        query = self.supabase_client.table('simple_logs').select('*')
        
        if event_name:
            query = query.eq('event_name', event_name)
        if user_id:
            query = query.eq('user_id', user_id)
        if thread_id:
            query = query.eq('thread_id', thread_id)
        if start_date:
            query = query.gte('created_at', start_date.isoformat())
        if end_date:
            query = query.lte('created_at', end_date.isoformat())
        
        query = query.order('created_at', desc=True).limit(limit)
        
        try:
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            self.error('logging.query.failed', str(e))
            return []

# Global logger instance
logger = LoggingService()

# Export convenience functions
def set_context(**kwargs):
    """Set global logging context"""
    logger.set_context(**kwargs)

def clear_context():
    """Clear global logging context"""
    logger.clear_context()

def debug(event_name: str, event_value: str = None, **kwargs):
    """Log debug message"""
    logger.debug(event_name, event_value, **kwargs)

def info(event_name: str, event_value: str = None, **kwargs):
    """Log info message"""
    logger.info(event_name, event_value, **kwargs)

def warning(event_name: str, event_value: str = None, **kwargs):
    """Log warning message"""
    logger.warning(event_name, event_value, **kwargs)

def error(event_name: str, event_value: str = None, exception: Exception = None, **kwargs):
    """Log error message"""
    logger.error(event_name, event_value, exception, **kwargs)

def critical(event_name: str, event_value: str = None, **kwargs):
    """Log critical message"""
    logger.critical(event_name, event_value, **kwargs)