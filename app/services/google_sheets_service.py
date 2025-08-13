"""
Google Sheets Integration Service for Query and Response Logging.

Implements:
- Real-time logging of all queries and responses to Google Sheets
- Structured data organization with timestamps and metadata
- Batch processing for performance optimization
- Error handling and retry mechanisms
- Analytics and insights tracking
- User interaction patterns logging
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..core.config import settings
from ..core.logging import get_logger
from ..models.schemas import QueryRequest, QueryResponse, QueryType
from ..utils.auth import get_service_account_credentials

logger = get_logger(__name__)


@dataclass
class QueryLogEntry:
    """Structure for query log entries."""
    timestamp: str
    session_id: Optional[str]
    user_id: Optional[str]
    query: str
    response: str
    query_type: str
    confidence_score: float
    processing_time: float
    sources_count: int
    metadata: Dict[str, Any]
    
    def to_row(self) -> List[Any]:
        """Convert to spreadsheet row format."""
        return [
            self.timestamp,
            self.session_id or "",
            self.user_id or "",
            self.query,
            self.response,
            self.query_type,
            self.confidence_score,
            self.processing_time,
            self.sources_count,
            json.dumps(self.metadata, default=str)
        ]


@dataclass
class InteractionLogEntry:
    """Structure for user interaction log entries."""
    timestamp: str
    session_id: Optional[str]
    user_id: Optional[str]
    interaction_type: str  # query, feedback, session_start, session_end
    details: Dict[str, Any]
    
    def to_row(self) -> List[Any]:
        """Convert to spreadsheet row format."""
        return [
            self.timestamp,
            self.session_id or "",
            self.user_id or "",
            self.interaction_type,
            json.dumps(self.details, default=str)
        ]


@dataclass
class AnalyticsEntry:
    """Structure for analytics entries."""
    timestamp: str
    metric_name: str
    metric_value: Union[int, float, str]
    category: str
    metadata: Dict[str, Any]
    
    def to_row(self) -> List[Any]:
        """Convert to spreadsheet row format."""
        return [
            self.timestamp,
            self.metric_name,
            self.metric_value,
            self.category,
            json.dumps(self.metadata, default=str)
        ]


class GoogleSheetsService:
    """Handles Google Sheets API operations."""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.spreadsheet_id = settings.google_sheets_spreadsheet_id
    
    async def initialize(self) -> None:
        """Initialize Google Sheets service."""
        try:
            # Load credentials
            self.credentials = await self._load_credentials()
            
            # Build Sheets service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            # Ensure spreadsheet and worksheets exist
            await self._setup_spreadsheet()
            
            logger.info("Google Sheets service initialized", 
                       spreadsheet_id=self.spreadsheet_id)
        except Exception as e:
            logger.error("Failed to initialize Google Sheets service", error=str(e))
            raise
    
    async def _load_credentials(self):
        """Load Google Sheets credentials using service account."""
        try:
            # Get service account credentials with Sheets scope
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            credentials = get_service_account_credentials(scopes)
            
            logger.info("Successfully loaded Google Sheets service account credentials")
            return credentials
            
        except Exception as e:
            logger.error("Failed to load Google Sheets credentials", error=str(e))
            raise
    
    async def _setup_spreadsheet(self) -> None:
        """Setup spreadsheet with required worksheets and headers."""
        try:
            # Get spreadsheet info
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            # Check existing sheets
            existing_sheets = {sheet['properties']['title'] 
                             for sheet in spreadsheet['sheets']}
            
            # Define required sheets and their headers
            required_sheets = {
                'Query_Logs': [
                    'Timestamp', 'Session_ID', 'User_ID', 'Query', 'Response',
                    'Query_Type', 'Confidence_Score', 'Processing_Time', 
                    'Sources_Count', 'Metadata'
                ],
                'Interaction_Logs': [
                    'Timestamp', 'Session_ID', 'User_ID', 'Interaction_Type', 'Details'
                ],
                'Analytics': [
                    'Timestamp', 'Metric_Name', 'Metric_Value', 'Category', 'Metadata'
                ],
                'Performance_Metrics': [
                    'Timestamp', 'Endpoint', 'Response_Time', 'Status_Code', 
                    'User_Count', 'Error_Rate', 'Metadata'
                ]
            }
            
            # Create missing sheets
            for sheet_name, headers in required_sheets.items():
                if sheet_name not in existing_sheets:
                    await self._create_worksheet(sheet_name, headers)
                else:
                    # Ensure headers are correct
                    await self._update_headers(sheet_name, headers)
            
            logger.info("Spreadsheet setup completed")
            
        except Exception as e:
            logger.error("Failed to setup spreadsheet", error=str(e))
            raise
    
    async def _create_worksheet(self, sheet_name: str, headers: List[str]) -> None:
        """Create a new worksheet with headers."""
        try:
            # Add sheet
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': len(headers)
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            # Add headers
            await self._update_headers(sheet_name, headers)
            
            logger.info("Created worksheet", sheet_name=sheet_name)
            
        except Exception as e:
            logger.error("Failed to create worksheet", 
                        sheet_name=sheet_name, 
                        error=str(e))
    
    async def _update_headers(self, sheet_name: str, headers: List[str]) -> None:
        """Update worksheet headers."""
        try:
            range_name = f"{sheet_name}!A1:{chr(65 + len(headers) - 1)}1"
            
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
        except Exception as e:
            logger.error("Failed to update headers", 
                        sheet_name=sheet_name, 
                        error=str(e))
    
    async def append_rows(self, sheet_name: str, rows: List[List[Any]]) -> bool:
        """Append rows to a worksheet."""
        try:
            if not rows:
                return True
            
            range_name = f"{sheet_name}!A:Z"
            
            body = {
                'values': rows
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.debug("Appended rows to sheet", 
                        sheet_name=sheet_name, 
                        rows_added=len(rows))
            return True
            
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit
                logger.warning("Rate limit hit, retrying", sheet_name=sheet_name)
                await asyncio.sleep(1)
                return await self.append_rows(sheet_name, rows)
            else:
                logger.error("Failed to append rows", 
                            sheet_name=sheet_name, 
                            error=str(e))
                return False
        except Exception as e:
            logger.error("Failed to append rows", 
                        sheet_name=sheet_name, 
                        error=str(e))
            return False


class QueryLogger:
    """Handles query and response logging to Google Sheets."""
    
    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.log_queue: List[QueryLogEntry] = []
        self.interaction_queue: List[InteractionLogEntry] = []
        self.analytics_queue: List[AnalyticsEntry] = []
        self.batch_size = settings.sheets_batch_size
        self.flush_interval = settings.sheets_flush_interval
        self._flush_task = None
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the query logger."""
        if self.initialized:
            return
        
        try:
            await self.sheets_service.initialize()
            
            # Start background flush task
            self._flush_task = asyncio.create_task(self._periodic_flush())
            
            self.initialized = True
            logger.info("Query logger initialized")
        except Exception as e:
            logger.error("Failed to initialize query logger", error=str(e))
            raise
    
    async def log_query_response(self, request: QueryRequest, 
                               response: QueryResponse) -> None:
        """Log a query and response."""
        try:
            if not self.initialized:
                await self.initialize()
            
            entry = QueryLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=request.session_id,
                user_id=request.user_id,
                query=request.query,
                response=response.response,
                query_type=response.query_type.value if response.query_type else "unknown",
                confidence_score=response.confidence_score,
                processing_time=response.processing_time,
                sources_count=len(response.sources),
                metadata={
                    "max_results": request.max_results,
                    "include_sources": request.include_sources,
                    "response_metadata": response.metadata or {}
                }
            )
            
            self.log_queue.append(entry)
            
            # Flush if queue is full
            if len(self.log_queue) >= self.batch_size:
                await self._flush_query_logs()
            
        except Exception as e:
            logger.error("Failed to log query response", error=str(e))
    
    async def log_interaction(self, session_id: Optional[str], 
                            user_id: Optional[str],
                            interaction_type: str,
                            details: Dict[str, Any]) -> None:
        """Log a user interaction."""
        try:
            if not self.initialized:
                await self.initialize()
            
            entry = InteractionLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                user_id=user_id,
                interaction_type=interaction_type,
                details=details
            )
            
            self.interaction_queue.append(entry)
            
            # Flush if queue is full
            if len(self.interaction_queue) >= self.batch_size:
                await self._flush_interaction_logs()
            
        except Exception as e:
            logger.error("Failed to log interaction", error=str(e))
    
    async def log_analytics_metric(self, metric_name: str,
                                 metric_value: Union[int, float, str],
                                 category: str = "general",
                                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log an analytics metric."""
        try:
            if not self.initialized:
                await self.initialize()
            
            entry = AnalyticsEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                metric_name=metric_name,
                metric_value=metric_value,
                category=category,
                metadata=metadata or {}
            )
            
            self.analytics_queue.append(entry)
            
            # Flush if queue is full
            if len(self.analytics_queue) >= self.batch_size:
                await self._flush_analytics_logs()
            
        except Exception as e:
            logger.error("Failed to log analytics metric", error=str(e))
    
    async def _flush_query_logs(self) -> None:
        """Flush query logs to Google Sheets."""
        if not self.log_queue:
            return
        
        try:
            rows = [entry.to_row() for entry in self.log_queue]
            success = await self.sheets_service.append_rows('Query_Logs', rows)
            
            if success:
                logged_count = len(self.log_queue)
                self.log_queue.clear()
                logger.debug("Flushed query logs", count=logged_count)
            
        except Exception as e:
            logger.error("Failed to flush query logs", error=str(e))
    
    async def _flush_interaction_logs(self) -> None:
        """Flush interaction logs to Google Sheets."""
        if not self.interaction_queue:
            return
        
        try:
            rows = [entry.to_row() for entry in self.interaction_queue]
            success = await self.sheets_service.append_rows('Interaction_Logs', rows)
            
            if success:
                logged_count = len(self.interaction_queue)
                self.interaction_queue.clear()
                logger.debug("Flushed interaction logs", count=logged_count)
            
        except Exception as e:
            logger.error("Failed to flush interaction logs", error=str(e))
    
    async def _flush_analytics_logs(self) -> None:
        """Flush analytics logs to Google Sheets."""
        if not self.analytics_queue:
            return
        
        try:
            rows = [entry.to_row() for entry in self.analytics_queue]
            success = await self.sheets_service.append_rows('Analytics', rows)
            
            if success:
                logged_count = len(self.analytics_queue)
                self.analytics_queue.clear()
                logger.debug("Flushed analytics logs", count=logged_count)
            
        except Exception as e:
            logger.error("Failed to flush analytics logs", error=str(e))
    
    async def _flush_all(self) -> None:
        """Flush all queued logs."""
        await asyncio.gather(
            self._flush_query_logs(),
            self._flush_interaction_logs(),
            self._flush_analytics_logs(),
            return_exceptions=True
        )
    
    async def _periodic_flush(self) -> None:
        """Periodically flush logs to Google Sheets."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_all()
            except asyncio.CancelledError:
                # Flush remaining logs before exit
                await self._flush_all()
                break
            except Exception as e:
                logger.error("Periodic flush failed", error=str(e))
    
    async def shutdown(self) -> None:
        """Shutdown the logger and flush remaining logs."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_all()
        logger.info("Query logger shutdown complete")


class AnalyticsTracker:
    """Tracks and logs various analytics metrics."""
    
    def __init__(self, logger: QueryLogger):
        self.logger = logger
        self.session_metrics: Dict[str, Dict[str, Any]] = {}
        self.user_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def track_session_start(self, session_id: str, user_id: Optional[str] = None) -> None:
        """Track session start."""
        timestamp = datetime.now(timezone.utc)
        
        self.session_metrics[session_id] = {
            'start_time': timestamp,
            'user_id': user_id,
            'query_count': 0,
            'total_processing_time': 0.0,
            'avg_confidence': 0.0
        }
        
        await self.logger.log_interaction(
            session_id, user_id, 'session_start',
            {'timestamp': timestamp.isoformat()}
        )
        
        await self.logger.log_analytics_metric(
            'session_started', 1, 'sessions',
            {'session_id': session_id, 'user_id': user_id}
        )
    
    async def track_session_end(self, session_id: str) -> None:
        """Track session end."""
        if session_id not in self.session_metrics:
            return
        
        metrics = self.session_metrics[session_id]
        end_time = datetime.now(timezone.utc)
        duration = (end_time - metrics['start_time']).total_seconds()
        
        await self.logger.log_interaction(
            session_id, metrics['user_id'], 'session_end',
            {
                'duration_seconds': duration,
                'query_count': metrics['query_count'],
                'avg_processing_time': metrics['total_processing_time'] / max(1, metrics['query_count']),
                'avg_confidence': metrics['avg_confidence']
            }
        )
        
        await self.logger.log_analytics_metric(
            'session_duration', duration, 'sessions',
            {'session_id': session_id, 'query_count': metrics['query_count']}
        )
        
        # Clean up
        del self.session_metrics[session_id]
    
    async def track_query_metrics(self, session_id: str, 
                                processing_time: float,
                                confidence_score: float,
                                query_type: str) -> None:
        """Track query-specific metrics."""
        if session_id in self.session_metrics:
            metrics = self.session_metrics[session_id]
            metrics['query_count'] += 1
            metrics['total_processing_time'] += processing_time
            
            # Update rolling average confidence
            old_avg = metrics['avg_confidence']
            count = metrics['query_count']
            metrics['avg_confidence'] = (old_avg * (count - 1) + confidence_score) / count
        
        await self.logger.log_analytics_metric(
            'query_processed', 1, 'queries',
            {
                'session_id': session_id,
                'processing_time': processing_time,
                'confidence_score': confidence_score,
                'query_type': query_type
            }
        )
    
    async def track_error(self, error_type: str, error_message: str,
                        session_id: Optional[str] = None,
                        user_id: Optional[str] = None) -> None:
        """Track error occurrences."""
        await self.logger.log_interaction(
            session_id, user_id, 'error',
            {
                'error_type': error_type,
                'error_message': error_message
            }
        )
        
        await self.logger.log_analytics_metric(
            'error_occurred', 1, 'errors',
            {
                'error_type': error_type,
                'session_id': session_id,
                'user_id': user_id
            }
        )
    
    async def track_performance_metric(self, endpoint: str,
                                     response_time: float,
                                     status_code: int,
                                     user_count: Optional[int] = None) -> None:
        """Track API performance metrics."""
        await self.logger.log_analytics_metric(
            'api_response_time', response_time, 'performance',
            {
                'endpoint': endpoint,
                'status_code': status_code,
                'user_count': user_count
            }
        )


# Global query logger and analytics tracker instances
query_logger = QueryLogger()
analytics_tracker = AnalyticsTracker(query_logger)
