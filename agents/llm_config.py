import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

_llm_instance = None


def get_shared_llm() -> ChatGroq:
    global _llm_instance
    
    if _llm_instance is None:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment")
        
        _llm_instance = ChatGroq(
            groq_api_key=api_key,
            model_name=os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768'),
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.3')),
            timeout=120,  # 2 minute timeout
            max_retries=2
        )
    
    return _llm_instance
