# tutor_engine.py (Updated)
# Project Codexa – GPT-OSS 20B powered engine
# - Teaching content generation
# - Quiz generation + parsing
# Requires: pip install ollama

import re
from typing import List, Dict, Any, Iterable, Tuple, Optional
import ollama

DEFAULT_MODEL = "gpt-oss:20b"

# ------------------ Helpers ------------------

QUIZ_TEMPLATE = """
[QUIZ START]
[QUESTION]
Question: Example question?
[A] Option A
[B] Option B
[C] Option C
[CORRECT: A]
[/QUESTION]
[QUIZ END]
""".strip()

def _system_prompt(language: str) -> str:
    return f"""
You are Study Buddy, an offline tutor for Classes 6–12 in India.
RULES:
- Always respond in {language}.
- Use LaTeX ($...$) for math/chemistry formulas where needed.
- TEACHING: 3–4 concise subtopics, with analogies, and end with a one-line check ("Does this make sense?").
- QUIZ: Output ONLY a quiz block exactly in this format:
{QUIZ_TEMPLATE}
STRICT CONSTRAINTS:
- Exactly 5 MCQs per quiz.
- Options limited to A, B, C.
- One correct answer per question.
- Each question must include a single-line 'Question: ' line.
- No extra text before [QUIZ START] or after [QUIZ END].
""".strip()

def _chat(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    try:
        resp = ollama.chat(model=model, messages=messages, stream=False)
        # Accessing assistant message content per ollama-python docs
        return resp["message"]["content"]
    except Exception as e:
        return f"Error: Ollama not available. Details: {e}"

# ------------------ Teaching ------------------

def teach_part(class_level: str,
               subject: str,
               chapter: str,
               part: int,
               language: str = "English",
               model: str = DEFAULT_MODEL) -> str:
    sys = _system_prompt(language)
    user = (
        f"TEACHING TASK.\n"
        f"Class: {class_level}\n"
        f"Subject: {subject}\n"
        f"Chapter: {chapter}\n"
        f"Part: {part}\n\n"
        f"Teach clearly, 3–4 key subtopics, use analogies, "
        f"and end with a one-line comprehension check. "
        f"Do NOT include any quiz block."
    )

    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]

    return _chat(messages, model=model).strip()

# ------------------ Quiz ------------------

def generate_quiz(class_level: str,
                  subject: str,
                  chapter: str,
                  part: int,
                  language: str = "English",
                  model: str = DEFAULT_MODEL) -> str:
    sys = _system_prompt(language)
    user = (
        "QUIZ TASK.\n"
        f"- Class: {class_level}\n"
        f"- Subject: {subject}\n"
        f"- Chapter: {chapter}\n"
        f"- Part: {part}\n\n"
        "Generate exactly 5 MCQs ONLY about this part. "
        "Use the strict QUIZ format with [QUESTION], [A], [B], [C], [CORRECT]."
    )

    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]

    return _chat(messages, model=model).strip()


def validate_quiz_block(text: str) -> bool:
    if not text or "[QUIZ START]" not in text or "[QUIZ END]" not in text:
        return False
    m = re.search(r"\[QUIZ START\](.*?)\[QUIZ END\]", text, flags=re.S)
    if not m:
        return False
    body = m.group(1)
    q_blocks = re.findall(r"\[QUESTION\](.*?)\[/QUESTION\]", body, flags=re.S)
    if len(q_blocks) != 5:
        return False

    for qb in q_blocks:
        if not re.search(r"^\s*Question:\s*.+", qb, flags=re.M):
            return False
        for k in ["A", "B", "C"]:
            if not re.search(rf"^\s*\[{k}\]\s*.+", qb, flags=re.M):
                return False
        if not re.search(r"^\s*\[CORRECT:\s*[A-C]\s*\]", qb, flags=re.M):
            return False
    return True


def parse_quiz_block(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    m = re.search(r"\[QUIZ START\](.*?)\[QUIZ END\]", text, flags=re.S)
    if not m:
        return []

    body = m.group(1)
    q_blocks = re.findall(r"\[QUESTION\](.*?)\[/QUESTION\]", body, flags=re.S)
    items: List[Dict[str, Any]] = []

    for qb in q_blocks:
        q_match = re.search(r"^\s*Question:\s*(.+)\s*$", qb, flags=re.M)
        question = q_match.group(1).strip() if q_match else ""

        options_map: Dict[str, str] = {}
        for key in ["A", "B", "C"]:
            om = re.search(rf"^\s*\[{key}\]\s*(.+)\s*$", qb, flags=re.M)
            if om:
                options_map[key] = om.group(1).strip()
            else:
                options_map[key] = ""

        corr_match = re.search(r"^\s*\[CORRECT:\s*([A-C])\s*\]", qb, flags=re.M)
        correct_key = corr_match.group(1) if corr_match else "A"

        if not question or not all(options_map.values()):
            continue

        items.append({
            "question": question,
            "options": [
                options_map.get("A", ""),
                options_map.get("B", ""),
                options_map.get("C", "")
            ],
            "answer": options_map.get(correct_key, ""),
            "explanation": "",
            "code": ""
        })
    return items

# ------------------ Answering Questions ------------------

def answer_question(question: str,
                    chapter: str,
                    subject: str,
                    class_level: str,
                    language: str = "English",
                    model: str = DEFAULT_MODEL) -> str:
    """
    Generates a contextual answer to a user's specific question.
    """
    sys = _system_prompt(language)
    user_context = (
        f"The user is studying Class {class_level} {subject}, focusing on the chapter '{chapter}'. "
        f"They have the following question: '{question}'"
    )

    user_prompt = (
        f"ANSWERING TASK.\n"
        f"Context: {user_context}\n\n"
        f"Please provide a clear, concise, and helpful answer to the user's question. "
        f"Explain the concept as you would to a student. Use an analogy if it helps. "
        f"Keep the response focused only on answering the question."
    )

    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_prompt},
    ]

    return _chat(messages, model=model).strip()

# ------------------ Orchestration: 5 parts per chapter ------------------

def run_chapters(
    class_level: str,
    subject: str,
    chapters: List[str],
    language: str = "English",
    parts_per_chapter: int = 5,
    model: str = DEFAULT_MODEL,
    retry_quiz: int = 1
) -> Iterable[Tuple[str, int, str, str, List[Dict[str, Any]]]]:
    for chapter in chapters:
        for part in range(1, parts_per_chapter + 1):
            lesson = teach_part(class_level, subject, chapter, part, language, model)
            quiz = generate_quiz(class_level, subject, chapter, part, language, model)
            attempts = 0
            while not validate_quiz_block(quiz) and attempts < retry_quiz:
                quiz = generate_quiz(class_level, subject, chapter, part, language, model)
                attempts += 1
            parsed = parse_quiz_block(quiz)
            yield (chapter, part, lesson, quiz, parsed)

# ------------------ CLI / Self-test ------------------

def print_parsed(parsed: List[Dict[str, Any]]) -> None:
    for i, it in enumerate(parsed, 1):
        print(f"{i}. {it['question']}")
        print(f"  A) {it['options'][0]}")
        print(f"  B) {it['options'][1]}")
        print(f"  C) {it['options'][2]}")
        print(f"  Correct: {it['answer']}")


if __name__ == "__main__":
    chapters = [
        "Light - Reflection and Refraction",
        "Human Eye and the Colourful World"
    ]

    print("=== RUN STUDY ENGINE ===")
    for chapter, part, lesson, quiz, parsed in run_chapters(
        class_level="10",
        subject="Physics",
        chapters=chapters,
        language="English",
        parts_per_chapter=1,
        model=DEFAULT_MODEL,
        retry_quiz=1
    ):
        print(f"\n=== Physics Class 10 | {chapter} — Part {part} ===")
        print("\n-- Lesson --")
        print(lesson)

        # Test the new function
        print("\n-- Answering Question --")
        test_q = "What is the focal length of a plane mirror?"
        print(f"Q: {test_q}")
        ans = answer_question(test_q, chapter, "Physics", "10")
        print(f"A: {ans}")
