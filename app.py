import streamlit as st
import os
import re
import json
import requests
import hashlib
from dotenv import load_dotenv
from datetime import datetime
from fpdf import FPDF

from crewai import Crew, Process
from agents import (
    problem_agent, customer_agent, competitor_agent,
    mvp_agent, revenue_agent, pitch_agent, risk_agent
)
from tasks import create_tasks

# ─────────────────────────────────────────
#  ENV & PAGE CONFIG
# ─────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

st.set_page_config(
    page_title="IdeaCheck AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
#  CUSTOM CSS  — dark futuristic theme
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0f;
    color: #e8e8f0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] * { color: #c0c0d8 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #ec4899) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Secondary buttons */
.stDownloadButton > button {
    background: #1a1a28 !important;
    color: #a78bfa !important;
    border: 1px solid rgba(108,99,255,0.4) !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1a1a28 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e8e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(108,99,255,0.6) !important;
    box-shadow: 0 0 0 2px rgba(108,99,255,0.15) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #1a1a28 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}
.streamlit-expanderContent {
    background: #13131e !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 0 0 10px 10px !important;
}

/* Metric */
[data-testid="metric-container"] {
    background: #1a1a28 !important;
    border: 1px solid rgba(108,99,255,0.3) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111118 !important;
    border-radius: 10px !important;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #9090a8 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTabs [aria-selected="true"] {
    background: #6c63ff !important;
    color: white !important;
}

/* Success / Error */
.stSuccess { background: rgba(16,185,129,0.12) !important; border: 1px solid rgba(16,185,129,0.3) !important; border-radius: 10px !important; }
.stError   { background: rgba(239,68,68,0.12)  !important; border: 1px solid rgba(239,68,68,0.3)  !important; border-radius: 10px !important; }
.stInfo    { background: rgba(108,99,255,0.12) !important; border: 1px solid rgba(108,99,255,0.3) !important; border-radius: 10px !important; }
.stWarning { background: rgba(245,158,11,0.12) !important; border: 1px solid rgba(245,158,11,0.3) !important; border-radius: 10px !important; }

/* Slider */
.stSlider > div > div > div { background: #6c63ff !important; }

/* Spinner */
.stSpinner > div { border-top-color: #6c63ff !important; }

/* Divider */
hr { border-color: rgba(255,255,255,0.07) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  FILES
# ─────────────────────────────────────────
USERS_FILE   = "users.json"
HISTORY_FILE = "history.json"

# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
for key, val in {
    "page": "login",
    "user": None,
    "results": None,
    "idea": "",
    "validated_idea": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────
#  CACHED HELPER FUNCTIONS
# ─────────────────────────────────────────

@st.cache_data
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

@st.cache_data
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    # Clear cache after saving
    st.cache_data.clear()

def check_login(username, password):
    users = load_users()
    return users.get(username) == hash_pw(password)

def signup_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = hash_pw(password)
    save_users(users)
    return True

@st.cache_data
def extract_score(text):
    """Extract VALIDATION SCORE: X/10 from problem agent output."""
    match = re.search(r"VALIDATION SCORE[:\s]*(\d+(?:\.\d+)?)\s*/\s*10", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match2 = re.search(r"\b(\d+)\s*/\s*10\b", text)
    if match2:
        val = float(match2.group(1))
        if 1 <= val <= 10:
            return val
    return 6.0

@st.cache_data
def score_label(score):
    if score >= 8:
        return " High Potential", "#10b981"
    elif score >= 6:
        return " Moderate", "#f59e0b"
    else:
        return " Needs Work", "#ef4444"

@st.cache_data
def safe_json_parse(text):
    try:
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []

@st.cache_data(ttl=3600)
def get_similar_startups_cached(idea):
    """Cache similar startups for 1 hour"""
    prompt = f"""List 5 real startups similar to: "{idea}"
Return ONLY JSON array, no explanation:
[{{"name":"","desc":"","tag":""}}]"""
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "meta-llama/llama-4-maverick:free",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=10
        )
        content = res.json()["choices"][0]["message"]["content"]
        return safe_json_parse(content)
    except Exception:
        return [
            {"name": "Example Startup", "desc": "Similar competitor", "tag": "Direct"},
        ]

def get_similar_startups(idea):
    """Non-cached wrapper"""
    return get_similar_startups_cached(idea)

def safe_text(text):
    """Remove/replace unicode characters for PDF"""
    # Replace common unicode characters
    replacements = {
        '–': '-',  # en dash
        '—': '-',  # em dash
        '‑': '-',  # hyphen
        '"': '"',  # smart quotes
        '"': '"',
        ''': "'",
        ''': "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove emojis
    text = ''.join(c if ord(c) < 128 else '' for c in text)
    return text

def generate_pdf(idea, tasks, score):
    try:
        pdf = FPDF()
        pdf.set_margins(15, 15, 15)
        pdf.add_page()

        # Header bar
        pdf.set_fill_color(108, 99, 255)
        pdf.rect(0, 0, 220, 14, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_xy(15, 4)
        pdf.cell(0, 6, "IdeaCheck AI - Startup Validation Report")

        # Title
        pdf.set_y(22)
        pdf.set_text_color(10, 10, 20)
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 10, "Startup Validation Report", ln=True)

        # Idea
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(100, 100, 120)
        safe_idea = safe_text(idea)
        pdf.multi_cell(0, 7, f"Idea: {safe_idea}")

        # Score
        label, _ = score_label(score)
        safe_label = safe_text(label)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(108, 99, 255)
        pdf.cell(0, 9, f"Validation Score: {score}/10  {safe_label}", ln=True)

        # Date
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(160, 160, 180)
        pdf.cell(0, 7, f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", ln=True)

        # Divider
        pdf.set_draw_color(200, 200, 220)
        pdf.ln(2)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)

        # Agent outputs
        for task in tasks:
            if pdf.get_y() > 255:
                pdf.add_page()
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(30, 30, 50)
            safe_name = safe_text(task["name"])
            pdf.cell(0, 8, safe_name, ln=True)
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 80)
            safe_out = safe_text(task["output"])
            pdf.multi_cell(0, 6, safe_out)
            pdf.ln(3)

        path = "ideacheck_report.pdf"
        pdf.output(path)
        return path
    except Exception as e:
        st.error(f"PDF generation error: {str(e)}")
        return None

def save_history(idea, tasks, score):
    hist = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                hist = json.load(f)
        except:
            hist = []
    
    hist.append({
        "idea": idea,
        "score": score,
        "label": score_label(score)[0],
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "tasks": tasks,
    })
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(hist, f, indent=2)

@st.cache_data
def load_history_cached():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

def load_history():
    """Non-cached wrapper to always get fresh history"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

# ─────────────────────────────────────────
#  SIDEBAR NAVIGATION
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;padding:8px 0 20px'>
        <div style='width:34px;height:34px;border-radius:8px;
                    background:linear-gradient(135deg,#6c63ff,#ec4899);
                    display:flex;align-items:center;justify-content:center;font-size:16px'>⚡</div>
        <span style='font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem;color:#f0f0f8'>
            IdeaCheck <span style='color:#6c63ff'>AI</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.user:
        st.markdown(f"**👤 {st.session_state.user}**")
        st.markdown("---")
        
        col_nav = st.columns(3)
        with col_nav[0]:
            if st.button("🏠Home", use_container_width=True, key="nav_home"):
                st.session_state.page = "home"
                st.rerun()
        with col_nav[1]:
            if st.button("📜History", use_container_width=True, key="nav_history"):
                st.session_state.page = "history"
                st.rerun()
        with col_nav[2]:
            if st.button("🚪Logout", use_container_width=True, key="nav_logout"):
                st.session_state.user = None
                st.session_state.page = "login"
                st.rerun()
    else:
        col_auth = st.columns(2)
        with col_auth[0]:
            if st.button("🔐 Login", use_container_width=True, key="nav_login"):
                st.session_state.page = "login"
                st.rerun()
        with col_auth[1]:
            if st.button("📝 Sign Up", use_container_width=True, key="nav_signup"):
                st.session_state.page = "signup"
                st.rerun()

# ─────────────────────────────────────────
#  PAGE: LOGIN
# ─────────────────────────────────────────
if st.session_state.page == "login":
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center;padding:40px 0 32px'>
            <div style='font-size:48px'>⚡</div>
            <h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:2rem;
                       background:linear-gradient(135deg,#6c63ff,#ec4899);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                       margin-bottom:6px'>IdeaCheck AI</h1>
            <p style='color:#9090a8;font-size:0.9rem'>Multi-Agent Startup Idea Validator</p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

        with tab1:
            st.markdown("### Welcome back")
            username = st.text_input("Username", key="l_user", placeholder="Enter username")
            password = st.text_input("Password", type="password", key="l_pass", placeholder="Enter password")
            st.markdown("")
            if st.button("Login →", key="login_btn", use_container_width=True):
                if not username or not password:
                    st.error("Please fill in all fields.")
                elif check_login(username, password):
                    st.session_state.user = username
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

            st.markdown("""
            <div style='margin-top:12px;padding:10px 14px;
                        background:rgba(108,99,255,0.1);border:1px solid rgba(108,99,255,0.25);
                        border-radius:8px;font-size:12px;color:#9090a8'>
                💡 <b style='color:#a78bfa'>Demo:</b> Sign up with any username & password.
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.markdown("### Create account")
            new_user = st.text_input("Choose Username", key="s_user", placeholder="Pick a username")
            new_pass = st.text_input("Choose Password", type="password", key="s_pass", placeholder="Min 4 characters")
            conf_pass = st.text_input("Confirm Password", type="password", key="s_conf", placeholder="Repeat password")
            st.markdown("")
            if st.button("Create Account →", key="signup_btn", use_container_width=True):
                if not new_user or not new_pass:
                    st.error("Please fill in all fields.")
                elif len(new_pass) < 4:
                    st.error("Password must be at least 4 characters.")
                elif new_pass != conf_pass:
                    st.error("Passwords do not match.")
                elif not signup_user(new_user, new_pass):
                    st.error("Username already taken.")
                else:
                    st.success(f"Account created! Please log in.")

# ─────────────────────────────────────────
#  PAGE: HOME — Validate Idea
# ─────────────────────────────────────────
elif st.session_state.page == "home":

    st.markdown("""
    <div style='padding:8px 0 28px'>
        <h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:2.2rem;line-height:1.2;
                   background:linear-gradient(135deg,#6c63ff,#ec4899);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
            Validate Your Startup Idea<br/>with AI Agents
        </h1>
        <p style='color:#9090a8;font-size:0.95rem;margin-top:8px'>
            7 specialist AI agents analyse your idea in real-time.
        </p>
    </div>
    """, unsafe_allow_html=True)

    agent_info = [
        ("🔍", "Problem",    "#6c63ff"),
        ("👤", "Customer",   "#06b6d4"),
        ("⚔️",  "Competitor", "#f59e0b"),
        ("🛠️", "MVP",        "#10b981"),
        ("💰", "Revenue",    "#ec4899"),
        ("🎤", "Pitch",      "#8b5cf6"),
        ("⚠️", "Risk",       "#ef4444"),
    ]
    cols = st.columns(len(agent_info))
    for col, (icon, name, color) in zip(cols, agent_info):
        with col:
            st.markdown(f"""
            <div style='text-align:center;padding:10px 6px;
                        background:{color}18;border:1px solid {color}40;border-radius:10px'>
                <div style='font-size:20px'>{icon}</div>
                <div style='font-size:11px;font-weight:600;color:{color};margin-top:4px'>{name}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    idea = st.text_area(
        "💡 Your Startup Idea",
        placeholder="Describe your startup idea...",
        height=130,
        key="idea_input"
    )

    if st.button("⚡ Validate My Idea", use_container_width=True, key="validate_btn"):
        if not idea.strip():
            st.error("Please enter a startup idea first!")
        else:
            st.session_state.idea = idea

            progress_box = st.empty()
            status_text  = st.empty()
            prog_bar     = st.progress(0)

            agent_names = ["Problem Analyst", "Customer Research", "Competitor Analyst",
                           "MVP Planner", "Revenue Strategist", "Pitch Writer", "Risk Analyst"]
            agent_icons = ["🔍", "👤", "⚔️", "🛠️", "💰", "🎤", "⚠️"]

            def show_progress(step, total=7):
                done = [f"<span style='color:#10b981'>✓ {agent_icons[i]} {agent_names[i]}</span>" for i in range(step)]
                if step < total:
                    running = f"<span style='color:#f59e0b'>⏳ {agent_icons[step]} {agent_names[step]}</span>"
                    remaining = [f"<span style='color:#555568'>○ {agent_icons[i]} {agent_names[i]}</span>" for i in range(step+1, total)]
                    all_items = done + [running] + remaining
                else:
                    all_items = done
                html = " &nbsp;→&nbsp; ".join(all_items)
                progress_box.markdown(f"""
                <div style='background:#1a1a28;border:1px solid rgba(255,255,255,0.08);
                            border-radius:12px;padding:14px 18px;font-size:12px;line-height:2'>
                    {html}
                </div>
                """, unsafe_allow_html=True)

            with st.spinner("🤖 Agents are validating your idea... Please wait"):
                tasks = create_tasks(idea)
                crew  = Crew(
                    agents=[problem_agent, customer_agent, competitor_agent,
                             mvp_agent, revenue_agent, pitch_agent, risk_agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=False
                )

                for i in range(7):
                    show_progress(i)
                    status_text.info(f"🤖 **{agent_icons[i]} {agent_names[i]}** is analysing...")
                    prog_bar.progress((i + 1) / 7)

                result  = crew.kickoff()
                outputs = crew.tasks
                show_progress(7)

            status_text.empty()
            prog_bar.empty()

            tasks_data = [
                {"name": "🔍 Problem Analysis",   "output": str(outputs[0].output)},
                {"name": "👤 Customer Persona",    "output": str(outputs[1].output)},
                {"name": "⚔️ Competitor Analysis", "output": str(outputs[2].output)},
                {"name": "🛠️ MVP Features",        "output": str(outputs[3].output)},
                {"name": "💰 Revenue Model",        "output": str(outputs[4].output)},
                {"name": "🎤 Investor Pitch",       "output": str(outputs[5].output)},
                {"name": "⚠️ Risk Analysis",        "output": str(outputs[6].output)},
            ]

            score = extract_score(str(outputs[0].output))

            st.session_state.results = {
                "final": str(result),
                "tasks": tasks_data,
                "score": score,
            }
            st.session_state.validated_idea = idea

            save_history(idea, tasks_data, score)

            st.session_state.page = "results"
            st.rerun()

# ─────────────────────────────────────────
#  PAGE: RESULTS
# ─────────────────────────────────────────
elif st.session_state.page == "results":

    idea   = st.session_state.validated_idea or st.session_state.idea
    res    = st.session_state.results
    score  = res.get("score", 6.0)
    tasks  = res.get("tasks", [])
    label, color = score_label(score)

    st.markdown(f"""
    <div style='padding:8px 0 20px'>
        <div style='font-size:12px;color:#9090a8;margin-bottom:6px'>VALIDATED IDEA</div>
        <h2 style='font-family:Syne,sans-serif;font-weight:700;font-size:1.5rem;
                   color:#f0f0f8;margin-bottom:0'>{idea}</h2>
    </div>
    """, unsafe_allow_html=True)

    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        st.metric("🎯 Score", f"{score}/10")
    with scol2:
        st.metric("📊 Status", label)
    with scol3:
        st.metric("🤖 Agents", "7/7")
    with scol4:
        st.metric("📅 Date", datetime.now().strftime("%d %b"))

    pct = int((score / 10) * 100)
    st.markdown(f"""
    <div style='margin:16px 0 8px;background:#1a1a28;border-radius:12px;
                border:1px solid rgba(255,255,255,0.07);padding:16px 20px'>
        <div style='display:flex;justify-content:space-between;margin-bottom:8px'>
            <span style='font-size:13px;font-weight:600'>Idea Strength</span>
            <span style='font-size:13px;font-weight:700;color:{color}'>{score}/10 — {label}</span>
        </div>
        <div style='height:10px;background:#0a0a0f;border-radius:5px;overflow:hidden'>
            <div style='height:100%;width:{pct}%;border-radius:5px;
                        background:linear-gradient(90deg,#6c63ff,{color})'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🤖 Agent Outputs")
    
    agent_colors = ["#6c63ff","#06b6d4","#f59e0b","#10b981","#ec4899","#8b5cf6","#ef4444"]
    for i, task in enumerate(tasks):
        with st.expander(task["name"], expanded=(i == 0)):
            st.markdown(task["output"])

    st.markdown("---")

    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        pdf_path = generate_pdf(idea, tasks, score)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "📄 Download PDF",
                data=f,
                file_name=f"ideacheck_{idea[:20].replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    with btn2:
        if st.button("🔄 New Idea", use_container_width=True, key="new_idea_btn"):
            st.session_state.page = "home"
            st.session_state.results = None
            st.rerun()
    with btn3:
        if st.button("📜 History", use_container_width=True, key="history_btn"):
            st.session_state.page = "history"
            st.rerun()

# ─────────────────────────────────────────
#  PAGE: HISTORY
# ─────────────────────────────────────────
elif st.session_state.page == "history":

    st.markdown("""
    <h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:2rem;
               background:linear-gradient(135deg,#6c63ff,#ec4899);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               padding-bottom:4px'>
        Validation History
    </h1>
    """, unsafe_allow_html=True)

    hist = load_history()

    if not hist:
        st.markdown("""
        <div style='text-align:center;padding:80px 20px'>
            <div style='font-size:56px;margin-bottom:16px'>📭</div>
            <h3 style='font-family:Syne,sans-serif;font-weight:700'>No history yet</h3>
            <p style='color:#9090a8;margin-top:8px'>Validate your first startup idea to see it here.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⚡ Validate an Idea", use_container_width=False, key="validate_from_history"):
            st.session_state.page = "home"
            st.rerun()
    else:
        hcol1, hcol2, hcol3 = st.columns([2, 1, 1])
        with hcol1:
            search = st.text_input("🔍 Search", placeholder="Search by idea name...", key="search_history")
        with hcol2:
            min_sc = st.number_input("Min", 0.0, 10.0, 0.0, 0.5, key="min_score")
        with hcol3:
            max_sc = st.number_input("Max", 0.0, 10.0, 10.0, 0.5, key="max_score")

        filtered = [h for h in reversed(hist)
                    if search.lower() in h.get("idea","").lower()
                    and min_sc <= h.get("score", 0) <= max_sc]

        st.markdown(f"<p style='color:#9090a8;font-size:13px'>{len(filtered)} result(s)</p>", unsafe_allow_html=True)

        if st.button("🗑️ Clear History", key="clear_history_btn"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            st.success("Cleared!")
            st.rerun()

        for idx, item in enumerate(filtered):
            sc    = item.get("score", 0)
            lbl   = item.get("label", score_label(sc)[0])
            date  = item.get("date", "")
            idea_h  = item.get("idea", "")
            tasks_h = item.get("tasks", [])

            with st.expander(f"{idea_h[:50]}...  —  {sc}/10  {lbl}", key=f"exp_{idx}"):
                for t in tasks_h:
                    st.markdown(f"**{t['name']}**")
                    st.markdown(t["output"])
                    st.markdown("---")

                pdf_path = generate_pdf(idea_h, tasks_h, sc)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "📄 Download PDF",
                        data=f,
                        file_name=f"ideacheck_{idea_h[:15].replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_{idx}"
                    )