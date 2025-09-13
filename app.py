# app.py
# Dashboard: Offline learning app with local GPT‑OSS 20B via tutor_engine,
# Streamlit tabs, chapter quiz flow, and pyttsx3 Text‑to‑Speech.

import os
import re
import json
import tempfile
from typing import Optional, Dict, Any, List

import requests
import streamlit as st
import pyttsx3

# tutor_engine.py MUST provide:
# - teach_part(class_level, subject, chapter, part, language)
# - generate_quiz(class_level, subject, chapter, part, language)
# - parse_quiz_block(text) -> List[Dict[str, Any]]
from tutor_engine import teach_part, generate_quiz, parse_quiz_block


# ----------------------------- Page config -----------------------------
st.set_page_config(
    page_title="Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)  # One st.chat_input in the main content area is the recommended chat pattern.


# ----------------------------- Helpers -----------------------------
def ensure_ollama_ready(base: str, timeout: float = 3.0) -> bool:
    """
    Return True if Ollama API responds at {base}/api/tags, else False.
    Normalizes 0.0.0.0 to 127.0.0.1 for client calls.
    """
    if not base:
        return False
    base = base.strip()
    if base.startswith("http://0.0.0.0"):
        base = base.replace("0.0.0.0", "127.0.0.1", 1)
    url = f"{base.rstrip('/')}/api/tags"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        # Optional: sanity check JSON
        _ = r.json()
        return True
    except Exception:
        return False  # Health check failed


# ----------------------------- Syllabus -----------------------------
SYLLABUS = {
    "6": {
        "Maths": [
            "Number System Basics",
            "Fractions and Decimals",
            "Ratio and Proportion",
            "Basic Geometry",
            "Mensuration",
        ],
        "Science": [
            "Food: Where Does It Come From?",
            "Components of Food",
            "Separation of Substances",
            "Sorting Materials",
            "Motion and Measurement of Distances",
            "Light, Shadows and Reflections",
        ],
    },
    "7": {
        "Maths": [
            "Integers",
            "Fractions and Decimals",
            "Simple Equations",
            "Lines and Angles",
            "Perimeter and Area",
        ],
        "Science": [
            "Nutrition in Plants",
            "Nutrition in Animals",
            "Heat",
            "Acids, Bases and Salts",
            "Physical and Chemical Changes",
        ],
    },
    "8": {
        "Maths": [
            "Rational Numbers",
            "Squares and Square Roots",
            "Cubes and Cube Roots",
            "Linear Equations in One Variable",
            "Mensuration",
        ],
        "Science": [
            "Crop Production and Management",
            "Materials: Metals and Non-metals",
            "Force and Pressure",
            "Friction",
            "Sound",
            "Light",
        ],
    },
    "9": {
        "Physics": ["Motion", "Force and Laws of Motion", "Gravitation", "Work and Energy", "Sound"],
        "Chemistry": ["Matter in Our Surroundings", "Is Matter Around Us Pure", "Atoms and Molecules", "Structure of the Atom"],
        "Biology": ["The Fundamental Unit of Life", "Tissues", "Diversity in Living Organisms", "Why Do We Fall Ill", "Natural Resources"],
        "Maths": ["Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations in Two Variables", "Triangles", "Statistics", "Probability"],
    },
    "10": {
        "Physics": ["Light - Reflection and Refraction", "Human Eye and Colourful World", "Electricity", "Magnetic Effects of Electric Current", "Sources of Energy"],
        "Chemistry": ["Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals", "Carbon and its Compounds", "Periodic Classification of Elements"],
        "Biology": ["Life Processes", "Control and Coordination", "How do Organisms Reproduce?", "Heredity and Evolution", "Our Environment"],
        "Maths": ["Real Numbers", "Polynomials", "Pair of Linear Equations in Two Variables", "Quadratic Equations", "Trigonometry Basics", "Statistics", "Probability"],
    },
    "11": {
        "Physics": ["Units and Measurements", "Motion in a Straight Line", "Laws of Motion", "Work, Energy and Power", "Waves"],
        "Chemistry": ["Some Basic Concepts of Chemistry", "Structure of Atom", "Chemical Bonding", "Thermodynamics", "Equilibrium"],
        "Biology": ["The Living World", "Cell: The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division", "Plant Physiology Basics"],
        "Maths": ["Sets", "Relations and Functions", "Complex Numbers", "Permutations and Combinations", "Limits and Derivatives"],
    },
    "12": {
        "Physics": ["Electric Charges and Fields", "Current Electricity", "Moving Charges and Magnetism", "EM Induction and AC", "Ray and Wave Optics"],
        "Chemistry": ["The Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics", "Surface Chemistry"],
        "Biology": ["Reproduction in Organisms", "Human Reproduction", "Principles of Inheritance and Variation", "Molecular Basis of Inheritance", "Evolution"],
        "Maths": ["Matrices", "Determinants", "Continuity and Differentiability", "Integrals", "Differential Equations"],
    },
}  # Tabs separate Learn vs Dashboard for clarity and navigation.


# ----------------------------- TTS (pyttsx3) -----------------------------
def generate_tts_bytes(
    text: str,
    voice_index: Optional[int] = None,
    rate: int = 175,
    volume: float = 1.0,
) -> Optional[bytes]:
    """
    Synthesize text into WAV bytes using pyttsx3.
    - voice_index: choose from available voices (0-based).
    - rate: speaking rate (words/min).
    - volume: float 0.0–1.0.
    Returns WAV bytes or None if synthesis fails.
    """
    if not text or not text.strip():
        return None
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", int(rate))
        engine.setProperty("volume", float(volume))
        voices = engine.getProperty("voices")
        if voice_index is not None and voices:
            idx = max(0, min(int(voice_index), len(voices) - 1))
            engine.setProperty("voice", voices[idx].id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()  # Flush and write the WAV.
        try:
            with open(tmp_path, "rb") as f:
                data = f.read()
            return data
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    except Exception:
        return None


def speak_in_streamlit(text: str, voice_index: Optional[int], rate: int, volume: float):
    audio = generate_tts_bytes(text, voice_index=voice_index, rate=rate, volume=volume)
    if audio:
        st.audio(audio, format="audio/wav")  # Inline playback for learners.


# ----------------------------- Badges & state -----------------------------
BADGE_LADDER = [(50, "💎 Diamond"), (30, "🥇 Gold"), (20, "🥈 Silver"), (10, "🥉 Bronze")]

def compute_badge(total: int) -> str:
    for threshold, name in BADGE_LADDER:
        if total >= threshold:
            return name
    return "No Badge Yet"

def init_state():
    s = st.session_state
    s.setdefault("name", "")
    s.setdefault("class_level", "10")
    s.setdefault("language", "English")
    s.setdefault("subject", "")
    s.setdefault("chapter", "")
    s.setdefault("part", 1)
    s.setdefault("messages", [])         # list[tuple(role, content)]
    s.setdefault("quiz_items", [])       # from parse_quiz_block()
    s.setdefault("quiz_score", 0)
    s.setdefault("quiz_total", 0)
    s.setdefault("quiz_count", 0)
    s.setdefault("progress", {})         # subject -> chapter -> {"score": x, "total": y}
    # TTS prefs
    s.setdefault("tts_voice_index", None)
    s.setdefault("tts_rate", 175)
    s.setdefault("tts_volume", 1.0)
    # Ollama URL
    s.setdefault("ollama_url", os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))

init_state()  # Persist chat and scores across reruns.


# ----------------------------- Sidebar -----------------------------
with st.sidebar:
    st.header("Dashboard")
    st.text_input("Name", key="name")
    st.selectbox("Class", options=list(SYLLABUS.keys()), key="class_level")
    st.selectbox(
        "Language",
        options=["English","Hindi","Bengali","Marathi","Gujarati","Tamil","Telugu","Kannada","Malayalam","Punjabi","Urdu"],
        key="language",
    )

    with st.expander("Voice & TTS"):
        try:
            _e = pyttsx3.init()
            _voices = _e.getProperty("voices")
            voice_labels = [f"{i}: {v.id}" for i, v in enumerate(_voices)]
        except Exception:
            _voices = []
            voice_labels = ["0: default"]
        st.selectbox(
            "Voice (by index)",
            options=["None (default)"] + voice_labels,
            key="tts_voice_label",
            help="Select a voice; default uses your system’s default TTS voice.",
        )
        if st.session_state.tts_voice_label and st.session_state.tts_voice_label != "None (default)":
            try:
                st.session_state.tts_voice_index = int(st.session_state.tts_voice_label.split(":"))
            except Exception:
                st.session_state.tts_voice_index = None
        else:
            st.session_state.tts_voice_index = None
        st.slider("Rate (words/min)", 80, 240, key="tts_rate")
        st.slider("Volume", 0.0, 1.0, key="tts_volume")

    st.divider()

    # Ollama connectivity
    st.subheader("Ollama")
    new_url = st.text_input("Ollama URL", value=st.session_state.ollama_url, help="e.g., http://127.0.0.1:11434")
    if new_url and new_url != st.session_state.ollama_url:
        st.session_state.ollama_url = new_url.strip()
    # Apply to process env so tutor_engine uses it
    os.environ["OLLAMA_HOST"] = st.session_state.ollama_url
    healthy = ensure_ollama_ready(st.session_state.ollama_url)
    if healthy:
        st.success("Ollama: Connected")
    else:
        st.error("Ollama: Not reachable. Start it and verify the URL.")

    st.divider()

    # Subject/Chapter cards
    cls = st.session_state.class_level
    subjects = list(SYLLABUS[cls].keys())

    st.subheader("Subjects")
    for subject in subjects:
        with st.container(border=True):
            if st.button(f"📘 {subject}", key=f"sub_{subject}", use_container_width=True):
                st.session_state.subject = subject
                st.session_state.chapter = ""
                st.session_state.part = 1

    if st.session_state.subject:
        st.subheader("Chapters")
        for ch in SYLLABUS[cls][st.session_state.subject]:
            with st.container(border=True):
                if st.button(f"📖 {ch}", key=f"chap_{ch}", use_container_width=True):
                    st.session_state.chapter = ch
                    st.session_state.part = 1
                    st.session_state.messages = []
                    st.session_state.quiz_items = []
                    with st.spinner("Generating lesson..."):
                        if not ensure_ollama_ready(st.session_state.ollama_url):
                            st.error("Cannot reach Ollama. Start it (e.g., `ollama run llama3.1:8b`) or fix the Ollama URL.")
                        else:
                            content = teach_part(
                                class_level=st.session_state.class_level,
                                subject=st.session_state.subject,
                                chapter=st.session_state.chapter,
                                part=st.session_state.part,
                                language=st.session_state.language,
                            )
                            st.session_state.messages.append(("assistant", content))
                            st.rerun()

    st.divider()
    if st.button("Clear Progress & Restart", type="primary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ----------------------------- Tabs -----------------------------
tab_learn, tab_dash = st.tabs(["Learn", "Dashboard"])  # Clean separation of doing vs. reviewing.


# ----------------------------- Learn tab -----------------------------
with tab_learn:
    st.title("📊 Dashboard")
    st.caption("Pick a subject and chapter on the left, then use the chat to say 'continue' for a quiz or 'next' to move on.")

    left, right = st.columns([2, 1], gap="large")

    with left:
        if st.session_state.subject and st.session_state.chapter:
            st.subheader(f"{st.session_state.subject}: {st.session_state.chapter} (Part {st.session_state.part})")
            st.divider()

            # Conversation history
            for role, content in st.session_state.messages[-12:]:
                with st.chat_message("assistant" if role == "assistant" else "user"):
                    st.markdown(content)

            # TTS button (reads last assistant message)
            if st.session_state.messages:
                if st.button("🔊 Read last explanation"):
                    for r, c in reversed(st.session_state.messages):
                        if r == "assistant":
                            speak_in_streamlit(
                                c,
                                voice_index=st.session_state.tts_voice_index,
                                rate=st.session_state.tts_rate,
                                volume=st.session_state.tts_volume,
                            )
                            break

            # Quick Quiz
            if st.session_state.quiz_items:
                st.subheader("Quick Quiz")
                answers: Dict[int, str] = {}

                def render_q(idx: int, qdict: Dict[str, Any]) -> Optional[str]:
                    st.markdown(f"Q{idx}. {qdict['question']}")  # LaTeX renders with \( … \)
                    if qdict.get("code"):
                        st.code(qdict["code"], language="python")
                    labels, mapping = [], {}
                    for letter in ["A", "B", "C"]:
                        opt_text = qdict.get("options", {}).get(letter, "").strip()
                        label = f"{letter}) {opt_text}" if opt_text else f"{letter})"
                        labels.append(label)
                        mapping[label] = letter
                    chosen_label = st.radio(
                        "Choose one",
                        options=labels,
                        key=f"quiz_{idx}",
                        label_visibility="collapsed",
                        horizontal=False,
                    )
                    return mapping.get(chosen_label)

                for idx, q in enumerate(st.session_state.quiz_items, start=1):
                    with st.container(border=True):
                        answers[idx] = render_q(idx, q)

                if st.button("Submit Quiz"):
                    score = 0
                    for idx, q in enumerate(st.session_state.quiz_items, start=1):
                        if answers.get(idx) == q["correct"]:
                            score += 1
                    st.success(f"Score: {score} / {len(st.session_state.quiz_items)}")

                    # Update stats
                    st.session_state.quiz_score += score
                    st.session_state.quiz_total += len(st.session_state.quiz_items)
                    st.session_state.quiz_count += 1

                    # Chapter accuracy
                    subj, chap = st.session_state.subject, st.session_state.chapter
                    st.session_state.progress.setdefault(subj, {}).setdefault(chap, {"score": 0, "total": 0})
                    st.session_state.progress[subj][chap]["score"] += score
                    st.session_state.progress[subj][chap]["total"] += len(st.session_state.quiz_items)

                    # Next part
                    st.session_state.quiz_items = []
                    st.session_state.part += 1
                    with st.spinner("Generating next lesson..."):
                        if not ensure_ollama_ready(st.session_state.ollama_url):
                            st.error("Cannot reach Ollama. Start it or fix the Ollama URL.")
                        else:
                            content = teach_part(
                                class_level=st.session_state.class_level,
                                subject=st.session_state.subject,
                                chapter=st.session_state.chapter,
                                part=st.session_state.part,
                                language=st.session_state.language,
                            )
                            st.session_state.messages.append(("assistant", content))
                            st.rerun()
        else:
            st.info("Pick a class, subject, and chapter from the sidebar to begin.")

    with right:
        st.subheader("Progress")
        c1, c2, c3 = st.columns(3)
        c1.metric("Quizzes", st.session_state.quiz_count)
        if st.session_state.quiz_total:
            acc = 100.0 * st.session_state.quiz_score / st.session_state.quiz_total
            c2.metric("Accuracy", f"{acc:.1f}%")
        else:
            c2.metric("Accuracy", "—")
        total = st.session_state.quiz_count
        c3.metric("Badge", compute_badge(total))
        st.divider()
        st.caption("Tips")
        st.write("• Say 'continue' or 'yes' for a short quiz on the current part.")
        st.write("• Say 'next' to move to the next part without a quiz.")
        st.write("• Ask follow‑ups like 'explain reflection again' for a recap.")

    # Bottom chat input (single, main area)
    user_msg = st.chat_input("Reply, ask, or say 'continue' for a quiz…")  # Chat input drives the flow.
    if user_msg and st.session_state.subject and st.session_state.chapter:
        st.session_state.messages.append(("user", user_msg))
        low = user_msg.lower().strip()

        if any(t in low for t in ["continue", "quiz", "yes", "ok", "next quiz"]):
            with st.spinner("Generating quiz..."):
                if not ensure_ollama_ready(st.session_state.ollama_url):
                    st.error("Cannot reach Ollama. Start it or fix the Ollama URL.")
                else:
                    qb = generate_quiz(
                        class_level=st.session_state.class_level,
                        subject=st.session_state.subject,
                        chapter=st.session_state.chapter,
                        part=st.session_state.part,
                        language=st.session_state.language,
                    )
                    items = parse_quiz_block(qb)
                    if not items:
                        st.warning("Could not parse a quiz. Please try again.")
                    else:
                        st.session_state.quiz_items = items

        elif "next" in low:
            st.session_state.part += 1
            with st.spinner("Generating lesson..."):
                if not ensure_ollama_ready(st.session_state.ollama_url):
                    st.error("Cannot reach Ollama. Start it or fix the Ollama URL.")
                else:
                    content = teach_part(
                        class_level=st.session_state.class_level,
                        subject=st.session_state.subject,
                        chapter=st.session_state.chapter,
                        part=st.session_state.part,
                        language=st.session_state.language,
                    )
                    st.session_state.messages.append(("assistant", content))
        else:
            with st.spinner("Explaining…"):
                if not ensure_ollama_ready(st.session_state.ollama_url):
                    st.error("Cannot reach Ollama. Start it or fix the Ollama URL.")
                else:
                    content = teach_part(
                        class_level=st.session_state.class_level,
                        subject=st.session_state.subject,
                        chapter=st.session_state.chapter,
                        part=st.session_state.part,
                        language=st.session_state.language,
                    )
                    st.session_state.messages.append(("assistant", content))
        st.rerun()


# ----------------------------- Dashboard tab -----------------------------
with tab_dash:
    st.title("📊 Dashboard")
    total_quizzes = st.session_state.quiz_count
    accuracy = (st.session_state.quiz_score / st.session_state.quiz_total * 100) if st.session_state.quiz_total else 0.0
    badge = compute_badge(total_quizzes)

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.metric("Quizzes Completed", total_quizzes)
    c2.metric("Overall Accuracy", f"{accuracy:.1f}%")
    c3.metric("Current Badge", badge)

    st.divider()
    st.subheader("Chapter‑wise Performance")
    if not st.session_state.progress:
        st.info("No quiz data yet — take a quiz from the Learn tab to populate your dashboard.")
    else:
        for subject in sorted(st.session_state.progress.keys()):
            st.markdown(f"### {subject}")
            for chapter, data in sorted(st.session_state.progress[subject].items()):
                sc = data.get("score", 0)
                tot = data.get("total", 0)
                acc = (sc / tot * 100) if tot else 0
                with st.container(border=True):
                    left, right = st.columns([3, 1])
                    with left:
                        st.markdown(f"**{chapter}**")
                        st.progress(acc / 100.0)
                    with right:
                        st.metric(label="Acc.", value=f"{acc:.1f}%")
