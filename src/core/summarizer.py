import asyncio
from typing import List, Dict, Any, Optional, TypedDict
from dataclasses import dataclass
import time
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, START, END

from ..core.vtt_parser import VTTParser, TranscriptSegment
from ..core.chunker import TextChunker, TextChunk
from ..services.ollama_service import OllamaService, OllamaResponse
from ..utils.config import Config

class SummarizationState(TypedDict):
    """State for the summarization workflow."""
    original_text: str
    chunks: Optional[List[TextChunk]]
    chunk_summaries: Optional[List[str]]
    final_summary: str
    processing_stats: Optional[Dict[str, Any]]
    error: Optional[str]

@dataclass
class SummarizationResult:
    """Result of the summarization process."""
    summary: str
    original_length: int
    summary_length: int
    chunks_processed: int
    processing_time: float
    compression_ratio: float
    error: Optional[str] = None

class TranscriptSummarizer:
    """Main summarizer class using LangGraph for workflow orchestration."""
    
    def __init__(self, config: Config):
        """
        Initialize the summarizer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.ollama_service = OllamaService(
            base_url=config.ollama_base_url,
            model=config.model_name,
            timeout=config.request_timeout
        )
        self.chunker = TextChunker(
            chunk_size=config.chunk_size,
            overlap_size=config.chunk_overlap
        )
        self.vtt_parser = VTTParser()
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """Create the LangGraph workflow for summarization."""
        
        def parse_input(state: SummarizationState) -> SummarizationState:
            """Parse and validate input."""
            if not state.get("original_text", "").strip():
                return {**state, "error": "Empty input text"}
            
            # Initialize processing stats
            processing_stats = {
                "start_time": time.time(),
                "original_length": len(state["original_text"]),
                "original_words": len(state["original_text"].split())
            }
            
            return {**state, "processing_stats": processing_stats}
        
        def chunk_text(state: SummarizationState) -> SummarizationState:
            """Chunk the text for processing."""
            if state.get("error"):
                return state
            
            try:
                chunks = self.chunker.chunk_by_sentences(state["original_text"])
                processing_stats = state.get("processing_stats", {})
                processing_stats.update({
                    "chunks_created": len(chunks),
                    "chunking_strategy": "sentence-based"
                })
                
                # If only one chunk, we might not need chunk-level summarization
                if len(chunks) == 1:
                    processing_stats["single_chunk"] = True
                
                return {**state, "chunks": chunks, "processing_stats": processing_stats}
                
            except Exception as e:
                return {**state, "error": f"Error chunking text: {str(e)}"}
        
        def summarize_chunks(state: SummarizationState) -> SummarizationState:
            """Summarize individual chunks."""
            if state.get("error") or not state.get("chunks"):
                return state
            
            try:
                chunks = state["chunks"]
                
                # If only one chunk, skip chunk summarization
                if len(chunks) == 1:
                    return {**state, "chunk_summaries": [chunks[0].content]}
                
                # Create prompts for each chunk
                chunk_prompts = []
                for i, chunk in enumerate(chunks):
                    prompt = self._create_chunk_summary_prompt(chunk.content, i + 1, len(chunks))
                    chunk_prompts.append(prompt)
                
                # Process chunks asynchronously
                chunk_summaries = asyncio.run(self._process_chunks_async(chunk_prompts))
                
                processing_stats = state.get("processing_stats", {})
                processing_stats["chunks_summarized"] = len(chunk_summaries)
                
                return {**state, "chunk_summaries": chunk_summaries, "processing_stats": processing_stats}
                
            except Exception as e:
                return {**state, "error": f"Error summarizing chunks: {str(e)}"}
        
        def create_final_summary(state: SummarizationState) -> SummarizationState:
            """Create the final summary from chunk summaries."""
            if state.get("error") or not state.get("chunk_summaries"):
                return state
            
            try:
                # Combine chunk summaries
                combined_summaries = "\n\n".join(state["chunk_summaries"])
                
                # Create final summary prompt
                final_prompt = self._create_final_summary_prompt(combined_summaries)
                
                # Generate final summary
                response = self.ollama_service.generate_sync(
                    prompt=final_prompt,
                    temperature=self.config.temperature
                )
                
                final_summary = response.content.strip()
                
                # Update processing stats
                processing_stats = state.get("processing_stats", {})
                end_time = time.time()
                processing_time = end_time - processing_stats.get("start_time", 0)
                
                processing_stats.update({
                    "end_time": end_time,
                    "processing_time": processing_time,
                    "final_summary_length": len(final_summary),
                    "final_summary_words": len(final_summary.split()),
                    "compression_ratio": len(state["original_text"]) / len(final_summary) if final_summary else 0
                })
                
                return {**state, "final_summary": final_summary, "processing_stats": processing_stats}
                
            except Exception as e:
                return {**state, "error": f"Error creating final summary: {str(e)}"}
        
        # Create the workflow graph
        workflow = StateGraph(SummarizationState)
        
        # Add nodes
        workflow.add_node("parse_input", parse_input)
        workflow.add_node("chunk_text", chunk_text)
        workflow.add_node("summarize_chunks", summarize_chunks)
        workflow.add_node("create_final_summary", create_final_summary)
        
        # Define the workflow
        workflow.add_edge(START, "parse_input")
        workflow.add_edge("parse_input", "chunk_text")
        workflow.add_edge("chunk_text", "summarize_chunks")
        workflow.add_edge("summarize_chunks", "create_final_summary")
        workflow.add_edge("create_final_summary", END)
        
        return workflow.compile()
    
    async def _process_chunks_async(self, prompts: List[str]) -> List[str]:
        """Process multiple chunk prompts asynchronously."""
        async with self.ollama_service:
            responses = await self.ollama_service.generate_multiple_async(
                prompts, 
                temperature=self.config.temperature
            )
            return [response.content.strip() for response in responses]
    
    def _create_chunk_summary_prompt(self, chunk_text: str, chunk_num: int, total_chunks: int) -> str:
        """Create a prompt for summarizing a text chunk."""
        return f"""You are an expert at summarizing transcript content. Please provide a concise but comprehensive summary of the following transcript segment.

This is chunk {chunk_num} of {total_chunks} from a larger transcript.

Key requirements:
- Capture the main topics and key points discussed
- Preserve important details, names, and specific information
- Keep the summary focused and well-structured
- Maintain the chronological flow of information
- Use clear, professional language

Transcript segment:
{chunk_text}

Summary:"""

    def _create_final_summary_prompt(self, combined_summaries: str) -> str:
        """Create a prompt for the final summary."""
        return f"""You are an expert at creating comprehensive summaries from multiple related text segments. Below are summaries of different parts of a transcript. Please create a final, cohesive summary that:

1. Integrates all the key information from the segments
2. Maintains logical flow and structure
3. Eliminates redundancy while preserving important details
4. Provides a clear overview of the main topics and conclusions
5. Uses professional, clear language
6. Organizes information in a helpful way for the reader

Segment summaries:
{combined_summaries}

Please provide a comprehensive final summary:"""

    def summarize_vtt_file(self, file_path: str) -> SummarizationResult:
        """
        Summarize a VTT file.
        
        Args:
            file_path: Path to the VTT file
            
        Returns:
            SummarizationResult object
        """
        try:
            # Parse VTT file
            segments = self.vtt_parser.parse_file(file_path)
            full_text = self.vtt_parser.get_full_transcript()
            
            return self.summarize_text(full_text)
            
        except Exception as e:
            return SummarizationResult(
                summary="",
                original_length=0,
                summary_length=0,
                chunks_processed=0,
                processing_time=0.0,
                compression_ratio=0.0,
                error=str(e)
            )
    
    def summarize_vtt_content(self, vtt_content: str) -> SummarizationResult:
        """
        Summarize VTT content from a string.
        
        Args:
            vtt_content: VTT content as string
            
        Returns:
            SummarizationResult object
        """
        try:
            # Parse VTT content
            segments = self.vtt_parser.parse_content(vtt_content)
            full_text = self.vtt_parser.get_full_transcript()
            
            return self.summarize_text(full_text)
            
        except Exception as e:
            return SummarizationResult(
                summary="",
                original_length=0,
                summary_length=0,
                chunks_processed=0,
                processing_time=0.0,
                compression_ratio=0.0,
                error=str(e)
            )
    
    def summarize_text(self, text: str) -> SummarizationResult:
        """
        Summarize plain text.
        
        Args:
            text: Input text to summarize
            
        Returns:
            SummarizationResult object
        """
        # Create initial state
        initial_state: SummarizationState = {
            "original_text": text,
            "chunks": None,
            "chunk_summaries": None,
            "final_summary": "",
            "processing_stats": None,
            "error": None
        }
        
        # Run the workflow
        result_state = self.workflow.invoke(initial_state)
        
        # Create result object
        if result_state.get("error"):
            return SummarizationResult(
                summary="",
                original_length=len(text),
                summary_length=0,
                chunks_processed=0,
                processing_time=0.0,
                compression_ratio=0.0,
                error=result_state["error"]
            )
        
        stats = result_state.get("processing_stats", {})
        return SummarizationResult(
            summary=result_state.get("final_summary", ""),
            original_length=stats.get("original_length", 0),
            summary_length=stats.get("final_summary_length", 0),
            chunks_processed=stats.get("chunks_summarized", 0),
            processing_time=stats.get("processing_time", 0.0),
            compression_ratio=stats.get("compression_ratio", 0.0)
        )
    
    def check_service_health(self) -> Dict[str, Any]:
        """
        Check the health of the Ollama service and model availability.
        
        Returns:
            Health check results
        """
        health_status = {
            "ollama_connection": False,
            "model_available": False,
            "model_info": {},
            "timestamp": time.time()
        }
        
        try:
            # Test connection
            health_status["ollama_connection"] = self.ollama_service.test_connection()
            
            if health_status["ollama_connection"]:
                # Check model availability
                health_status["model_available"] = self.ollama_service.check_model_availability()
                
                # Get model info
                health_status["model_info"] = self.ollama_service.get_model_info()
        
        except Exception as e:
            health_status["error"] = str(e)
        
        return health_status
