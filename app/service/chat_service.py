def send_message_service(message, genai):
    response = genai.generate_content(message)
    text = getattr(response, "text", None)

    return {"response": text or ""}