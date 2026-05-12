import random
from typing import List, Union

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        print(f"Loaded Mock Embedding Service: {model_name} (due to disk space limits)")

    def generate_embeddings(self, text: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(text, str):
            text = [text]
        # Return random 384-d vector for each text
        return [[random.random() for _ in range(384)] for _ in text]

embedding_service = EmbeddingService()

