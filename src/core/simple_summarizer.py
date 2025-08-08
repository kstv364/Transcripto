import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from ..core.vtt_parser import VTTParser, TranscriptSegment
from ..core.chunker import TextChunker, TextChunk
from ..services.ollama_service import OllamaService, OllamaResponse
from ..utils.config import Config

@dataclass
class SimpleSummarizationResult:
    """Simplified result of the summarization process."""
    summary: str
    original_length: int
    summary_length: int
    chunks_processed: int
    processing_time: float
    compression_ratio: float
    error: Optional[str] = None

class SimpleTranscriptSummarizer:
    """Simplified summarizer without LangGraph dependency."""
    
    def __init__(self, config: Config):
        """
        Initialize the simplified summarizer.
        
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

    def summarize_text(self, text: str) -> SimpleSummarizationResult:
        """
        Summarize plain text using a simplified workflow.
        
        Args:
            text: Input text to summarize
            
        Returns:
            SimpleSummarizationResult object
        """
        start_time = time.time()
        
        try:
            # Step 1: Chunk the text
            chunks = self.chunker.chunk_by_sentences(text)
            
            if not chunks:
                return SimpleSummarizationResult(
                    summary="No content to summarize.",
                    original_length=len(text),
                    summary_length=0,
                    chunks_processed=0,
                    processing_time=time.time() - start_time,
                    compression_ratio=0.0,
                    error="No chunks created from input text"
                )
            
            # Step 2: Process chunks
            if len(chunks) == 1:
                # Single chunk - direct summarization
                prompt = self._create_final_summary_prompt(chunks[0].content)
                response = self.ollama_service.generate_sync(
                    prompt=prompt,
                    temperature=self.config.temperature
                )
                final_summary = response.content.strip()
                chunks_processed = 1
            else:
                # Multiple chunks - two-stage summarization
                chunk_prompts = [
                    self._create_chunk_summary_prompt(chunk.content, i + 1, len(chunks))
                    for i, chunk in enumerate(chunks)
                ]
                
                # Process chunks asynchronously
                chunk_summaries = asyncio.run(self._process_chunks_async(chunk_prompts))
                
                # Combine chunk summaries
                combined_summaries = "\n\n".join(chunk_summaries)
                
                # Create final summary
                final_prompt = self._create_final_summary_prompt(combined_summaries)
                response = self.ollama_service.generate_sync(
                    prompt=final_prompt,
                    temperature=self.config.temperature
                )
                final_summary = response.content.strip()
                chunks_processed = len(chunks)
            
            # Calculate results
            end_time = time.time()
            processing_time = end_time - start_time
            
            return SimpleSummarizationResult(
                summary=final_summary,
                original_length=len(text),
                summary_length=len(final_summary),
                chunks_processed=chunks_processed,
                processing_time=processing_time,
                compression_ratio=len(text) / len(final_summary) if final_summary else 0.0
            )
            
        except Exception as e:
            return SimpleSummarizationResult(
                summary="",
                original_length=len(text),
                summary_length=0,
                chunks_processed=0,
                processing_time=time.time() - start_time,
                compression_ratio=0.0,
                error=str(e)
            )
    
    def summarize_vtt_file(self, file_path: str) -> SimpleSummarizationResult:
        """
        Summarize a VTT file.
        
        Args:
            file_path: Path to the VTT file
            
        Returns:
            SimpleSummarizationResult object
        """
        try:
            # Parse VTT file
            segments = self.vtt_parser.parse_file(file_path)
            full_text = self.vtt_parser.get_full_transcript()
            
            return self.summarize_text(full_text)
            
        except Exception as e:
            return SimpleSummarizationResult(
                summary="",
                original_length=0,
                summary_length=0,
                chunks_processed=0,
                processing_time=0.0,
                compression_ratio=0.0,
                error=str(e)
            )
    
    def summarize_vtt_content(self, vtt_content: str) -> SimpleSummarizationResult:
        """
        Summarize VTT content from a string.
        
        Args:
            vtt_content: VTT content as string
            
        Returns:
            SimpleSummarizationResult object
        """
        try:
            # Parse VTT content
            segments = self.vtt_parser.parse_content(vtt_content)
            full_text = self.vtt_parser.get_full_transcript()
            
            return self.summarize_text(full_text)
            
        except Exception as e:
            return SimpleSummarizationResult(
                summary="",
                original_length=0,
                summary_length=0,
                chunks_processed=0,
                processing_time=0.0,
                compression_ratio=0.0,
                error=str(e)
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
