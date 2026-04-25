"""Generative AI module for grounded response generation using Groq."""

from __future__ import annotations

from neurvinch.models import RetrievalResult


class GroqGenerator:
    """Generates grounded responses using Groq's LLM API."""

    def __init__(
        self,
        api_key: str,
        model: str = "mixtral-8x7b-32768",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> None:
        """Initialize Groq generator.

        Args:
            api_key: Groq API key
            model: Model name (default: mixtral-8x7b-32768)
            temperature: Response temperature (0-1)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not api_key:
            raise ValueError("GROQ_API_KEY is required but not set. Check your .env file.")

        try:
            from groq import Groq
        except ImportError:
            raise ImportError("groq package not installed. Run: pip install groq")

        self.client = Groq(api_key=api_key)

    def generate(
        self,
        query: str,
        context: list[RetrievalResult],
        system_prompt: str | None = None,
    ) -> str:
        """Generate a grounded response based on retrieved context.

        Args:
            query: User's question
            context: List of retrieved relevant chunks
            system_prompt: Optional custom system prompt

        Returns:
            Generated response grounded in the context
        """
        if not context:
            return "No relevant information found in the knowledge base to answer your question."

        # Build context string
        context_str = "\n\n".join(
            [f"[{i+1}] {result.text}\nSource: {result.source.path}" 
             for i, result in enumerate(context)]
        )

        # Default system prompt
        if system_prompt is None:
            system_prompt = (
                "You are a helpful assistant that answers questions based solely on the provided context. "
                "Always cite your sources. If the context doesn't contain the answer, say so explicitly."
            )

        # Construct messages
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": f"Context:\n{context_str}\n\nQuestion: {query}",
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
