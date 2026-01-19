import ollama

class TextRefiner:
    def __init__(self, model="llama3"):
        self.model = model
        print(f"TextRefiner initialized with model: {self.model}")

    def refine(self, text):
        """
        Sends text to Ollama for grammar and formatting correction.
        """
        if not text:
            return None

        prompt = (
            f"Please fix the grammar, punctuation, and formatting of the following text. "
            f"Remove any filler words (like 'um', 'uh'). "
            f"Return ONLY the corrected text, do not add any conversational filler or introductions.\n\n"
            f"Text: {text}"
        )

        try:
            response = ollama.chat(model=self.model, messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            return response['message']['content'].strip()
        except Exception as e:
            print(f"Ollama error: {e}")
            return text # Fallback to original text if Ollama fails
