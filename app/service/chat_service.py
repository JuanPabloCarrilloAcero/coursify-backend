from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.service.course_service import get_course


def _format_duration(seconds: Optional[int]) -> Optional[str]:
    if not seconds:
        return None
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"


def _build_course_context(course) -> str:
    parts: list[str] = []
    if getattr(course, "title", None):
        parts.append(f"Título: {course.title}")
    if getattr(course, "description", None):
        parts.append(f"Descripción: {course.description}")
    duration = _format_duration(getattr(course, "duration_seconds", None))
    if duration:
        parts.append(f"Duración aproximada: {duration}")
    if getattr(course, "format", None):
        parts.append(f"Formato: {course.format}")
    if getattr(course, "course_type", None):
        parts.append(f"Tipo: {course.course_type}")
    if getattr(course, "learning_goals", None):
        parts.append(f"Objetivos de aprendizaje: {course.learning_goals}")
    tags = [t.tag for t in getattr(course, "tags", []) if getattr(t, "tag", None)]
    if tags:
        parts.append(f"Etiquetas: {', '.join(tags)}")
    return "\n".join(parts)


def send_message_service(message: str, genai, *, db: Optional[Session] = None,
                        course_id: Optional[int] = None):
    prompt = message

    if db is not None and course_id:
        course = None
        try:
            course = get_course(course_id, db)
        except HTTPException:
            course = None

        if course:
            context = _build_course_context(course)
            if context:
                prompt = (
                    "Eres un asistente para estudiantes. Usa exclusivamente la siguiente información del curso"
                    " para responder. Si algún dato no está en el contexto, indícalo y evita inventar contenido.\n\n"
                    f"Información del curso:\n{context}\n\n"
                    f"Pregunta del usuario:\n{message}"
                )

    response = genai.generate_content(prompt)
    text = getattr(response, "text", None)

    return {"response": text or ""}