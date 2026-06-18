from app.moduller import llm_router


def sor(prompt: str) -> dict:
    if not prompt or not prompt.strip():
        return {"success": False, "error": "Prompt gerekli"}
    try:
        text, engine = llm_router.generate(prompt.strip(), min_length=30)
        if text:
            return {"success": True, "response": text, "reply": text, "engine": engine}
        return {"success": False, "error": "Hiçbir AI motoru yanıt vermedi (API key veya Ollama kontrol et)"}
    except Exception as e:
        return {"success": False, "error": str(e)}
