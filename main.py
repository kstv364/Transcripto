import os
import gradio as gr
from src.ui.gradio_app import create_gradio_interface
from src.utils.config import Config

def main():
    """Main entry point for the transcript summarizer application."""
    # Load configuration
    config = Config()
    
    print("🚀 Starting Transcript Summarizer...")
    print(f"📡 Ollama URL: {config.ollama_base_url}")
    print(f"🤖 Model: {config.model_name}")
    print(f"🌐 Port: {config.gradio_port}")
    
    # Create and launch Gradio interface
    interface = create_gradio_interface(config)
    
    # Launch the application
    interface.launch(
        server_name="0.0.0.0",
        server_port=config.gradio_port,
        share=False,
        show_error=True
    )

if __name__ == "__main__":
    main()
