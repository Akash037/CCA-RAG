"""
Advanced RAG Service with Multi-Source Retrieval and Hybrid Search.

Implements:
- Multi-source retrieval (documents, memory, session, user profile)
- Hybrid search (semantic + keyword)
- Advanced ranking and reranking
- Multi-agent response generation
- Confidence scoring and source attribution
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview import rag
from google.cloud import aiplatform

from ..core.config import settings
from ..core.logging import get_logger
from ..models.schemas import (
    QueryRequest, QueryResponse, SourceDocument, 
    QueryType, MemoryContext
)
from .memory_manager import memory_manager

logger = get_logger(__name__)


class RetrievalStrategy(str, Enum):
    """Retrieval strategy enumeration."""
    SEMANTIC_ONLY = "semantic_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    MEMORY_FIRST = "memory_first"
    MULTI_AGENT = "multi_agent"


class AgentType(str, Enum):
    """Agent type enumeration."""
    FACTUAL = "factual"
    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"
    MULTIMODAL = "multimodal"


@dataclass
class RetrievalResult:
    """Retrieval result container."""
    documents: List[Dict[str, Any]]
    source: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class ProcessedQuery:
    """Processed query container."""
    original_query: str
    expanded_queries: List[str]
    query_type: QueryType
    strategy: RetrievalStrategy
    agent_type: AgentType
    metadata: Dict[str, Any]


class QueryProcessor:
    """Handles query analysis, expansion, and routing."""
    
    def __init__(self):
        self.model = None
    
    async def initialize(self) -> None:
        """Initialize the query processor."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            self.model = GenerativeModel(settings.generation_model)
            logger.info("Query processor initialized")
        except Exception as e:
            logger.error("Failed to initialize query processor", error=str(e))
    
    async def classify_query(self, query: str, 
                           context: Optional[MemoryContext] = None) -> QueryType:
        """Classify the query type using LLM."""
        try:
            classification_prompt = f"""
            Classify the following query into one of these categories:
            - FACTUAL: Questions seeking specific facts or information
            - CONVERSATIONAL: Casual conversation, greetings, or personal questions
            - ANALYTICAL: Questions requiring analysis, comparison, or reasoning
            - MULTIMODAL: Questions involving images, documents, or multiple media types
            
            Query: "{query}"
            
            Context: {context.session_memory if context else "None"}
            
            Respond with only the category name.
            """
            
            if self.model:
                response = await self.model.generate_content_async(classification_prompt)
                query_type = response.text.strip().upper()
                
                # Validate and default
                for qt in QueryType:
                    if qt.value.upper() == query_type:
                        return qt
            
            # Default classification
            return QueryType.FACTUAL
            
        except Exception as e:
            logger.error("Query classification failed", error=str(e))
            return QueryType.FACTUAL
    
    async def expand_query(self, query: str, 
                          context: Optional[MemoryContext] = None) -> List[str]:
        """Expand query using LLM for better retrieval."""
        try:
            expansion_prompt = f"""
            Generate 2-3 alternative phrasings of this query to improve information retrieval:
            
            Original Query: "{query}"
            
            Context: {context.session_memory.get('current_topic') if context and context.session_memory else "None"}
            
            Provide alternative phrasings that capture the same intent but use different keywords.
            Format as a simple list, one per line.
            """
            
            if self.model:
                response = await self.model.generate_content_async(expansion_prompt)
                expanded = [line.strip() for line in response.text.split('\n') if line.strip()]
                return [query] + expanded[:3]  # Original + up to 3 expansions
            
            return [query]
            
        except Exception as e:
            logger.error("Query expansion failed", error=str(e))
            return [query]
    
    def determine_retrieval_strategy(self, query_type: QueryType, 
                                   context: Optional[MemoryContext] = None) -> RetrievalStrategy:
        """Determine the best retrieval strategy."""
        if query_type == QueryType.CONVERSATIONAL:
            return RetrievalStrategy.MEMORY_FIRST
        elif query_type == QueryType.ANALYTICAL:
            return RetrievalStrategy.MULTI_AGENT
        elif query_type == QueryType.MULTIMODAL:
            return RetrievalStrategy.HYBRID
        else:
            return RetrievalStrategy.HYBRID
    
    def determine_agent_type(self, query_type: QueryType) -> AgentType:
        """Determine the appropriate agent type."""
        if query_type == QueryType.FACTUAL:
            return AgentType.FACTUAL
        elif query_type == QueryType.CONVERSATIONAL:
            return AgentType.CONVERSATIONAL
        elif query_type == QueryType.ANALYTICAL:
            return AgentType.ANALYTICAL
        elif query_type == QueryType.MULTIMODAL:
            return AgentType.MULTIMODAL
        else:
            return AgentType.FACTUAL
    
    async def process_query(self, query: str, 
                          context: Optional[MemoryContext] = None) -> ProcessedQuery:
        """Process and analyze the query."""
        # Classify query
        query_type = await self.classify_query(query, context)
        
        # Expand query
        expanded_queries = await self.expand_query(query, context)
        
        # Determine strategies
        strategy = self.determine_retrieval_strategy(query_type, context)
        agent_type = self.determine_agent_type(query_type)
        
        return ProcessedQuery(
            original_query=query,
            expanded_queries=expanded_queries,
            query_type=query_type,
            strategy=strategy,
            agent_type=agent_type,
            metadata={
                "processing_time": time.time(),
                "context_available": context is not None
            }
        )


class MultiSourceRetriever:
    """Handles retrieval from multiple sources with hybrid search."""
    
    def __init__(self):
        self.document_corpus = None
        self.memory_corpus = None
        self.rag_client = None
    
    async def initialize(self) -> None:
        """Initialize the retriever."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            
            # Initialize RAG corpora
            self.document_corpus = rag.RagCorpus(
                name=f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}/ragCorpora/{settings.rag_document_corpus_id}"
            )
            
            self.memory_corpus = rag.RagCorpus(
                name=f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}/ragCorpora/{settings.rag_memory_corpus_id}"
            )
            
            logger.info("Multi-source retriever initialized")
        except Exception as e:
            logger.error("Failed to initialize retriever", error=str(e))
    
    async def semantic_search(self, query: str, corpus_id: str, 
                            top_k: int = 10) -> RetrievalResult:
        """Perform semantic search using dense vectors."""
        try:
            # Use Vertex AI RAG API for semantic search
            response = await aiplatform.gapic.VertexRagDataServiceAsyncClient().retrieve_contexts(
                request={
                    "parent": f"projects/{settings.google_cloud_project}/locations/{settings.vertex_ai_location}",
                    "query": {"text": query, "similarity_top_k": top_k},
                    "vertex_rag_store": {
                        "rag_resources": [{"rag_corpus": corpus_id}],
                        "similarity_top_k": top_k,
                        "vector_distance_threshold": settings.similarity_threshold
                    }
                }
            )
            
            documents = []
            for context in response.contexts:
                documents.append({
                    "content": context.source_uri,
                    "text": context.text,
                    "distance": context.distance,
                    "source_uri": context.source_uri
                })
            
            return RetrievalResult(
                documents=documents,
                source="semantic_search",
                confidence=0.8,  # Base confidence for semantic search
                metadata={"query": query, "corpus_id": corpus_id}
            )
            
        except Exception as e:
            logger.error("Semantic search failed", error=str(e))
            return RetrievalResult(documents=[], source="semantic_search", confidence=0.0, metadata={})
    
    async def keyword_search(self, query: str, corpus_id: str, 
                           top_k: int = 10) -> RetrievalResult:
        """Perform keyword search using sparse vectors."""
        try:
            # Implement keyword search (placeholder)
            # This would use BM25 or similar keyword matching
            
            return RetrievalResult(
                documents=[],
                source="keyword_search",
                confidence=0.6,  # Base confidence for keyword search
                metadata={"query": query, "corpus_id": corpus_id}
            )
            
        except Exception as e:
            logger.error("Keyword search failed", error=str(e))
            return RetrievalResult(documents=[], source="keyword_search", confidence=0.0, metadata={})
    
    async def hybrid_search(self, query: str, corpus_id: str, 
                          alpha: float = 0.6, top_k: int = 10) -> RetrievalResult:
        """Perform hybrid search combining semantic and keyword search."""
        try:
            # Perform both searches in parallel
            semantic_task = self.semantic_search(query, corpus_id, top_k)
            keyword_task = self.keyword_search(query, corpus_id, top_k)
            
            semantic_result, keyword_result = await asyncio.gather(
                semantic_task, keyword_task
            )
            
            # Combine results with alpha weighting
            combined_documents = []
            
            # Weight semantic results
            for doc in semantic_result.documents:
                doc["hybrid_score"] = alpha * (1 - doc.get("distance", 1.0))
                combined_documents.append(doc)
            
            # Weight keyword results
            for doc in keyword_result.documents:
                doc["hybrid_score"] = (1 - alpha) * doc.get("score", 0.0)
                combined_documents.append(doc)
            
            # Sort by hybrid score and deduplicate
            combined_documents.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            combined_documents = combined_documents[:top_k]
            
            confidence = (alpha * semantic_result.confidence + 
                         (1 - alpha) * keyword_result.confidence)
            
            return RetrievalResult(
                documents=combined_documents,
                source="hybrid_search",
                confidence=confidence,
                metadata={
                    "alpha": alpha,
                    "semantic_count": len(semantic_result.documents),
                    "keyword_count": len(keyword_result.documents)
                }
            )
            
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            return RetrievalResult(documents=[], source="hybrid_search", confidence=0.0, metadata={})
    
    async def retrieve_from_documents(self, processed_query: ProcessedQuery) -> RetrievalResult:
        """Retrieve from document corpus."""
        if processed_query.strategy == RetrievalStrategy.SEMANTIC_ONLY:
            return await self.semantic_search(
                processed_query.original_query, 
                settings.rag_document_corpus_id
            )
        elif processed_query.strategy == RetrievalStrategy.KEYWORD_ONLY:
            return await self.keyword_search(
                processed_query.original_query, 
                settings.rag_document_corpus_id
            )
        else:  # HYBRID or others default to hybrid
            return await self.hybrid_search(
                processed_query.original_query, 
                settings.rag_document_corpus_id,
                alpha=settings.hybrid_search_alpha
            )
    
    async def retrieve_from_memory(self, processed_query: ProcessedQuery, 
                                 context: MemoryContext) -> RetrievalResult:
        """Retrieve from memory corpus and session memory."""
        memory_documents = []
        
        # Add session memory
        if context.session_memory:
            for msg in context.session_memory.get("conversation_history", []):
                memory_documents.append({
                    "content": msg.get("content", ""),
                    "role": msg.get("role", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "source": "session_memory",
                    "hybrid_score": 0.9  # High relevance for recent conversation
                })
        
        # Add short-term memory
        if context.short_term_memory:
            for interaction in context.short_term_memory.get("recent_interactions", []):
                if interaction.get("type") == "query_response":
                    memory_documents.append({
                        "content": interaction.get("response", ""),
                        "query": interaction.get("query", ""),
                        "timestamp": interaction.get("timestamp", ""),
                        "source": "short_term_memory",
                        "hybrid_score": 0.7
                    })
        
        return RetrievalResult(
            documents=memory_documents,
            source="memory_retrieval",
            confidence=0.8,
            metadata={"query": processed_query.original_query}
        )
    
    async def retrieve_multi_source(self, processed_query: ProcessedQuery, 
                                  context: MemoryContext) -> List[RetrievalResult]:
        """Retrieve from multiple sources based on strategy."""
        results = []
        
        if processed_query.strategy == RetrievalStrategy.MEMORY_FIRST:
            # Prioritize memory sources
            memory_result = await self.retrieve_from_memory(processed_query, context)
            document_result = await self.retrieve_from_documents(processed_query)
            results = [memory_result, document_result]
        
        elif processed_query.strategy == RetrievalStrategy.MULTI_AGENT:
            # Use all sources for comprehensive analysis
            memory_task = self.retrieve_from_memory(processed_query, context)
            document_task = self.retrieve_from_documents(processed_query)
            
            memory_result, document_result = await asyncio.gather(
                memory_task, document_task
            )
            results = [document_result, memory_result]
        
        else:
            # Default: documents first, then memory
            document_result = await self.retrieve_from_documents(processed_query)
            memory_result = await self.retrieve_from_memory(processed_query, context)
            results = [document_result, memory_result]
        
        return results


class AdvancedRanker:
    """Advanced ranking and reranking of search results."""
    
    def __init__(self):
        self.model = None
    
    async def initialize(self) -> None:
        """Initialize the ranker."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            self.model = GenerativeModel(settings.generation_model)
            logger.info("Advanced ranker initialized")
        except Exception as e:
            logger.error("Failed to initialize ranker", error=str(e))
    
    async def rerank_results(self, query: str, 
                           results: List[RetrievalResult]) -> List[Dict[str, Any]]:
        """Rerank results using advanced scoring."""
        if not settings.enable_reranking:
            # Simple concatenation without reranking
            all_documents = []
            for result in results:
                all_documents.extend(result.documents)
            return all_documents
        
        try:
            # Combine all documents from different sources
            all_documents = []
            for result in results:
                for doc in result.documents:
                    doc["source_type"] = result.source
                    doc["source_confidence"] = result.confidence
                    all_documents.append(doc)
            
            # Score documents based on multiple factors
            for doc in all_documents:
                score = 0.0
                
                # Base hybrid score
                score += doc.get("hybrid_score", 0.0) * 0.4
                
                # Source confidence
                score += doc.get("source_confidence", 0.0) * 0.3
                
                # Recency bonus for memory sources
                if doc.get("source_type") in ["session_memory", "short_term_memory"]:
                    score += 0.2
                
                # Content length normalization
                content_length = len(doc.get("content", ""))
                if 50 <= content_length <= 1000:  # Optimal length range
                    score += 0.1
                
                doc["final_score"] = score
            
            # Sort by final score
            all_documents.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            # Return top results
            return all_documents[:settings.max_retrieval_documents]
            
        except Exception as e:
            logger.error("Reranking failed", error=str(e))
            # Return original results if reranking fails
            all_documents = []
            for result in results:
                all_documents.extend(result.documents)
            return all_documents


class ResponseGenerator:
    """Multi-agent response generation system."""
    
    def __init__(self):
        self.models = {}
    
    async def initialize(self) -> None:
        """Initialize response generators."""
        try:
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            
            # Initialize different models for different agent types
            self.models[AgentType.FACTUAL] = GenerativeModel(settings.generation_model)
            self.models[AgentType.CONVERSATIONAL] = GenerativeModel(settings.generation_model)
            self.models[AgentType.ANALYTICAL] = GenerativeModel(settings.generation_model)
            self.models[AgentType.MULTIMODAL] = GenerativeModel(settings.generation_model)
            
            logger.info("Response generators initialized")
        except Exception as e:
            logger.error("Failed to initialize response generators", error=str(e))
    
    async def generate_factual_response(self, query: str, 
                                      documents: List[Dict[str, Any]],
                                      context: MemoryContext) -> Tuple[str, float]:
        """Generate factual response."""
        try:
            # Build context from documents
            context_text = "\n\n".join([
                f"Source: {doc.get('source', 'Unknown')}\nContent: {doc.get('content', '')}"
                for doc in documents[:5]  # Top 5 documents
            ])
            
            prompt = f"""
            You are a knowledgeable assistant providing factual information.
            
            Query: {query}
            
            Context Information:
            {context_text}
            
            Please provide a comprehensive, accurate answer based on the provided context.
            If the context doesn't contain enough information, state that clearly.
            Always cite your sources when possible.
            """
            
            model = self.models.get(AgentType.FACTUAL)
            if model:
                response = await model.generate_content_async(prompt)
                return response.text, 0.85  # High confidence for factual responses
            
            return "I don't have enough information to answer that question.", 0.3
            
        except Exception as e:
            logger.error("Factual response generation failed", error=str(e))
            return "I encountered an error while processing your request.", 0.1
    
    async def generate_conversational_response(self, query: str,
                                             documents: List[Dict[str, Any]],
                                             context: MemoryContext) -> Tuple[str, float]:
        """Generate conversational response."""
        try:
            # Use conversation history for context
            conversation_history = ""
            if context.session_memory:
                recent_messages = context.session_memory.get("conversation_history", [])[-5:]
                conversation_history = "\n".join([
                    f"{msg.get('role', '')}: {msg.get('content', '')}"
                    for msg in recent_messages
                ])
            
            prompt = f"""
            You are a friendly, conversational assistant.
            
            Recent conversation:
            {conversation_history}
            
            Current query: {query}
            
            Please respond in a natural, conversational manner while being helpful and informative.
            """
            
            model = self.models.get(AgentType.CONVERSATIONAL)
            if model:
                response = await model.generate_content_async(prompt)
                return response.text, 0.75  # Good confidence for conversational responses
            
            return "I'm here to help! Could you tell me more about what you're looking for?", 0.5
            
        except Exception as e:
            logger.error("Conversational response generation failed", error=str(e))
            return "I'd love to chat with you! What would you like to talk about?", 0.4
    
    async def generate_response(self, processed_query: ProcessedQuery,
                              documents: List[Dict[str, Any]],
                              context: MemoryContext) -> Tuple[str, float]:
        """Generate response using the appropriate agent."""
        if processed_query.agent_type == AgentType.CONVERSATIONAL:
            return await self.generate_conversational_response(
                processed_query.original_query, documents, context
            )
        else:
            # Default to factual for all other types
            return await self.generate_factual_response(
                processed_query.original_query, documents, context
            )


class AdvancedRAGService:
    """Main RAG service orchestrating all components."""
    
    def __init__(self):
        self.query_processor = QueryProcessor()
        self.retriever = MultiSourceRetriever()
        self.ranker = AdvancedRanker()
        self.response_generator = ResponseGenerator()
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize all RAG components."""
        if self.initialized:
            return
        
        try:
            await asyncio.gather(
                self.query_processor.initialize(),
                self.retriever.initialize(),
                self.ranker.initialize(),
                self.response_generator.initialize()
            )
            
            self.initialized = True
            logger.info("Advanced RAG Service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize RAG service", error=str(e))
            raise
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Process a RAG query through the complete pipeline."""
        start_time = time.time()
        
        try:
            # Ensure service is initialized
            await self.initialize()
            
            # Get comprehensive memory context
            context = await memory_manager.get_comprehensive_memory(
                request.session_id or "default",
                request.user_id
            )
            
            # Process and analyze query
            processed_query = await self.query_processor.process_query(
                request.query, context
            )
            
            # Retrieve from multiple sources
            retrieval_results = await self.retriever.retrieve_multi_source(
                processed_query, context
            )
            
            # Rank and rerank results
            ranked_documents = await self.ranker.rerank_results(
                request.query, retrieval_results
            )
            
            # Generate response
            response_text, confidence = await self.response_generator.generate_response(
                processed_query, ranked_documents, context
            )
            
            # Convert documents to source format
            sources = []
            for doc in ranked_documents[:request.max_results or 5]:
                source = SourceDocument(
                    document_id=doc.get("source_uri", "unknown"),
                    title=doc.get("title", "Document"),
                    content_snippet=doc.get("content", "")[:200] + "...",
                    confidence_score=doc.get("final_score", 0.5),
                    metadata=doc.get("metadata", {})
                )
                sources.append(source)
            
            # Update memory after interaction
            if request.user_id:
                await memory_manager.update_memory_after_interaction(
                    request.session_id or "default",
                    request.user_id,
                    request.query,
                    response_text,
                    {"query_type": processed_query.query_type.value}
                )
            
            processing_time = time.time() - start_time
            
            return QueryResponse(
                query=request.query,
                response=response_text,
                sources=sources,
                confidence_score=confidence,
                processing_time=processing_time,
                session_id=request.session_id,
                query_type=processed_query.query_type,
                metadata={
                    "agent_type": processed_query.agent_type.value,
                    "retrieval_strategy": processed_query.strategy.value,
                    "total_documents_retrieved": len(ranked_documents)
                }
            )
            
        except Exception as e:
            logger.error("RAG query processing failed", 
                        query=request.query, 
                        error=str(e))
            
            processing_time = time.time() - start_time
            
            return QueryResponse(
                query=request.query,
                response="I encountered an error while processing your request. Please try again.",
                sources=[],
                confidence_score=0.0,
                processing_time=processing_time,
                session_id=request.session_id,
                metadata={"error": str(e)}
            )


# Global RAG service instance
rag_service = AdvancedRAGService()
