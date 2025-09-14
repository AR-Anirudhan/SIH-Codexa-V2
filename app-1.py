# app.py
# Project Codexa – AI Learning Platform (Fully Gamified Edition)
# Tabs: Learn | Quiz | Ask | Games (Sudoku) | Quests | Shop | Progress
# Features:
# - Animated UI, TTS
# - Doodle Map Quiz Adventure (forward on correct, backward on wrong; 80% gate)
# - Streaks: Daily streak + Correct-answer streak
# - Levels, Ranks, XP curve, Coins/Credits economy
# - Achievements and Badges
# - Quests: Daily/Weekly objectives with rewards
# - Avatars (doodle icons) and unlocks
# - Analytics: Activity heatmap, mastery heatmap, timeline
# - Sudoku mini-game

import os
import re
import time
import random
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import streamlit as st
import pyttsx3

# Optional Plotly (guarded)
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

# Tutor engine API (local/offline model wrapper)
from tutor_engine import teach_part, generate_quiz, parse_quiz_block, answer_question

# ----------------------------- Gamification constants -----------------------------
RANKS = [
    (0, "Rookie"), (100, "Apprentice"), (300, "Scholar"),
    (700, "Mentor"), (1200, "Master"), (2000, "Grandmaster"),
]
LEVEL_XP = [0, 100, 250, 450, 700, 1000, 1400, 1850, 2350, 2900, 3500, 4200]  # cumulative
AVATARS = ["🎒","🧠","🧭","🛡️","⚙️","🦉","🐱","🐶","🐧","🐉","🦊","🦄"]
DOODLE_TILES = ["🟨","🟦","🟪","🟩","🟧","🟫","⬜","⬛"]

ACHIEVEMENTS = [
    ("First Steps", "Complete 1 quiz", lambda ss: ss.quiz_count >= 1, "🥉", 25),
    ("Warming Up", "Reach 5 quizzes", lambda ss: ss.quiz_count >= 5, "🥈", 50),
    ("Quiz Pro", "Reach 20 quizzes", lambda ss: ss.quiz_count >= 20, "🥇", 100),
    ("Hot Streak", "Daily streak 5+", lambda ss: ss.daily_streak >= 5, "🔥", 50),
    ("Flawless", "Score 100% in a quiz", lambda ss: ss.last_quiz_pct == 100, "💯", 50),
    ("Marathon", "Answer 50 correct in total", lambda ss: ss.correct_total >= 50, "🏅", 75),
]

DAILY_QUESTS = [
    {"id": "q_daily_quiz", "name": "Daily Quizzer", "desc": "Complete 1 quiz today", "target": 1, "key": "daily_quizzes", "reward_xp": 20, "reward_coins": 5},
    {"id": "q_daily_correct", "name": "Sharp Mind", "desc": "Get 5 correct answers today", "target": 5, "key": "daily_correct", "reward_xp": 20, "reward_coins": 5},
]
WEEKLY_QUESTS = [
    {"id": "q_weekly_quizzes", "name": "Weekly Warrior", "desc": "Complete 10 quizzes this week", "target": 10, "key": "weekly_quizzes", "reward_xp": 100, "reward_coins": 25},
    {"id": "q_weekly_accuracy", "name": "Precision", "desc": "Achieve 80%+ in 3 quizzes this week", "target": 3, "key": "weekly_80plus", "reward_xp": 100, "reward_coins": 25},
]

SHOP_ITEMS = [
    {"id": "avatar_owl", "name": "Avatar: 🦉", "cost": 20, "type": "avatar", "value": "🦉"},
    {"id": "avatar_dragon", "name": "Avatar: 🐉", "cost": 40, "type": "avatar", "value": "🐉"},
    {"id": "credit_pack", "name": "Credit Pack (+3)", "cost": 15, "type": "credits", "value": 3},
]

# ----------------------------- Page config -----------------------------
st.set_page_config(
    page_title="Project Codexa - AI Learning Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- CSS -----------------------------
def load_custom_css(primary="#667eea", secondary="#764ba2"):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    .main {{ background: linear-gradient(135deg, #0f172a 0%, #111827 100%); min-height: 100vh; }}

    @keyframes gradient {{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
    @keyframes fadeInUp {{from{{opacity:0; transform:translateY(40px)}} to{{opacity:1; transform:translateY(0)}}}}
    @keyframes pulse {{0%{{transform:scale(1)}}50%{{transform:scale(1.05)}}100%{{transform:scale(1)}}}}

    .main-header {{
        background: linear-gradient(135deg, {primary} 0%, {secondary} 100%);
        background-size: 400% 400%; animation: gradient 15s ease infinite;
        padding: 2.5rem 2rem; text-align: center; margin-bottom: 1rem;
        border-radius: 0 0 36px 36px; box-shadow: 0 16px 40px rgba(0,0,0,0.35); color: white;
    }}
    .main-title {{ font-family: 'Poppins',sans-serif; font-size: 3.0rem; font-weight: 900; margin-bottom: .25rem; }}
    .header-stats {{ display:flex; justify-content:center; gap:1rem; flex-wrap:wrap; margin-top:1rem; }}
    .header-stat {{ background: rgba(255,255,255,0.15); backdrop-filter: blur(16px); padding:.6rem 1.2rem;
                   border-radius:999px; font-weight:700; border:1px solid rgba(255,255,255,0.25); }}
    .header-avatar {{ font-size: 2.0rem; padding: .2rem .8rem; background:rgba(255,255,255,0.15); border-radius: 14px; }}

    .learning-card, .game-card, .quiz-card {{
        background:#0b1220; border:1px solid rgba(255,255,255,0.06);
        border-radius:20px; padding:1.25rem; margin-bottom:1rem;
        box-shadow:0 12px 30px rgba(0,0,0,0.35); animation: fadeInUp .6s ease; color:#e5e7eb; position:relative;
    }}
    .learning-card::before, .quiz-card::before {{
        content:''; position:absolute; top:0; left:0; right:0; height:4px;
        background: linear-gradient(90deg, {primary}, {secondary}); background-size:300% 100%;
        animation: gradient 8s ease infinite; border-radius:20px 20px 0 0;
    }}

    .stats-card {{ background:#0b1220; border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:1.0rem;
                  text-align:center; color:#e5e7eb; }}
    .credits-display {{ background:linear-gradient(135deg,#f59e0b,#f97316); color:white; border-radius:16px; padding:1rem 1.25rem;
                        font-weight:800; text-align:center; box-shadow:0 12px 28px rgba(249,115,22,0.35); }}
    .xp-display {{ background:linear-gradient(135deg,#10b981,#059669); color:white; border-radius:16px; padding:1rem 1.25rem;
                   font-weight:800; text-align:center; box-shadow:0 12px 28px rgba(16,185,129,0.35); }}

    .success-animation {{ background:linear-gradient(135deg,#10b981,#059669); color:white; border-radius:16px; padding:1.1rem;
                          text-align:center; animation:pulse .8s ease; }}
    .error-card {{ background:linear-gradient(135deg,#ef4444,#dc2626); color:white; border-radius:16px; padding:1.1rem; text-align:center; }}
    .warning-card {{ background:linear-gradient(135deg,#f59e0b,#d97706); color:white; border-radius:16px; padding:1.1rem; text-align:center; }}

    /* Sudoku: compact grid */
    .sudoku-grid {{ display:grid; grid-template-columns: repeat(9, 1fr); gap: 4px; width:100%; max-width: 420px; margin: 0 auto; }}
    .sudoku-cell-wrap {{ aspect-ratio: 1 / 1; position: relative; }}
    .sudoku-box {{
        display:flex; align-items:center; justify-content:center; width:100%; height:100%;
        font-weight:800; font-size:18px; background:#111827; border:2px solid #334155; color:#e5e7eb; border-radius:6px;
    }}
    .sudoku-input {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
        background:#0f172a; border:2px solid #334155; border-radius:6px; }}
    .sudoku-input input {{
        text-align:center !important; font-weight:800 !important; font-size:18px !important; background:transparent !important; color:#e5e7eb !important;
    }}
    .sudoku-block-r {{ border-right: 3px solid #475569 !important; }}
    .sudoku-block-b {{ border-bottom: 3px solid #475569 !important; }}

    @media (max-width: 768px) {{ .main-title {{ font-size: 2.2rem; }} }}
    </style>
    """, unsafe_allow_html=True)

load_custom_css()

# ----------------------------- Syllabus -----------------------------
SYLLABUS = {
    "6": {"Maths": ["Number System Basics","Fractions and Decimals","Ratio and Proportion","Basic Geometry","Mensuration"],
          "Science": ["Food: Where Does It Come From?","Components of Food","Separation of Substances","Sorting Materials","Motion and Measurement of Distances"]},
    "7": {"Maths": ["Integers","Fractions and Decimals","Simple Equations","Lines and Angles","Perimeter and Area"],
          "Science": ["Nutrition in Plants","Nutrition in Animals","Heat","Acids, Bases and Salts","Physical and Chemical Changes"]},
    "8": {"Maths": ["Rational Numbers","Squares and Square Roots","Cubes and Cube Roots","Linear Equations in One Variable","Mensuration"],
          "Science": ["Crop Production and Management","Materials: Metals and Non-metals","Force and Pressure","Friction","Sound","Light"]},
    "9": {"Physics": ["Motion","Force and Laws of Motion","Gravitation","Work and Energy","Sound"],
          "Chemistry": ["Matter in Our Surroundings","Is Matter Around Us Pure","Atoms and Molecules","Structure of the Atom"],
          "Biology": ["The Fundamental Unit of Life","Tissues","Diversity in Living Organisms","Why Do We Fall Ill","Natural Resources"],
          "Maths": ["Number Systems","Polynomials","Coordinate Geometry","Linear Equations in Two Variables","Triangles","Statistics","Probability"]},
    "10": {"Physics": ["Light - Reflection and Refraction","Human Eye and Colourful World","Electricity","Magnetic Effects of Electric Current","Sources of Energy"],
           "Chemistry": ["Chemical Reactions and Equations","Acids, Bases and Salts","Metals and Non-metals","Carbon and its Compounds","Periodic Classification of Elements"],
           "Biology": ["Life Processes","Control and Coordination","How do Organisms Reproduce?","Heredity and Evolution","Our Environment"],
           "Maths": ["Real Numbers","Polynomials","Pair of Linear Equations in Two Variables","Quadratic Equations","Trigonometry Basics","Statistics","Probability"]},
    "11": {"Physics": ["Units and Measurements","Motion in a Straight Line","Laws of Motion","Work, Energy and Power","Waves"],
           "Chemistry": ["Some Basic Concepts of Chemistry","Structure of Atom","Chemical Bonding","Thermodynamics","Equilibrium"],
           "Biology": ["The Living World","Cell: The Unit of Life","Biomolecules","Cell Cycle and Cell Division","Plant Physiology Basics"],
           "Maths": ["Sets","Relations and Functions","Complex Numbers","Permutations and Combinations","Limits and Derivatives"]},
    "12": {"Physics": ["Electric Charges and Fields","Current Electricity","Moving Charges and Magnetism","EM Induction and AC","Ray and Wave Optics"],
           "Chemistry": ["The Solid State","Solutions","Electrochemistry","Chemical Kinetics","Surface Chemistry"],
           "Biology": ["Reproduction in Organisms","Human Reproduction","Principles of Inheritance and Variation","Molecular Basis of Inheritance","Evolution"],
           "Maths": ["Matrices","Determinants","Continuity and Differentiability","Integrals","Differential Equations"]},
}
SUBJECT_ICONS = {"Maths":"🔢","Science":"🔬","Physics":"⚛️","Chemistry":"🧪","Biology":"🧬"}

# ----------------------------- Sudoku -----------------------------
def generate_sudoku():
    base = 3; side = base * base
    def pattern(r,c): return (base*(r%base)+r//base+c) % side
    def shuffle(s): return random.sample(s, len(s))
    rBase = range(base)
    rows = [g*base+r for g in shuffle(rBase) for r in shuffle(rBase)]
    cols = [g*base+c for g in shuffle(rBase) for c in shuffle(rBase)]
    nums = shuffle(range(1, side+1))
    board = [[nums[pattern(r,c)] for c in cols] for r in rows]
    squares = side*side; empties = squares*3//5
    for _ in range(empties):
        r = random.randint(0, side-1); c = random.randint(0, side-1)
        board[r][c] = 0
    return board

def validate_sudoku(board: List[List[int]]) -> bool:
    def valid_group(group):
        group = [x for x in group if x != 0]
        return len(group) == len(set(group)) and all(1 <= x <= 9 for x in group)
    for row in board:
        if not valid_group(row): return False
    for c in range(9):
        if not valid_group([board[r][c] for r in range(9)]): return False
    for br in range(3):
        for bc in range(3):
            box = [board[r][c] for r in range(br*3, br*3+3) for c in range(bc*3, bc*3+3)]
            if not valid_group(box): return False
    return True

def render_sudoku_game():
    st.markdown('<h3 style="text-align:center;">🎮 Sudoku Challenge</h3>', unsafe_allow_html=True)
    if 'sudoku_games_played' not in st.session_state:
        st.session_state.sudoku_games_played = 0
    if st.session_state.game_credits <= 0:
        st.markdown("""
        <div class="game-card"><div style="text-align:center;">
            <h4 style="color:#fecaca;">🚫 Insufficient Credits</h4>
            <p>You need at least 1 credit to play Sudoku.</p>
            <div class="stats-card" style="margin-top:10px;">
                <b>Earn credits:</b><br>• Complete a quiz: +1<br>• Complete a chapter: +3<br>• Perfect quiz: +1 bonus
            </div>
        </div></div>
        """, unsafe_allow_html=True)
        return
    if 'current_sudoku' not in st.session_state:
        st.session_state.current_sudoku = generate_sudoku()
        st.session_state.sudoku_user_input = [[0 for _ in range(9)] for _ in range(9)]
        st.session_state.sudoku_started = False

    st.markdown('<div class="game-card" style="text-align:center;"><p><b>Cost:</b> 1 Credit • <b>Reward:</b> +10 XP + Credit Refund on Win</p></div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("🎲 New Game"):
            st.session_state.current_sudoku = generate_sudoku()
            st.session_state.sudoku_user_input = [[0 for _ in range(9)] for _ in range(9)]
            st.session_state.sudoku_started = False; st.rerun()
    with c2:
        if not st.session_state.sudoku_started:
            if st.button("🎯 Start"):
                if st.session_state.game_credits > 0:
                    st.session_state.game_credits -= 1
                    st.session_state.sudoku_started = True
                    st.success("Game started! 1 credit deducted."); st.rerun()
                else:
                    st.error("Not enough credits!")
        else:
            if st.button("🔍 Check"):
                combined = []
                for i in range(9):
                    row = []
                    for j in range(9):
                        row.append(st.session_state.current_sudoku[i][j] or st.session_state.sudoku_user_input[i][j])
                    combined.append(row)
                if any(0 in r for r in combined):
                    st.markdown('<div class="warning-card">⚠️ Fill all cells before checking.</div>', unsafe_allow_html=True)
                elif validate_sudoku(combined):
                    st.markdown('<div class="success-animation"><b>🎉 Correct! +10 XP & credit refunded.</b></div>', unsafe_allow_html=True)
                    st.balloons()
                    st.session_state.total_xp += 10; st.session_state.game_credits += 1
                    st.session_state.sudoku_wins = st.session_state.get('sudoku_wins', 0) + 1
                    st.session_state.sudoku_started = False
                    st.session_state.sudoku_games_played += 1; st.rerun()
                else:
                    st.markdown('<div class="error-card">❌ Incorrect solution, try again!</div>', unsafe_allow_html=True)
    with c3:
        if st.button("💡 Hint"):
            if st.session_state.sudoku_started:
                empties = [(i,j) for i in range(9) for j in range(9)
                           if st.session_state.current_sudoku[i][j] == 0 and st.session_state.sudoku_user_input[i][j] == 0]
                if empties:
                    i,j = random.choice(empties); st.info(f"Focus on row {i+1}, column {j+1}.")
                else:
                    st.info("Board seems full, try Check.")
            else:
                st.info("Start the game to get hints.")
    with c4:
        if st.button("🔄 Reset Inputs"):
            if st.session_state.sudoku_started:
                st.session_state.sudoku_user_input = [[0 for _ in range(9)] for _ in range(9)]
                st.success("Inputs reset."); st.rerun()

    if st.session_state.sudoku_started:
        st.markdown("### 🎯 Sudoku Grid")
        for i in range(9):
            cols = st.columns(9, gap="small")
            for j in range(9):
                right_block = " sudoku-block-r" if j in (2, 5) else ""
                bottom_block = " sudoku-block-b" if i in (2, 5) else ""
                with cols[j]:
                    st.markdown(f'<div class="sudoku-cell-wrap{right_block}{bottom_block}">', unsafe_allow_html=True)
                    val = st.session_state.current_sudoku[i][j]
                    if val != 0:
                        st.markdown(f'<div class="sudoku-box{right_block}{bottom_block}">{val}</div>', unsafe_allow_html=True)
                    else:
                        v = st.number_input(" ", min_value=0, max_value=9,
                                            value=st.session_state.sudoku_user_input[i][j],
                                            key=f"sudoku_{i}_{j}", label_visibility="collapsed", step=1)
                        st.session_state.sudoku_user_input[i][j] = v
                        st.markdown('<div class="sudoku-input"></div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

        filled = sum(1 for i in range(9) for j in range(9)
                     if st.session_state.current_sudoku[i][j] != 0 or st.session_state.sudoku_user_input[i][j] != 0)
        st.progress(min(filled/81, 1.0), text=f"Progress: {filled}/81")

    st.markdown("---")
    k1,k2,k3 = st.columns(3)
    with k1:
        st.markdown(f'<div class="stats-card"><h2>{st.session_state.get("sudoku_wins",0)}</h2><p>🏆 Wins</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="stats-card"><h2>{st.session_state.get("sudoku_games_played",0)}</h2><p>🎮 Played</p></div>', unsafe_allow_html=True)
    with k3:
        played = st.session_state.get("sudoku_games_played", 0); wins = st.session_state.get("sudoku_wins", 0)
        wr = (wins/played*100) if played else 0
        st.markdown(f'<div class="stats-card"><h2>{wr:.1f}%</h2><p>📈 Win Rate</p></div>', unsafe_allow_html=True)

# ----------------------------- TTS (hardened) -----------------------------
def generate_tts_bytes(text: str, voice_index: Optional[int] = None, rate: int = 175, volume: float = 1.0) -> Optional[bytes]:
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

        clean_text = re.sub(r'\$.*?\$', '', text)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
        engine.save_to_file(clean_text, tmp_path)
        engine.runAndWait()

        data = None
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 44:
            with open(tmp_path, "rb") as f:
                data = f.read()
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return data
    except Exception:
        return None

def speak_in_streamlit(text: str, voice_index: Optional[int], rate: int, volume: float):
    audio = generate_tts_bytes(text, voice_index=voice_index, rate=rate, volume=volume)
    if audio:
        st.audio(audio, format="audio/wav")
    else:
        st.warning("TTS audio could not be generated. Try another voice or adjust rate/volume.")

# ----------------------------- Badges & Levels -----------------------------
BADGE_LADDER = [(100,"💎 Diamond Master"),(50,"💎 Diamond"),(30,"🥇 Gold"),(20,"🥈 Silver"),(10,"🥉 Bronze"),(5,"⭐ Rising Star")]
def compute_badge(total: int) -> str:
    for threshold, name in BADGE_LADDER:
        if total >= threshold: return name
    return "🌟 Novice"

def compute_rank(xp: int) -> str:
    r = "Rookie"
    for threshold, name in RANKS:
        if xp >= threshold:
            r = name
    return r

def compute_level(xp: int) -> int:
    lvl = 1
    for i, cxp in enumerate(LEVEL_XP):
        if xp >= cxp:
            lvl = i + 1
    return min(lvl, len(LEVEL_XP))

# ----------------------------- State & Progress helpers -----------------------------
def init_state():
    defaults = dict(
        name="", class_level="10", language="English", subject="", chapter="", part=1,
        messages=[], quiz_items=[], quiz_score=0, quiz_total=0, quiz_count=0, progress={},
        tts_voice_index=None, tts_rate=175, tts_volume=1.0,
        game_credits=3, total_xp=0, coins=0,
        sudoku_wins=0, sudoku_games_played=0, chapters_completed=[],
        history=[], last_lesson="", show_lesson=False,
        # Gamified
        avatar=AVATARS[0], unlocked_avatars=set([AVATARS[0]]),
        daily_streak=0, last_active_date=None,
        correct_streak=0, correct_total=0, last_quiz_pct=0.0,
        quests_daily_progress={"daily_quizzes":0,"daily_correct":0,"reset_date":datetime.utcnow().date()},
        quests_weekly_progress={"weekly_quizzes":0,"weekly_80plus":0,"week_start":datetime.utcnow().date()},
        # Quiz map
        quiz_map_position=0, quiz_map_total_questions=0, quiz_map_correct=0, quiz_map_qindex=0,
        quiz_map_anim="idle", quiz_map_done=False, quiz_map_answers={}
    )
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    # Sets in session_state must be cast from list if restored
    if isinstance(st.session_state.unlocked_avatars, list):
        st.session_state.unlocked_avatars = set(st.session_state.unlocked_avatars)

init_state()

def touch_daily_streak():
    today = datetime.utcnow().date()
    last = st.session_state.last_active_date
    if last is None:
        st.session_state.daily_streak = 1
    else:
        diff = (today - last).days
        if diff == 1:
            st.session_state.daily_streak += 1
        elif diff > 1:
            st.session_state.daily_streak = 1
    st.session_state.last_active_date = today

def update_quests(progress_key: str, inc: int = 1, is_80plus: bool = False):
    today = datetime.utcnow().date()
    # reset daily
    if st.session_state.quests_daily_progress.get("reset_date") != today:
        st.session_state.quests_daily_progress = {"daily_quizzes":0,"daily_correct":0,"reset_date":today}
    st.session_state.quests_daily_progress[progress_key] = st.session_state.quests_daily_progress.get(progress_key, 0) + inc

    # reset weekly (weeks start on Monday)
    week_start = st.session_state.quests_weekly_progress.get("week_start")
    if week_start is None or (today - week_start).days >= 7:
        st.session_state.quests_weekly_progress = {"weekly_quizzes":0,"weekly_80plus":0,"week_start":today}
    if progress_key == "daily_quizzes":
        st.session_state.quests_weekly_progress["weekly_quizzes"] += inc
        if is_80plus:
            st.session_state.quests_weekly_progress["weekly_80plus"] += 1
    if progress_key == "daily_correct":
        # counted individually as correct answers; weekly not tied to this metric
        pass

def grant_quest_rewards(completed_ids: List[str]) -> None:
    # Award rewards for newly completed quests
    for q in DAILY_QUESTS + WEEKLY_QUESTS:
        if q["id"] in completed_ids:
            st.session_state.total_xp += q["reward_xp"]
            st.session_state.coins += q["reward_coins"]

def check_achievements() -> List[str]:
    newly = []
    for title, desc, cond, emoji, xp in ACHIEVEMENTS:
        key = f"ach_{title}"
        if not st.session_state.get(key) and cond(st.session_state):
            st.session_state[key] = True
            st.session_state.total_xp += xp
            newly.append(f"{emoji} {title} (+{xp} XP)")
    return newly

def compute_learning_progress() -> dict:
    part_now = st.session_state.get("part", 1)
    part_pct = max(0, min(100, int((part_now - 1) / 5 * 100)))
    total_chapters = 0
    completed_chapters = 0
    for subject, chapters in st.session_state.progress.items():
        for chapter, data in chapters.items():
            total_chapters += 1
            total = max(1, data.get("total", 0))
            acc = (data.get("score", 0) / total) * 100 if total > 0 else 0
            if acc >= 70: completed_chapters += 1
    chapter_pct = int((completed_chapters / total_chapters) * 100) if total_chapters > 0 else 0
    return dict(part_pct=part_pct, chapter_pct=chapter_pct, completed_chapters=completed_chapters, total_chapters=total_chapters)

def format_rank_level():
    rank = compute_rank(st.session_state.total_xp)
    level = compute_level(st.session_state.total_xp)
    return rank, level

# ----------------------------- Header -----------------------------
touch_daily_streak()
rank, level = format_rank_level()
st.markdown(f"""
<div class="main-header">
  <h1 class="main-title">🚀 Project Codexa</h1>
  <div class="main-subtitle">Personalized Learning Hub</div>
  <div class="header-stats">
    <span class="header-stat">⚡ {st.session_state.total_xp} XP • Lv {level}</span>
    <span class="header-stat">🎖️ {rank}</span>
    <span class="header-stat">🔥 {st.session_state.daily_streak} Day Streak</span>
    <span class="header-stat">💰 {st.session_state.game_credits} Credits</span>
    <span class="header-stat">🪙 {st.session_state.coins} Coins</span>
    <span class="header-avatar">{st.session_state.avatar}</span>
  </div>
</div>
""", unsafe_allow_html=True)

prog = compute_learning_progress()
pg1, pg2 = st.columns([3, 2])
with pg1:
    st.markdown("**📚 Chapter Progress**")
    st.progress(prog["chapter_pct"], text=f"{prog['completed_chapters']}/{prog['total_chapters']} chapters • {prog['chapter_pct']}%")
with pg2:
    st.markdown("**🧩 Part Progress (current chapter)**")
    st.progress(prog["part_pct"], text=f"Part {st.session_state.part}/5 • {prog['part_pct']}%")

# ----------------------------- Sidebar -----------------------------
with st.sidebar:
    st.markdown("## 👤 Profile")
    st.session_state.name = st.text_input("Your Name", value=st.session_state.name)
    st.session_state.class_level = st.selectbox("Class", options=list(SYLLABUS.keys()),
                                                index=list(SYLLABUS.keys()).index(st.session_state.class_level))
    st.session_state.language = st.selectbox(
        "Language",
        options=["English","Hindi","Telugu","Tamil","Bengali","Gujarati","Kannada","Marathi","Malayalam","Punjabi","Odia","Urdu","Assamese"],
        index=0
    )
    st.markdown("---")
    st.markdown(f'<div class="credits-display">💰 Credits: {st.session_state.game_credits}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="xp-display" style="margin-top:8px;">⚡ XP: {st.session_state.total_xp}</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("## 📚 Study Selection")
    if st.session_state.class_level in SYLLABUS:
        subjects = list(SYLLABUS[st.session_state.class_level].keys())
        subject = st.selectbox("Choose Subject", options=[""]+subjects,
            format_func=lambda x: f"{SUBJECT_ICONS.get(x,'📖')} {x}" if x else "Select a subject",
            index=0 if not st.session_state.subject or st.session_state.subject not in subjects
                   else subjects.index(st.session_state.subject)+1)
        if subject:
            st.session_state.subject = subject
            chapters = SYLLABUS[st.session_state.class_level][subject]
            chapter = st.selectbox("Choose Chapter", options=[""]+chapters,
                index=0 if not st.session_state.chapter or st.session_state.chapter not in chapters
                       else chapters.index(st.session_state.chapter)+1)
            if chapter:
                st.session_state.chapter = chapter
                st.session_state.part = st.slider("Select Part", 1, 5, st.session_state.part)
    st.markdown("---")
    with st.expander("🎭 Avatar"):
        av = st.selectbox("Choose Avatar", AVATARS, index=AVATARS.index(st.session_state.avatar) if st.session_state.avatar in AVATARS else 0)
        if av in st.session_state.unlocked_avatars:
            if av != st.session_state.avatar and st.button("Set Avatar"):
                st.session_state.avatar = av; st.success("Avatar updated!")
        else:
            st.info("Locked. Unlock via Shop or Achievements.")
    with st.expander("🔊 Text-to-Speech"):
        st.session_state.tts_voice_index = st.selectbox("Voice", [None,0,1], index=0)
        st.session_state.tts_rate = st.slider("Rate", 100, 300, st.session_state.tts_rate)
        st.session_state.tts_volume = st.slider("Volume", 0.0, 1.0, st.session_state.tts_volume)

# ----------------------------- Tabs -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📖 Learn","🧠 Quiz","💬 Ask","🎮 Games","🗺️ Quests","🛒 Shop","📊 Progress"])

# ----------------------------- Learn Tab -----------------------------
with tab1:
    st.markdown("## 📖 Learning Section")
    st.markdown("### 🚀 Your Progress")
    st.progress(prog["part_pct"], text=f"Part {st.session_state.part}/5 • {prog['part_pct']}%")

    if st.session_state.subject and st.session_state.chapter:
        st.markdown(f"""
        <div class="learning-card">
          <h4>📚 Ready to Learn?</h4>
          <p><b>Subject:</b> {SUBJECT_ICONS.get(st.session_state.subject,'📖')} {st.session_state.subject}</p>
          <p><b>Class:</b> {st.session_state.class_level}</p>
          <p><b>Chapter:</b> {st.session_state.chapter}</p>
          <p><b>Part:</b> {st.session_state.part} of 5</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"🚀 Start / Regenerate: Part {st.session_state.part}", type="primary", key="start_learn"):
            with st.spinner("Preparing your personalized lesson..."):
                lesson = teach_part(st.session_state.class_level, st.session_state.subject,
                                    st.session_state.chapter, st.session_state.part, st.session_state.language)
            st.session_state.last_lesson = lesson
            st.session_state.show_lesson = True
            st.rerun()

        if st.session_state.get("show_lesson") and st.session_state.get("last_lesson"):
            st.markdown(f"""
            <div class="learning-card">
              <h4>📚 {st.session_state.subject} - Class {st.session_state.class_level}</h4>
              <p>Chapter: {st.session_state.chapter} (Part {st.session_state.part})</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(st.session_state.last_lesson)

            c1,c2 = st.columns(2)
            with c1:
                if st.button("🔊 Listen to Lesson", key="listen_lesson"):
                    speak_in_streamlit(
                        st.session_state.get("last_lesson",""),
                        st.session_state.tts_voice_index,
                        st.session_state.tts_rate,
                        st.session_state.tts_volume
                    )
            with c2:
                st.info("Tip: Take a quiz from the next tab after reading.")

        st.markdown("---")
        n1, n2, n3 = st.columns(3)
        with n1:
            if st.button("⬅️ Previous Part", key="prev_part") and st.session_state.part > 1:
                st.session_state.part = max(1, st.session_state.part - 1)
                st.session_state.show_lesson = False
                st.rerun()
        with n2:
            st.markdown(f"<p style='text-align:center;'>Part {st.session_state.part} of 5</p>", unsafe_allow_html=True)
        with n3:
            if st.button("➡️ Next Part", key="next_part") and st.session_state.part < 5:
                st.session_state.part = min(5, st.session_state.part + 1)
                st.session_state.show_lesson = False
                st.rerun()
    else:
        st.info("👈 Select subject and chapter from the sidebar to begin.")

# ----------------------------- Quiz Adventure Helpers -----------------------------
def initialize_quiz_map_state():
    ss = st.session_state
    defaults = dict(
        quiz_map_position=0,
        quiz_map_total_questions=0,
        quiz_map_correct=0,
        quiz_map_qindex=0,
        quiz_map_anim="idle",   # idle | fwd | back | celebrate
        quiz_map_done=False,
        quiz_map_answers={}
    )
    for k, v in defaults.items():
        if k not in ss:
            ss[k] = v

def doodle_tile(i: int) -> str:
    return DOODLE_TILES[i % len(DOODLE_TILES)]

def render_quiz_map(total_q: int, pos: int, qidx: int, anim: str) -> None:
    trail_len = total_q + 2  # 0=start, last=finish
    icon = {"idle":"🚀","fwd":"✨","back":"💫","celebrate":"🎉"}.get(anim, "🚀")

    tiles = []
    for i in range(trail_len):
        if i == 0:
            label = "🏁"
        elif i == trail_len - 1:
            label = "🏆"
        else:
            # doodle label: tile + number
            label = f"{doodle_tile(i)} {i}"
        here = (i == pos)
        active = i <= pos
        bg = "#4CAF50" if active and i != pos else ("#2196F3" if here else "#374151")
        if here and anim == "back":
            bg = "#ef4444"
        tile = (
            '<div style="position:relative;width:54px;height:54px;margin:0 6px;border-radius:14px;'
            'display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;'
            f'background:{bg};box-shadow:0 6px 18px rgba(0,0,0,.25);font-size:12px;">' + label +
            (f'<div style="position:absolute;top:-26px;font-size:20px;">{icon}</div>' if here else "") +
            "</div>"
        )
        tiles.append(tile)
        if i < trail_len-1:
            arrow_color = "#10b981" if i < pos else "#6b7280"
            tiles.append(f'<div style="color:{arrow_color};font-size:18px;">→</div>')

    inner = ''.join(tiles)
    html = (
        '<div style="display:flex;justify-content:center;margin:14px 0;">'
        '<div style="display:flex;align-items:center;background:linear-gradient(90deg,#667eea,#764ba2);'
        'padding:14px;border-radius:16px;box-shadow:0 8px 22px rgba(0,0,0,.35);">'
        + inner +
        '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    acc = 0
    if qidx > 0:
        acc = int(100 * st.session_state.quiz_map_correct / max(1, qidx))
    st.markdown(
        f"<p style='text-align:center;color:#cbd5e1;'>Question {qidx}/{total_q} • Position {pos}/{trail_len-1} • Accuracy {acc}%</p>",
        unsafe_allow_html=True
    )

def apply_answer_and_move(is_correct: bool, qidx: int):
    ss = st.session_state
    if is_correct:
        ss.quiz_map_position = min(ss.quiz_map_position + 1, ss.quiz_map_total_questions + 1)
        ss.quiz_map_correct += 1
        ss.quiz_map_anim = "fwd"
        ss.total_xp += 5
        ss.correct_streak += 1
        ss.correct_total += 1
        update_quests("daily_correct", 1)
    else:
        ss.quiz_map_position = max(0, ss.quiz_map_position - 1)
        ss.quiz_map_anim = "back"
        ss.correct_streak = 0
    ss.quiz_map_qindex = qidx + 1

def check_completion_gate() -> tuple[bool,str]:
    ss = st.session_state
    if ss.quiz_map_qindex >= ss.quiz_map_total_questions and not ss.quiz_map_done:
        accuracy = 100.0 * ss.quiz_map_correct / max(1, ss.quiz_map_total_questions)
        ss.last_quiz_pct = accuracy
        # weekly quest 80%+
        update_quests("daily_quizzes", 1, is_80plus=accuracy >= 80.0)
        if accuracy >= 80.0:
            ss.quiz_map_done = True
            ss.quiz_map_anim = "celebrate"
            ss.total_xp += 25
            ss.game_credits += 1
            ss.coins += 5
            # cumulative stats
            ss.quiz_score += ss.quiz_map_correct
            ss.quiz_total += ss.quiz_map_total_questions
            ss.quiz_count += 1
            subj, chap = ss.subject, ss.chapter
            ss.progress.setdefault(subj, {}).setdefault(chap, {"score":0,"total":0})
            ss.progress[subj][chap]["score"] += ss.quiz_map_correct
            ss.progress[subj][chap]["total"] += ss.quiz_map_total_questions
            # history
            ss.history.append({
                "date": pd.Timestamp("today").normalize().strftime("%Y-%m-%d"),
                "subject": subj, "chapter": chap,
                "score": ss.quiz_map_correct, "total": ss.quiz_map_total_questions,
                "xp": 25 + 5*ss.quiz_map_correct
            })
            # achievements
            newly = check_achievements()
            if newly:
                st.success("Achievements unlocked: " + ", ".join(newly))
            return True, f"🎉 Great job! {accuracy:.0f}% achieved. +25 XP, +1 Credit, +5 Coins"
        else:
            # still record quiz attempt
            ss.quiz_score += ss.quiz_map_correct
            ss.quiz_total += ss.quiz_map_total_questions
            ss.quiz_count += 1
            subj, chap = ss.subject, ss.chapter
            ss.progress.setdefault(subj, {}).setdefault(chap, {"score":0,"total":0})
            ss.progress[subj][chap]["score"] += ss.quiz_map_correct
            ss.progress[subj][chap]["total"] += ss.quiz_map_total_questions
            ss.history.append({
                "date": pd.Timestamp("today").normalize().strftime("%Y-%m-%d"),
                "subject": subj, "chapter": chap,
                "score": ss.quiz_map_correct, "total": ss.quiz_map_total_questions,
                "xp": 5*ss.quiz_map_correct
            })
            newly = check_achievements()
            if newly:
                st.success("Achievements unlocked: " + ", ".join(newly))
            return False, f"📚 You scored {accuracy:.0f}%. Need at least 80% to move forward. Retry!"
    return False, ""

# ----------------------------- Quiz Tab (Doodle Map Adventure) -----------------------------
with tab2:
    st.markdown("## 🧠 Quiz Adventure")
    initialize_quiz_map_state()
    if st.session_state.subject and st.session_state.chapter:
        if st.button(f"🎯 Start Quiz Adventure: Part {st.session_state.part}", type="primary", key="gen_quiz"):
            with st.spinner("Creating your quiz adventure..."):
                quiz_text = generate_quiz(
                    st.session_state.class_level,
                    st.session_state.subject,
                    st.session_state.chapter,
                    st.session_state.part,
                    st.session_state.language
                )
                st.session_state.quiz_items = parse_quiz_block(quiz_text)

            st.session_state.quiz_map_total_questions = len(st.session_state.quiz_items)
            st.session_state.quiz_map_position = 0
            st.session_state.quiz_map_correct = 0
            st.session_state.quiz_map_qindex = 0
            st.session_state.quiz_map_anim = "idle"
            st.session_state.quiz_map_done = False
            st.session_state.quiz_map_answers = {}
            st.rerun()

        if st.session_state.quiz_items:
            st.markdown(f"""
                <div class='quiz-card'>
                  <h4>🗺️ Quiz Adventure Map</h4>
                  <p><b>Subject:</b> {st.session_state.subject} • <b>Chapter:</b> {st.session_state.chapter} (Part {st.session_state.part})</p>
                  <p><b>Questions:</b> {len(st.session_state.quiz_items)} • <b>Required:</b> 80%+</p>
                </div>
            """, unsafe_allow_html=True)

            render_quiz_map(
                st.session_state.quiz_map_total_questions,
                st.session_state.quiz_map_position,
                st.session_state.quiz_map_qindex,
                st.session_state.quiz_map_anim
            )
            if st.session_state.quiz_map_anim in ("fwd", "back"):
                st.session_state.quiz_map_anim = "idle"

            done, msg = check_completion_gate()
            if done:
                st.success(msg)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔄 Retry Quiz"):
                        for k in list(st.session_state.keys()):
                            if k.startswith("quiz_map_") or k in ("quiz_items",):
                                del st.session_state[k]
                        st.rerun()
                with c2:
                    if st.button("➡️ Next Part"):
                        if st.session_state.part < 5:
                            st.session_state.part += 1
                        for k in list(st.session_state.keys()):
                            if k.startswith("quiz_map_") or k in ("quiz_items",):
                                del st.session_state[k]
                        st.rerun()
            elif msg:
                st.warning(msg)
                if st.button("🔄 Retry Quiz"):
                    for k in list(st.session_state.keys()):
                        if k.startswith("quiz_map_") or k in ("quiz_items",):
                            del st.session_state[k]
                    st.rerun()

            if st.session_state.quiz_map_qindex < len(st.session_state.quiz_items):
                qi = st.session_state.quiz_map_qindex
                q = st.session_state.quiz_items[qi]
                st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:18px;border-radius:14px;color:white;">
                      <b>Question {qi+1}</b><br/>{q['question']}
                    </div>
                """, unsafe_allow_html=True)
                cols = st.columns(2)
                for i, opt in enumerate(q['options']):
                    with cols[i % 2]:
                        if st.button(f"{chr(65+i)}. {opt}", use_container_width=True, key=f"opt_{qi}_{i}"):
                            # Support either 'correct' index or 'answer' text
                            correct_index = q.get('correct')
                            if correct_index is None:
                                correct_index = next((j for j, o in enumerate(q['options']) if o == q.get('answer')), -1)
                            is_ok = (i == correct_index)
                            st.session_state.quiz_map_answers[qi] = {"sel": i, "ok": is_ok}
                            apply_answer_and_move(is_ok, qi)
                            if is_ok:
                                st.success("✅ Correct! Moving forward…")
                                st.balloons()
                            else:
                                st.error("❌ Incorrect! Moving backward…")
                                if correct_index != -1:
                                    st.info(f"Answer: {q['options'][correct_index]}")
                            time.sleep(0.6)
                            st.rerun()

            if st.session_state.quiz_map_qindex > 0:
                with st.expander("📊 Quiz Stats", expanded=False):
                    acc = 100.0 * st.session_state.quiz_map_correct / max(1, st.session_state.quiz_map_qindex)
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Answered", st.session_state.quiz_map_qindex)
                    c2.metric("Correct", st.session_state.quiz_map_correct)
                    c3.metric("Accuracy", f"{acc:.1f}%")
                    c4.metric("Position", f"{st.session_state.quiz_map_position}/{st.session_state.quiz_map_total_questions+1}")
        else:
            st.info("Click Start Quiz Adventure to begin.")
    else:
        st.info("👈 Select subject and chapter in the sidebar.")

# ----------------------------- Ask Tab -----------------------------
with tab3:
    st.markdown("## 💬 Ask Questions")
    if st.session_state.subject and st.session_state.chapter:
        for role, content in st.session_state.messages:
            st.markdown(f"**{'🧑‍🎓' if role=='user' else '🤖'}:** {content}")
        q = st.text_input("Ask anything about this chapter:")
        if st.button("🚀 Ask", type="primary", key="ask_btn") and q:
            st.session_state.messages.append(("user", q))
            with st.spinner("Thinking..."):
                ans = answer_question(q, st.session_state.chapter, st.session_state.subject,
                                      st.session_state.class_level, st.session_state.language)
            st.session_state.messages.append(("assistant", ans)); st.rerun()
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.messages = []; st.rerun()
    else:
        st.info("👈 Select subject and chapter first.")

# ----------------------------- Games Tab -----------------------------
with tab4:
    st.markdown("## 🎮 Games")
    render_sudoku_game()

# ----------------------------- Quests Tab -----------------------------
def quest_progress_view():
    today = datetime.utcnow().date()
    daily = st.session_state.quests_daily_progress
    weekly = st.session_state.quests_weekly_progress

    st.markdown("### 🌤️ Daily Quests")
    completed_today = []
    for q in DAILY_QUESTS:
        cur = daily.get(q["key"], 0)
        pct = min(1.0, cur / q["target"])
        st.progress(pct, text=f"{q['name']} • {cur}/{q['target']} • {q['desc']}")
        if cur >= q["target"] and not st.session_state.get(f"quest_done_{q['id']}_{today}"):
            st.session_state[f"quest_done_{q['id']}_{today}"] = True
            completed_today.append(q["id"])
    if completed_today:
        grant_quest_rewards(completed_today)
        st.success("Daily quest rewards claimed!")

    st.markdown("### 📅 Weekly Quests")
    wk_start = weekly.get("week_start", today)
    completed_week = []
    for q in WEEKLY_QUESTS:
        cur = weekly.get(q["key"], 0)
        pct = min(1.0, cur / q["target"])
        st.progress(pct, text=f"{q['name']} • {cur}/{q['target']} • {q['desc']}")
        mark_key = f"quest_done_{q['id']}_{wk_start}"
        if cur >= q["target"] and not st.session_state.get(mark_key):
            st.session_state[mark_key] = True
            completed_week.append(q["id"])
    if completed_week:
        grant_quest_rewards(completed_week)
        st.success("Weekly quest rewards claimed!")

with tab5:
    st.markdown("## 🗺️ Quests & Achievements")
    quest_progress_view()

    st.markdown("### 🏆 Achievements")
    rows = []
    for title, desc, cond, emoji, xp in ACHIEVEMENTS:
        got = st.session_state.get(f"ach_{title}", False)
        rows.append((emoji, title, desc, xp, "Unlocked ✅" if got else "Locked 🔒"))
    for emoji, title, desc, xp, status in rows:
        st.markdown(f"- {emoji} {title} — {desc} • +{xp} XP • {status}")

# ----------------------------- Shop Tab -----------------------------
with tab6:
    st.markdown("## 🛒 Shop")
    st.markdown(f"Coins: {st.session_state.coins} • Credits: {st.session_state.game_credits}")
    for item in SHOP_ITEMS:
        c1, c2 = st.columns([4,1])
        with c1:
            st.write(f"{item['name']} — Cost: {item['cost']} coins")
        with c2:
            if st.button(f"Buy", key=f"buy_{item['id']}"):
                if st.session_state.coins >= item["cost"]:
                    st.session_state.coins -= item["cost"]
                    if item["type"] == "avatar":
                        st.session_state.unlocked_avatars.add(item["value"])
                        st.success(f"Unlocked avatar {item['value']}! Set it from the sidebar.")
                    elif item["type"] == "credits":
                        st.session_state.game_credits += int(item["value"])
                        st.success(f"Added {item['value']} credits.")
                else:
                    st.error("Not enough coins.")

# ----------------------------- Progress Tab -----------------------------
with tab7:
    st.markdown("## 📊 Progress & Analytics")
    total_quizzes = st.session_state.quiz_count
    accuracy = (st.session_state.quiz_score / st.session_state.quiz_total * 100) if st.session_state.quiz_total else 0.0
    s1,s2,s3,s4 = st.columns(4)
    with s1: st.markdown(f'<div class="stats-card"><h2>{total_quizzes}</h2><p>📝 Quizzes</p></div>', unsafe_allow_html=True)
    with s2: st.markdown(f'<div class="stats-card"><h2>{accuracy:.1f}%</h2><p>🎯 Accuracy</p></div>', unsafe_allow_html=True)
    with s3: st.markdown(f'<div class="stats-card"><h2>{len(st.session_state.progress)}</h2><p>📚 Subjects</p></div>', unsafe_allow_html=True)
    with s4: st.markdown(f'<div class="stats-card"><h2>{compute_badge(total_quizzes)}</h2><p>🏆 Badge</p></div>', unsafe_allow_html=True)

    hist_df = pd.DataFrame(st.session_state.history)
    st.markdown("### 🔥 Activity Heat Map")
    if not hist_df.empty:
        hist_df["date"] = pd.to_datetime(hist_df["date"])
        daily = (hist_df.groupby("date")
                 .agg(quizzes=("total","count"), correct=("score","sum"),
                      questions=("total","sum"), xp=("xp","sum"))
                 .reset_index())
        daily["accuracy"] = (daily["correct"] / daily["questions"]).replace([float("inf"), float("nan")], 0) * 100
        used_calplot = False
        try:
            import calplot
            fig_cal = calplot.calplot(
                daily.set_index("date")["quizzes"],
                suptitle="Daily Learning Activity (quizzes/day)",
                colorscale="Blues", gap=2, month_lines_width=1, name="Quizzes", dark_theme=True
            )
            st.plotly_chart(fig_cal, use_container_width=True)
            used_calplot = True
        except Exception:
            used_calplot = False
        if not used_calplot:
            df = daily.copy()
            df["week"] = df["date"].dt.isocalendar().week.astype(int)
            df["year"] = df["date"].dt.isocalendar().year.astype(int)
            df["weekday"] = df["date"].dt.weekday
            uniq_weeks = df.sort_values("date")["week"].unique()
            recent_weeks = uniq_weeks[-26:] if len(uniq_weeks) > 26 else uniq_weeks
            df = df[df["week"].isin(recent_weeks)]
            weekday_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            df["weekday_label"] = df["weekday"].map({i:d for i,d in enumerate(weekday_labels)})
            df["year_week"] = df["year"].astype(str) + "-W" + df["week"].astype(str).str.zfill(2)
            fig = px.density_heatmap(
                df, x="year_week", y="weekday_label", z="quizzes",
                color_continuous_scale="Blues", histfunc="sum",
                title="Daily Learning Activity (quizzes/day) - recent weeks"
            )
            fig.update_layout(xaxis_title="Year-Week", yaxis_title="Weekday", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activity yet to plot on the calendar.")

    st.markdown("### 📈 Progress Over Time")
    if not hist_df.empty:
        daily = (hist_df.groupby("date")
                 .agg(quizzes=("total","count"), correct=("score","sum"),
                      questions=("total","sum"), xp=("xp","sum"))
                 .reset_index())
        daily["accuracy"] = (daily["correct"] / daily["questions"]).replace([float("inf"), float("nan")], 0) * 100
        daily["cum_quizzes"] = daily["quizzes"].cumsum()
        daily["cum_xp"] = daily["xp"].cumsum()
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=daily["date"], y=daily["cum_xp"],
                                   mode="lines+markers", name="Cumulative XP",
                                   line=dict(color="#10b981", width=3)))
        fig_t.add_trace(go.Scatter(x=daily["date"], y=daily["cum_quizzes"],
                                   mode="lines+markers", name="Cumulative Quizzes",
                                   line=dict(color="#6366f1", width=2, dash="dash")))
        fig_t.add_trace(go.Scatter(x=daily["date"], y=daily["accuracy"],
                                   mode="lines+markers", name="Daily Accuracy (%)",
                                   line=dict(color="#f59e0b", width=2), yaxis="y2"))
        fig_t.update_layout(
            title="Learning Progress Timeline",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Cumulative XP / Quizzes"),
            yaxis2=dict(title="Accuracy (%)", overlaying="y", side="right", range=[0,100]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            template="plotly_dark",
        )
        st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.info("No progress data yet.")

    st.markdown("### 🧠 Mastery Heat Map (By Topic)")
    if st.session_state.progress:
        rows = []
        for subject, chapters in st.session_state.progress.items():
            for chapter, data in chapters.items():
                total = max(1, data.get("total", 0))
                acc = (data.get("score", 0) / total) * 100 if total > 0 else 0
                rows.append({"Subject": subject, "Chapter": chapter, "Accuracy": acc})
        perf_df = pd.DataFrame(rows).sort_values(["Subject","Chapter"])
        figp = px.density_heatmap(
            perf_df, x="Chapter", y="Subject", z="Accuracy",
            color_continuous_scale="Purples", range_color=[0,100],
            histfunc="avg", title="Accuracy by Subject and Chapter"
        )
        figp.update_layout(xaxis_title="Chapter", yaxis_title="Subject", template="plotly_dark")
        st.plotly_chart(figp, use_container_width=True)
    else:
        st.info("No per-topic accuracy yet. Complete a quiz to populate this view.")

# ----------------------------- Footer -----------------------------
st.markdown("---")
st.markdown(f"""
<div style="text-align:center; padding: 1.2rem; background: #0b1220; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; color: #e5e7eb;">
  Built with ❤️ using Streamlit • GPT-OSS 20B • Version 3.0 (Doodle Map + Full Gamification)
</div>
""", unsafe_allow_html=True)
