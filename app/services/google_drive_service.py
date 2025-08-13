"""
Google Drive Integration Service for RAG Document Sync.

Implements:
- Intelligent document discovery and sync from Google Drive folder
- File format detection and processing (PDF, DOCX, TXT, MD, etc.)
- Content extraction and preprocessing
- RAG corpus integration with metadata
- Incremental sync with change detection
- Batch processing for large document sets
"""

import asyncio
import hashlib
import mimetypes
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

import aiofiles
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

import vertexai
from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel

# Document processing libraries
import PyPDF2
from docx import Document as DocxDocument
import markdown
from bs4 import BeautifulSoup

from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import get_logger
from ..models.schemas import DocumentMetadata, SyncStatus

logger = get_logger(__name__)


class DocumentProcessor:
    """Handles document content extraction and preprocessing."""
    
    SUPPORTED_MIME_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/plain': 'txt',
        'text/markdown': 'md',
        'text/html': 'html',
        'application/vnd.google-apps.document': 'google_doc',
        'application/vnd.google-apps.presentation': 'google_slides',
        'application/vnd.google-apps.spreadsheet': 'google_sheets'
    }
    
    def __init__(self):
        self.model = None
    
    async def initialize(self) -> None:
        """Initialize the document processor."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            self.model = GenerativeModel(settings.generation_model)
            logger.info("Document processor initialized")
        except Exception as e:
            logger.error("Failed to initialize document processor", error=str(e))
    
    def is_supported_format(self, mime_type: str) -> bool:
        """Check if document format is supported."""
        return mime_type in self.SUPPORTED_MIME_TYPES
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            text = ""
            async with aiofiles.open(file_path, 'rb') as file:
                pdf_content = await file.read()
                
            # Use PyPDF2 for text extraction
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error("PDF text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    async def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error("DOCX text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    async def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from plain text file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                return await file.read()
        except Exception as e:
            logger.error("TXT text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    async def extract_text_from_markdown(self, file_path: str) -> str:
        """Extract text from Markdown file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                md_content = await file.read()
            
            # Convert markdown to HTML then extract text
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()
        except Exception as e:
            logger.error("Markdown text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    async def extract_text_from_html(self, file_path: str) -> str:
        """Extract text from HTML file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                html_content = await file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        except Exception as e:
            logger.error("HTML text extraction failed", file_path=file_path, error=str(e))
            return ""
    
    async def extract_text(self, file_path: str, mime_type: str) -> str:
        """Extract text from various document formats."""
        file_type = self.SUPPORTED_MIME_TYPES.get(mime_type, 'unknown')
        
        if file_type == 'pdf':
            return await self.extract_text_from_pdf(file_path)
        elif file_type == 'docx':
            return await self.extract_text_from_docx(file_path)
        elif file_type == 'txt':
            return await self.extract_text_from_txt(file_path)
        elif file_type == 'md':
            return await self.extract_text_from_markdown(file_path)
        elif file_type == 'html':
            return await self.extract_text_from_html(file_path)
        else:
            logger.warning("Unsupported file type for text extraction", 
                         file_path=file_path, 
                         mime_type=mime_type)
            return ""
    
    async def preprocess_text(self, text: str, metadata: Dict[str, Any]) -> str:
        """Preprocess extracted text for better RAG performance."""
        try:
            if not text.strip():
                return text
            
            # Basic preprocessing
            # Remove excessive whitespace
            text = ' '.join(text.split())
            
            # If text is very long, use LLM to summarize and create chunks
            if len(text) > settings.max_document_length:
                if self.model:
                    summary_prompt = f"""
                    Please create a comprehensive summary of this document that preserves all key information:
                    
                    Document: {text[:10000]}...
                    
                    Include main topics, key facts, and important details.
                    Maintain the document's structure and context.
                    """
                    
                    try:
                        response = await self.model.generate_content_async(summary_prompt)
                        return response.text
                    except Exception as e:
                        logger.error("LLM preprocessing failed", error=str(e))
                        # Fallback to truncation
                        return text[:settings.max_document_length]
                else:
                    # Simple truncation if no model available
                    return text[:settings.max_document_length]
            
            return text
        except Exception as e:
            logger.error("Text preprocessing failed", error=str(e))
            return text
    
    def create_document_chunks(self, text: str, chunk_size: int = 1000, 
                             overlap: int = 200) -> List[str]:
        """Create overlapping chunks from document text."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings near the break point
                for i in range(end, max(start + chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks


class GoogleDriveService:
    """Handles Google Drive API operations."""
    
    def __init__(self):
        self.service = None
        self.credentials = None
    
    async def initialize(self) -> None:
        """Initialize Google Drive service."""
        try:
            # Load credentials
            self.credentials = await self._load_credentials()
            
            # Build Drive service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
            logger.info("Google Drive service initialized")
        except Exception as e:
            logger.error("Failed to initialize Google Drive service", error=str(e))
            raise
    
    async def _load_credentials(self) -> Credentials:
        """Load Google Drive credentials."""
        try:
            # Try to load from file first
            if os.path.exists(settings.google_drive_token_path):
                creds = Credentials.from_authorized_user_file(
                    settings.google_drive_token_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                
                # Refresh if necessary
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                
                if creds and creds.valid:
                    return creds
            
            # If no valid credentials, need to run OAuth flow
            logger.error("No valid Google Drive credentials found")
            raise Exception("Google Drive authentication required")
            
        except Exception as e:
            logger.error("Failed to load Google Drive credentials", error=str(e))
            raise
    
    async def get_folder_contents(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get all files in a Google Drive folder recursively."""
        try:
            files = []
            
            # Get direct files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively get subfolder contents
                    subfolder_files = await self.get_folder_contents(item['id'])
                    files.extend(subfolder_files)
                else:
                    files.append(item)
            
            return files
            
        except HttpError as e:
            logger.error("Failed to get folder contents", folder_id=folder_id, error=str(e))
            return []
    
    async def download_file(self, file_id: str, file_name: str, 
                          mime_type: str) -> Optional[str]:
        """Download file from Google Drive to temporary location."""
        try:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            safe_filename = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            temp_path = os.path.join(temp_dir, f"drive_{file_id}_{safe_filename}")
            
            # Handle Google Workspace files (export as text)
            if mime_type.startswith('application/vnd.google-apps'):
                if mime_type == 'application/vnd.google-apps.document':
                    export_mime = 'text/plain'
                elif mime_type == 'application/vnd.google-apps.presentation':
                    export_mime = 'text/plain'
                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                    export_mime = 'text/csv'
                else:
                    logger.warning("Unsupported Google Workspace file type", 
                                 mime_type=mime_type)
                    return None
                
                request = self.service.files().export(fileId=file_id, mimeType=export_mime)
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            # Download file
            with open(temp_path, 'wb') as file:
                downloader = MediaIoBaseDownload(file, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            return temp_path
            
        except Exception as e:
            logger.error("Failed to download file", file_id=file_id, error=str(e))
            return None
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for change detection."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Failed to calculate file hash", file_path=file_path, error=str(e))
            return ""


class RAGCorpusManager:
    """Manages RAG corpus operations for document indexing."""
    
    def __init__(self):
        self.corpus = None
        self.rag_client = None
    
    async def initialize(self) -> None:
        """Initialize RAG corpus manager."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            
            # Initialize document corpus
            self.corpus = rag.RagCorpus(
                name=f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}/ragCorpora/{settings.rag_document_corpus_id}"
            )
            
            logger.info("RAG corpus manager initialized")
        except Exception as e:
            logger.error("Failed to initialize RAG corpus manager", error=str(e))
    
    async def upload_document_to_corpus(self, document_content: str,
                                      metadata: DocumentMetadata) -> Optional[str]:
        """Upload document to RAG corpus."""
        try:
            # Create RAG file
            rag_file = await self.corpus.upload_file_async(
                path=None,  # We're providing content directly
                display_name=metadata.title,
                description=f"Document from Google Drive: {metadata.source_path}",
                file_content=document_content.encode('utf-8'),
                metadata=metadata.dict()
            )
            
            logger.info("Document uploaded to RAG corpus", 
                       document_id=metadata.document_id,
                       rag_file_id=rag_file.name)
            
            return rag_file.name
            
        except Exception as e:
            logger.error("Failed to upload document to RAG corpus",
                        document_id=metadata.document_id, 
                        error=str(e))
            return None
    
    async def delete_document_from_corpus(self, rag_file_id: str) -> bool:
        """Delete document from RAG corpus."""
        try:
            await self.corpus.delete_file_async(rag_file_id)
            logger.info("Document deleted from RAG corpus", rag_file_id=rag_file_id)
            return True
        except Exception as e:
            logger.error("Failed to delete document from RAG corpus",
                        rag_file_id=rag_file_id, 
                        error=str(e))
            return False


class GoogleDriveRAGSync:
    """Main service for syncing Google Drive documents with RAG corpus."""
    
    def __init__(self):
        self.drive_service = GoogleDriveService()
        self.document_processor = DocumentProcessor()
        self.corpus_manager = RAGCorpusManager()
        self.database = DatabaseManager()
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize all components."""
        if self.initialized:
            return
        
        try:
            await asyncio.gather(
                self.drive_service.initialize(),
                self.document_processor.initialize(),
                self.corpus_manager.initialize(),
                self.database.initialize()
            )
            
            self.initialized = True
            logger.info("Google Drive RAG Sync initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Google Drive RAG Sync", error=str(e))
            raise
    
    async def get_stored_document_metadata(self, drive_file_id: str) -> Optional[DocumentMetadata]:
        """Get stored document metadata from database."""
        try:
            async with self.database.get_session() as session:
                result = await session.execute(
                    "SELECT * FROM document_sync WHERE drive_file_id = ?",
                    (drive_file_id,)
                )
                row = result.fetchone()
                
                if row:
                    return DocumentMetadata(
                        document_id=row['document_id'],
                        title=row['title'],
                        source_path=row['source_path'],
                        file_type=row['file_type'],
                        content_hash=row['content_hash'],
                        last_modified=datetime.fromisoformat(row['last_modified']),
                        metadata=row.get('metadata', {})
                    )
                return None
        except Exception as e:
            logger.error("Failed to get stored document metadata", 
                        drive_file_id=drive_file_id, 
                        error=str(e))
            return None
    
    async def store_document_metadata(self, drive_file_id: str, 
                                    metadata: DocumentMetadata,
                                    rag_file_id: str) -> None:
        """Store document metadata in database."""
        try:
            async with self.database.get_session() as session:
                await session.execute("""
                    INSERT OR REPLACE INTO document_sync 
                    (drive_file_id, document_id, title, source_path, file_type, 
                     content_hash, last_modified, rag_file_id, metadata, sync_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    drive_file_id,
                    metadata.document_id,
                    metadata.title,
                    metadata.source_path,
                    metadata.file_type,
                    metadata.content_hash,
                    metadata.last_modified.isoformat(),
                    rag_file_id,
                    str(metadata.metadata),
                    SyncStatus.SYNCED.value
                ))
                await session.commit()
        except Exception as e:
            logger.error("Failed to store document metadata", 
                        drive_file_id=drive_file_id, 
                        error=str(e))
    
    async def process_drive_file(self, drive_file: Dict[str, Any]) -> bool:
        """Process a single Google Drive file."""
        try:
            drive_file_id = drive_file['id']
            file_name = drive_file['name']
            mime_type = drive_file['mimeType']
            modified_time = datetime.fromisoformat(
                drive_file['modifiedTime'].replace('Z', '+00:00')
            )
            
            # Check if file format is supported
            if not self.document_processor.is_supported_format(mime_type):
                logger.info("Skipping unsupported file format", 
                          file_name=file_name, 
                          mime_type=mime_type)
                return False
            
            # Check if document needs updating
            stored_metadata = await self.get_stored_document_metadata(drive_file_id)
            
            if stored_metadata and stored_metadata.last_modified >= modified_time:
                logger.debug("Document up to date, skipping", file_name=file_name)
                return True
            
            # Download file
            logger.info("Processing document", file_name=file_name)
            temp_path = await self.drive_service.download_file(
                drive_file_id, file_name, mime_type
            )
            
            if not temp_path:
                logger.error("Failed to download file", file_name=file_name)
                return False
            
            try:
                # Extract text content
                content = await self.document_processor.extract_text(temp_path, mime_type)
                
                if not content.strip():
                    logger.warning("No content extracted from file", file_name=file_name)
                    return False
                
                # Calculate content hash
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                
                # Skip if content hasn't changed
                if stored_metadata and stored_metadata.content_hash == content_hash:
                    logger.debug("Content unchanged, skipping", file_name=file_name)
                    return True
                
                # Create metadata
                metadata = DocumentMetadata(
                    document_id=drive_file_id,
                    title=file_name,
                    source_path=f"googledrive://{drive_file_id}",
                    file_type=mime_type,
                    content_hash=content_hash,
                    last_modified=modified_time,
                    metadata={
                        'drive_file_id': drive_file_id,
                        'web_view_link': drive_file.get('webViewLink', ''),
                        'size': drive_file.get('size', 0),
                        'mime_type': mime_type
                    }
                )
                
                # Preprocess content
                processed_content = await self.document_processor.preprocess_text(
                    content, metadata.metadata
                )
                
                # Remove old version from corpus if exists
                if stored_metadata and hasattr(stored_metadata, 'rag_file_id'):
                    await self.corpus_manager.delete_document_from_corpus(
                        stored_metadata.rag_file_id
                    )
                
                # Upload to RAG corpus
                rag_file_id = await self.corpus_manager.upload_document_to_corpus(
                    processed_content, metadata
                )
                
                if rag_file_id:
                    # Store metadata
                    await self.store_document_metadata(drive_file_id, metadata, rag_file_id)
                    logger.info("Document successfully processed and indexed", 
                              file_name=file_name)
                    return True
                else:
                    logger.error("Failed to upload document to RAG corpus", 
                               file_name=file_name)
                    return False
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
        except Exception as e:
            logger.error("Failed to process drive file", 
                        file_name=drive_file.get('name', 'unknown'), 
                        error=str(e))
            return False
    
    async def sync_drive_folder(self, folder_id: Optional[str] = None,
                              batch_size: int = 10) -> Dict[str, Any]:
        """Sync entire Google Drive folder with RAG corpus."""
        try:
            await self.initialize()
            
            folder_id = folder_id or settings.google_drive_folder_id
            if not folder_id:
                raise ValueError("No Google Drive folder ID provided")
            
            # Get all files in folder
            logger.info("Starting Google Drive folder sync", folder_id=folder_id)
            drive_files = await self.drive_service.get_folder_contents(folder_id)
            
            logger.info("Found files in Google Drive", count=len(drive_files))
            
            # Process files in batches
            processed = 0
            successful = 0
            failed = 0
            
            for i in range(0, len(drive_files), batch_size):
                batch = drive_files[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [self.process_drive_file(file) for file in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    processed += 1
                    if isinstance(result, Exception):
                        failed += 1
                        logger.error("File processing failed", error=str(result))
                    elif result:
                        successful += 1
                    else:
                        failed += 1
                
                logger.info("Processed batch", 
                          batch_number=i // batch_size + 1,
                          processed=processed,
                          successful=successful,
                          failed=failed)
            
            sync_result = {
                "folder_id": folder_id,
                "total_files": len(drive_files),
                "processed": processed,
                "successful": successful,
                "failed": failed,
                "sync_time": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("Google Drive sync completed", **sync_result)
            return sync_result
            
        except Exception as e:
            logger.error("Google Drive sync failed", error=str(e))
            raise
    
    async def setup_periodic_sync(self, interval_hours: int = 24) -> None:
        """Setup periodic sync of Google Drive folder."""
        logger.info("Setting up periodic Google Drive sync", 
                   interval_hours=interval_hours)
        
        while True:
            try:
                await self.sync_drive_folder()
                logger.info("Periodic sync completed successfully")
            except Exception as e:
                logger.error("Periodic sync failed", error=str(e))
            
            # Wait for next sync
            await asyncio.sleep(interval_hours * 3600)


# Global Google Drive sync service instance
drive_sync_service = GoogleDriveRAGSync()
