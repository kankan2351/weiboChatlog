# src/utils/embeddings.py
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import List

load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT"),
    api_key=os.getenv("AZURE_EMBEDDING_KEY"),
    api_version="2024-02-01"
)

def generate_embeddings(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Generate embeddings for text using Azure OpenAI"""
    try:
        response = client.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"Error generating embeddings: {str(e)}")
        return []
