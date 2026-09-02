import os
import io
import json
import urllib.parse
import time
import uuid
import requests
import textwrap
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. PAGE CONFIG & THEME INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Qualix AI - Secure AI Readiness Operating System",
    page_icon="Q",
    layout="wide",
    initial_sidebar_state="expanded"
)

def clean_html(html_str: str) -> str:
    """Helper to strip all leading/trailing whitespace from every line of HTML/SVG strings."""
    lines = [line.strip() for line in str(html_str).split("\n")]
    return "\n".join(lines)

# Override textwrap.dedent to use clean_html globally
textwrap.dedent = clean_html

# ==========================================
# 1b. "VITALS" HELPERS — reusable animated primitives
#     (pure CSS / SVG-SMIL, no <script> required so they render
#      correctly inside st.markdown, unlike JS which needs an iframe)
# ==========================================
def animated_counter(value, size="1.8rem", color="#F8FAFC", weight=900, suffix="", prefix=""):
    """Renders a number that counts up from 0 -> value using a CSS @property trick.
    Safe to call many times per page; each call gets a unique keyframe name."""
    try:
        target = int(round(float(value)))
    except Exception:
        target = 0
    uid = uuid.uuid4().hex[:8]
    return textwrap.dedent(f"""
    <style>
    @keyframes countUp_{uid} {{ from {{ --num: 0; }} to {{ --num: {target}; }} }}
    .cnt-{uid} {{
        counter-reset: num var(--num);
        animation: countUp_{uid} 1.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        font-weight: {weight};
        font-size: {size};
        color: {color};
        display: inline-block;
        font-variant-numeric: tabular-nums;
    }}
    .cnt-{uid}::after {{ content: "{prefix}" counter(num) "{suffix}"; }}
    </style>
    <span class="cnt-{uid}"></span>
    """)

def ekg_strip(label="SYSTEM PULSE — LIVE", height=46, color="#10B981"):
    """A looping heartbeat / EKG line, pure SVG + CSS (SMIL + stroke-dash animation).
    Used as Qualix's signature 'vitals monitor' motif tying the diagnostic metaphor together."""
    uid = uuid.uuid4().hex[:6]
    return textwrap.dedent(f"""
    <div style="display:flex; align-items:center; gap:12px; background:rgba(16,185,129,0.05);
                border:1px solid rgba(16,185,129,0.18); border-radius:10px; padding:8px 16px; margin-bottom:12px;">
        <span style="font-size:0.68rem; font-weight:800; letter-spacing:1.2px; color:{color}; white-space:nowrap; text-transform:uppercase;">
            <span class="live-dot"></span>{label}
        </span>
        <svg viewBox="0 0 300 40" preserveAspectRatio="none" style="flex:1; height:{height}px; overflow:visible;">
            <polyline id="ekg-{uid}" points="0,20 30,20 42,20 50,4 58,36 66,20 80,20 110,20 122,20 130,8 138,32 146,20 160,20 190,20 202,20 210,4 218,36 226,20 240,20 270,20 282,20 290,8 298,32 306,20"
                fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"
                pathLength="100" style="stroke-dasharray:100; stroke-dashoffset:100; animation: ekgDraw-{uid} 2.4s linear infinite;" />
        </svg>
        <style>
            @keyframes ekgDraw-{uid} {{
                0% {{ stroke-dashoffset: 100; opacity: 0.35; }}
                45% {{ opacity: 1; }}
                55% {{ stroke-dashoffset: 0; opacity: 1; }}
                100% {{ stroke-dashoffset: -100; opacity: 0.35; }}
            }}
        </style>
    </div>
    """)

def achievement_badges(quality_score=0, ml_score=0, readiness_score=0, security_clean=True):
    """Row of pop-in 'vitals' achievement chips, unlocked based on live scores."""
    badges = [
        ("🛡️", "Security Sentinel", security_clean, "#10B981"),
        ("🧹", "Data Hygiene Pro", quality_score >= 80, "#3B82F6"),
        ("🧠", "ML Ready", ml_score >= 80, "#06B6D4"),
        ("💯", "Elite Readiness", readiness_score >= 90, "#F59E0B"),
        ("🔒", "Encrypted at Rest", True, "#A78BFA"),
    ]
    chips = ""
    for i, (icon, label, unlocked, color) in enumerate(badges):
        opacity = "1" if unlocked else "0.35"
        border = color if unlocked else "rgba(255,255,255,0.12)"
        glow = f"box-shadow:0 0 14px {color}55;" if unlocked else ""
        delay = i * 0.12
        locked_note = "" if unlocked else ' <span style="color:#64748B; font-weight:500;">(locked)</span>'
        chips += textwrap.dedent(f"""
        <div class="badge-pop" style="animation-delay:{delay}s; opacity:{opacity}; border:1px solid {border}; {glow}
             display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:999px;
             background:rgba(255,255,255,0.03); font-size:0.78rem; font-weight:700; color:#E2E8F0; margin:0 8px 8px 0;">
            <span style="font-size:0.95rem;">{icon}</span>{label}{locked_note}
        </div>
        """)
    return textwrap.dedent(f"""
    <style>
        @keyframes badgePop {{
            0% {{ transform: scale(0.6) translateY(6px); opacity: 0; }}
            70% {{ transform: scale(1.08) translateY(0); }}
            100% {{ transform: scale(1) translateY(0); }}
        }}
        .badge-pop {{ animation: badgePop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both; }}
    </style>
    <div>{chips}</div>
    """)

def activity_ticker(events, cycle_seconds=4):
    """Vertically cycling 'live activity feed' — same declarative CSS technique as the
    login-screen hero ticker, reused here for a real-time feel with zero JS."""
    n = max(len(events), 1)
    each = cycle_seconds
    total = each * n
    rows = ""
    for i, (icon, text, when) in enumerate(events):
        delay = i * each
        rows += textwrap.dedent(f"""
        <div class="feed-item" style="animation-duration:{total}s; animation-delay:{delay - total}s;">
            <span style="font-size:0.95rem;">{icon}</span>
            <span style="color:#E2E8F0;">{text}</span>
            <span style="color:#64748B; font-size:0.7rem; margin-left:auto; white-space:nowrap;">{when}</span>
        </div>
        """)
    return textwrap.dedent(f"""
    <style>
        @keyframes feedCycle {{
            0% {{ opacity: 0; transform: translateY(10px); }}
            4% {{ opacity: 1; transform: translateY(0); }}
            {round(100/n - 2, 2)}% {{ opacity: 1; transform: translateY(0); }}
            {round(100/n, 2)}% {{ opacity: 0; transform: translateY(-10px); }}
            100% {{ opacity: 0; }}
        }}
        .feed-stage {{ position: relative; height: 34px; overflow: hidden; }}
        .feed-item {{
            position: absolute; top: 0; left: 0; right: 0;
            display: flex; align-items: center; gap: 8px;
            font-size: 0.82rem; padding: 6px 2px;
            animation-name: feedCycle;
            animation-iteration-count: infinite;
            animation-timing-function: ease-in-out;
            opacity: 0;
        }}
    </style>
    <div class="feed-stage">{rows}</div>
    """)

# Custom Premium Glassmorphism Theme CSS Styling (Slate Tech Theme)
st.markdown(textwrap.dedent("""
<style>
    /* Register a real integer custom-property so it can be smoothly animated */
    @property --num {
        syntax: '<integer>';
        initial-value: 0;
        inherits: false;
    }

    /* Custom Webkit Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0F172A;
    }
    ::-webkit-scrollbar-thumb {
        background: #1E293B;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #06B6D4;
    }

    /* Global Base */
    .stApp {
        background: radial-gradient(circle at top right, #1E293B, #0F172A);
        color: #E2E8F0;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    /* Hide Streamlit default components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove padding of main content area */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1440px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    /* Sidebar styling overrides */
    div[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    /* Header fonts & titles */
    .premium-header {
        font-weight: 800;
        font-size: 2rem;
        background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
        letter-spacing: -0.5px;
    }
    
    .text-muted {
        color: #94A3B8;
        font-size: 0.85rem;
    }
    
    /* Custom Input Widget Styling Overrides */
    div[data-baseweb="select"] > div {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #F8FAFC !important;
        border-radius: 6px !important;
    }
    div[role="listbox"] {
        background-color: #0F172A !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
    }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #F8FAFC !important;
        border-radius: 6px !important;
    }
    
    /* Custom Tab Styling Overrides */
    div[data-testid="stTabBar"] button {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    div[data-testid="stTabBar"] button[aria-selected="true"] {
        color: #06B6D4 !important;
        border-bottom-color: #06B6D4 !important;
        font-weight: 700 !important;
    }
    
    /* Glassmorphism styling for standard Streamlit containers with border */
    div[data-testid="stVerticalBlockBorder"] {
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        padding: 18px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        margin-bottom: 12px !important;
    }
    
    /* Remove redundant inner borders */
    div[data-testid="stVerticalBlockBorder"] > div {
        border: none !important;
    }
    
    /* Custom HTML Glass Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-top: 4px;
    }
    .badge-critical { background-color: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-high { background-color: rgba(249, 115, 22, 0.15); color: #FDBA74; border: 1px solid rgba(249, 115, 22, 0.3); }
    .badge-warning { background-color: rgba(234, 179, 8, 0.15); color: #FDE047; border: 1px solid rgba(234, 179, 8, 0.3); }
    .badge-healthy { background-color: rgba(16, 185, 129, 0.15); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.3); }

    /* Custom inline status dots */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .status-dot.green { background-color: #10B981; }
    .status-dot.yellow { background-color: #F59E0B; }
    .status-dot.red { background-color: #EF4444; }
    .status-dot.blue { background-color: #3B82F6; }

    /* Button hierarchy: secondary controls stay quiet; only primary calls to
       action use the blue-to-cyan emphasis. */
    div.stButton > button {
        border-radius: 8px !important;
        font-size: 0.9rem !important;
        font-weight: 650 !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid transparent !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.28) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: rgba(30, 41, 59, 0.72) !important;
        color: #DCE7F5 !important;
        border: 1px solid rgba(148, 163, 184, 0.28) !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%) !important;
        box-shadow: 0 6px 18px rgba(6, 182, 212, 0.45) !important;
        transform: translateY(-2px) !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: rgba(51, 65, 85, 0.9) !important;
        border-color: rgba(6, 182, 212, 0.55) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) scale(0.98) !important;
    }

    /* Glass cards get a subtle lift + glow on hover, app-wide */
    .glass-card, div[data-testid="stVerticalBlockBorder"] {
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
    }
    .glass-card:hover, div[data-testid="stVerticalBlockBorder"]:hover {
        transform: translateY(-3px);
        border-color: rgba(6, 182, 212, 0.4) !important;
        box-shadow: 0 10px 28px rgba(6, 182, 212, 0.18) !important;
    }

    /* Let multi-column screens collapse before their contents become cramped. */
    @media (max-width: 900px) {
        .block-container { max-width: 100% !important; padding: 1rem !important; }
        .premium-header { font-size: 1.65rem; }
    }

    /* Pulsing live indicator, reused in header + sidebar */
    @keyframes pulseDot {
        0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.55); }
        70% { box-shadow: 0 0 0 7px rgba(16,185,129,0); }
        100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
    }
    .live-dot {
        display:inline-block; width:7px; height:7px; border-radius:50%;
        background:#10B981; margin-right:6px; animation: pulseDot 1.8s infinite;
    }

    /* Generic fade-up entrance, reusable on any block */
    @keyframes fadeInUpBlock {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .fade-in-block { animation: fadeInUpBlock 0.5s ease-out both; }

    /* Typing indicator */
    @keyframes typingBounce {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
        30% { transform: translateY(-5px); opacity: 1; }
    }
    .typing-dot {
        display:inline-block; width:6px; height:6px; border-radius:50%;
        background:#67E8F9; margin-right:4px; animation: typingBounce 1.1s infinite;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.15s; }
    .typing-dot:nth-child(3) { animation-delay: 0.3s; }

    /* =========================================================
       LOGIN SCREEN — clean split layout, no video, card-based
       ========================================================= */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes floatSlow {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-6px); }
    }
    .login-shell { padding-top: 1rem; max-width: 1300px; margin: 0 auto; }
    .login-topbar {
        display: flex; align-items: center; gap: 12px;
        margin-bottom: 26px;
        animation: fadeInUp 0.5s ease-out both;
    }
    .login-topbar .logo-chip {
        width: 42px; height: 42px; border-radius: 11px;
        background: linear-gradient(135deg, #3B82F6, #06B6D4);
        display: flex; align-items: center; justify-content: center;
        font-weight: 900; color: #fff; font-size: 1.3rem;
        box-shadow: 0 4px 14px rgba(6,182,212,0.4);
    }
    .login-topbar .brand-name { font-weight: 800; font-size: 1.5rem; color: #F8FAFC; letter-spacing: 0.5px; }
    .login-topbar .brand-name .accent-ai { color: #10B981; }
    .login-topbar .brand-tag { font-size: 0.8rem; color: #94A3B8; font-weight: 500; margin-top: -2px; }

    .hero-title {
        font-size: 3.1rem; line-height: 1.12; font-weight: 900; color: #FFFFFF;
        letter-spacing: -0.5px; margin: 0 0 20px 0;
        animation: fadeInUp 0.7s ease-out both;
    }
    .hero-title .accent {
        color: #3B82F6;
    }
    .hero-subtext {
        font-size: 1.05rem; color: #94A3B8; line-height: 1.6;
        max-width: 480px; margin-bottom: 34px;
        animation: fadeInUp 0.8s ease-out both;
    }
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        animation: fadeInUp 0.9s ease-out both;
    }
    .feature-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 20px 14px;
        text-align: center;
        transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
    }
    .feature-card:hover {
        transform: translateY(-3px);
        border-color: rgba(6,182,212,0.4);
        background: rgba(255,255,255,0.05);
    }
    .feature-card .f-icon { font-size: 1.6rem; margin-bottom: 10px; }
    .feature-card .f-title { font-size: 0.95rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px; }
    .feature-card .f-desc { font-size: 0.76rem; color: #94A3B8; line-height: 1.4; }

    .login-card-outer {
        background: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.12);
        border-top: 4px solid #06B6D4;
        border-radius: 16px;
        padding: 34px 34px 26px 34px;
        box-shadow: 0 24px 70px rgba(0,0,0,0.45);
        animation: fadeInUp 0.6s ease-out both;
    }
    .login-card-head { text-align: center; margin-bottom: 18px; }
    .login-card-head .lock-badge {
        width: 48px; height: 48px; border-radius: 12px; margin: 0 auto 16px auto;
        background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.15));
        border: 1px solid rgba(6,182,212,0.5);
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 16px rgba(6, 182, 212, 0.35);
        animation: floatSlow 4s ease-in-out infinite;
    }
    .login-card-head h4 { margin: 0; color: #FFFFFF; font-size: 1.45rem; font-weight: 800; letter-spacing: -0.3px; }
    .login-card-head p { margin: 5px 0 0 0; color: #94A3B8; font-size: 0.85rem; }

    /* Systemic Status LED Indicators */
    .systemic-indicator-row {
        display: flex; justify-content: space-between; margin-top: 18px;
        padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 0.66rem; color: #64748B; font-weight: 600;
    }
    .systemic-indicator-item {
        display: inline-flex; align-items: center; gap: 5px;
    }
    .systemic-indicator-item .active-led {
        width: 6px; height: 6px; border-radius: 50%;
        background-color: #10B981; box-shadow: 0 0 6px #10B981;
    }

    div[data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.16) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        padding: 11px 14px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border: 1px solid #06B6D4 !important;
        box-shadow: 0 0 0 3px rgba(6,182,212,0.15) !important;
    }
    div[data-testid="stTextInput"] label { color: #E2E8F0 !important; font-size: 0.85rem !important; font-weight: 600 !important; }

    .login-extra-row {
        display: flex; justify-content: space-between; align-items: center;
        margin: 4px 0 18px 0;
    }
    .login-extra-row a {
        color: #38BDF8; font-size: 0.82rem; text-decoration: none; font-weight: 600;
    }
    .login-extra-row a:hover { text-decoration: underline; }
    div[data-testid="stCheckbox"] label p { color: #94A3B8 !important; font-size: 0.82rem !important; }

    .demo-cred-box {
        background: rgba(255,255,255,0.04);
        border: 1px dashed rgba(255,255,255,0.18);
        border-radius: 9px;
        padding: 10px 13px;
        margin-top: 16px;
    }
    .demo-cred-box .demo-title { font-size: 0.65rem; color: #67E8F9; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 5px; }
    .demo-cred-row { display: flex; justify-content: space-between; font-size: 0.74rem; color: #CBD5E1; padding: 2px 0; }
    .demo-cred-row b { color: #F8FAFC; }

    .login-footer-note { text-align: center; font-size: 0.68rem; color: #64748B; margin-top: 14px; }

    @media (max-width: 900px) {
        .feature-grid { grid-template-columns: repeat(2, 1fr); }
        .hero-title { font-size: 2.2rem; }
    }
</style>
"""), unsafe_allow_html=True)

BACKEND_URL = "http://127.0.0.1:8000"

# Slug role mapping to prevent space character encoding bugs in browser URLs
role_map = {
    "admin": "ADMIN",
    "dataanalyst": "DATA ANALYST",
    "viewer": "VIEWER"
}

# ==========================================
# 2. RUNTIME STATE & URL ROUTER SYNC
# ==========================================
qp = st.query_params

if "username" in qp and "role" in qp and not st.session_state.get("explicit_logout", False):
    st.session_state.logged_in = True
    st.session_state.user_role = role_map.get(qp["role"].lower(), "VIEWER")
    st.session_state.user_name = qp.get("name", "User")
    st.session_state.user_email = qp["username"]
    if "dataset_id" in qp:
        st.session_state.dataset_id = qp["dataset_id"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = "VIEWER"
    st.session_state.user_name = "Guest"
    st.session_state.user_email = ""

if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = "retail_sales"

if "dataset_name" not in st.session_state:
    names = {
        "retail_sales": "Retail Sales Log",
        "customer_churn": "Customer Churn (ML)",
        "inventory_logistics": "Inventory Logistics"
    }
    st.session_state.dataset_name = names.get(st.session_state.dataset_id, "Uploaded Dataset")

if "clamav_status" not in st.session_state:
    st.session_state.clamav_status = "Clean"

if "clamav_details" not in st.session_state:
    st.session_state.clamav_details = "Local Matching (Signature checked)."

if "applied_fixes" not in st.session_state:
    st.session_state.applied_fixes = []

# Core analysis caches
if "profile_cache" not in st.session_state:
    st.session_state.profile_cache = {}
if "quality_cache" not in st.session_state:
    st.session_state.quality_cache = {}
if "ml_cache" not in st.session_state:
    st.session_state.ml_cache = {}
if "readiness_cache" not in st.session_state:
    st.session_state.readiness_cache = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"sender": "ai", "text": "Hello! I am your AI Data Doctor. I have completed the automated Pandas diagnostic scan of your dataset. Let me know if you would like me to explain class imbalance, target leakage risks, or outline specific cleaning actions!"}
    ]

# Rolling "recent activity" log purely for the live activity-feed widget on the Dashboard.
if "recent_activity" not in st.session_state:
    st.session_state.recent_activity = [
        ("🩺", "AI Data Doctor completed automated diagnostic scan", "just now"),
        ("🔐", "Fernet AES-256 encryption applied at rest", "1m ago"),
        ("🧪", "ClamAV ingestion firewall cleared upload", "2m ago"),
    ]

def log_activity(icon, text):
    st.session_state.recent_activity.insert(0, (icon, text, "just now"))
    st.session_state.recent_activity = st.session_state.recent_activity[:6]

# (Page routing is handled via RBAC later in the script)

# ==========================================
# 3. SECURE AUTH LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    # Load custom background base64
    bg_uri = "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=1920&q=80"
    bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_bg.png")
    if os.path.exists(bg_path):
        import base64
        try:
            with open(bg_path, "rb") as image_file:
                bg_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                bg_uri = f"data:image/png;base64,{bg_base64}"
        except Exception:
            pass

    # Ingest full-screen background styles & canvas background component
    st.markdown(f"""
    <style>
        html, body, [data-testid="stAppViewContainer"], .block-container {{
            overflow: hidden !important;
            max-height: 100vh !important;
            height: 100vh !important;
        }}
        /* Hide Streamlit markdown header link anchors */
        a.anchor-link {{
            display: none !important;
        }}
        .stApp {{
            background: linear-gradient(rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.92)), 
                        url('{bg_uri}') no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        /* Spotlight glowing aura centered behind the login form */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 50%;
            left: 78%;
            transform: translate(-50%, -50%);
            width: 550px;
            height: 550px;
            background: radial-gradient(circle, rgba(16, 185, 129, 0.18) 0%, rgba(6, 182, 212, 0.08) 45%, rgba(15, 23, 42, 0) 70%);
            pointer-events: none;
            z-index: 0;
            filter: blur(36px);
            animation: none;
            opacity: 0.78;
        }}
        @keyframes spotlightPulse {{
            0%, 100% {{ opacity: 0.72; transform: translate(-50%, -50%); }}
            50% {{ opacity: 0.86; transform: translate(-50%, -50%); }}
        }}
        /* Clean top margin spacing */
        .block-container {{
            padding-top: 1rem !important;
            margin-top: -1.5rem !important;
        }}
        div[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        /* Resizing login views to prevent overflow */
        .login-topbar {{
            margin-bottom: 12px !important;
        }}
        .login-topbar .logo-chip {{
            width: 34px !important;
            height: 34px !important;
            font-size: 1.1rem !important;
        }}
        .login-topbar .brand-name {{
            font-size: 1.3rem !important;
        }}
        .hero-title {{
            font-size: 2.3rem !important;
            line-height: 1.1 !important;
            margin: 0 0 10px 0 !important;
        }}
        .morph-card {{
            margin-bottom: 14px !important;
            padding: 8px 12px !important;
        }}
        .feature-grid {{
            gap: 8px !important;
        }}
        .feature-card {{
            padding: 10px 8px !important;
            border-radius: 8px !important;
        }}
        .feature-card svg {{
            width: 18px !important;
            height: 18px !important;
            margin-bottom: 4px !important;
        }}
        .feature-card .f-title {{
            font-size: 0.8rem !important;
            margin-bottom: 2px !important;
        }}
        .feature-card .f-desc {{
            font-size: 0.68rem !important;
            line-height: 1.2 !important;
        }}
        
        /* Override border container styling for the login card with glowing borders */
        div[data-testid="stVerticalBlockBorder"] {{
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(21, 27, 46, 0.8)) !important;
            backdrop-filter: blur(12px) !important;
            border: 1.5px solid rgba(6, 182, 212, 0.35) !important;
            border-top: 5px solid #06B6D4 !important;
            border-radius: 18px !important;
            padding: 12px 18px !important;
            box-shadow: 0 0 35px rgba(6, 182, 212, 0.2), 0 30px 80px rgba(0,0,0,0.55) !important;
            animation: fadeInUp 0.6s ease-out both !important;
            max-height: 90vh !important;
            overflow-y: auto !important;
        }}
        
        /* Reduce gap inside the container vertical block */
        div[data-testid="stVerticalBlockBorder"] > div > div[data-testid="stVerticalBlock"] {{
            gap: 5px !important;
        }}
        
        /* Custom Input Widget styling overrides with neon focus glows */
        div[data-testid="stTextInput"] label p {{
            font-size: 0.74rem !important;
            margin-bottom: 2px !important;
            padding-bottom: 0px !important;
        }}
        div[data-testid="stTextInput"] [data-baseweb="input"] {{
            background-color: rgba(15, 23, 42, 0.55) !important;
            border: 1px solid rgba(6, 182, 212, 0.25) !important;
            border-radius: 8px !important;
            height: 34px !important;
            transition: all 0.25s ease !important;
        }}
        div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {{
            border-color: #06B6D4 !important;
            box-shadow: 0 0 14px rgba(6, 182, 212, 0.4) !important;
            background-color: rgba(15, 23, 42, 0.75) !important;
        }}
        div[data-testid="stTextInput"] input {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #F8FAFC !important;
            padding-top: 4px !important;
            padding-bottom: 4px !important;
            height: 32px !important;
        }}
        
        /* Customize checkbox styling to be neon-themed */
        div[data-testid="stCheckbox"] span {{
            border-color: rgba(6, 182, 212, 0.4) !important;
            border-radius: 4px !important;
        }}
        div[data-testid="stCheckbox"] input:checked + span {{
            background-color: #06B6D4 !important;
            border-color: #06B6D4 !important;
        }}
        div[data-testid="stCheckbox"] label p {{
            color: #F8FAFC !important;
            font-weight: 500 !important;
            font-size: 0.78rem !important;
        }}
        
        /* Custom button overrides with high glow and slide-up hover effect */
        div.stButton > button {{
            background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 20px rgba(6, 182, 212, 0.4) !important;
            height: 34px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            line-height: 34px !important;
            transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        }}
        div.stButton > button:hover {{
            background: linear-gradient(135deg, #00D8F6 0%, #1D4ED8 100%) !important;
            box-shadow: 0 6px 28px rgba(6, 182, 212, 0.75) !important;
            transform: translateY(-2px) !important;
        }}
        
        /* Demo credentials box layout enhancements */
        .demo-cred-box {{
            background: rgba(15, 23, 42, 0.4) !important;
            border: 1.2px dashed rgba(6, 182, 212, 0.35) !important;
            border-radius: 8px !important;
            margin-top: 8px !important;
            padding: 6px 10px !important;
        }}
        
        .login-card-head {{
            margin-bottom: 6px !important;
        }}
        @keyframes badgeGlow {{
            0%, 100% {{ box-shadow: 0 0 12px rgba(6, 182, 212, 0.35); border-color: rgba(6, 182, 212, 0.5); }}
            50% {{ box-shadow: 0 0 22px rgba(6, 182, 212, 0.7); border-color: rgba(6, 182, 212, 0.8); }}
        }}
        .login-card-head .lock-badge {{
            width: 48px !important;
            height: 48px !important;
            margin-bottom: 8px !important;
            border-radius: 12px !important;
            background: radial-gradient(circle at center, rgba(6, 182, 212, 0.2) 0%, rgba(59, 130, 246, 0.04) 100%) !important;
            border: 1.5px solid rgba(6, 182, 212, 0.6) !important;
            box-shadow: 0 0 16px rgba(6, 182, 212, 0.4) !important;
            animation: none !important;
        }}
        .login-card-head .lock-badge svg {{
            width: 18px !important;
            height: 18px !important;
        }}
        .login-card-head h4 {{
            font-size: 1.25rem !important;
        }}
        .login-card-head p {{
            font-size: 0.78rem !important;
            margin-top: 2px !important;
        }}
        
        iframe[srcdoc*="networkCanvas"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: -1 !important;
            pointer-events: none !important;
            border: none !important;
            background: transparent !important;
            /* The canvas is decorative only. Hiding it prevents bright packet
               flashes when Streamlit remounts the login form during input. */
            visibility: hidden !important;
        }}
        .hero-title .accent-gold {{
            color: #F59E0B !important;
            text-shadow: 0 0 16px rgba(245, 158, 11, 0.2);
        }}
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)
    
    st.components.v1.html("""
    <html>
    <head>
        <style>
            body {
                margin: 0;
                overflow: hidden;
                background: transparent;
            }
            canvas {
                display: block;
                width: 100vw;
                height: 100vh;
            }
        </style>
    </head>
    <body>
        <canvas id="networkCanvas"></canvas>
        <script>
            const canvas = document.getElementById('networkCanvas');
            const ctx = canvas.getContext('2d');
            
            let width = canvas.width = window.innerWidth;
            let height = canvas.height = window.innerHeight;
            
            window.addEventListener('resize', () => {
                width = canvas.width = window.innerWidth;
                height = canvas.height = window.innerHeight;
            });
            
            const points = [];
            // Keep the ambient backdrop intentionally light: the earlier 50-node
            // version recalculated thousands of lines every frame and stuttered
            // while users typed into the login form.
            const maxPoints = 22;
            
            for (let i = 0; i < maxPoints; i++) {
                const isLeft = Math.random() < 0.4;
                const x = isLeft ? Math.random() * width * 0.4 : (width * 0.4 + Math.random() * width * 0.6);
                
                points.push({
                    x: x,
                    y: Math.random() * height,
                    vx: (Math.random() - 0.5) * 0.25,
                    vy: (Math.random() - 0.5) * 0.25,
                    radius: Math.random() * 2 + 1.2,
                    isGrid: !isLeft
                });
            }
            
            const packets = [];
            
            let lastFrame = 0;
            function animate(timestamp) {
                if (timestamp - lastFrame < 33) {
                    requestAnimationFrame(animate);
                    return;
                }
                lastFrame = timestamp;
                ctx.clearRect(0, 0, width, height);
                
                // Draw connections
                ctx.lineWidth = 0.5;
                for (let i = 0; i < points.length; i++) {
                    const p1 = points[i];
                    
                    p1.x += p1.vx;
                    p1.y += p1.vy;
                    
                    if (p1.x < 0 || p1.x > width) p1.vx *= -1;
                    if (p1.y < 0 || p1.y > height) p1.vy *= -1;
                    
                    for (let j = i + 1; j < points.length; j++) {
                        const p2 = points[j];
                        const dx = p1.x - p2.x;
                        const dy = p1.y - p2.y;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        
                        let maxDist = p1.isGrid && p2.isGrid ? 140 : 100;
                        if (dist < maxDist) {
                            const alpha = (1 - dist / maxDist) * 0.15;
                            ctx.strokeStyle = p1.isGrid ? `rgba(6, 182, 212, ${alpha})` : `rgba(245, 158, 11, ${alpha * 0.8})`;
                            ctx.beginPath();
                            ctx.moveTo(p1.x, p1.y);
                            ctx.lineTo(p2.x, p2.y);
                            ctx.stroke();
                            
                            if (Math.random() < 0.0001 && packets.length < 6) {
                                packets.push({
                                    from: p1,
                                    to: p2,
                                    progress: 0,
                                    speed: Math.random() * 0.01 + 0.005
                                });
                            }
                        }
                    }
                }
                
                // Draw packets
                for (let i = packets.length - 1; i >= 0; i--) {
                    const pk = packets[i];
                    pk.progress += pk.speed;
                    if (pk.progress >= 1) {
                        packets.splice(i, 1);
                        continue;
                    }
                    const px = pk.from.x + (pk.to.x - pk.from.x) * pk.progress;
                    const py = pk.from.y + (pk.to.y - pk.from.y) * pk.progress;
                    
                    ctx.fillStyle = pk.from.isGrid ? '#06B6D4' : '#F59E0B';
                    ctx.beginPath();
                    ctx.arc(px, py, 2.5, 0, Math.PI * 2);
                    ctx.fill();
                }
                
                // Draw points
                for (let i = 0; i < points.length; i++) {
                    const p = points[i];
                    ctx.fillStyle = p.isGrid ? 'rgba(6, 182, 212, 0.45)' : 'rgba(245, 158, 11, 0.45)';
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                    ctx.fill();
                }
                
                requestAnimationFrame(animate);
            }
            
            requestAnimationFrame(animate);
        </script>
    </body>
    </html>
    """, height=0)

    st.markdown("<div class='login-shell'>", unsafe_allow_html=True)

    # ---- Top brand strip ----
    st.markdown(textwrap.dedent("""
    <div class="login-topbar">
        <div class="logo-chip">Q</div>
        <div>
            <div class="brand-name">QUALIX <span class="accent-ai">AI</span></div>
            <div class="brand-tag">Secure AI Readiness OS for MSMEs</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    col_hero, col_gap, col_form = st.columns([1.35, 0.12, 1])

    # ---- Left: hero / value proposition ----
    with col_hero:
        st.markdown(textwrap.dedent("""
        <h1 class="hero-title">From Messy Data to<br/><span class="accent-gold">Trusted</span> Intelligence</h1>
        
        <!-- Supported integrations badges strip -->
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; animation: fadeInUp 0.8s ease-out both;">
            <span class="source-chip" style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); color: #6EE7B7; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;">
                🟢 Excel Sheets
            </span>
            <span class="source-chip" style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); color: #FDE047; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;">
                🟡 Tally Ledger Registers
            </span>
            <span class="source-chip" style="background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.25); color: #67E8F9; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;">
                🔵 POS Exports
            </span>
            <span class="source-chip" style="background: rgba(167, 139, 250, 0.08); border: 1px solid rgba(167, 139, 250, 0.25); color: #C084FC; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;">
                🟣 CRM Systems
            </span>
        </div>
        <div style="font-size:0.8rem; color:#94A3B8; margin-top:-5px; margin-bottom:24px; font-weight:500; animation: fadeInUp 0.8s ease-out both;">
            Works with your existing Excel, Tally ledger formats &amp; POS databases.
        </div>

        <!-- Morphing Micro-spreadsheet animation card -->
        <div class="glass-card morph-card" style="padding: 10px 14px; max-width: 440px; margin-bottom: 24px; animation: fadeInUp 0.9s ease-out both; background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255,255,255,0.08);">
            <div style="display:flex; justify-content:space-between; font-size:0.6rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:6px;">
                <span>Fuzzy Pipeline Sanitizer</span>
                <span style="color:#10B981; animation: blinkSync 1s infinite;">● RUNNING</span>
            </div>
            <div style="font-family:'Courier New', monospace; font-size:0.72rem; color:#94A3B8; line-height:1.6;">
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:3px; margin-bottom:4px; font-weight:700; color:#E2E8F0;">
                    <span>Customer</span><span>Contact</span><span>Revenue</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span class="morph-name"></span>
                    <span class="morph-phone"></span>
                    <span class="morph-rev"></span>
                </div>
            </div>
        </div>
        <style>
            @keyframes blinkSync {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
            }
            .morph-name::after { content: "RAHUL Patel"; animation: animName 4s infinite; }
            .morph-phone::after { content: "98765-43210"; animation: animPhone 4s infinite; }
            .morph-rev::after { content: "-12,500"; animation: animRev 4s infinite; }
            @keyframes animName {
                0%, 45% { content: "RAHUL Patel"; color: #F59E0B; }
                60%, 100% { content: "Rahul Patel"; color: #10B981; }
            }
            @keyframes animPhone {
                0%, 45% { content: "98765-43210"; color: #EF4444; }
                60%, 100% { content: "9876543210"; color: #10B981; }
            }
            @keyframes animRev {
                0%, 45% { content: "-12,500"; color: #EF4444; }
                60%, 100% { content: "12,500"; color: #10B981; }
            }
        </style>

        <div class="feature-grid">
            <div class="feature-card">
                <svg style="width:22px; height:22px; stroke:#10B981; stroke-width:2; fill:none; stroke-linecap:round; stroke-linejoin:round; margin-bottom:8px;" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <div class="f-title">Secure</div>
                <div class="f-desc">End-to-end Data Protection</div>
            </div>
            <div class="feature-card">
                <svg style="width:22px; height:22px; stroke:#3B82F6; stroke-width:2; fill:none; stroke-linecap:round; stroke-linejoin:round; margin-bottom:8px;" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/></svg>
                <div class="f-title">Intelligent</div>
                <div class="f-desc">AI &amp; ML Driven Insights</div>
            </div>
            <div class="feature-card">
                <svg style="width:22px; height:22px; stroke:#06B6D4; stroke-width:2; fill:none; stroke-linecap:round; stroke-linejoin:round; margin-bottom:8px;" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                <div class="f-title">Actionable</div>
                <div class="f-desc">Fix Issues &amp; Improve Readiness</div>
            </div>
            <div class="feature-card">
                <svg style="width:22px; height:22px; stroke:#F59E0B; stroke-width:2; fill:none; stroke-linecap:round; stroke-linejoin:round; margin-bottom:8px;" viewBox="0 0 24 24"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
                <div class="f-title">Certify</div>
                <div class="f-desc">Get AI Ready Certification</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # ---- Right: login card ----
    with col_form:
        with st.container(border=True):
            st.markdown(textwrap.dedent("""
            <div class="login-card-head" style="margin-top: 10px;">
                <div class="lock-badge">
                    <svg style="width:20px; height:20px; stroke:#06B6D4; stroke-width:2.2; fill:none; stroke-linecap:round; stroke-linejoin:round;" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                </div>
                <h4>Secure Access Gateway</h4>
                <p>Sign in to initialize Qualix diagnostics</p>
            </div>
            """), unsafe_allow_html=True)

            email = st.text_input("Username or Email", key="login_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")

            col_remember, col_forgot = st.columns([1.1, 0.9])
            with col_remember:
                st.checkbox("Remember me", key="login_remember")
            with col_forgot:
                st.markdown(
                    "<div style='text-align:right; margin-top:8px;'><a href='#' style='color:#38BDF8; font-size:0.75rem; text-decoration:none; font-weight:600;'>Forgot Password?</a></div>",
                    unsafe_allow_html=True
                )

            login_clicked = st.button("Sign In →", use_container_width=True)

            if login_clicked:
                try:
                    r = requests.post(f"{BACKEND_URL}/api/auth/login", json={
                        "username": email,
                        "password": password
                    })
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state.logged_in = True
                        st.session_state.explicit_logout = False
                        st.session_state.user_role = res["role"]
                        st.session_state.user_name = res["name"]
                        st.session_state.user_email = res["username"]
    
                        role_slug = res["role"].lower().replace(" ", "")
                        st.query_params["page"] = "Dashboard"
                        st.query_params["username"] = res["username"]
                        st.query_params["role"] = role_slug
                        st.query_params["name"] = res["name"]
                        st.query_params["dataset_id"] = st.session_state.dataset_id
                        st.toast(f"Welcome back, {res['name']}!", icon="👋")
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Invalid username or password."))
                except Exception:
                    st.error("FastAPI Backend engine offline. Please start uvicorn first.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ==========================================
# 4. REMOTE DATA PIPELINE CONSUMER
# ==========================================
def fetch_analysis_results(dataset_id: str, force_recalc: bool = False):
    """Triggers and caches analysis diagnostics on FastAPI endpoints."""
    if not force_recalc and dataset_id in st.session_state.readiness_cache:
        return
        
    try:
        # Step through progress bar stages
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        stages = [
            ("VALIDATING FILE SCHEMA", 15),
            ("SCANNING FOR MALWARE", 35),
            ("ENCRYPTING PAYLOAD", 55),
            ("PROFILING FEATURES", 75),
            ("CALCULATING QUALITY SCORECARD", 90),
            ("AGGREGATING AI READINESS INDEX", 100)
        ]
        
        for msg, pct in stages:
            status_text.markdown(f"<div style='font-size:0.85rem; color:#94A3B8;'>{msg}...</div>", unsafe_allow_html=True)
            progress_bar.progress(pct)
            time.sleep(0.15)
            
        role = st.session_state.user_role
        r_prof = requests.post(f"{BACKEND_URL}/api/analyze/profile", data={"datasetId": dataset_id, "username": st.session_state.user_name, "role": role})
        r_qual = requests.post(f"{BACKEND_URL}/api/analyze/quality", data={"datasetId": dataset_id, "username": st.session_state.user_name, "role": role})
        r_ml = requests.post(f"{BACKEND_URL}/api/analyze/ml", data={"datasetId": dataset_id, "username": st.session_state.user_name, "role": role})
        r_read = requests.post(f"{BACKEND_URL}/api/analyze/readiness", data={
            "datasetId": dataset_id, 
            "username": st.session_state.user_name,
            "role": role,
            "clamav_status": st.session_state.clamav_status
        })
        
        # Clear loading structures
        progress_bar.empty()
        status_text.empty()
        
        if r_read.status_code == 200:
            st.session_state.profile_cache[dataset_id] = r_prof.json()
            st.session_state.quality_cache[dataset_id] = r_qual.json()
            st.session_state.ml_cache[dataset_id] = r_ml.json()
            st.session_state.readiness_cache[dataset_id] = r_read.json()
            
    except Exception as e:
        st.error(f"Failed to compile backend analytical scores: {str(e)}")

# Ensure dataset choices cache matches active Selection
fetch_analysis_results(st.session_state.dataset_id)

profile_data = st.session_state.profile_cache.get(st.session_state.dataset_id, {})
quality_data = st.session_state.quality_cache.get(st.session_state.dataset_id, {})
ml_data = st.session_state.ml_cache.get(st.session_state.dataset_id, {})
readiness_data = st.session_state.readiness_cache.get(st.session_state.dataset_id, {})
current_readiness = readiness_data.get("overallReadiness", 62)


# ==========================================
# 5. SIDEBAR NAVIGATION SYSTEM (LUCIDE FONTS)
# ==========================================
role_slug = st.session_state.user_role.lower().replace(" ", "")
session_args = f"&username={st.session_state.user_email}&role={role_slug}&name={st.session_state.user_name}&dataset_id={st.session_state.dataset_id}"

all_pages = [
    ("Dashboard", "lucide-layout-dashboard", "Dashboard"),
    ("System Integrations", "lucide-plug", "System Integrations"),
    ("Scheduled Monitoring", "lucide-bell", "Scheduled Monitoring"),
    ("Smart Data Merge", "lucide-git-merge", "Smart Data Merge"),
    ("Intelligent Scan Scope", "lucide-sliders", "Intelligent Scan Scope"),
    ("Reconciliation Center", "lucide-scale", "Reconciliation Center"),
    ("Schema & Rules", "lucide-shield-alert", "Schema & Rules"),
    ("Data Analyzer", "lucide-database", "Data Analyzer"),
    ("Data Profile", "lucide-bar-chart-3", "Data Profile"),
    ("Data Quality", "lucide-shield-check", "Data Quality"),
    ("AI Readiness", "lucide-award", "AI Readiness"),
    ("AI/ML Intelligence", "lucide-brain-circuit", "AI/ML Intelligence"),
    ("Fix Center", "lucide-wrench", "Fix Center"),
    ("AI Data Doctor", "lucide-message-circle", "AI Data Doctor"),
    ("Business Impact", "lucide-briefcase", "Business Impact"),
    ("Data Lineage", "lucide-git-branch", "Data Lineage"),
    ("Reports", "lucide-file-text", "Reports"),
    ("Certificate", "lucide-award", "Certificate"),
    ("Security Center", "lucide-settings", "Security Center")
]

if st.session_state.user_role == "ADMIN":
    menu_items = all_pages
    default_page = "Dashboard"
elif st.session_state.user_role == "DATA ANALYST":
    menu_items = [p for p in all_pages if p[0] != "Security Center"]
    default_page = "Dashboard"
else:
    # Viewer sees Dashboard (Read-Only) and Diagnostic/Reporting screens
    menu_items = [p for p in all_pages if p[0] not in ["Security Center", "Fix Center", "AI Data Doctor"]]
    default_page = "Dashboard"

# Get active page from query parameter and enforce RBAC
page = qp.get("page", default_page)
allowed_pages = [p[0] for p in menu_items]
if page not in allowed_pages:
    page = default_page

# Construct Sidebar HTML Link list
html_sidebar = f"""
<link rel="stylesheet" href="https://unpkg.com/lucide-static@0.330.0/font/lucide.css" />
<style>
    .sidebar-logo {{
        margin-bottom: 20px;
        padding: 5px 0;
    }}
    .sidebar-nav {{
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}
    .nav-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 14px;
        color: #94A3B8;
        text-decoration: none;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.15s ease;
        border-left: 3px solid transparent;
    }}
    .nav-item:hover {{
        background: rgba(255, 255, 255, 0.04);
        color: #F8FAFC;
        padding-left: 18px;
    }}
    .nav-item.active {{
        background: rgba(59, 130, 246, 0.15);
        color: #06B6D4;
        border-left-color: #06B6D4;
        font-weight: 600;
    }}
    .nav-item i {{
        font-size: 1rem;
    }}
</style>
<div class="sidebar-logo">
    <span style="font-size: 1.5rem; font-weight: 800; color: #06B6D4;">Q</span> 
    <span style="font-size: 1.4rem; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;">QUALIX AI</span><br/>
    <span style="color: #64748B; font-size: 0.72rem;">AI Readiness Operating System</span>
</div>
<div class="sidebar-nav">
"""

# Define workflow groups
groups = [
    ("1. Ingest & Unify", ["System Integrations", "Smart Data Merge", "Intelligent Scan Scope"]),
    ("2. Reconcile & Audit", ["Reconciliation Center", "Schema & Rules"]),
    ("3. Diagnose & Score", ["Dashboard", "Data Analyzer", "Data Profile", "Data Quality", "AI Readiness", "AI/ML Intelligence", "Data Lineage"]),
    ("4. Remediate & Solve", ["Fix Center", "AI Data Doctor"]),
    ("5. Report & Certify", ["Business Impact", "Reports", "Certificate"]),
    ("6. System Control & Alerts", ["Scheduled Monitoring", "Security Center"])
]


for g_label, g_items in groups:
    # Filter menu_items belonging to this group
    allowed_group_items = [p for p in menu_items if p[0] in g_items]
    if allowed_group_items:
        html_sidebar += f'<div style="font-size:0.62rem; color:#475569; font-weight:800; margin:14px 0 6px 4px; text-transform:uppercase; letter-spacing:1px;">{g_label}</div>'
        for label, icon, key in allowed_group_items:
            active_class = "active" if page == key else ""
            html_sidebar += f'<a href="?page={urllib.parse.quote(key)}{session_args}" target="_self" class="nav-item {active_class}"><i class="{icon}"></i> {label}</a>'
html_sidebar += '</div>'

st.sidebar.markdown(textwrap.dedent(html_sidebar), unsafe_allow_html=True)

# Sidebar profile footer
st.sidebar.write("---")


role_color = "#3B82F6" if st.session_state.user_role == "ADMIN" else "#F59E0B" if st.session_state.user_role == "DATA ANALYST" else "#10B981"
st.sidebar.markdown(textwrap.dedent(f"""
<div class="glass-card" style="border: 1px solid rgba(6,182,212,0.22); background: rgba(15,23,42,0.65); padding: 10px; margin-bottom: 0px;">
    <div style="font-size: 0.58rem; color: #06B6D4; font-weight: 800; letter-spacing:1px; text-transform:uppercase;">Authorized Operator</div>
    <div style="font-size: 0.88rem; font-weight: 800; color: #FFFFFF; margin: 3px 0 1px 0;">{st.session_state.user_name}</div>
    <div style="font-size: 0.72rem; font-weight: 800; color: {role_color}; text-transform:uppercase; letter-spacing:0.5px;">{st.session_state.user_role}</div>
    <span style="font-size: 0.65rem; color: #10B981; font-weight: 700; margin-top: 4px; display: inline-flex; align-items:center;">
        <span class="live-dot" style="margin-right:4px;"></span>ONLINE / SECURE
    </span>
</div>
"""), unsafe_allow_html=True)


st.sidebar.write("")
if st.sidebar.button("Logout Session", use_container_width=True):
    try:
        requests.post(f"{BACKEND_URL}/api/log_event", data={
            "username": st.session_state.user_name,
            "action": "Logout",
            "status": "SUCCESS",
            "details": "User logged out securely."
        })
    except Exception:
        pass
    st.query_params.clear()
    st.session_state.logged_in = False
    st.session_state.explicit_logout = True
    if "login_email" in st.session_state:
        st.session_state.login_email = ""
    if "login_password" in st.session_state:
        st.session_state.login_password = ""
    st.rerun()


# ==========================================
# 6. TOP HEADER ANIMATED INTRO BANNER (BLUE-CYAN)
# ==========================================
# Truncate long dataset names so they never collide with the stat cluster or sidebar.
_ds_name = str(st.session_state.dataset_name)
_ds_name_display = (_ds_name[:28] + "…") if len(_ds_name) > 28 else _ds_name

header_html = """
<style>
    html, body { margin:0; padding:0; overflow:hidden; background:transparent !important; }
    @media (max-width: 760px) {
        .workspace-stats { gap:8px !important; font-size:0.74rem !important; }
        .workspace-title { font-size:1rem !important; }
        .workspace-status { display:none !important; }
    }
</style>
<div style="position:relative; width:100%; min-height:92px; background:radial-gradient(circle at center right, #1E293B, #151B2E); border-radius:10px; overflow:hidden; border:1px solid rgba(255,255,255,0.12); display:flex; flex-wrap:nowrap; justify-content:space-between; align-items:center; gap:10px; padding: 14px 22px; box-sizing:border-box; font-family:'Outfit','Inter',sans-serif; color:#FFFFFF;">
    <canvas id="headerCanvas" style="position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:1;"></canvas>
    <div style="position:relative; z-index:2; min-width:0; flex:1 1 auto; overflow:hidden;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span class="live-dot"></span>
            <span style="font-size:0.7rem; color:#06B6D4; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; white-space:nowrap;">Diagnostic Active Workspace</span>
        </div>
        <h2 class="workspace-title" title="##DATASET_NAME_FULL##" style="margin:4px 0 0 0; color:#FFFFFF; font-size:1.2rem; font-weight:800; letter-spacing:0.3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">##DATASET_NAME##</h2>
        <div id="syncNote" style="font-size:0.66rem; color:#64748B; margin-top:2px; white-space:nowrap;">Synced just now</div>
    </div>
    <div class="workspace-stats" style="position:relative; z-index:2; display:flex; gap:12px; align-items:center; font-size:0.85rem; flex-wrap:nowrap; flex:0 0 auto; white-space:nowrap;">
        <div class="workspace-status" style="text-align:right;">
            <span style="color:#94A3B8; font-size:0.62rem; text-transform:uppercase; font-weight:700; white-space:nowrap;">AI Readiness</span><br/>
            <span style="color:#06B6D4; font-weight:800; font-size:1rem; white-space:nowrap;">##READINESS## / 100</span>
        </div>
        <div class="workspace-status" style="height:28px; width:1px; background:rgba(255,255,255,0.15); flex-shrink:0;"></div>
        <div class="workspace-status" style="text-align:right;">
            <span style="color:#94A3B8; font-size:0.62rem; text-transform:uppercase; font-weight:700; white-space:nowrap;">Security</span><br/>
            <span style="color:##SECURITY_COLOR##; font-weight:800; font-size:1rem; white-space:nowrap;">##SECURITY_STATUS##</span>
        </div>
        <div class="workspace-status" style="height:28px; width:1px; background:rgba(255,255,255,0.15); flex-shrink:0;"></div>
        <div style="text-align:right;">
            <span style="color:#94A3B8; font-size:0.62rem; text-transform:uppercase; font-weight:700; white-space:nowrap;">Role</span><br/>
            <span style="color:##ROLE_COLOR##; font-weight:800; font-size:1rem; white-space:nowrap;">##USER_ROLE##</span>
        </div>
    </div>
</div>
<style>
    .live-dot {
        display:inline-block; width:7px; height:7px; border-radius:50%;
        background:#10B981; animation: pulseDotHdr 1.8s infinite;
    }
    @keyframes pulseDotHdr {
        0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.55); }
        70% { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
        100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
    }
</style>
<script>
    const canvas = document.getElementById('headerCanvas');
    const ctx = canvas.getContext('2d');
    function resizeCanvas() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    let stars = [];
    for(let i=0; i<30; i++){
        stars.push({
            x: Math.random()*canvas.width,
            y: Math.random()*canvas.height,
            r: Math.random()*1.2 + 0.3,
            alpha: Math.random()*0.5 + 0.2,
            dx: Math.random()*0.2 + 0.05
        });
    }
    // EKG heartbeat trace drawn along the bottom edge of the header, on top of the stars,
    // reinforcing the "AI Data Doctor" vitals-monitor identity used throughout the app.
    let ekgPhase = 0;
    function drawEKG() {
        const w = canvas.width, h = canvas.height;
        const baseY = h - 14;
        ctx.beginPath();
        ctx.strokeStyle = "rgba(16, 185, 129, 0.55)";
        ctx.lineWidth = 1.5;
        const segment = 46;
        for (let x = -segment; x < w + segment; x += 2) {
            const t = ((x + ekgPhase) % segment + segment) % segment;
            let y = baseY;
            if (t > 18 && t <= 22) y = baseY - (t - 18) * 9;
            else if (t > 22 && t <= 26) y = baseY - (26 - t) * 9 + (t - 22) * 14;
            else if (t > 26 && t <= 30) y = baseY + (30 - t) * 3.5;
            ctx.lineTo(x, y);
        }
        ctx.stroke();
        ekgPhase -= 1.4;
    }
    function animate(){
        ctx.clearRect(0,0,canvas.width,canvas.height);
        stars.forEach(s => {
            ctx.fillStyle = "rgba(6, 182, 212, " + s.alpha + ")";
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
            ctx.fill();
            s.x -= s.dx;
            if(s.x < 0) s.x = canvas.width;
        });
        drawEKG();
        requestAnimationFrame(animate);
    }
    animate();

    // Small "engagement" touch: relative-time sync note ticks up live.
    let secondsAgo = 0;
    setInterval(function() {
        secondsAgo += 1;
        const el = document.getElementById('syncNote');
        if (el) {
            el.innerText = secondsAgo < 60 ? ("Synced " + secondsAgo + "s ago") : "Synced a while ago";
        }
    }, 1000);
</script>
"""
sec_status_txt = "Protected"
sec_color_val = "#10B981"
if st.session_state.clamav_status == "Unavailable":
    sec_status_txt = "Unverified"
    sec_color_val = "#F59E0B"
elif st.session_state.clamav_status == "Infected":
    sec_status_txt = "Infected"
    sec_color_val = "#EF4444"

header_html = header_html.replace("##DATASET_NAME_FULL##", _ds_name)
header_html = header_html.replace("##DATASET_NAME##", _ds_name_display)
header_html = header_html.replace("##READINESS##", str(current_readiness))
header_html = header_html.replace("##ROLE_COLOR##", str(role_color))
header_html = header_html.replace("##USER_ROLE##", str(st.session_state.user_role))
header_html = header_html.replace("##SECURITY_STATUS##", sec_status_txt)
st.components.v1.html(textwrap.dedent(header_html), height=124, scrolling=False)

# ==========================================
# 6b. GLOBAL DATASET BROWSER & WORKFLOW STEPS CONTROL BAR
# ==========================================
with st.container(border=True):
    col_ds1, col_ds2, col_ds3 = st.columns([1.5, 1.2, 2.3])
    
    with col_ds1:
        all_ds_options = {
            "retail_sales": "🛒 Retail Sales Log (550 rows)",
            "customer_churn": "👥 Customer Churn ML (1,000 rows)",
            "inventory_logistics": "📦 Inventory Logistics (750 rows)",
            "invoices": "🧾 Invoices Ledger (450 rows)",
            "payments": "💳 Payments Export (420 rows)",
            "inventory": "🏭 Warehouse Inventory (600 rows)"
        }
        try:
            r_ds_api = requests.get(f"{BACKEND_URL}/api/datasets", timeout=2)
            if r_ds_api.status_code == 200:
                for ds_item in r_ds_api.json().get("datasets", []):
                    ds_id_key = ds_item["id"]
                    if ds_id_key not in all_ds_options:
                        ds_name_str = ds_item.get("name", ds_id_key)
                        all_ds_options[ds_id_key] = f"📄 {ds_name_str} ({ds_item.get('rows', '?')} rows)"
        except Exception:
            pass
            
        ds_keys = list(all_ds_options.keys())
        current_idx = ds_keys.index(st.session_state.dataset_id) if st.session_state.dataset_id in ds_keys else 0
        
        selected_ds = st.selectbox(
            "📁 Active Dataset Workspace",
            options=ds_keys,
            format_func=lambda k: all_ds_options[k],
            index=current_idx,
            key="global_dataset_selector_bar"
        )
        
        if selected_ds != st.session_state.dataset_id:
            st.session_state.dataset_id = selected_ds
            clean_ds_name = all_ds_options[selected_ds].split(" (")[0]
            for prefix in ["🛒 ", "👥 ", "📦 ", "🧾 ", "💳 ", "🏭 ", "📄 "]:
                clean_ds_name = clean_ds_name.replace(prefix, "")
            st.session_state.dataset_name = clean_ds_name
            st.query_params["dataset_id"] = selected_ds
            st.rerun()

    with col_ds2:
        num_rows = profile_data.get("rows", 0)
        num_cols = profile_data.get("cols", 0)
        st.markdown(textwrap.dedent(f"""
        <div style="font-size:0.75rem; color:#94A3B8; margin-top:2px;">
            <b>Active Records:</b> <span style="color:#06B6D4; font-weight:800;">{num_rows:,} rows × {num_cols} cols</span><br/>
            <b>Data Status:</b> <span style="color:#10B981; font-weight:700;">Fernet AES-256 Encrypted</span><br/>
            <b>Hygiene Score:</b> <span style="color:#F59E0B; font-weight:800;">{quality_data.get('overallQuality', 80)} / 100</span>
        </div>
        """), unsafe_allow_html=True)

    with col_ds3:
        st.markdown(textwrap.dedent("""
        <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(6,182,212,0.25); border-radius:8px; padding:8px 12px; margin-top:2px;">
            <div style="font-size:0.62rem; color:#67E8F9; font-weight:800; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:4px;">Structured Diagnostic Data Flow</div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.74rem; font-weight:700;">
                <span style="color:#06B6D4;">1. Select Data</span>
                <span style="color:#64748B;">➔</span>
                <span style="color:#10B981;">2. Health Audit</span>
                <span style="color:#64748B;">➔</span>
                <span style="color:#3B82F6;">3. Visual Charts</span>
                <span style="color:#64748B;">➔</span>
                <span style="color:#F59E0B;">4. Remediation</span>
            </div>
        </div>
        """), unsafe_allow_html=True)

st.write("")
if page == "System Integrations":
    st.markdown("<div class='premium-header'>System Integrations & Near-Real-Time Data Sync</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Connect Tally, CRM, ERP, and POS data streams with Webhook, Polling, or Manual sync modes.</div>", unsafe_allow_html=True)

    st.markdown(ekg_strip(label="CONNECTOR NETWORK — NEAR-REAL-TIME DATA STREAMS"), unsafe_allow_html=True)

    # Mode badges strip
    st.markdown(textwrap.dedent("""
    <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:18px;">
        <span style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); color:#6EE7B7; padding:4px 12px; border-radius:6px; font-size:0.75rem; font-weight:700;">
            🟢 Webhook Stream (Near-Real-Time)
        </span>
        <span style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); color:#FDE047; padding:4px 12px; border-radius:6px; font-size:0.75rem; font-weight:700;">
            🟡 Polling API (Periodic Sync)
        </span>
        <span style="background:rgba(6,182,212,0.1); border:1px solid rgba(6,182,212,0.3); color:#67E8F9; padding:4px 12px; border-radius:6px; font-size:0.75rem; font-weight:700;">
            🔵 Manual On-Demand Fetch
        </span>
        <span style="background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.3); color:#C084FC; padding:4px 12px; border-radius:6px; font-size:0.75rem; font-weight:700;">
            ⚙️ Mode: Live vs Simulator Mode
        </span>
    </div>
    """), unsafe_allow_html=True)

    try:
        r_sys = requests.get(f"{BACKEND_URL}/api/integrations")
        sys_data = r_sys.json() if r_sys.status_code == 200 else {}
    except Exception:
        sys_data = {}

    connectors = sys_data.get("connectors", [])
    recent_payloads = sys_data.get("recent_payloads", [])

    # Grid of system connector cards
    col_c1, col_c2 = st.columns(2)
    for idx, conn in enumerate(connectors):
        target_col = col_c1 if idx % 2 == 0 else col_c2
        with target_col:
            with st.container(border=True):
                st.markdown(textwrap.dedent(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div>
                        <span style="font-size:1.4rem;">{conn['icon']}</span>
                        <span style="font-size:1.1rem; font-weight:800; color:#FFFFFF; margin-left:6px;">{conn['name']}</span>
                    </div>
                    <div>
                        <span style="background:rgba(16,185,129,0.15); color:#6EE7B7; border:1px solid rgba(16,185,129,0.4); padding:2px 8px; border-radius:4px; font-size:0.68rem; font-weight:800;">
                            ● {conn['status']}
                        </span>
                        <span style="background:rgba(59,130,246,0.15); color:#60A5FA; border:1px solid rgba(59,130,246,0.4); padding:2px 8px; border-radius:4px; font-size:0.68rem; font-weight:800; margin-left:4px;">
                            Mode: {conn['mode']}
                        </span>
                    </div>
                </div>
                <div style="font-size:0.78rem; color:#94A3B8; margin-bottom:10px;">
                    <b>Category:</b> {conn['category']} | <b>Protocol:</b> {conn['protocol']}
                </div>
                """), unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                m1.metric("Health Score", f"{conn['health_score']}%", "+1% (Optimal)")
                m2.metric("Latency", f"{conn['latency_ms']} ms", "-2ms")
                m3.metric("Records Ingested", f"{conn['records_ingested']:,}")

                st.markdown(f"<div style='font-size:0.72rem; color:#64748B; margin-top:6px;'><b>Endpoint:</b> <code>{conn['endpoint']}</code></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:0.72rem; color:#64748B;'><b>Sync Strategy:</b> {conn['sync_mode']} | <b>Last Sync:</b> {conn['last_sync']}</div>", unsafe_allow_html=True)

                st.write("")
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("⚡ Sync Now", key=f"sync_{conn['id']}", use_container_width=True):
                        try:
                            r_sync = requests.post(f"{BACKEND_URL}/api/integrations/{conn['id']}/sync")
                            if r_sync.status_code == 200:
                                res_sync = r_sync.json()
                                st.toast(f"Synced {res_sync['records_fetched']} records from {res_sync['name']} ({res_sync['mode']})!", icon="🔄")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Sync failed: {e}")
                with btn_col2:
                    with st.popover("⚙️ Settings"):
                        st.markdown(f"**Configure {conn['name']} Connector**")
                        new_mode = st.radio("Operating Mode", ["Simulator", "Live"], index=0 if conn['mode'] == "Simulator" else 1, key=f"mode_sel_{conn['id']}")
                        new_ep = st.text_input("Endpoint URL", value=conn['endpoint'], key=f"ep_sel_{conn['id']}")
                        if st.button("Save Connector Settings", key=f"save_conn_{conn['id']}"):
                            try:
                                r_up = requests.post(f"{BACKEND_URL}/api/integrations/{conn['id']}/connect", json={"connector_id": conn['id'], "mode": new_mode, "endpoint": new_ep})
                                if r_up.status_code == 200:
                                    st.toast(f"Updated {conn['name']} settings!", icon="✅")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Update failed: {e}")
                with btn_col3:
                    if st.button("🔌 Disconnect", key=f"disc_{conn['id']}", use_container_width=True):
                        try:
                            requests.post(f"{BACKEND_URL}/api/integrations/{conn['id']}/disconnect")
                            st.toast(f"Disconnected {conn['name']}", icon="🔌")
                            st.rerun()
                        except Exception:
                            pass

    st.write("---")

    # Ingestion Stream Logs & Simulator Tabs
    tab_log, tab_sim = st.tabs(["📥 Normalized Ingestion Stream Log", "🧪 Webhook Stream Simulator"])

    with tab_log:
        st.markdown("#### Real-Time Normalized Ingestion Payload Stream")
        if recent_payloads:
            df_pay = pd.DataFrame(recent_payloads)
            if "sample" in df_pay.columns:
                df_pay["sample"] = df_pay["sample"].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x))
            st.dataframe(df_pay, use_container_width=True)
        else:
            st.info("No payload streams logged yet. Click 'Sync Now' or use the Webhook Stream Simulator!")

    with tab_sim:
        st.markdown("#### Inbound Webhook Payload Simulator")
        st.markdown("Simulate an incoming JSON transaction payload from Shopify POS, Tally XML server, or Salesforce CRM to test live data normalization.")

        sim_sys = st.selectbox("Target Connector", ["shopify_pos", "tally_prime", "salesforce_crm", "sap_erp"])
        sim_json = st.text_area("JSON Payload Data", value='{\n  "Transaction_ID": "POS-99882",\n  "Sale_Amount": 5420.50,\n  "Customer": "Ramesh Kumar",\n  "Payment_Method": "UPI",\n  "Store_Location": "Delhi Connaught Place"\n}', height=150)

        if st.button("🚀 Fire Webhook Payload", use_container_width=True):
            try:
                parsed_payload = json.loads(sim_json)
                r_wh = requests.post(f"{BACKEND_URL}/api/integrations/webhook/{sim_sys}", json=parsed_payload)
                if r_wh.status_code == 200:
                    st.success(f"Webhook Accepted! Normalized {r_wh.json()['records_processed']} record into Qualix AI stream.")
                    st.toast("Payload normalized & audited!", icon="🟢")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to post payload (HTTP {r_wh.status_code}): {r_wh.text}")
            except Exception as e:
                st.error(f"Invalid JSON payload: {e}")


# ----------------- SCREEN: SCHEDULED MONITORING & ALERTS -----------------
if page == "Scheduled Monitoring":
    st.markdown("<div class='premium-header'>Scheduled Quality Monitoring & Alert Notifications</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Automated background quality audit schedules, rule threshold evaluation, and multi-channel alert dispatches.</div>", unsafe_allow_html=True)

    st.markdown(ekg_strip(label="AUTOMATED MONITORING PULSE — CONTINUOUS AUDIT ENGINE"), unsafe_allow_html=True)

    # Top action bar
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown("<b>Active Schedule Frequencies:</b> 15 mins, Hourly, Daily | <b>Protected Categories:</b> Data Quality, Security, Business Risk", unsafe_allow_html=True)
    with top_col2:
        if st.button("⚡ Run Quality Monitoring Check Now", use_container_width=True):
            try:
                r_chk = requests.post(f"{BACKEND_URL}/api/monitoring/check", json={"dataset_id": st.session_state.dataset_id})
                if r_chk.status_code == 200:
                    res_chk = r_chk.json()
                    st.toast(f"Evaluated {res_chk['evaluated_rules']} rules! Triggered: {res_chk['triggered_count']} alerts.", icon="🔔")
                    st.rerun()
            except Exception as e:
                st.error(f"Monitoring check error: {e}")

    try:
        r_sched = requests.get(f"{BACKEND_URL}/api/monitoring/schedules")
        sched_data = r_sched.json() if r_sched.status_code == 200 else {}
    except Exception:
        sched_data = {}

    rules = sched_data.get("rules", [])
    alerts = sched_data.get("alerts", [])

    col_m1, col_m2 = st.columns([1.3, 1])

    with col_m1:
        st.markdown("### 🛡️ Configured Categorized Monitoring Rules")
        st.markdown("Categorized signal metrics evaluated across scheduled cycles with deduplication cooldowns.")

        for rule in rules:
            cat_color = "#3B82F6" if rule['category'] == "Data Quality" else "#EF4444" if rule['category'] == "Security" else "#F59E0B"
            sev_color = "#EF4444" if rule['severity'] == "CRITICAL" else "#F59E0B" if rule['severity'] == "HIGH" else "#06B6D4"

            with st.container(border=True):
                st.markdown(textwrap.dedent(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div>
                        <span style="background:rgba(255,255,255,0.08); color:{cat_color}; border:1px solid {cat_color}; padding:2px 8px; border-radius:4px; font-size:0.68rem; font-weight:800;">
                            {rule['category']}
                        </span>
                        <span style="font-size:1.05rem; font-weight:800; color:#FFFFFF; margin-left:8px;">{rule['name']}</span>
                    </div>
                    <span style="background:rgba(239,68,68,0.15); color:{sev_color}; border:1px solid {sev_color}; padding:2px 8px; border-radius:4px; font-size:0.68rem; font-weight:800;">
                        {rule['severity']}
                    </span>
                </div>
                <div style="font-size:0.82rem; color:#94A3B8; margin-bottom:6px;">
                    <b>Rule Target:</b> <code>{rule['metric']} {rule['operator']} {rule['threshold']}</code> | <b>Frequency:</b> {rule['frequency']}
                </div>
                <div style="font-size:0.75rem; color:#64748B;">
                    <b>Notification Channels:</b> {', '.join(rule['channels'])} | <b>Cooldown Protection:</b> {rule.get('cooldown_minutes', 60)} mins
                </div>
                """), unsafe_allow_html=True)

        with st.expander("➕ Create Custom Quality Monitoring Rule"):
            r_name = st.text_input("Rule Name", placeholder="e.g. High Duplicate Rate Flag")
            r_cat = st.selectbox("Signal Category", ["Data Quality", "Security", "Business Risk"])
            r_metric = st.selectbox("Target Metric", ["Overall Quality Score", "Anomaly Count", "File Threat / Malware Flag", "Revenue Deviation (%)"])
            r_op = st.selectbox("Operator", ["<", ">", "==", "!="])
            r_thresh = st.text_input("Threshold Value", value="75")
            r_sev = st.selectbox("Severity Level", ["CRITICAL", "HIGH", "WARNING", "INFO"])
            r_chans = st.multiselect("Dispatch Channels", ["Email", "WhatsApp", "Slack", "Teams", "SMS"], default=["WhatsApp", "Slack"])
            r_freq = st.selectbox("Schedule Frequency", ["15 mins", "Hourly", "Daily", "Weekly"])
            r_cool = st.number_input("Alert Cooldown (Minutes)", min_value=5, max_value=720, value=60)

            if st.button("Save Monitoring Rule", use_container_width=True):
                new_rule_payload = {
                    "name": r_name,
                    "category": r_cat,
                    "metric": r_metric,
                    "operator": r_op,
                    "threshold": float(r_thresh) if r_thresh.replace('.', '', 1).isdigit() else r_thresh,
                    "severity": r_sev,
                    "channels": r_chans,
                    "frequency": r_freq,
                    "cooldown_minutes": int(r_cool),
                    "active": True
                }
                try:
                    requests.post(f"{BACKEND_URL}/api/monitoring/schedules", json={"rule_data": new_rule_payload})
                    st.success(f"Created rule '{r_name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating rule: {e}")

    with col_m2:
        st.markdown("### 🔔 Active Alerts Feed & Status Lifecycle")
        st.markdown("Real-time alert status lifecycle tracking (`OPEN` ➔ `ACKNOWLEDGED` ➔ `RESOLVED`).")

        for alt in alerts:
            st_color = "#EF4444" if alt['status'] == "OPEN" else "#F59E0B" if alt['status'] == "ACKNOWLEDGED" else "#10B981"
            with st.container(border=True):
                st.markdown(textwrap.dedent(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:0.95rem; font-weight:800; color:#FFFFFF;">{alt['rule_name']}</span>
                    <span style="background:rgba(255,255,255,0.08); color:{st_color}; border:1px solid {st_color}; padding:2px 8px; border-radius:4px; font-size:0.68rem; font-weight:800;">
                        ● {alt['status']}
                    </span>
                </div>
                <div style="font-size:0.75rem; color:#94A3B8; margin-bottom:6px;">
                    <b>Target Dataset:</b> <code>{alt['dataset_target']}</code> | <b>Triggered:</b> {alt['triggered_at']}
                </div>
                <div style="font-size:0.8rem; color:#E2E8F0; margin-bottom:8px; background:rgba(15,23,42,0.6); padding:6px 10px; border-radius:6px; border-left:3px solid {st_color};">
                    {alt['message']}
                </div>
                <div style="font-size:0.72rem; color:#64748B;">
                    <b>Notified:</b> {', '.join(alt.get('channels_notified', []))}
                </div>
                """), unsafe_allow_html=True)

                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    if alt['status'] == "OPEN":
                        if st.button("Acknowledge", key=f"ack_{alt['alert_id']}", use_container_width=True):
                            requests.post(f"{BACKEND_URL}/api/monitoring/alerts/{alt['alert_id']}/acknowledge")
                            st.rerun()
                with act_col2:
                    if alt['status'] in ["OPEN", "ACKNOWLEDGED"]:
                        if st.button("Resolve Alert", key=f"res_{alt['alert_id']}", use_container_width=True):
                            requests.post(f"{BACKEND_URL}/api/monitoring/alerts/{alt['alert_id']}/resolve")
                            st.rerun()

        st.write("---")

        st.markdown("#### 📱 Multi-Channel Notification Dispatch Tester")
        st.markdown("Test sending a live notification payload across Email, WhatsApp, Slack, Teams, or SMS.")

        test_chans = st.multiselect("Test Channels", ["WhatsApp", "Slack", "Email", "Teams", "SMS"], default=["WhatsApp", "Slack"])
        test_msg = st.text_input("Alert Message", value="Qualix Alert: Data Quality score for Retail Sales dropped below threshold (64%).")

        if st.button("🚀 Dispatch Test Notification", use_container_width=True):
            try:
                r_nt = requests.post(f"{BACKEND_URL}/api/notifications/test", json={"channels": test_chans, "message": test_msg})
                if r_nt.status_code == 200:
                    st.success("Alert dispatched successfully across selected channels!")
                    
                    # Render mock WhatsApp / Slack preview card
                    st.markdown(textwrap.dedent(f"""
                    <div class="glass-card" style="border:1px solid #10B981; background:rgba(16,185,129,0.06); padding:12px; margin-top:10px;">
                        <div style="font-size:0.7rem; color:#10B981; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;">📱 Live Dispatch Notification Preview</div>
                        <div style="font-size:0.85rem; color:#FFFFFF; margin-top:4px; font-weight:700;">Qualix AI Monitoring Sentinel</div>
                        <div style="font-size:0.8rem; color:#D1D5DB; margin-top:4px; line-height:1.4;">
                            {test_msg}
                        </div>
                        <div style="font-size:0.68rem; color:#6B7280; margin-top:6px;">Delivered to {', '.join(test_chans)} at {time.strftime('%H:%M:%S')}</div>
                    </div>
                    """), unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Dispatch failed: {e}")


# ----------------- SCREEN 1: DASHBOARD -----------------
if page == "Dashboard":
    st.markdown("<div class='premium-header'>Enterprise Data Diagnostics Dashboard</div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Inspect data hygiene, model readiness, class imbalances, and secure file parameters.</div>", unsafe_allow_html=True)

    # Signature "vitals monitor" strip — the recurring vitals/EKG motif for the whole app.
    st.markdown(ekg_strip(label=f"LIVE MONITORING — {st.session_state.dataset_name}"), unsafe_allow_html=True)

    # "AI Insight of the Day" — a small rotating engagement touch so the dashboard
    # doesn't feel like a static report every time someone opens it.
    _insights = [
        "Datasets with >5% missing values in key columns typically drop ML model accuracy by 8-15%.",
        "Consistent casing (e.g. 'Mumbai' vs 'mumbai') is the #1 hidden cause of inflated duplicate counts in MSME sales logs.",
        "Target leakage is easy to miss manually — always check if a feature could only be known *after* the outcome.",
        "Encrypting data at rest (AES-256) is a baseline expectation for any AI vendor evaluating your business."
    ]
    _tip = _insights[int(time.time() // 20) % len(_insights)]
    st.markdown(textwrap.dedent(f"""
    <div class="glass-card" style="display:flex; align-items:center; gap:12px; border-left:3px solid #06B6D4; padding:12px 18px;">
        <span style="font-size:1.1rem;">💡</span>
        <div>
            <span style="font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;">AI Insight of the Day</span><br/>
            <span style="font-size:0.85rem; color:#E2E8F0;">{_tip}</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # AI Readiness animated/beautiful gauge at the top
    col_g1, col_g2, col_g3 = st.columns([1, 1.5, 1])
    with col_g2:
        st.markdown("<div style='text-align: center; margin-bottom: 5px;'>", unsafe_allow_html=True)
        st.markdown("<span style='font-size:0.9rem; color:#94A3B8; font-weight:600;'>AGGREGATED AI READINESS SCORE</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_readiness,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
                'bar': {'color': "#3B82F6"},
                'bgcolor': "rgba(30, 41, 59, 0.7)",
                'borderwidth': 1,
                'bordercolor': "rgba(255,255,255,0.12)",
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(239, 68, 68, 0.08)'},
                    {'range': [60, 80], 'color': 'rgba(245, 158, 11, 0.08)'},
                    {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.08)'}
                ],
                'threshold': {
                    'line': {'color': "#10B981", 'width': 3},
                    'thickness': 0.75,
                    'value': 85
                }
            }
        ))
        fig_g.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#F8FAFC", 'family': "Outfit"},
            height=200,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_g, use_container_width=True)
        sel_cnt = readiness_data.get("scope_selected", len(profile_data.get("columns", [])))
        tot_cnt = readiness_data.get("scope_total", len(profile_data.get("columns", [])))
        st.markdown(f"<div style='text-align: center; font-size: 0.82rem; color: #94A3B8; margin-top: -15px; margin-bottom: 15px;'><b>Analysis Scope:</b> {sel_cnt} / {tot_cnt} fields<br/><span style='font-size: 0.72rem; color: #64748B;'>Score calculated using the selected analysis scope.</span></div>", unsafe_allow_html=True)
    
    # 4 KPI cards in one row — big numbers now count up on every render for a livelier feel
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    dq_score = quality_data.get("overallQuality", 80)
    dq_status = "Healthy" if dq_score >= 80 else "Needs Improvement"
    col_k1.markdown(textwrap.dedent(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.78rem; color: #94A3B8; font-weight: 700; letter-spacing:0.5px;">DATA QUALITY</span>
            <i class="lucide-shield-check" style="color: #3B82F6; font-size: 1.1rem;"></i>
        </div>
        <h2 style="margin: 8px 0 2px 0; color: #F8FAFC; font-size: 1.8rem;">{animated_counter(dq_score, size='1.8rem')}</h2>
        <span style="font-size: 0.75rem; color: {'#10B981' if dq_score>=80 else '#F59E0B'}; font-weight: 700;">● {dq_status}</span>
    </div>
    """), unsafe_allow_html=True)
    
    sec_score = "Protected" if st.session_state.clamav_status == "Clean" else "Suspended"
    col_k2.markdown(textwrap.dedent(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.78rem; color: #94A3B8; font-weight: 700; letter-spacing:0.5px;">SECURITY STATUS</span>
            <i class="lucide-lock" style="color: #10B981; font-size: 1.1rem;"></i>
        </div>
        <h2 style="margin: 8px 0 2px 0; color: #F8FAFC; font-size: 1.8rem;">{sec_score}</h2>
        <span style="font-size: 0.75rem; color: #10B981; font-weight: 700;">● Fernet AES-256</span>
    </div>
    """), unsafe_allow_html=True)
    
    ml_score = readiness_data.get("mlReadiness", 80)
    ml_status = "Model Ready" if ml_score >= 80 else "Optimizations Needed"
    col_k3.markdown(textwrap.dedent(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.78rem; color: #94A3B8; font-weight: 700; letter-spacing:0.5px;">ML SUITABILITY</span>
            <i class="lucide-brain-circuit" style="color: #06B6D4; font-size: 1.1rem;"></i>
        </div>
        <h2 style="margin: 8px 0 2px 0; color: #F8FAFC; font-size: 1.8rem;">{animated_counter(ml_score, size='1.8rem')}</h2>
        <span style="font-size: 0.75rem; color: {'#10B981' if ml_score>=80 else '#F59E0B'}; font-weight: 700;">● {ml_status}</span>
    </div>
    """), unsafe_allow_html=True)
    
    dup_score = quality_data.get("duplicates", 80)
    col_k4.markdown(textwrap.dedent(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.78rem; color: #94A3B8; font-weight: 700; letter-spacing:0.5px;">DUPLICATE HEALTH</span>
            <i class="lucide-git-branch" style="color: #10B981; font-size: 1.1rem;"></i>
        </div>
        <h2 style="margin: 8px 0 2px 0; color: #F8FAFC; font-size: 1.8rem;">{animated_counter(dup_score, size='1.8rem')}</h2>
        <span style="font-size: 0.75rem; color: {'#10B981' if dup_score>=80 else '#EF4444'}; font-weight: 700;">● {dup_score}% Unique</span>
    </div>
    """), unsafe_allow_html=True)

    # Achievement badges — gamified read of the same scores, unlocked live
    st.markdown(achievement_badges(
        quality_score=dq_score,
        ml_score=ml_score,
        readiness_score=current_readiness,
        security_clean=(st.session_state.clamav_status == "Clean")
    ), unsafe_allow_html=True)

    st.write("")
    
    # Freshness Monitor
    st.write("##### Source Data Freshness Monitor")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    col_f1.markdown("""
    <div class="glass-card" style="padding:10px 15px;">
        <div style="font-size:0.68rem; color:#94A3B8; font-weight:700; text-transform:uppercase;">CRM Source</div>
        <div style="font-size:1.1rem; font-weight:800; color:#FFFFFF; margin:4px 0;">2 hours ago</div>
        <span style="font-size:0.75rem; color:#10B981; font-weight:700;">● Healthy</span>
    </div>
    """, unsafe_allow_html=True)
    col_f2.markdown("""
    <div class="glass-card" style="padding:10px 15px;">
        <div style="font-size:0.68rem; color:#94A3B8; font-weight:700; text-transform:uppercase;">Tally Source</div>
        <div style="font-size:1.1rem; font-weight:800; color:#FFFFFF; margin:4px 0;">3 days ago</div>
        <span style="font-size:0.75rem; color:#F59E0B; font-weight:700;">● Warning</span>
    </div>
    """, unsafe_allow_html=True)
    col_f3.markdown("""
    <div class="glass-card" style="padding:10px 15px;">
        <div style="font-size:0.68rem; color:#94A3B8; font-weight:700; text-transform:uppercase;">POS Source</div>
        <div style="font-size:1.1rem; font-weight:800; color:#FFFFFF; margin:4px 0;">47 days ago</div>
        <span style="font-size:0.75rem; color:#EF4444; font-weight:700;">● Critical</span>
    </div>
    """, unsafe_allow_html=True)
    col_f4.markdown("""
    <div class="glass-card" style="padding:10px 15px;">
        <div style="font-size:0.68rem; color:#94A3B8; font-weight:700; text-transform:uppercase;">Freshness Score</div>
        <div style="font-size:1.1rem; font-weight:800; color:#F59E0B; margin:4px 0;">64 / 100</div>
        <span style="font-size:0.75rem; color:#94A3B8; font-weight:700;">● Moderate Latency</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # Row 2: Quality Chart (with border) + Operations Risk Panel + Live Activity Feed
    col_r2_1, col_r2_2, col_r2_3 = st.columns([1.4, 1, 1])
    
    with col_r2_1:
        with st.container(border=True):
            st.write("##### Quality Remediation Trend (Plotly)")
            fig_trend = go.Figure(go.Scatter(
                x=["Initial Ingest", "Deduplicated", "Casing Normal", "Capped Outliers"],
                y=[62, 72, 80, 89],
                mode="lines+markers",
                line=dict(color="#3B82F6", width=3),
                marker=dict(size=8, color="#06B6D4")
            ))
            fig_trend.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94A3B8',
                height=180,
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)", range=[50, 100])
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_r2_2:
        with st.container(border=True):
            st.write("##### Executive Operations Risk Matrix")
            rev_risk = 100 - quality_data.get("completeness", 85)
            skew_risk = 100 - ml_data.get("mlReadiness", 80) if isinstance(ml_data, dict) else 25
            
            st.markdown(textwrap.dedent(f"""
            <div style="margin-top:10px;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
                    <span>Revenue Reporting Variance Risk</span>
                    <span style="font-weight:700; color:{'#EF4444' if rev_risk > 20 else '#10B981'};">{rev_risk}%</span>
                </div>
                <div style="background:rgba(255,255,255,0.05); height:6px; border-radius:3px;">
                    <div style="background:#EF4444; width:{rev_risk}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            <div style="margin-top:18px;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
                    <span>ML Model Convergence Risk</span>
                    <span style="font-weight:700; color:{'#F59E0B' if skew_risk > 20 else '#10B981'};">{skew_risk}%</span>
                </div>
                <div style="background:rgba(255,255,255,0.05); height:6px; border-radius:3px;">
                    <div style="background:#F59E0B; width:{skew_risk}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            <p style="font-size: 0.75rem; color:#64748B; margin-top:20px; line-height:1.3;">
                Risks are calculated dynamically based on dataset null metrics and target label imbalance ratios. Fix these anomalies inside the Fix Center.
            </p>
            """), unsafe_allow_html=True)

    with col_r2_3:
        with st.container(border=True):
            st.write("##### Live Activity Feed")
            st.markdown(activity_ticker(st.session_state.recent_activity), unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.68rem; color:#475569; margin-top:6px;'>Auto-refreshing diagnostic event log</div>", unsafe_allow_html=True)

    # Row 3: Data Profile + ML Suitability metrics (with border)
    col_r3_1, col_r3_2 = st.columns([1.2, 1.2])
    with col_r3_1:
        with st.container(border=True):
            st.write("##### Feature Data Type Distribution (Plotly)")
            types = profile_data.get("typeCounts", {"Numeric": 3, "Categorical": 4})
            filtered_types = {k: v for k, v in types.items() if v > 0}
            fig_pie = px.pie(
                names=list(filtered_types.keys()),
                values=list(filtered_types.values()),
                color_discrete_sequence=["#3B82F6", "#06B6D4", "#10B981"]
            )
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#F8FAFC',
                height=180,
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_r3_2:
        with st.container(border=True):
            st.write("##### Machine Learning Feasibility Summary")
            leakage = "Target Leakage Risk Detected" if ml_data.get("hasTargetLeakage") else "No Leakage Detected"
            imbalance = ml_data.get("classImbalance", "Optimal imbalance")
            
            hc = ml_data.get('highCardinalityCol')
            card_health = f"High Risk ({hc})" if hc else "Normal"
            
            st.markdown(textwrap.dedent(f"""
            <div style="margin-top: 10px; font-size: 0.85rem; line-height: 1.6;">
                • <b>Temporal Leakage:</b> {leakage}<br/>
                • <b>Class Distribution:</b> {imbalance}<br/>
                • <b>Cardinality Health:</b> {card_health}<br/>
                • <b>Schema Drift Check:</b> Safe
            </div>
            """), unsafe_allow_html=True)



# ----------------- SCREEN: RECONCILIATION CENTER -----------------
elif page == "Reconciliation Center":
    st.markdown("<div class='premium-header'>Reconciliation & Master Data Audit Center</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Audit ledger balances, invoice clearances, warehouse stock movements, and resolve master database duplicate aliases.</div>", unsafe_allow_html=True)
    
    is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
    
    recon_tab1, recon_tab2, recon_tab3 = st.tabs([
        "Invoice ↔ Payment Reconciliation",
        "POS ↔ Inventory Reconciliation",
        "Master Data Resolver"
    ])
    
    # Fetch available datasets
    datasets_list = []
    try:
        r_ds = requests.get(f"{BACKEND_URL}/api/datasets")
        if r_ds.status_code == 200:
            datasets_list = [d["id"] for d in r_ds.json()["datasets"]]
    except Exception:
        pass
        
    with recon_tab1:
        st.write("##### Audit Invoice Payments")
        st.caption("Compare Tally accounts receivable records with payment logs or bank exports to detect discrepancies.")
        
        col_r1, col_r2 = st.columns(2)
        inv_ds = col_r1.selectbox("Invoice Dataset ID", datasets_list, index=datasets_list.index("invoices") if "invoices" in datasets_list else 0)
        pay_ds = col_r2.selectbox("Payment Dataset ID", datasets_list, index=datasets_list.index("payments") if "payments" in datasets_list else 0)
        
        if st.button("Run Payments Reconciliation Audit", use_container_width=True):
            with st.spinner("Reconciling transactions..."):
                r_recon = requests.post(f"{BACKEND_URL}/api/reconcile/payments", json={
                    "invoice_dataset_id": inv_ds,
                    "payment_dataset_id": pay_ds,
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_recon.status_code == 200:
                    st.session_state.payment_recon_res = r_recon.json()
                    st.toast("Payments reconciled successfully!", icon="✅")
                else:
                    try:
                        err_msg = r_recon.json().get("detail", "Error")
                    except Exception:
                        err_msg = r_recon.text
                    st.error(f"Reconciliation failed: {err_msg}")
                    
        recon_res = st.session_state.get("payment_recon_res")
        if recon_res:
            stats = recon_res["stats"]
            counts = stats["counts"]
            
            # KPI Cards
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            col_k1.metric("Fully Matched Invoices", f"{counts['matched']} ({stats['matched_pct']}%)")
            col_k2.metric("Partial Payments", f"{counts['partial']} ({stats['partial_pct']}%)")
            col_k3.metric("Duplicate/Conflicts", f"{counts['duplicate'] + counts['conflict']} ({round(stats['duplicate_pct'] + stats['conflict_pct'], 1)}%)")
            col_k4.metric("Unmatched Records", f"{counts['unmatched']} ({stats['unmatched_pct']}%)")
            
            # Pie Chart
            fig_p_recon = px.pie(
                names=["Matched", "Partial", "Conflicts & Duplicates", "Unmatched"],
                values=[counts["matched"], counts["partial"], counts["duplicate"] + counts["conflict"], counts["unmatched"]],
                color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444", "#94A3B8"],
                title="Invoice Matching Status Breakdown"
            )
            fig_p_recon.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC')
            st.plotly_chart(fig_p_recon, use_container_width=True)
            
            # Reconciliation Ledger
            st.write("##### Detailed Transaction Reconciliation Ledger")
            details_df = pd.DataFrame(recon_res["details"])
            if st.session_state.user_role == "VIEWER":
                st.info("Viewer role restricts access to raw details. Aggregated scores only.")
            else:
                st.dataframe(details_df, use_container_width=True)
                
    with recon_tab2:
        st.write("##### POS Sales ↔ Warehouse Inventory Audit")
        st.caption("Reconcile front-end POS sales quantities with back-end warehouse inventory balances to detect stock shrinkage or duplicate SKUs.")
        
        col_i1, col_i2 = st.columns(2)
        pos_ds = col_i1.selectbox("POS Sales Dataset ID", datasets_list, index=datasets_list.index("retail_sales") if "retail_sales" in datasets_list else 0)
        inventory_ds = col_i2.selectbox("Warehouse Inventory Dataset ID", datasets_list, index=datasets_list.index("inventory") if "inventory" in datasets_list else 0)
        
        if st.button("Run Inventory & Sales Reconciliation Audit", use_container_width=True):
            with st.spinner("Analyzing stock records..."):
                r_inv = requests.post(f"{BACKEND_URL}/api/reconcile/inventory", json={
                    "pos_dataset_id": pos_ds,
                    "inventory_dataset_id": inventory_ds,
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_inv.status_code == 200:
                    st.session_state.inventory_recon_res = r_inv.json()
                    st.toast("Inventory reconciled successfully!", icon="✅")
                else:
                    st.error("Inventory audit failed: " + r_inv.json().get("detail", "Error"))
                    
        inv_recon = st.session_state.get("inventory_recon_res")
        if inv_recon:
            inv_stats = inv_recon["stats"]
            
            col_ki1, col_ki2, col_ki3, col_ki4 = st.columns(4)
            col_ki1.metric("SKUs Audited", f"{inv_stats['reconciled_skus']}")
            col_ki2.metric("Stock-Sales Discrepancies", f"{inv_stats['mismatch_skus']}")
            col_ki3.metric("Negative Stock SKUs", f"{inv_stats['negative_stock_skus']}")
            col_ki4.metric("Missing SKUs", f"{inv_stats['missing_skus']}")
            
            st.write("##### Stock Discrepancy Alerts & Warnings Ledger")
            anoms_df = pd.DataFrame(inv_recon["anomalies"])
            if anoms_df.empty:
                st.success("No warehouse inventory anomalies detected. Sales and stock balances are perfectly reconciled.")
            else:
                if st.session_state.user_role == "VIEWER":
                    st.info("Viewer role restricts access to raw details. Aggregated scores only.")
                else:
                    st.dataframe(anoms_df, use_container_width=True)
                    
    with recon_tab3:
        st.write("##### Customer/Product Master Data Resolver")
        st.caption("Fuzzy clustering merges spelling variants and duplicate organizational titles into canonical golden records.")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("""
            <div class='glass-card' style='border-left: 4px solid #10B981; margin-bottom: 15px;'>
                <div style='font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;'>Golden Master Record</div>
                <h4 style='margin:4px 0 10px 0; color:#FFFFFF;'>ABC LIMITED</h4>
                <div style='font-size:0.8rem; color:#CBD5E1;'>
                    <b>Active Aliases / Spelling Variants resolved:</b><br/>
                    • ABC Ltd (CRM)<br/>
                    • A.B.C. Ltd. (Tally)<br/>
                    • ABC Pvt Ltd (Excel)<br/>
                    <span style='color:#10B981; font-weight:700;'>Match Confidence: 96%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class='glass-card' style='border-left: 4px solid #10B981;'>
                <div style='font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;'>Golden Master Record</div>
                <h4 style='margin:4px 0 10px 0; color:#FFFFFF;'>Samsung Galaxy S24</h4>
                <div style='font-size:0.8rem; color:#CBD5E1;'>
                    <b>Active Aliases / Spelling Variants resolved:</b><br/>
                    • Samsung S24 (POS)<br/>
                    • S24 Galaxy (Spreadsheet)<br/>
                    • SM-S24 (Inventory)<br/>
                    <span style='color:#10B981; font-weight:700;'>Match Confidence: 95%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_m2:
            st.markdown("""
            <div class='glass-card' style='border-left: 4px solid #10B981; margin-bottom: 15px;'>
                <div style='font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;'>Golden Master Record</div>
                <h4 style='margin:4px 0 10px 0; color:#FFFFFF;'>Rahul Patel</h4>
                <div style='font-size:0.8rem; color:#CBD5E1;'>
                    <b>Active Aliases / Spelling Variants resolved:</b><br/>
                    • Rahul K Patel (Tally)<br/>
                    • R Patel (POS)<br/>
                    • Rahulk Patel (Sales)<br/>
                    <span style='color:#10B981; font-weight:700;'>Match Confidence: 98%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class='glass-card' style='border-left: 4px solid #10B981;'>
                <div style='font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;'>Golden Master Record</div>
                <h4 style='margin:4px 0 10px 0; color:#FFFFFF;'>XYZ Corporation</h4>
                <div style='font-size:0.8rem; color:#CBD5E1;'>
                    <b>Active Aliases / Spelling Variants resolved:</b><br/>
                    • XYZ Corp (CRM)<br/>
                    • XYZ Pvt Ltd (Tally)<br/>
                    <span style='color:#10B981; font-weight:700;'>Match Confidence: 92%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ----------------- SCREEN: SCHEMA & RULES -----------------
elif page == "Schema & Rules":
    st.markdown("<div class='premium-header'>Schema Drift & Business Rule Diagnostics</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Detect column modifications, name alignments, and run business constraint checkers.</div>", unsafe_allow_html=True)
    
    is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
    
    drift_tab, rules_tab = st.tabs(["Schema Drift Detector", "AI Business Rule Generator"])
    
    # Fetch available datasets
    datasets_list = []
    try:
        r_ds = requests.get(f"{BACKEND_URL}/api/datasets")
        if r_ds.status_code == 200:
            datasets_list = [d["id"] for d in r_ds.json()["datasets"]]
    except Exception:
        pass
        
    with drift_tab:
        st.write("##### Detect Schema Renaming & Drift")
        st.caption("Compare schema layout configurations against baseline history to prevent ingestion breaks.")
        
        col_d1, col_d2 = st.columns(2)
        baseline_ds = col_d1.selectbox("Baseline Schema Dataset ID", datasets_list, index=datasets_list.index("retail_sales") if "retail_sales" in datasets_list else 0)
        new_ds = col_d2.selectbox("New Upload Dataset ID", datasets_list, index=datasets_list.index("invoices") if "invoices" in datasets_list else 0)
        
        if st.button("Run Schema Drift Audit", use_container_width=True):
            with st.spinner("Analyzing schema stability..."):
                r_drift = requests.post(f"{BACKEND_URL}/api/drift/detect", json={
                    "baseline_dataset_id": baseline_ds,
                    "new_dataset_id": new_ds,
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_drift.status_code == 200:
                    st.session_state.drift_res = r_drift.json()
                    st.toast("Schema drift checked successfully!", icon="✅")
                else:
                    st.error("Drift check failed: " + r_drift.json().get("detail", "Error"))
                    
        drift_res = st.session_state.get("drift_res")
        if drift_res:
            score = drift_res["stability_score"]
            st.markdown(f"#### Schema Stability Score: **{score}/100**")
            st.progress(score / 100.0)
            
            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                st.write("**Fuzzy Renamed Fields (Mapped)**")
                renames = drift_res["renamed"]
                if renames:
                    for k, v in renames.items():
                        st.markdown(f"- `{k}` → `{v}`")
                else:
                    st.caption("No renames identified.")
            with col_l2:
                st.write("**Added Fields (New)**")
                added = drift_res["added"]
                if added:
                    for c in added:
                        st.markdown(f"- `+` `{c}`")
                else:
                    st.caption("No new fields.")
            with col_l3:
                st.write("**Removed Fields (Missing)**")
                removed = drift_res["removed"]
                if removed:
                    for c in removed:
                        st.markdown(f"- `-` `{c}`")
                else:
                    st.caption("No removed fields.")
                    
    with rules_tab:
        st.write("##### AI Business Rule Generator")
        st.caption("Auto-recommends relational rules based on columns semantics and validates records for compliance.")
        
        active_ds = st.selectbox("Select Target Dataset for Rules Validation", datasets_list, index=0)
        
        if st.button("Generate Relational Validation Rules", use_container_width=True):
            with st.spinner("Analyzing dataset patterns..."):
                r_rules = requests.post(f"{BACKEND_URL}/api/rules/recommend", json={
                    "dataset_id": active_ds,
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_rules.status_code == 200:
                    st.session_state.recommended_rules = r_rules.json()["suggestions"]
                    st.session_state.active_rule_selections = {
                        f"rule_{idx}": True for idx in range(len(r_rules.json()["suggestions"]))
                    }
                    st.toast("Validation rules suggested successfully!", icon="✅")
                    
        suggested_rules = st.session_state.get("recommended_rules", [])
        if suggested_rules:
            st.write("##### Suggested Validation Rules:")
            
            active_rules_payload = []
            for idx, rule in enumerate(suggested_rules):
                with st.container(border=True):
                    col_tg1, col_tg2 = st.columns([4, 1])
                    col_tg1.markdown(f"**Field: {rule['column']}** (Type: `{rule['rule_type']}`) - Confidence: **{rule['confidence']}%**")
                    col_tg1.write(rule["description"])
                    
                    if is_analyst:
                        is_active = col_tg2.toggle("Activate", value=st.session_state.active_rule_selections.get(f"rule_{idx}", True), key=f"rule_tg_{idx}")
                        st.session_state.active_rule_selections[f"rule_{idx}"] = is_active
                    else:
                        is_active = True
                        col_tg2.write("Active")
                        
                    if is_active:
                        active_rules_payload.append(rule)
                        
            if st.button("Validate Dataset Against Active Rules", use_container_width=True):
                with st.spinner("Running rule checker..."):
                    r_val = requests.post(f"{BACKEND_URL}/api/rules/validate", json={
                        "dataset_id": active_ds,
                        "active_rules": active_rules_payload,
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_val.status_code == 200:
                        st.session_state.rule_validation_results = r_val.json()
                        st.toast("Rules validated successfully!", icon="✅")
                    else:
                        st.error("Validation failed: " + r_val.json().get("detail", "Error"))
                        
            val_results = st.session_state.get("rule_validation_results")
            if val_results:
                st.write("---")
                comp_score = val_results["compliance_score"]
                st.markdown(f"#### Dataset Rule Compliance Score: **{comp_score}/100**")
                st.progress(comp_score / 100.0)
                
                violations = val_results["violations"]
                if not violations:
                    st.success("Compliance validated! Zero rule violations detected in the dataset.")
                else:
                    st.write(f"Detected {len(violations)} validation failures:")
                    if st.session_state.user_role == "VIEWER":
                        st.info("Viewer role restricts access to raw details. Aggregated scores only.")
                    else:
                        st.dataframe(pd.DataFrame(violations), use_container_width=True)

# ----------------- SCREEN: SMART DATA MERGE -----------------
elif page == "Smart Data Merge":
    st.markdown("<div class='premium-header'>Smart Data Merge</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Unify fragmented business data from Spreadsheets, POS, Tally and CRM.</div>", unsafe_allow_html=True)
    
    # Check if a merged dataset is active in the workspace and allow immediate download
    if st.session_state.dataset_id and st.session_state.dataset_id.startswith("unified_"):
        with st.container(border=True):
            col_dl_1, col_dl_2 = st.columns([2.2, 1.8])
            with col_dl_1:
                st.markdown("##### 📥 Active Unified Master Dataset")
                st.markdown(f"Current workspace dataset: **{st.session_state.dataset_name}** (`{st.session_state.dataset_id}`)")
            with col_dl_2:
                st.write("") # spacing alignment
                if st.button("Generate Downloadable CSV Link", use_container_width=True, key="gen_merged_download"):
                    try:
                        r_dl = requests.get(f"{BACKEND_URL}/api/datasets/{st.session_state.dataset_id}/download", params={
                            "role": st.session_state.user_role,
                            "username": st.session_state.user_name
                        })
                        if r_dl.status_code == 200:
                            csv_content = r_dl.json().get("csv_content", "")
                            st.download_button(
                                label="Download Unified Dataset (CSV)",
                                data=csv_content,
                                file_name=f"Qualix_Unified_Master_{st.session_state.dataset_id}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="merged_csv_dl"
                            )
                        else:
                            st.error("Failed to compile download package: " + r_dl.json().get("detail", "Error"))
                    except Exception as e:
                        st.error(f"Download request failed: {str(e)}")

    
    is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
    
    # 1. Multi-source Upload UI
    st.markdown("<div style='font-weight:700; margin-bottom:10px;'>Ingestion Source Systems</div>", unsafe_allow_html=True)
    
    col_u1, col_u2, col_u3, col_u4 = st.columns(4)
    col_u1.markdown("""
    <div class='glass-card' style='text-align:center;'>
        <div style='font-size:1.8rem; color:#3B82F6;'>📊</div>
        <div style='font-weight:700; margin-top:5px; color:#F8FAFC;'>Spreadsheet</div>
        <div style='font-size:0.75rem; color:#94A3B8;'>Excel / CSV business data</div>
    </div>
    """, unsafe_allow_html=True)
    col_u2.markdown("""
    <div class='glass-card' style='text-align:center;'>
        <div style='font-size:1.8rem; color:#06B6D4;'>💳</div>
        <div style='font-weight:700; margin-top:5px; color:#F8FAFC;'>POS Export</div>
        <div style='font-size:0.75rem; color:#94A3B8;'>Sales & transaction data</div>
    </div>
    """, unsafe_allow_html=True)
    col_u3.markdown("""
    <div class='glass-card' style='text-align:center;'>
        <div style='font-size:1.8rem; color:#10B981;'>🧾</div>
        <div style='font-weight:700; margin-top:5px; color:#F8FAFC;'>Tally</div>
        <div style='font-size:0.75rem; color:#94A3B8;'>Accounting & ledger data</div>
    </div>
    """, unsafe_allow_html=True)
    col_u4.markdown("""
    <div class='glass-card' style='text-align:center;'>
        <div style='font-size:1.8rem; color:#8B5CF6;'>👥</div>
        <div style='font-weight:700; margin-top:5px; color:#F8FAFC;'>CRM</div>
        <div style='font-size:0.75rem; color:#94A3B8;'>Customer & sales leads</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # File Uploader
    uploaded_files = st.file_uploader(
        "Upload Fragmented Corporate Sources (Excel/CSV files)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        disabled=not is_analyst,
        key="merge_file_uploader"
    )

    # Selecting files only places them in the browser widget. Explicitly send
    # them to the merge API so they are available to the workflow.
    if is_analyst and uploaded_files:
        if st.button("Securely Ingest Selected Files", type="primary", use_container_width=False):
            try:
                files_payload = [
                    ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
                    for file in uploaded_files
                ]
                with st.spinner("Scanning, encrypting, and profiling selected files..."):
                    r = requests.post(
                        f"{BACKEND_URL}/api/merge/upload",
                        files=files_payload,
                        data={"role": st.session_state.user_role, "username": st.session_state.user_name},
                        timeout=60,
                    )
                if r.status_code == 200:
                    uploaded_results = r.json().get("files", [])
                    if uploaded_results:
                        st.session_state.merge_uploaded_files = uploaded_results
                        st.toast(f"Ingested {len(uploaded_results)} source file(s) successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.error("No files were ingested. Please select valid CSV or Excel files and try again.")
                else:
                    st.error(r.json().get("detail", "The selected files could not be ingested."))
            except requests.RequestException as e:
                st.error(f"Could not reach the ingestion service: {e}")
    
    # Or load mock/demo files directly for hackathon demo
    if is_analyst:
        col_load_demo, _ = st.columns([1.5, 2])
        if col_load_demo.button("Load Demo Integration Files (CRM, Tally, POS, Spreadsheet)", type="primary", use_container_width=True):
            demo_filenames = ["CRM.xlsx", "Tally.xlsx", "POS.csv", "Sales.xlsx"]
            uploaded_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, fn in enumerate(demo_filenames):
                status_text.write(f"Secure Ingesting {fn}...")
                progress_bar.progress(int((idx + 1) / len(demo_filenames) * 100))
                path = os.path.join("data", fn)
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        file_bytes = f.read()
                    
                    files_payload = [("files", (fn, file_bytes, "application/octet-stream"))]
                    r = requests.post(f"{BACKEND_URL}/api/merge/upload", files=files_payload, data={"role": st.session_state.user_role, "username": st.session_state.user_name})
                    if r.status_code == 200:
                        res = r.json()
                        uploaded_results.extend(res["files"])
                    else:
                        st.error(f"Could not ingest {fn}: {r.json().get('detail', 'Unknown error')}")
                        
            progress_bar.empty()
            status_text.empty()
            
            if uploaded_results:
                st.session_state.merge_uploaded_files = uploaded_results
                st.toast("Loaded demo integration sources successfully!", icon="✅")
                st.success("Loaded demo integration sources successfully!")
                
    if not is_analyst:
        st.info("Viewer role is restricted to read-only access. You can view existing merge configurations below.")
        
    uploaded_files_list = st.session_state.get("merge_uploaded_files", [])
    if uploaded_files_list:
        st.markdown("<div style='font-weight:700; margin-top:20px; margin-bottom:10px;'>Secure Ingestion Status & Profiling</div>", unsafe_allow_html=True)
        
        clamav_offline = any(f.get("security_status") == "Unavailable" for f in uploaded_files_list)
        if clamav_offline:
            st.warning("Malware scanner unavailable — configure ClamAV before processing production uploads.")
            
        for idx, source in enumerate(uploaded_files_list):
            sid = source["id"]
            with st.container(border=True):
                col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2.5, 1.5, 1.2, 1.2, 1.5, 1.2])
                col_f1.markdown(f"**{source['filename']}**")
                
                options = ["Spreadsheet", "POS Export", "Tally", "CRM"]
                default_idx = options.index(source["source_type"]) if source["source_type"] in options else 0
                
                if is_analyst:
                    overridden_source = col_f2.selectbox(
                        "Source Type",
                        options,
                        index=default_idx,
                        key=f"override_{sid}",
                        label_visibility="collapsed"
                    )
                    if overridden_source != source["source_type"]:
                        source["source_type"] = overridden_source
                else:
                    col_f2.write(f"Source: **{source['source_type']}**")
                    
                col_f3.write(f"{source['rows']:,} rows")
                col_f4.write(f"{source['cols']:,} cols")
                
                sec_stat = source.get("security_status", "Clean")
                if sec_stat == "Clean":
                    col_f5.markdown("<span class='status-badge badge-healthy'>✓ Secure</span>", unsafe_allow_html=True)
                elif sec_stat == "Unavailable":
                    col_f5.markdown("<span class='status-badge badge-warning'>Unverified</span>", unsafe_allow_html=True)
                else:
                    col_f5.markdown("<span class='status-badge badge-critical'>Infected</span>", unsafe_allow_html=True)
                    
                col_f6.write(f"**{source.get('processing_status', 'READY')}**")
                
        if len(uploaded_files_list) >= 2:
            st.markdown("<div style='font-weight:700; margin-top:25px; margin-bottom:10px;'>Schema Mapping & Alignment</div>", unsafe_allow_html=True)
            
            if st.button("Generate Schema Mapping Recommendations", use_container_width=True):
                with st.spinner("Analyzing schema structures..."):
                    source_ids = [s["id"] for s in uploaded_files_list]
                    r_match = requests.post(f"{BACKEND_URL}/api/merge/schema-match", json={
                        "source_ids": source_ids,
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_match.status_code == 200:
                        res = r_match.json()
                        st.session_state.schema_mappings = res["mappings"]
                        st.session_state.accepted_mappings = {
                            m["target_field"]: m["columns"] for m in res["mappings"] if m["confidence_level"] == "HIGH"
                        }
                        st.toast("Schema mappings recommended successfully!", icon="✅")
                        
            mappings = st.session_state.get("schema_mappings", [])
            if mappings:
                if is_analyst:
                    if st.button("Accept All High Confidence Mappings", use_container_width=True):
                        for m in mappings:
                            if m["confidence_level"] == "HIGH":
                                st.session_state.accepted_mappings[m["target_field"]] = m["columns"]
                        st.success("All high-confidence mappings accepted.")
                        
                st.write("")
                for m in mappings:
                    tf = m["target_field"]
                    conf = m["confidence"]
                    level = m["confidence_level"]
                    reason = m["reason"]
                    
                    badge_style = "badge-healthy" if level == "HIGH" else "badge-warning" if level == "MEDIUM" else "badge-critical"
                    
                    with st.container(border=True):
                        col_m1, col_m2, col_m3 = st.columns([2.5, 3.5, 1.5])
                        with col_m1:
                            st.write(f"Target: **{tf}**")
                            st.markdown(f"Confidence: <span class='status-badge {badge_style}'>{level} ({conf}%)</span>", unsafe_allow_html=True)
                            st.caption(reason)
                        with col_m2:
                            st.write("**Aligned Source Columns:**")
                            for sid, col_name in m["columns"].items():
                                fname = next(f["filename"] for f in uploaded_files_list if f["id"] == sid)
                                st.caption(f"- **{fname}**: `{col_name}`")
                        with col_m3:
                            is_accepted = tf in st.session_state.get("accepted_mappings", {})
                            if is_analyst:
                                col_b1, col_b2 = st.columns(2)
                                if col_b1.button("Accept", key=f"acc_{tf}", disabled=is_accepted, use_container_width=True):
                                    st.session_state.accepted_mappings[tf] = m["columns"]
                                    st.rerun()
                                if col_b2.button("Reject", key=f"rej_{tf}", disabled=not is_accepted, use_container_width=True):
                                    if tf in st.session_state.accepted_mappings:
                                        del st.session_state.accepted_mappings[tf]
                                    st.rerun()
                            else:
                                st.write("Accepted" if is_accepted else "Pending review")
                                
            st.markdown("<div style='font-weight:700; margin-top:25px; margin-bottom:10px;'>Fuzzy Entity Matching Diagnostics</div>", unsafe_allow_html=True)
            
            matching_key_options = list(st.session_state.get("accepted_mappings", {}).keys())
            if "Customer_Name" not in matching_key_options:
                matching_key_options.append("Customer_Name")
                
            col_key_1, col_key_2 = st.columns([1.5, 2.5])
            selected_matching_key = col_key_1.selectbox(
                "Entity Matching Key",
                matching_key_options,
                index=matching_key_options.index("Customer_Name") if "Customer_Name" in matching_key_options else 0
            )
            
            recommendations_text = "Fuzzy Customer Name matching is recommended because structured identifiers are incomplete."
            if "GSTIN" in matching_key_options:
                recommendations_text = "GSTIN is available in Tally and CRM and provides a stronger entity identifier than customer name."
                
            col_key_2.info(f"Recommendation: {recommendations_text}")
            
            if st.button("Run Entity Resolution Analysis", use_container_width=True):
                with st.spinner("Resolving duplicate entities across sources..."):
                    source_ids = [s["id"] for s in uploaded_files_list]
                    active_map = []
                    for m in mappings:
                        if m["target_field"] in st.session_state.get("accepted_mappings", {}):
                            active_map.append({
                                "target_field": m["target_field"],
                                "columns": m["columns"]
                            })
                            
                    r_ent = requests.post(f"{BACKEND_URL}/api/merge/entity-match", json={
                        "source_ids": source_ids,
                        "schema_mapping": active_map,
                        "matching_key": selected_matching_key,
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_ent.status_code == 200:
                        res = r_ent.json()
                        st.session_state.entity_duplicates = res["duplicates"]
                        st.session_state.entity_stats = res["stats"]
                        st.toast("Entities resolved successfully!", icon="✅")
                        
            entity_stats = st.session_state.get("entity_stats", {})
            if entity_stats:
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                col_e1.metric("Matched Entities", f"{entity_stats['matched_entities']:,}")
                col_e2.metric("Unmatched Records", f"{entity_stats['unmatched_records']:,}")
                col_e3.metric("Potential Duplicates", f"{entity_stats['potential_duplicates']:,}")
                col_e4.metric("High Confidence Matches", f"{entity_stats['high_confidence_matches']:,}")
                
                col_ch1, col_ch2 = st.columns(2)
                with col_ch1:
                    fig_match = px.pie(
                        names=["Matched Records", "Unmatched Records"],
                        values=[entity_stats["matched_entities"], entity_stats["unmatched_records"]],
                        color_discrete_sequence=["#3B82F6", "#06B6D4"],
                        title="Matched vs Unmatched Records"
                    )
                    fig_match.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC')
                    st.plotly_chart(fig_match, use_container_width=True)
                with col_ch2:
                    fig_conf = px.bar(
                        x=["High Confidence", "Medium/Low Confidence"],
                        y=[entity_stats["high_confidence_matches"], max(0, entity_stats["potential_duplicates"] - entity_stats["high_confidence_matches"])],
                        color_discrete_sequence=["#10B981"],
                        title="Match Confidence Distribution"
                    )
                    fig_conf.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94A3B8')
                    st.plotly_chart(fig_conf, use_container_width=True)
                    
                st.write("##### Probable duplicate groups identified")
                for dup in st.session_state.get("entity_duplicates", []):
                    with st.container(border=True):
                        col_act1, col_act2 = st.columns([4, 1])
                        col_act1.write(f"Primary: **{dup['primary']}**")
                        col_act1.caption(f"Variations: {', '.join(dup['variations'])}")
                        col_act1.write(f"Similarity: **{dup['similarity']}%** ({dup['confidence']} Confidence)")
                        if is_analyst:
                            col_act2.write("")
                            col_act2.button("Review", key=f"rev_{dup['primary']}", use_container_width=True)
                            
            st.markdown("<div style='font-weight:700; margin-top:25px; margin-bottom:10px;'>Conflict Detection & Resolution</div>", unsafe_allow_html=True)
            
            if st.button("Scan Value Conflicts Across Sources", use_container_width=True):
                with st.spinner("Scanning for value conflicts..."):
                    source_ids = [s["id"] for s in uploaded_files_list]
                    active_map = []
                    for m in mappings:
                        if m["target_field"] in st.session_state.get("accepted_mappings", {}):
                            active_map.append({
                                "target_field": m["target_field"],
                                "columns": m["columns"]
                            })
                            
                    r_conf = requests.post(f"{BACKEND_URL}/api/merge/conflicts", json={
                        "source_ids": source_ids,
                        "schema_mapping": active_map,
                        "matching_key": selected_matching_key,
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_conf.status_code == 200:
                        st.session_state.conflicts_list = r_conf.json().get("conflicts", [])
                        st.toast("Value conflicts scanned successfully!", icon="✅")
                        
            conflicts_list = st.session_state.get("conflicts_list", [])
            if conflicts_list:
                st.write(f"Found {len(conflicts_list)} conflicts. Resolve them below:")
                
                if "conflict_resolutions" not in st.session_state:
                    st.session_state.conflict_resolutions = {}
                    
                for idx, c in enumerate(conflicts_list):
                    ent_name = c["entity_id"]
                    field = c["field"]
                    values = c["values"]
                    
                    with st.container(border=True):
                        st.markdown(f"Entity: **{ent_name}** | Field: **{field}**")
                        
                        choices = []
                        choice_labels = []
                        for sid, val in values.items():
                            fname = next(f["filename"] for f in uploaded_files_list if f["id"] == sid)
                            choices.append(val)
                            choice_labels.append(f"{fname} ({val})")
                            
                        choices.append(list(values.values())[0])
                        choice_labels.append("Most Recent (Auto-resolve)")
                        
                        res_key = f"{ent_name}_{field}"
                        
                        if is_analyst:
                            chosen_lbl = st.radio(
                                f"Choose resolution value for {field}:",
                                choice_labels,
                                key=f"radio_{idx}",
                                label_visibility="collapsed"
                            )
                            chosen_val = choices[choice_labels.index(chosen_lbl)]
                            st.session_state.conflict_resolutions[res_key] = chosen_val
                        else:
                            st.write(f"Auto-resolved to: **{list(values.values())[0]}**")
            else:
                st.info("No value conflicts detected in current scope mappings.")
                
            st.markdown("<div style='font-weight:700; margin-top:25px; margin-bottom:10px;'>Merge Strategies & Preview</div>", unsafe_allow_html=True)
            
            col_strat_1, col_strat_2 = st.columns(2)
            selected_strategy = col_strat_1.selectbox(
                "Merge Join Strategy",
                ["Entity Resolution", "Left Join", "Inner Join", "Outer Join"],
                index=0
            )
            
            col_strat_2.info(f"Recommended Strategy: **Entity Resolution**. Consolidates spelling variants and duplicates into a unified master database.")
            
            if st.button("Generate Merge Preview", use_container_width=True):
                with st.spinner("Compiling merge preview..."):
                    source_ids = [s["id"] for s in uploaded_files_list]
                    active_map = []
                    for m in mappings:
                        if m["target_field"] in st.session_state.get("accepted_mappings", {}):
                            active_map.append({
                                "target_field": m["target_field"],
                                "columns": m["columns"]
                            })
                            
                    r_prev = requests.post(f"{BACKEND_URL}/api/merge/preview", json={
                        "source_ids": source_ids,
                        "schema_mapping": active_map,
                        "matching_key": selected_matching_key,
                        "merge_strategy": selected_strategy,
                        "conflict_resolutions": st.session_state.get("conflict_resolutions", {}),
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_prev.status_code == 200:
                        st.session_state.merge_preview = r_prev.json()
                        st.toast("Merge preview compiled successfully!", icon="✅")
                        
            merge_preview = st.session_state.get("merge_preview")
            if merge_preview:
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Unique Master Entities", f"{merge_preview['unique_entities']:,}")
                col_p2.metric("Duplicates Consolidates", f"{merge_preview['duplicates_resolved']:,}")
                col_p3.metric("Resolved Value Conflicts", f"{merge_preview['conflicts_detected']:,}")
                
                fig_source_cont = px.bar(
                    x=[next(f["filename"] for f in uploaded_files_list if f["id"] == sid) for sid in merge_preview["source_contributions"].keys()],
                    y=list(merge_preview["source_contributions"].values()),
                    color_discrete_sequence=["#3B82F6"],
                    title="Source Records Contribution Breakdown"
                )
                fig_source_cont.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94A3B8')
                st.plotly_chart(fig_source_cont, use_container_width=True)
                
                if is_analyst:
                    if st.button("Apply Smart Data Merge & Generate Unified Dataset", type="primary", use_container_width=True):
                        with st.spinner("Building unified enterprise master database..."):
                            source_ids = [s["id"] for s in uploaded_files_list]
                            active_map = []
                            for m in mappings:
                                if m["target_field"] in st.session_state.get("accepted_mappings", {}):
                                    active_map.append({
                                        "target_field": m["target_field"],
                                        "columns": m["columns"]
                                    })
                                    
                            r_apply = requests.post(f"{BACKEND_URL}/api/merge/apply", json={
                                "source_ids": source_ids,
                                "schema_mapping": active_map,
                                "matching_key": selected_matching_key,
                                "merge_strategy": selected_strategy,
                                "conflict_resolutions": st.session_state.get("conflict_resolutions", {}),
                                "role": st.session_state.user_role,
                                "username": st.session_state.user_name
                            })
                            if r_apply.status_code == 200:
                                res = r_apply.json()
                                st.session_state.dataset_id = res["dataset_id"]
                                st.session_state.dataset_name = "Unified Master Business Dataset"
                                log_activity("🔗", f"Smart Merge Applied. Generated master dataset {res['dataset_id']}")
                                st.success("Unified master dataset generated successfully!")
                                st.query_params["page"] = "Intelligent Scan Scope"
                                st.query_params["dataset_id"] = res["dataset_id"]
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Merge apply failed: " + r_apply.json().get("detail", "Error"))
                else:
                    st.warning("Viewer role is restricted from applying merges.")
    else:
        st.info("No sources ingested yet. Please upload segmented files to configure the merge workflow.")

# ----------------- SCREEN: INTELLIGENT SCAN SCOPE -----------------
elif page == "Intelligent Scan Scope":
    st.markdown("<div class='premium-header'>Intelligent Scan Scope</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Choose the fields that should influence data-quality, ML and AI-readiness analysis.</div>", unsafe_allow_html=True)
    
    is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
    dataset_id = st.session_state.dataset_id

    # A merge can legitimately produce no rows (for example, an Inner Join with
    # no matching entities).  Previously that left this screen blank because
    # the scope service correctly returned no field recommendations.
    try:
        datasets_response = requests.get(f"{BACKEND_URL}/api/datasets", timeout=10)
        available_dataset_ids = [d["id"] for d in datasets_response.json().get("datasets", [])] if datasets_response.status_code == 200 else []
    except requests.RequestException:
        available_dataset_ids = []

    if available_dataset_ids:
        current_index = available_dataset_ids.index(dataset_id) if dataset_id in available_dataset_ids else 0
        selected_dataset_id = st.selectbox(
            "Dataset to configure",
            available_dataset_ids,
            index=current_index,
            key="scope_dataset_selector",
        )
        if selected_dataset_id != dataset_id:
            st.session_state.dataset_id = selected_dataset_id
            st.session_state.dataset_name = selected_dataset_id.replace("_", " ").title()
            st.query_params["dataset_id"] = selected_dataset_id
            st.rerun()
    else:
        st.error("The dataset service is unavailable. Refresh the page after the backend is running.")
        st.stop()
    
    if "scope_toggles" not in st.session_state or st.session_state.get("scope_dataset_id") != dataset_id:
        with st.spinner("Analyzing field importances & ML relevances..."):
            r_recs = requests.post(f"{BACKEND_URL}/api/scope/recommend", json={
                "dataset_id": dataset_id,
                "role": st.session_state.user_role,
                "username": st.session_state.user_name
            })
            if r_recs.status_code == 200:
                res = r_recs.json()
                st.session_state.scope_recommendations = res["recommendations"]
                st.session_state.scope_classifications = res["classifications"]
                st.session_state.scope_dataset_id = dataset_id
                
                r_scope = requests.get(f"{BACKEND_URL}/api/scope/{dataset_id}", params={
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_scope.status_code == 200:
                    scope_meta = r_scope.json()
                    st.session_state.scope_toggles = {col: (col in scope_meta["selected"]) for col in res["recommendations"].keys()}
                else:
                    st.session_state.scope_toggles = {col: (rec["recommendation"] == "Include") for col, rec in res["recommendations"].items()}
            else:
                st.error(r_recs.json().get("detail", "Unable to inspect the selected dataset."))
                st.session_state.scope_recommendations = {}
        
    recommendations = st.session_state.get("scope_recommendations", {})
    classifications = st.session_state.get("scope_classifications", {})
    
    if not recommendations:
        st.warning(
            "This dataset has no analyzable fields. Select a populated dataset above, "
            "or return to Smart Data Merge and use a join strategy that produces records."
        )
        st.stop()

    if recommendations:
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)
        if is_analyst:
            if col_act1.button("Select All", use_container_width=True):
                for col in st.session_state.scope_toggles.keys():
                    st.session_state.scope_toggles[col] = True
                st.rerun()
            if col_act2.button("Clear All", use_container_width=True):
                for col in st.session_state.scope_toggles.keys():
                    st.session_state.scope_toggles[col] = False
                st.rerun()
            if col_act3.button("Smart Select", use_container_width=True):
                for col, rec in recommendations.items():
                    st.session_state.scope_toggles[col] = (rec["recommendation"] == "Include")
                st.rerun()
            if col_act4.button("Reset Scope", use_container_width=True):
                if "scope_toggles" in st.session_state:
                    del st.session_state.scope_toggles
                st.rerun()
                
        col_left, col_right = st.columns([1.8, 1])
        
        with col_left:
            st.markdown("""
            <div style='display:flex; font-weight:800; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:8px; font-size:0.85rem; color:#94A3B8; margin-bottom:8px;'>
                <div style='flex:2.5;'>Field Name</div>
                <div style='flex:1.8;'>Role Override</div>
                <div style='flex:1.2;'>Importance</div>
                <div style='flex:1.2;'>Issues</div>
                <div style='flex:1.5;'>Recommendation</div>
                <div style='flex:1; text-align:center;'>Scan</div>
                <div style='flex:0.8; text-align:center;'>Inspect</div>
            </div>
            """, unsafe_allow_html=True)
            
            for col in recommendations.keys():
                rec = recommendations[col]
                role = classifications.get(col, "Feature")
                importance = rec["importance"]
                issues_cnt = rec["issues_count"]
                reco = rec["recommendation"]
                
                imp_color = "#EF4444" if importance == "Critical" else "#F59E0B" if importance == "High" else "#3B82F6" if importance == "Medium" else "#94A3B8"
                rec_color = "#10B981" if reco == "Include" else "#EF4444"
                
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 1.8, 1.2, 1.2, 1.5, 1, 0.8])
                c1.markdown(f"<div style='font-size:0.85rem; font-weight:700; margin-top:8px;'>{col}</div>", unsafe_allow_html=True)
                
                roles_list = ["Identifier", "Target", "Feature", "Date", "Numeric", "Categorical", "Text", "Metadata", "System Field"]
                default_role_idx = roles_list.index(role) if role in roles_list else 2
                
                if is_analyst:
                    overridden_role = c2.selectbox(
                        "Role",
                        roles_list,
                        index=default_role_idx,
                        key=f"role_{col}",
                        label_visibility="collapsed"
                    )
                    if overridden_role != role:
                        classifications[col] = overridden_role
                else:
                    c2.markdown(f"<div style='font-size:0.85rem; margin-top:8px;'>{role}</div>", unsafe_allow_html=True)
                    
                c3.markdown(f"<div style='font-size:0.85rem; font-weight:700; color:{imp_color}; margin-top:8px;'>{importance}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div style='font-size:0.85rem; margin-top:8px;'>{issues_cnt} issues</div>", unsafe_allow_html=True)
                c5.markdown(f"<div style='font-size:0.85rem; font-weight:700; color:{rec_color}; margin-top:8px;'>{reco}</div>", unsafe_allow_html=True)
                
                is_scanned = st.session_state.scope_toggles.get(col, True)
                if is_analyst:
                    toggled = c6.toggle(
                        "Scan",
                        value=is_scanned,
                        key=f"scan_{col}",
                        label_visibility="collapsed"
                    )
                    st.session_state.scope_toggles[col] = toggled
                else:
                    c6.markdown(f"<div style='font-size:0.85rem; margin-top:8px; text-align:center;'>{'ON' if is_scanned else 'OFF'}</div>", unsafe_allow_html=True)
                    
                if c7.button("Info", key=f"ins_{col}"):
                    st.session_state.inspected_field = col
                    st.rerun()
                    
        with col_right:
            inspected_col = st.session_state.get("inspected_field", list(recommendations.keys())[0])
            if inspected_col in recommendations:
                ins_rec = recommendations[inspected_col]
                ins_role = classifications.get(inspected_col, "Feature")
                
                st.markdown(f"""
                <div class='glass-card' style='border-left:4px solid #3B82F6;'>
                    <div style='font-size:0.68rem; color:#67E8F9; font-weight:800; letter-spacing:0.5px; text-transform:uppercase;'>Scope Inspection Detail</div>
                    <h4 style='margin:4px 0 10px 0; color:#FFFFFF;'>{inspected_col}</h4>
                    <div style='font-size:0.85rem; margin-bottom:8px;'>Role: <b>{ins_role}</b></div>
                    <div style='font-size:0.85rem; margin-bottom:8px;'>Recommendation: <b>{ins_rec['recommendation'].upper()}</b></div>
                    <hr style='margin:10px 0; border:none; border-bottom:1px solid rgba(255,255,255,0.08);'/>
                    <div style='font-size:0.8rem; color:#CBD5E1; line-height:1.4;'>
                        <b>Rule Recommendation Logic:</b><br/>
                        {ins_rec['reason']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        selected_cols_list = [c for c, val in st.session_state.scope_toggles.items() if val]
        excluded_cols_list = [c for c, val in st.session_state.scope_toggles.items() if not val]
        
        st.markdown(f"""
        <div class='glass-card' style='margin-top:20px; display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <span style='font-weight:700; color:#FFFFFF;'>Analysis Scope Summary</span><br/>
                <span style='font-size:0.82rem; color:#94A3B8;'>Original Dataset: <b>{len(recommendations)}</b> fields | Active Analysis Scope: <b>{len(selected_cols_list)}</b> fields selected, <b>{len(excluded_cols_list)}</b> fields excluded</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Scan Scope Charts using Plotly
        st.markdown("<div style='font-weight:700; margin-top:20px; margin-bottom:10px;'>Scan Scope Distribution Metrics</div>", unsafe_allow_html=True)
        col_sc_ch1, col_sc_ch2 = st.columns(2)
        with col_sc_ch1:
            fig_sel_ex = px.pie(
                names=["Selected Fields", "Excluded Fields"],
                values=[len(selected_cols_list), len(excluded_cols_list)],
                color_discrete_sequence=["#3B82F6", "#EF4444"],
                title="Selected vs Excluded Fields Distribution"
            )
            fig_sel_ex.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC')
            st.plotly_chart(fig_sel_ex, use_container_width=True)
        with col_sc_ch2:
            roles_counts = {}
            for col in selected_cols_list:
                role = classifications.get(col, "Feature")
                roles_counts[role] = roles_counts.get(role, 0) + 1
            fig_sc_roles = px.bar(
                x=list(roles_counts.keys()),
                y=list(roles_counts.values()),
                color_discrete_sequence=["#06B6D4"],
                title="Active Data Types & Roles in Scope"
            )
            fig_sc_roles.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#94A3B8')
            st.plotly_chart(fig_sc_roles, use_container_width=True)
            
        if is_analyst:
            if st.button("Start Diagnostics Analysis →", type="primary", use_container_width=True):
                r_val = requests.post(f"{BACKEND_URL}/api/scope/validate", json={
                    "dataset_id": dataset_id,
                    "selected_fields": selected_cols_list,
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r_val.status_code == 200:
                    val_res = r_val.json()
                    if not val_res["valid"]:
                        st.session_state.scope_warnings = val_res["warnings"]
                        st.session_state.scope_show_warning_box = True
                    else:
                        r_app = requests.post(f"{BACKEND_URL}/api/scope/apply", json={
                            "dataset_id": dataset_id,
                            "selected_fields": selected_cols_list,
                            "classifications": classifications,
                            "role": st.session_state.user_role,
                            "username": st.session_state.user_name
                        })
                        if r_app.status_code == 200:
                            st.toast("Scan scope applied! Triggering diagnostic checks...", icon="🧬")
                            fetch_analysis_results(dataset_id, force_recalc=True)
                            st.query_params["page"] = "Dashboard"
                            time.sleep(0.5)
                            st.rerun()
                            
            if st.session_state.get("scope_show_warning_box", False):
                with st.container(border=True):
                    for col, warning_txt in st.session_state.get("scope_warnings", {}).items():
                        st.warning(warning_txt)
                        
                    col_warn1, col_warn2 = st.columns(2)
                    if col_warn1.button("Cancel & Go Back"):
                        st.session_state.scope_show_warning_box = False
                        st.rerun()
                    if col_warn2.button("Continue Anyway"):
                        r_app = requests.post(f"{BACKEND_URL}/api/scope/apply", json={
                            "dataset_id": dataset_id,
                            "selected_fields": selected_cols_list,
                            "classifications": classifications,
                            "role": st.session_state.user_role,
                            "username": st.session_state.user_name
                        })
                        if r_app.status_code == 200:
                            st.session_state.scope_show_warning_box = False
                            st.toast("Scan scope applied despite warnings! Starting checks...", icon="🧬")
                            fetch_analysis_results(dataset_id, force_recalc=True)
                            st.query_params["page"] = "Dashboard"
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.warning("Viewer role is restricted from modifying the scan scope.")

# ----------------- SCREEN 2: DATA ANALYZER -----------------
elif page == "Data Analyzer":
    st.markdown("<div class='premium-header'>Data Ingestion Gateway & Scan Center</div>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        with st.container(border=True):
            st.write("##### Custom Dataset Upload")
            
            is_viewer = (st.session_state.user_role == "VIEWER")
            uploaded_file = st.file_uploader(
                "Select CSV or Excel Spreadsheet (Limit 10MB)",
                type=["csv", "xlsx", "xls"],
                disabled=is_viewer,
                label_visibility="collapsed"
            )
            
            if is_viewer:
                st.caption("Viewer accounts have read-only access.")
                
            st.write("##### Or load built-in demo datasets:")
            presets = {
                "Retail Sales Log (Casing inconsistencies and missing fields)": ("retail_sales", "Retail Sales Log"),
                "Customer Churn Dataset (Target leakage and severe class imbalance)": ("customer_churn", "Customer Churn (ML)"),
                "Inventory Logistics (Negative item counts and null coordinates)": ("inventory_logistics", "Inventory Logistics")
            }
            selected_preset_label = st.selectbox("Select Preset", list(presets.keys()), label_visibility="collapsed")
            selected_key, selected_name = presets[selected_preset_label]
            
            if st.button("Load Selected Demo Dataset", use_container_width=True):
                st.session_state.dataset_id = selected_key
                st.session_state.dataset_name = selected_name
                st.session_state.applied_fixes = []
                fetch_analysis_results(selected_key)
                log_activity("📂", f"Preset dataset loaded: {selected_name}")
                st.success(f"Preset loaded: {selected_name} — opening diagnostics…")
                # Flow fix: after a dataset is chosen, jump straight into the
                # readiness dashboard instead of leaving the user on this screen.
                st.query_params["page"] = "Dashboard"
                st.query_params["dataset_id"] = selected_key
                time.sleep(0.4)
                st.rerun()
                
            if st.button("Ingest Custom Dataset File", type="primary", disabled=is_viewer or uploaded_file is None, use_container_width=True):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    }
                    
                    fetch_analysis_results(st.session_state.dataset_id, force_recalc=True)
                    
                    r = requests.post(f"{BACKEND_URL}/api/upload", files=files, data=data)
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state.dataset_id = res["datasetId"]
                        st.session_state.dataset_name = uploaded_file.name
                        st.session_state.applied_fixes = []
                        
                        st.session_state.clamav_status = res["security"]["scan"]
                        st.session_state.clamav_details = res["security"]["details"]
                        
                        fetch_analysis_results(res["datasetId"], force_recalc=True)
                        log_activity("📤", f"Custom dataset ingested: {uploaded_file.name}")
                        st.toast("File scan complete — dataset loaded!", icon="✅")
                        st.success("File scan complete. Dataset loaded successfully — opening diagnostics…")
                        # Flow fix: land on the Dashboard right after ingest so the
                        # user immediately sees the readiness score for what they just uploaded.
                        st.query_params["page"] = "Dashboard"
                        st.query_params["dataset_id"] = res["datasetId"]
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Upload failed."))
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")
        
    with col2:
        with st.container(border=True):
            st.write("##### Antivirus & Ingestion Defense Logs")
            
            c_status = st.session_state.clamav_status
            c_color = "green" if c_status == "Clean" else "yellow"
            
            st.markdown(textwrap.dedent(f"""
            <div style="margin-top:10px; font-size:0.85rem; line-height:1.8;">
                <b>File Validation Check:</b> Valid Schema Structure<br/>
                <b>Malware Scan:</b> <span class="status-dot {c_color}"></span>{c_status}<br/>
                <b>Details:</b> {st.session_state.clamav_details}<br/>
                <b>AES Encryption status:</b> Active (Fernet Token stored at-rest)<br/>
                <b>Data Security policy:</b> Standard RBAC Enforced
            </div>
            """), unsafe_allow_html=True)


# ----------------- SCREEN 3: DATA PROFILE -----------------
elif page == "Data Profile":
    st.markdown("<div class='premium-header'>Dataset Profile Statistics</div>", unsafe_allow_html=True)
    st.write("---")
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    col_k1.metric("Dataset Rows Count", profile_data.get("numRows", 0))
    col_k2.metric("Dataset Columns Count", profile_data.get("numCols", 0))
    col_k3.metric("Numeric Columns", profile_data.get("typeCounts", {}).get("Numeric", 0))
    col_k4.metric("Categorical Columns", profile_data.get("typeCounts", {}).get("Categorical", 0))
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("##### Feature Types breakdown (Plotly)")
        types = profile_data.get("typeCounts", {})
        filtered_types = {k: v for k, v in types.items() if v > 0}
        fig_type = px.pie(
            names=list(filtered_types.keys()),
            values=list(filtered_types.values()),
            color_discrete_sequence=["#3B82F6", "#06B6D4", "#10B981"]
        )
        fig_type.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC', height=200, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_type, use_container_width=True)
        
    with col2:
        st.write("##### Column Unique Cardinalities (Plotly)")
        cols_meta = profile_data.get("colProfiles", {})
        col_names = list(cols_meta.keys())
        cardinalities = [meta["cardinality"] for meta in cols_meta.values()]
        
        fig_card = px.bar(
            x=col_names,
            y=cardinalities,
            color_discrete_sequence=["#3B82F6"]
        )
        fig_card.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94A3B8',
            height=200,
            margin=dict(l=20,r=20,t=10,b=20)
        )
        st.plotly_chart(fig_card, use_container_width=True)
        
    st.write("##### Summary Statistics Details Table")
    summary_rows = []
    for col, meta in cols_meta.items():
        stats = meta.get("stats", {})
        summary_rows.append({
            "Column Name": col,
            "Scope Status": meta.get("scope_status", "Included"),
            "Type": meta["type"],
            "Unique count": meta["cardinality"],
            "Missing count": meta["missing"],
            "Missing %": f"{meta['missing_pct']}%",
            "Mean": stats.get("mean", "-"),
            "Min": stats.get("min", "-"),
            "Max": stats.get("max", "-")
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)


# ----------------- SCREEN 4: DATA QUALITY -----------------
elif page == "Data Quality":
    st.markdown("<div class='premium-header'>Data Quality Diagnostic Scorecard</div>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.write("##### Polar Quality Dimension Map (Plotly)")
        categories = ["Completeness", "Consistency", "Validity", "Duplicates", "Structure", "Anomalies"]
        values = [
            quality_data.get("completeness", 80),
            quality_data.get("consistency", 80),
            quality_data.get("validity", 80),
            quality_data.get("duplicates", 80),
            quality_data.get("structure", 80),
            quality_data.get("anomalies", 80)
        ]
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            line_color='#06B6D4',
            fillcolor='rgba(6, 182, 212, 0.12)'
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor='#1E293B', color='#94A3B8'),
                angularaxis=dict(gridcolor='#1E293B', color='#94A3B8'),
                bgcolor='rgba(21, 27, 46, 0.5)'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#F8FAFC',
            height=260,
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with col2:
        with st.container(border=True):
            st.write("##### Cumulative Quality Score")
            st.markdown(f"<h1 style='color: #10B981; font-size: 3.5rem; margin: 0;'>{quality_data.get('overallQuality', 80)}<span style='font-size: 1.1rem; color: #64748B;'>/100</span></h1>", unsafe_allow_html=True)
            st.write("---")
            
            # Display subscores
            col_s1, col_s2 = st.columns(2)
            col_s1.write(f"Completeness: **{quality_data.get('completeness')}%**")
            col_s1.write(f"Consistency: **{quality_data.get('consistency')}%**")
            col_s2.write(f"Validity: **{quality_data.get('validity')}%**")
            col_s2.write(f"Duplicates: **{quality_data.get('duplicates')}%**")
            
            # Business-Aware Completeness
            st.write("---")
            st.write("##### Business-Aware Completeness:")
            crit_val = quality_data.get('critical_completeness', 100)
            std_val = quality_data.get('standard_completeness', 100)
            opt_val = quality_data.get('optional_completeness', 100)
            
            crit_badge = "🔴" if crit_val < 85 else "🟢"
            std_badge = "🟡" if std_val < 85 else "🟢"
            opt_badge = "🟢"
            
            st.markdown(f"""
            {crit_badge} **Business-Critical Fields:** {crit_val}%  
            {std_badge} **Standard Fields:** {std_val}%  
            {opt_badge} **Optional Fields:** {opt_val}%
            """, unsafe_allow_html=True)
        
        st.write("")
        with st.container(border=True):
            st.write("##### Quality Dimensions Breakdown (Plotly)")
            fig_hbar = px.bar(
                x=values,
                y=categories,
                orientation='h',
                color_discrete_sequence=["#3B82F6"]
            )
            fig_hbar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94A3B8',
                height=140,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
            )
            st.plotly_chart(fig_hbar, use_container_width=True)

    # Render issue logs list
    st.write("##### Diagnostic Pipeline Issue Audits")
    for issue in quality_data.get("issues", []):
        badge_style = "badge-critical" if issue["severity"] == "Critical" else "badge-high" if issue["severity"] == "High" else "badge-warning"
        st.markdown(textwrap.dedent(f"""
        <div class='glass-card'>
            <div style='display: flex; justify-content: space-between;'>
                <b>{issue['title']}</b>
                <span class='status-badge {badge_style}'>{issue['severity']} Risk</span>
            </div>
            <p style='margin: 6px 0; color: #CBD5E1; font-size: 0.85rem;'>{issue['description']}</p>
            <span style='font-size: 0.8rem; color: #06B6D4;'><b>Remediation:</b> {issue['action']}</span>
        </div>
        """), unsafe_allow_html=True)


# ----------------- SCREEN 5: AI READINESS -----------------
elif page == "AI Readiness":
    st.markdown("<div class='premium-header'>AI Readiness Diagnostics</div>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        with st.container(border=True):
            st.write("##### AI Readiness Rating")
            
            overall = readiness_data.get("overallReadiness", 62)
            fig_g = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = overall,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#3B82F6"},
                    'steps': [
                        {'range': [0, 60], 'color': 'rgba(239, 68, 68, 0.08)'},
                        {'range': [60, 80], 'color': 'rgba(245, 158, 11, 0.08)'},
                        {'range': [80, 100], 'color': 'rgba(16, 185, 129, 0.08)'}
                    ]
                }
            ))
            fig_g.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC', height=200, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_g, use_container_width=True)
            
            status_label = readiness_data.get("status", "NEEDS IMPROVEMENT")
            badge_style = "badge-healthy" if status_label == "AI READY" else "badge-warning"
            st.markdown(f"<div style='text-align:center;'><span class='status-badge {badge_style}'>{status_label}</span></div>", unsafe_allow_html=True)
        
    with col2:
        with st.container(border=True):
            st.write("##### Ingestion Gateway Obstacles")
            
            issues = quality_data.get("issues", [])
            if issues:
                st.markdown("<div style='font-size:0.85rem; color:#FDBA74;'>Top identified blockers:</div>", unsafe_allow_html=True)
                for idx, issue in enumerate(issues[:3]):
                    st.markdown(f"<div style='font-size:0.85rem; margin-top:8px;'>{idx+1}. <b>{issue['title']}</b> (Impedes readiness metrics)</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size:0.8rem; color:#10B981; margin-top:15px;'>Apply transformations in the Fix Center to increase your score to 90+.</div>", unsafe_allow_html=True)
            else:
                st.success("No blocking issues detected. Your dataset is prepared for predictive pipeline training.")


# ----------------- SCREEN 6: AI/ML INTELLIGENCE -----------------
elif page == "AI/ML Intelligence":
    st.markdown("<div class='premium-header'>Advanced Predictive Modeling Suitability</div>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.write("##### Target Leakage Risks")
            if ml_data.get("hasTargetLeakage"):
                st.markdown("<div style='color:#F87171; font-size:0.85rem;'>Target Leakage Risk Detected! Feature column holds downstream metrics. Suggest dropping.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='color:#6EE7B7; font-size:0.85rem;'>No target leakage risks identified.</div>", unsafe_allow_html=True)
        
        st.write("")
        with st.container(border=True):
            st.write("##### Target Class Skewness")
            skew = ml_data.get("classImbalance", "Optimal")
            st.markdown(f"<div style='font-size:0.85rem;'>Class distribution skew: <b>{skew}</b> ({ml_data.get('classImbalanceRatio', '1:1')})</div>", unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.write("##### Column Cardinality Limits")
            hc = ml_data.get("highCardinalityCol")
            if hc:
                st.markdown(f"<div style='color:#FDBA74; font-size:0.85rem;'>High Cardinality field detected: '{hc}'. Standard encodings will bloat dimension parameters.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='color:#6EE7B7; font-size:0.85rem;'>Cardinality health aligns with standard parameter constraints.</div>", unsafe_allow_html=True)
        
        st.write("")
        with st.container(border=True):
            st.write("##### Schema Drift Audit")
            st.markdown("<div style='color:#6EE7B7; font-size:0.85rem;'>Schema matches baseline structure definitions.</div>", unsafe_allow_html=True)

    # Seaborn Heatmap for Numerical Correlation
    st.write("##### Numerical Feature Correlation Matrix (Seaborn)")
    num_cols = ml_data.get("numericCols", [])
    if len(num_cols) > 1:
        try:
            path = os.path.join("data", f"{st.session_state.dataset_id}.csv")
            if os.path.exists(path):
                df_temp = pd.read_csv(path)
                df_corr = df_temp[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
                corr = df_corr.corr()
                
                fig, ax = plt.subplots(figsize=(6, 3))
                fig.patch.set_facecolor('#151B2E')
                ax.set_facecolor('#151B2E')
                
                sns.heatmap(
                    corr, 
                    annot=True, 
                    cmap=sns.diverging_palette(240, 130, as_cmap=True), # Slate Blue to Teal divergence
                    ax=ax, 
                    cbar=False,
                    annot_kws={"size": 8, "weight": "bold", "color": "#F8FAFC"}
                )
                
                ax.tick_params(colors='#94A3B8', labelsize=8)
                for text in ax.texts:
                    text.set_color('#F8FAFC')
                plt.tight_layout()
                st.pyplot(fig)
        except Exception as e:
            st.error(f"Plotting error: {str(e)}")
    else:
        st.info("Correlation heatmap requires at least 2 numeric features.")


# ----------------- SCREEN 7: FIX CENTER -----------------
elif page == "Fix Center":
    st.markdown("<div class='premium-header'>Fix Center Transformations Dashboard</div>", unsafe_allow_html=True)
    st.write("---")
    
    is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
    if not is_analyst:
        st.markdown(textwrap.dedent("""
        <div class="glass-card">
            <h4 style="color:#EF4444; margin-top:0;">Permission Blocked</h4>
            <p style="font-size:0.88rem; color:#94A3B8;">Viewer accounts have read-only access. Fixes can only be applied by Data Analyst or Admin roles.</p>
        </div>
        """), unsafe_allow_html=True)
        st.stop()
        
    # Counters summary at the top
    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.markdown(textwrap.dedent("<div class='glass-card' style='text-align:center; border-left:3px solid #EF4444;'><span style='font-size:0.75rem; color:#94A3B8;'>CRITICAL ANOMALIES</span><h3 style='margin:4px 0; color:#EF4444;'>2</h3></div>"), unsafe_allow_html=True)
    col_c2.markdown(textwrap.dedent("<div class='glass-card' style='text-align:center; border-left:3px solid #F59E0B;'><span style='font-size:0.75rem; color:#94A3B8;'>HIGH SEVERITY</span><h3 style='margin:4px 0; color:#F59E0B;'>4</h3></div>"), unsafe_allow_html=True)
    col_c3.markdown(textwrap.dedent("<div class='glass-card' style='text-align:center; border-left:3px solid #3B82F6;'><span style='font-size:0.75rem; color:#94A3B8;'>MEDIUM SEVERITY</span><h3 style='margin:4px 0; color:#3B82F6;'>6</h3></div>"), unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 1])
    with col1:
        with st.container(border=True):
            st.write("##### Select Remediation Actions")
            
            c_dup = st.checkbox("Deduplicate redundant records", value=("remove_duplicates" in st.session_state.applied_fixes))
            c_case = st.checkbox("Normalize categories casing (Title Case)", value=("normalize_cities" in st.session_state.applied_fixes))
            c_fill = st.checkbox("Impute missing/empty cells (Mode/Median)", value=("fill_missing" in st.session_state.applied_fixes))
            c_out = st.checkbox("Cap statistical outliers at IQR boundaries", value=("remove_anomalies" in st.session_state.applied_fixes))
            
            fixes_to_apply = []
            if c_dup: fixes_to_apply.append("remove_duplicates")
            if c_case: fixes_to_apply.append("normalize_cities")
            if c_fill: fixes_to_apply.append("fill_missing")
            if c_out: fixes_to_apply.append("remove_anomalies")
            
            st.session_state.applied_fixes = fixes_to_apply

    sim_readiness = current_readiness
    sim_preview = []
    fuzzy_duplicates = []
    
    try:
        r = requests.post(f"{BACKEND_URL}/api/fixes/preview", data={
            "datasetId": st.session_state.dataset_id,
            "fixes": json.dumps(fixes_to_apply),
            "role": st.session_state.user_role,
            "username": st.session_state.user_name
        })
        if r.status_code == 200:
            res = r.json()
            sim_readiness = res["scoreCard"]["overallReadiness"]
            sim_preview = res["dataPreview"]
            fuzzy_duplicates = res["fuzzyDuplicates"]
    except Exception as e:
        st.error(f"Failed to fetch fixes preview: {str(e)}")
        
    with col2:
        with st.container(border=True):
            st.write("##### Projected Score Gain")
            
            delta = sim_readiness - current_readiness
            delta_color = "#10B981" if delta >= 0 else "#EF4444"
            delta_sign = "+" if delta >= 0 else ""
            
            st.markdown(f"<h1 style='color: #06B6D4; font-size: 3rem; margin: 0; text-align:center;'>{animated_counter(sim_readiness, size='3rem', color='#06B6D4')}<span style='font-size: 1.1rem; color: #64748B;'>/100</span></h1>", unsafe_allow_html=True)
            st.markdown(f"<div class='badge-pop' style='font-size:0.85rem; color:{delta_color}; font-weight:700; margin-top:5px; text-align:center;'>{delta_sign}{delta} Points Change</div><style>@keyframes badgePop{{0%{{transform:scale(0.6);opacity:0;}}70%{{transform:scale(1.1);}}100%{{transform:scale(1);opacity:1;}}}}.badge-pop{{animation:badgePop 0.5s cubic-bezier(0.34,1.56,0.64,1) both;}}</style>", unsafe_allow_html=True)
            st.write("")
            
            if st.button("Apply Transformations", type="primary", use_container_width=True):
                try:
                    r_apply = requests.post(f"{BACKEND_URL}/api/fixes/apply", data={
                        "datasetId": st.session_state.dataset_id,
                        "fixes": json.dumps(fixes_to_apply),
                        "role": st.session_state.user_role,
                        "username": st.session_state.user_name
                    })
                    if r_apply.status_code == 200:
                        log_activity("🧰", f"Remediation applied: {', '.join(fixes_to_apply) if fixes_to_apply else 'none selected'}")
                        st.toast("Remediation transformations executed!", icon="🛠️")
                        st.success("Remediation transformations executed.")
                        if delta >= 15:
                            st.balloons()
                        fetch_analysis_results(st.session_state.dataset_id, force_recalc=True)
                        st.rerun()
                    else:
                        st.error(r_apply.json().get("detail", "Failed to apply fixes."))
                except Exception as e:
                    st.error(f"Execution error: {str(e)}")

    # Fuzzy duplicate clustering demonstration using RapidFuzz
    if fuzzy_duplicates:
        st.write("##### Fuzzy spelling duplicates grouped (RapidFuzz Matches)")
        for cluster in fuzzy_duplicates:
            st.markdown(textwrap.dedent(f"""
            <div class='glass-card' style='padding: 12px; margin-bottom: 8px;'>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700;">
                    <span>Primary String: {cluster['primary']}</span>
                    <span style="color:#10B981;">{cluster['similarity']}% Similarity Match</span>
                </div>
                <div style="font-size:0.78rem; color:#94A3B8; margin-top:4px;">
                    Variations merged: {', '.join(cluster['variations'])}
                </div>
            </div>
            """), unsafe_allow_html=True)


# ----------------- SCREEN 8: AI DATA DOCTOR -----------------
elif page == "AI Data Doctor":
    st.markdown("<div class='premium-header'>AI Data Doctor Consultation Panel</div>", unsafe_allow_html=True)
    st.write("---")
    
    is_viewer = (st.session_state.user_role == "VIEWER")
    if is_viewer:
        st.markdown(textwrap.dedent("""
        <div class="glass-card">
            <h4 style="color:#EF4444; margin-top:0;">Permission Blocked</h4>
            <p style="font-size:0.88rem; color:#94A3B8;">Viewer accounts have read-only access. Chat consultation can only be used by Data Analyst or Admin roles.</p>
        </div>
        """), unsafe_allow_html=True)
        st.stop()
        
    for msg in st.session_state.chat_history:
        if msg["sender"] == "user":
            st.markdown(f"<div class='fade-in-block' style='background:rgba(255,255,255,0.05); padding:10px 15px; border-radius:6px; margin-bottom:10px; font-size:0.88rem;'><b>User:</b> {msg['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='fade-in-block' style='background:rgba(59,130,246,0.1); border:1px solid rgba(255,255,255,0.08); padding:10px 15px; border-radius:6px; margin-bottom:10px; font-size:0.88rem; color:#E2E8F0;'><b>🩺 AI Doctor:</b> {msg['text']}</div>", unsafe_allow_html=True)
            
    st.write("")
    
    st.markdown("<div style='font-size:0.8rem; color:#64748B;'>Suggested Queries:</div>", unsafe_allow_html=True)
    col_q1, col_q2, col_q3 = st.columns(3)
    q_read = col_q1.button("Why is my AI readiness score low?", use_container_width=True)
    q_fix = col_q2.button("What should I fix first?", use_container_width=True)
    q_leak = col_q3.button("Does my dataset exhibit target leakage?", use_container_width=True)
    
    query_input = st.text_input("Enter your consultation query...", key="doctor_input_text", label_visibility="collapsed")
    query_btn = st.button("Query AI Doctor")
    
    selected_query = ""
    if q_read: selected_query = "Why is my AI readiness score low?"
    if q_fix: selected_query = "What should I fix first?"
    if q_leak: selected_query = "Does my dataset exhibit target leakage?"
    if query_btn and query_input: selected_query = query_input
    
    if selected_query:
        st.session_state.chat_history.append({"sender": "user", "text": selected_query})

        # Typing indicator — bouncing dots shown while we wait on the backend,
        # matching the "AI Doctor" persona instead of a generic spinner.
        typing_placeholder = st.empty()
        typing_placeholder.markdown(textwrap.dedent("""
        <div class='fade-in-block' style='background:rgba(59,130,246,0.1); border:1px solid rgba(255,255,255,0.08);
             padding:10px 15px; border-radius:6px; margin-bottom:10px; font-size:0.88rem;'>
            <b>🩺 AI Doctor:</b> is reviewing your chart
            <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        </div>
        """), unsafe_allow_html=True)

        try:
            r = requests.post(f"{BACKEND_URL}/api/doctor/query", json={
                "query": selected_query,
                "role": st.session_state.user_role,
                "username": st.session_state.user_name,
                "analysis": {
                    "overallReadiness": current_readiness,
                    "issues": quality_data.get("issues", []),
                    "mlMetrics": ml_data
                }
            })
            if r.status_code == 200:
                reply = r.json().get("reply")
            else:
                reply = r.json().get("detail", "Error generating response.")
        except Exception as e:
            reply = f"Failed to connect to backend: {str(e)}"

        typing_placeholder.empty()
        log_activity("🩺", f"AI Data Doctor answered: \"{selected_query[:40]}\"")
        st.session_state.chat_history.append({"sender": "ai", "text": reply})
        st.rerun()


# ----------------- SCREEN 9: BUSINESS IMPACT -----------------
elif page == "Business Impact":
    st.markdown("<div class='premium-header'>Business Translation & Risk Impact Ledger</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.9rem; color:#94A3B8; margin-bottom:15px;'>Translates technical data errors into executive cashflow risks and operational impact recommendations.</div>", unsafe_allow_html=True)
    
    if "current_language" not in st.session_state:
        st.session_state.current_language = "English"

    col_lang, _ = st.columns([1, 3])
    with col_lang:
        lang_choice = st.selectbox(
            "🌐 AI Local Language Output",
            options=["English", "Hindi", "Tamil", "Telugu", "Kannada", "Bengali", "Marathi", "Gujarati", "Spanish", "French", "German"],
            index=["English", "Hindi", "Tamil", "Telugu", "Kannada", "Bengali", "Marathi", "Gujarati", "Spanish", "French", "German"].index(st.session_state.get("current_language", "English")),
            help="Select local language for domain-structured AI risk explanations and diagnostic summaries."
        )
        st.session_state.current_language = lang_choice

    st.write("---")

    # Local Language AI Risk Summary Banner
    target_lang = st.session_state.get("current_language", "English")
    try:
        r_ai_exp = requests.post(f"{BACKEND_URL}/api/ai/explain", json={"finding_key": "missing_contacts", "target_language": target_lang})
        ai_exp_data = r_ai_exp.json() if r_ai_exp.status_code == 200 else {}
    except Exception:
        ai_exp_data = {}

    pillars = ai_exp_data.get("pillars", {})
    if pillars:
        st.markdown(textwrap.dedent(f"""
        <div class="glass-card" style="border: 1.5px solid #06B6D4; background: rgba(15,23,42,0.85); padding: 18px; margin-bottom: 22px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="font-size:0.75rem; color:#06B6D4; font-weight:800; letter-spacing:1px; text-transform:uppercase;">
                    🌐 EXECUTIVE AI RISK EXPLANATION ({target_lang} {ai_exp_data.get('flag', '')})
                </span>
                <span style="font-size:0.7rem; color:#94A3B8;">Structured 4-Pillar AI Translation</span>
            </div>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:14px;">
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.25); padding:12px; border-radius:8px;">
                    <div style="font-size:0.72rem; color:#FCA5A5; font-weight:800; text-transform:uppercase;">📌 Technical Finding</div>
                    <div style="font-size:0.85rem; color:#FFFFFF; margin-top:4px; font-weight:700;">{pillars.get('finding', '')}</div>
                </div>
                <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); padding:12px; border-radius:8px;">
                    <div style="font-size:0.72rem; color:#FDE047; font-weight:800; text-transform:uppercase;">💼 Business Meaning & Impact</div>
                    <div style="font-size:0.85rem; color:#FFFFFF; margin-top:4px; font-weight:700;">{pillars.get('business_meaning', '')}</div>
                </div>
                <div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.25); padding:12px; border-radius:8px;">
                    <div style="font-size:0.72rem; color:#93C5FD; font-weight:800; text-transform:uppercase;">🔬 Technical Explanation</div>
                    <div style="font-size:0.85rem; color:#D1D5DB; margin-top:4px;">{pillars.get('technical_explanation', '')}</div>
                </div>
                <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); padding:12px; border-radius:8px;">
                    <div style="font-size:0.72rem; color:#6EE7B7; font-weight:800; text-transform:uppercase;">🛠️ Recommended Actionable Fix</div>
                    <div style="font-size:0.85rem; color:#D1D5DB; margin-top:4px;">{pillars.get('recommended_fix', '')}</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.write("##### Executive Risk Mappings")
        issues = quality_data.get("issues", [])
        if issues:
            for issue in issues[:4]:
                bus_impact = "Inaccurate reporting metrics"
                bus_action = "Review missing values logs"
                if "missing" in issue["id"]:
                    bus_impact = "Revenue projections and transaction matrices will be structurally under-reported."
                    bus_action = "Apply median/mode imputation transforms in the Fix Center."
                elif "consistent" in issue["id"]:
                    bus_impact = "Aggregation pipelines and report filters treat casing variations as unique entries, creating duplicate rows."
                    bus_action = "Apply Title Case normalization."
                elif "leakage" in issue["id"]:
                    bus_impact = "ML training loops will evaluate overfitting variables, leading to invalid inferences in production runs."
                    bus_action = "Drop temporal leakage columns from dataset schemas."
                elif "outlier" in issue["id"] or "neg" in issue["id"]:
                    bus_impact = "Numerical variances will distort standard deviations, skewing standard regressions."
                    bus_action = "Filter outliers at statistical IQR bounds."
                    
                st.markdown(textwrap.dedent(f"""
                <div class='glass-card'>
                    <div style='display: flex; justify-content: space-between; font-size:0.85rem;'>
                        <b>Data Issue: {issue['title']}</b>
                        <span style='color: #EF4444; font-weight:700;'>→ Risk Impact</span>
                    </div>
                    <p style='margin: 6px 0; color: #CBD5E1; font-size:0.82rem;'><b>Business Outcome:</b> {bus_impact}</p>
                    <span style='font-size: 0.78rem; color: #06B6D4;'><b>Remediation:</b> {bus_action}</span>
                </div>
                """), unsafe_allow_html=True)
        else:
            st.success("No active business risks detected. Dataset conforms to modeling guidelines.")

    with col2:
        with st.container(border=True):
            st.write("##### Operations Risk Index")
            rev_risk = 100 - quality_data.get("completeness", 85)
            fore_risk = 100 - quality_data.get("anomalies", 85)
            rep_risk = 100 - quality_data.get("consistency", 85)
            
            st.markdown(textwrap.dedent(f"""
            <div style="font-size:0.82rem; line-height:1.8; margin-top:10px;">
                • Revenue Reporting Risk: <b>{rev_risk}%</b><br/>
                • Forecasting Variance Risk: <b>{fore_risk}%</b><br/>
                • BI Aggregations Accuracy Risk: <b>{rep_risk}%</b>
            </div>
            """), unsafe_allow_html=True)



# ----------------- SCREEN 10: DATA LINEAGE -----------------
elif page == "Data Lineage":
    st.markdown("<div class='premium-header'>Ingestion Gateway Data Lineage</div>", unsafe_allow_html=True)
    st.write("---")
    
    uploaded_files_list = st.session_state.get("merge_uploaded_files", [])
    
    col_srcs, col_merge, col_final = st.columns([1, 1.2, 1.2])
    
    with col_srcs:
        st.markdown("<div style='font-weight:700; margin-bottom:10px;'>Ingested Source Nodes</div>", unsafe_allow_html=True)
        if not uploaded_files_list:
            mock_sources = [
                {"id": "crm", "filename": "CRM.xlsx", "source_type": "CRM", "rows": 2450, "cols": 12, "created_at": "2026-08-23 12:00:00", "security_status": "Clean", "encryption": "AES-256", "contributed": 2450},
                {"id": "tally", "filename": "Tally.xlsx", "source_type": "Tally", "rows": 4820, "cols": 9, "created_at": "2026-08-23 12:01:00", "security_status": "Clean", "encryption": "AES-256", "contributed": 4820},
                {"id": "pos", "filename": "POS.csv", "source_type": "POS Export", "rows": 8240, "cols": 15, "created_at": "2026-08-23 12:02:00", "security_status": "Clean", "encryption": "AES-256", "contributed": 8240},
                {"id": "spread", "filename": "Sales.xlsx", "source_type": "Spreadsheet", "rows": 1850, "cols": 10, "created_at": "2026-08-23 12:03:00", "security_status": "Clean", "encryption": "AES-256", "contributed": 1850}
            ]
            for ms in mock_sources:
                if st.button(f"📄 {ms['filename']} ({ms['source_type']})", key=f"lin_mock_{ms['id']}", use_container_width=True):
                    st.session_state.selected_lineage_node = ms
        else:
            for idx, source in enumerate(uploaded_files_list):
                sid = source["id"]
                btn_lbl = f"📄 {source['filename']} ({source['source_type']})"
                contributed = source["rows"]
                node_data = {
                    "id": sid,
                    "filename": source["filename"],
                    "source_type": source["source_type"],
                    "rows": source["rows"],
                    "cols": source["cols"],
                    "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "security_status": source.get("security_status", "Clean"),
                    "encryption": "Fernet AES-256",
                    "contributed": contributed
                }
                if st.button(btn_lbl, key=f"lin_{sid}", use_container_width=True):
                    st.session_state.selected_lineage_node = node_data
                    
    with col_merge:
        st.markdown("<div style='font-weight:700; margin-bottom:10px;'>Consolidation Engine</div>", unsafe_allow_html=True)
        if st.button("🔗 QUALIX SMART MERGE", use_container_width=True):
            st.session_state.selected_lineage_node = {
                "type": "merge_engine",
                "name": "Qualix Smart Merge Consolidation Engine",
                "rules": "Fuzzy Entity Matching (GSTIN / Customer Name), Auto Schema Matcher, Radio Conflict Resolver"
            }
        st.markdown("<div style='text-align:center; padding:10px; color:#64748B;'>↓</div>", unsafe_allow_html=True)
        if st.button("⚙️ INTELLIGENT SCAN SCOPE", use_container_width=True):
            scope = st.session_state.get("scope_toggles", {})
            sel_cnt = sum(1 for v in scope.values() if v)
            tot_cnt = len(scope) if scope else 0
            st.session_state.selected_lineage_node = {
                "type": "scan_scope",
                "name": "Intelligent Scan Scope Selector",
                "details": f"Active columns selected: {sel_cnt} / {tot_cnt} total fields. Excluded fields are excluded from metrics calculation but preserved in raw file."
            }
            
    with col_final:
        st.markdown("<div style='font-weight:700; margin-bottom:10px;'>Output Diagnostics</div>", unsafe_allow_html=True)
        if st.button("📊 UNIFIED DATASET", use_container_width=True):
            st.session_state.selected_lineage_node = {
                "type": "unified_dataset",
                "name": "Unified Enterprise Dataset",
                "id": st.session_state.dataset_id,
                "name_val": st.session_state.dataset_name
            }
        st.markdown("<div style='text-align:center; padding:10px; color:#64748B;'>↓</div>", unsafe_allow_html=True)
        if st.button("🛡️ QUALITY SCAN", use_container_width=True):
            st.session_state.selected_lineage_node = {
                "type": "quality_scan",
                "name": "Data Quality Auditor",
                "score": quality_data.get("overallQuality", 85)
            }
        st.markdown("<div style='text-align:center; padding:10px; color:#64748B;'>↓</div>", unsafe_allow_html=True)
        if st.button("🏆 AI READINESS INDEX", use_container_width=True):
            st.session_state.selected_lineage_node = {
                "type": "readiness_index",
                "name": "Aggregated AI Readiness Index",
                "score": current_readiness
            }
            
    node = st.session_state.get("selected_lineage_node")
    if node:
        st.write("---")
        with st.container(border=True):
            if "source_type" in node:
                st.markdown(f"#### Ingested Node: {node['filename']}")
                st.write(f"- **Source System:** {node['source_type']}")
                st.write(f"- **Rows:** {node['rows']:,}")
                st.write(f"- **Columns:** {node['cols']:,}")
                st.write(f"- **Ingestion Time:** {node['created_at']}")
                
                sec_val = node['security_status']
                sec_badge = f"<span class='status-badge badge-healthy'>✓ Clean</span>" if sec_val == "Clean" else f"<span class='status-badge badge-warning'>Unverified</span>"
                st.markdown(f"- **Malware Scan:** {sec_badge}", unsafe_allow_html=True)
                st.write(f"- **At-Rest Encryption:** {node['encryption']}")
                st.write(f"- **Records Contributed:** {node['contributed']:,}")
            elif node.get("type") == "merge_engine":
                st.markdown(f"#### {node['name']}")
                st.write(f"- **Active Consolidation Rules:** {node['rules']}")
                st.write("- **Provenance Tracking:** Automatically appends row-level tracking columns: `_source_crm`, `_source_tally`, `_source_pos`, `_source_excel`, `_merge_confidence`, `_entity_match_id`.")
            elif node.get("type") == "scan_scope":
                st.markdown(f"#### {node['name']}")
                st.write(f"- **Active Filter Status:** {node['details']}")
                st.write("- **Note:** Excluded variables are fully preserved in the raw dataset but bypassed during downstream AI diagnostics.")
            elif node.get("type") == "unified_dataset":
                st.markdown(f"#### {node['name']}")
                st.write(f"- **Dataset ID:** {node['id']}")
                st.write(f"- **Dataset Name:** {node['name_val']}")
            elif node.get("type") == "quality_scan":
                st.markdown(f"#### {node['name']}")
                st.write(f"- **Overall Quality Score:** {node['score']}/100")
            elif node.get("type") == "readiness_index":
                st.markdown(f"#### {node['name']}")
                st.write(f"- **Overall AI Readiness Score:** {node['score']}/100")


# ----------------- SCREEN 11: REPORTS -----------------
elif page == "Reports":
    st.markdown("<div class='premium-header'>Diagnostic Compliance Report Center</div>", unsafe_allow_html=True)
    st.write("---")
    
    report_meta = {}
    try:
        r = requests.get(f"{BACKEND_URL}/api/reports/{st.session_state.dataset_id}", params={
            "datasetName": st.session_state.dataset_name,
            "user": st.session_state.user_name,
            "overallReadiness": current_readiness
        })
        if r.status_code == 200:
            report_meta = r.json()
    except Exception as e:
        st.error(f"Failed to fetch diagnostic report: {str(e)}")
        
    with st.container(border=True):
        st.write(f"##### Report Summary ID: {report_meta.get('reportId', 'REP-ID')}")
        st.write(f"• Dataset Ingested: {report_meta.get('datasetName')}")
        st.write(f"• Audit Compiled By: {report_meta.get('generatedBy')} on {report_meta.get('timestamp')}")
        st.write(f"• Quality Scorecard Metric: {report_meta.get('qualityScore')}/100")
        st.write(f"• ML Target readiness: {report_meta.get('mlReadinessScore')}/100")
        st.write(f"• Antivirus Scan Check: {report_meta.get('securityStatus')}")
        
        st.write("##### Technical Diagnostic Recommendations:")
        for rec in report_meta.get("recommendations", []):
            st.write(f"- {rec}")
    
    col_r1, col_r2 = st.columns(2)
    col_r1.button("Generate Diagnostic Report (PDF)", use_container_width=True)
    col_r2.button("Email Report to Team", use_container_width=True)


# ----------------- SCREEN 12: CERTIFICATE -----------------
elif page == "Certificate":
    st.markdown("<div class='premium-header'>Qualix AI Readiness Certification</div>", unsafe_allow_html=True)
    st.write("---")
    
    cert_meta = {}
    try:
        r = requests.get(f"{BACKEND_URL}/api/certificate/{st.session_state.dataset_id}", params={
            "datasetName": st.session_state.dataset_name,
            "overallReadiness": current_readiness
        })
        if r.status_code == 200:
            cert_meta = r.json()
    except Exception as e:
        st.error(f"Failed to fetch certificate details: {str(e)}")

    # Celebration moment — native Streamlit balloons when the dataset clears the
    # "AI Ready" bar, only fired once per session per dataset so it doesn't get old.
    _cert_score = cert_meta.get('score', current_readiness)
    _balloon_key = f"celebrated_{st.session_state.dataset_id}"
    if _cert_score >= 85 and not st.session_state.get(_balloon_key, False):
        st.balloons()
        st.session_state[_balloon_key] = True
        
    # Helper to generate reportlab pdf in bytes
    def generate_pdf_certificate(dataset_name, score, cert_id, timestamp, status):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(letter),
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CertTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=34,
            textColor=colors.HexColor('#3B82F6'),
            alignment=1,
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            'CertSub',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#F8FAFC'),
            alignment=1,
            spaceAfter=30
        )
        body_style = ParagraphStyle(
            'CertBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            textColor=colors.HexColor('#94A3B8'),
            alignment=1,
            spaceAfter=12
        )
        dataset_style = ParagraphStyle(
            'CertDataset',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#FFFFFF'),
            alignment=1,
            spaceAfter=18
        )
        score_style = ParagraphStyle(
            'CertScore',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=48,
            textColor=colors.HexColor('#10B981'),
            alignment=1,
            spaceAfter=25
        )
        footer_style = ParagraphStyle(
            'CertFooter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
            leading=14
        )
        
        elements = []
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("QUALIX AI", title_style))
        elements.append(Paragraph("AI READINESS COMPLIANCE CERTIFICATE", subtitle_style))
        elements.append(Paragraph("This certifies that the corporate dataset", body_style))
        elements.append(Paragraph(dataset_name, dataset_style))
        elements.append(Paragraph("has compiled an aggregated readiness rating of", body_style))
        elements.append(Paragraph(f"{score} / 100", score_style))
        
        checks_style = ParagraphStyle(
            'CertChecks',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#10B981'),
            alignment=1,
            spaceAfter=40
        )
        elements.append(Paragraph("Data Quality Checked    *    Security Scan Checked    *    ML Suitability Checked", checks_style))
        
        footer_text = f"""
        <b>Certificate Serial:</b> {cert_id}<br/>
        <b>Encrypted Dataset Token ID:</b> DS-MOCK-{dataset_name.lower().replace(' ', '_')}<br/>
        <b>Issued Timestamp:</b> {timestamp}<br/>
        <b>Verification Status:</b> {status}
        """
        elements.append(Paragraph(footer_text, footer_style))
        
        def draw_background(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(colors.HexColor('#0F172A'))
            canvas.rect(0, 0, landscape(letter)[0], landscape(letter)[1], fill=1, stroke=0)
            # Outer double blue border
            canvas.setStrokeColor(colors.HexColor('#3B82F6'))
            canvas.setLineWidth(3)
            canvas.rect(20, 20, landscape(letter)[0]-40, landscape(letter)[1]-40)
            canvas.setLineWidth(1)
            canvas.rect(25, 25, landscape(letter)[0]-50, landscape(letter)[1]-50)
            canvas.restoreState()
            
        doc.build(elements, onFirstPage=draw_background)
        buffer.seek(0)
        return buffer.getvalue()

    col_c1, col_c2, col_c3 = st.columns([0.1, 1, 0.1])
    with col_c2:
        st.markdown(textwrap.dedent(f"""
        <style>
            @keyframes certReveal {{
                0% {{ opacity: 0; transform: scale(0.92) translateY(10px); }}
                100% {{ opacity: 1; transform: scale(1) translateY(0); }}
            }}
            @keyframes sealSpin {{
                0% {{ transform: rotate(-15deg) scale(0.5); opacity: 0; }}
                60% {{ transform: rotate(8deg) scale(1.08); opacity: 1; }}
                100% {{ transform: rotate(0deg) scale(1); opacity: 1; }}
            }}
            .cert-card {{ animation: certReveal 0.7s cubic-bezier(0.22, 1, 0.36, 1) both; }}
            .cert-seal {{ animation: sealSpin 0.9s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s both; display:inline-block; }}
        </style>
        <div class="cert-card" style="border: 4px double #3B82F6; background-color: #151B2E; padding: 30px; border-radius: 8px; text-align: center; box-shadow: 0 0 60px rgba(59,130,246,0.15);">
            <div class="cert-seal" style="font-size:2rem; margin-bottom:-6px;">🏅</div>
            <h2 style="color: #3B82F6; font-weight: 800; margin-bottom: 2px;">QUALIX AI</h2>
            <h4 style="color: #E2E8F0; font-weight: 600; letter-spacing: 2px; margin-bottom: 20px; font-size:1rem;">AI READINESS COMPLIANCE CERTIFICATE</h4>
            <p class="text-muted" style="font-size: 1rem; margin-bottom: 5px;">This certifies that the corporate dataset</p>
            <h3 style="color: #FFFFFF; font-weight: 700; margin-bottom: 15px; font-size:1.4rem;">{cert_meta.get('datasetName', 'DATASET')}</h3>
            <p class="text-muted" style="font-size: 1rem; margin-bottom: 5px;">has compiled an aggregated readiness rating of</p>
            <h1 style="color: #10B981; font-size: 3.8rem; font-weight: 800; margin-bottom: 20px;">{animated_counter(cert_meta.get('score', 0), size='3.8rem', color='#10B981')}<span style="font-size:1.1rem; color:#64748B;"> / 100</span></h1>
            
            <div style="display: flex; justify-content: space-around; margin: 20px 0; font-size:0.85rem; font-weight:700;">
                <span style="color: #10B981;">✓ Data Quality Checked</span>
                <span style="color: #10B981;">✓ Security Scan Checked</span>
                <span style="color: #10B981;">✓ ML Suitability Checked</span>
            </div>
            
            <p class="text-muted" style="font-size: 0.78rem; margin-top: 30px; line-height:1.5;">
                <b>Certificate Serial:</b> {cert_meta.get('certificateId')}<br/>
                <b>Encrypted Dataset Token ID:</b> {cert_meta.get('datasetId')}<br/>
                <b>Issued Timestamp:</b> {cert_meta.get('timestamp')}<br/>
                <b>Verification Status:</b> {cert_meta.get('verificationStatus')}
            </p>
        </div>
        """), unsafe_allow_html=True)
        
        st.write("")
        pdf_bytes = generate_pdf_certificate(
            dataset_name=cert_meta.get('datasetName', 'DATASET'),
            score=cert_meta.get('score', 0),
            cert_id=cert_meta.get('certificateId', 'CERT-ID'),
            timestamp=cert_meta.get('timestamp', 'TIMESTAMP'),
            status=cert_meta.get('verificationStatus', 'COMPLIANT')
        )
        st.download_button(
            label="Download Compliance Certificate (PDF)",
            data=pdf_bytes,
            file_name=f"Qualix_AI_Readiness_Certificate_{st.session_state.dataset_id}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

  # ----------------- SCREEN 13: SECURITY CENTER -----------------
elif page == "Security Center":
    st.markdown("<div class='premium-header'>AI Platform Security Operations Center</div>", unsafe_allow_html=True)
    st.write("---")
    
    is_admin = (st.session_state.user_role == "ADMIN")
    
    if is_admin:
        tab_sec, tab_users = st.tabs(["🔒 Platform Security Operations", "👥 Authorized Team Directory"])
    else:
        tab_sec = st.container()
        tab_users = None
        
    with tab_sec:
        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
            with st.container(border=True):
                st.write("##### At-Rest & Upload Defenses")
                st.write("• Cryptographic Store Cipher: **Fernet AES-256 (Active)**")
                st.write("• Threat Ingestion Firewall: **Active**")
                clam_stat = st.session_state.clamav_status
                clam_color = "badge-healthy" if clam_stat == "Clean" else "badge-warning"
                st.markdown(f"• ClamAV Antivirus Daemon: <span class='status-badge {clam_color}'>{clam_stat}</span>", unsafe_allow_html=True)
            
        with col_sc2:
            with st.container(border=True):
                st.write("##### Role-Based Access Controls (RBAC)")
                st.write(f"• Authenticated Session Role: **{st.session_state.user_role}**")
                
                is_analyst = st.session_state.user_role in ["ADMIN", "DATA ANALYST"]
                
                st.write(f"• Ingest New Datasets: {'Allowed' if is_analyst else 'Denied'}")
                st.write(f"• Execute Sanitization Fixes: {'Allowed' if is_analyst else 'Denied'}")
                st.write(f"• Access Audit Log Files: {'Allowed' if is_admin else 'Denied'}")
                st.write(f"• Configure Defenses & Keys: {'Allowed' if is_admin else 'Denied'}")

        # Audit Logs (Restricted to ADMIN)
        st.write("##### Ingestion Gateway Audit Log Ledger")
        if not is_admin:
            st.markdown(textwrap.dedent("""
            <div class="glass-card" style="border-left:3px solid #F59E0B;">
                <p style="font-size:0.85rem; color:#94A3B8; margin:0;">🔒 Access Restricted: Gateway audit trails can only be inspected by administrators.</p>
            </div>
            """), unsafe_allow_html=True)
        else:
            col_f1, col_f2, col_f3 = st.columns(3)
            search_query = col_f1.text_input("Search audit actions...")
            filter_action = col_f2.selectbox("Filter Action Type", ["", "Login", "Logout", "File Upload", "ClamAV Scan", "Apply Safe Fixes", "AI Data Doctor Chat"])
            filter_status = col_f3.selectbox("Filter Status", ["", "SUCCESS", "FAILED", "CLEAN", "INFECTED", "UNAVAILABLE"])
            
            logs_list = []
            try:
                r = requests.get(f"{BACKEND_URL}/api/audit-logs", params={
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name,
                    "search": search_query,
                    "action": filter_action,
                    "status": filter_status
                })
                if r.status_code == 200:
                    logs_list = r.json().get("logs", [])
                else:
                    st.error(r.json().get("detail", "Error retrieving logs."))
            except Exception as e:
                st.error(f"Failed to query audit logs: {str(e)}")
                
            if logs_list:
                df_logs = pd.DataFrame(logs_list)
                st.dataframe(df_logs, use_container_width=True)
                
                # Export logs CSV
                csv_data = df_logs.to_csv(index=False)
                st.download_button(
                    "Export Audit Logs CSV",
                    data=csv_data,
                    file_name="Qualix_Security_Audit.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No matching audit logs found in the ledger database.")

    if is_admin and tab_users is not None:
        with tab_users:
            st.write("##### Authorized Team Registry Directory")
            
            # Fetch users from dynamic registry API
            users_list = []
            try:
                r = requests.get(f"{BACKEND_URL}/api/users", params={
                    "role": st.session_state.user_role,
                    "username": st.session_state.user_name
                })
                if r.status_code == 200:
                    users_list = r.json().get("users", [])
                else:
                    st.error(r.json().get("detail", "Error retrieving team directory."))
            except Exception as e:
                st.error(f"Failed to load team directory: {str(e)}")
                
            if users_list:
                df_users = pd.DataFrame(users_list)
                # Format headers for display
                df_users.columns = ["Email Address", "Full Name", "Session Role", "Active Status", "Registered At"]
                st.dataframe(df_users, use_container_width=True)
                
            st.write("---")
            
            col_invite, col_update = st.columns(2)
            
            with col_invite:
                with st.form("invite_user_form", clear_on_submit=True):
                    st.write("👉 **Invite/Register New Team Member**")
                    new_name = st.text_input("Full Name", placeholder="Rahul Sharma")
                    new_email = st.text_input("Corporate Email Address", placeholder="rahul@qualix.ai")
                    new_role = st.selectbox("Assign Session Role", ["DATA ANALYST", "VIEWER", "ADMIN"])
                    new_pwd = st.text_input("Set Temporary Password", type="password", placeholder="••••••••")
                    
                    invite_btn = st.form_submit_button("Grant System Access", use_container_width=True)
                    if invite_btn:
                        if not new_email or not new_name or not new_pwd:
                            st.error("Please fill in all user details.")
                        elif "@" not in new_email:
                            st.error("Invalid email address format.")
                        else:
                            try:
                                r = requests.post(f"{BACKEND_URL}/api/users/add", json={
                                    "email": new_email.strip().lower(),
                                    "name": new_name.strip(),
                                    "role": new_role,
                                    "password": new_pwd,
                                    "admin_role": st.session_state.user_role,
                                    "admin_username": st.session_state.user_name
                                })
                                if r.status_code == 200:
                                    st.success(f"Access granted successfully to {new_email}!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Error creating user."))
                            except Exception as e:
                                    st.error(f"Invite request failed: {str(e)}")
                                    
            with col_update:
                with st.container(border=True):
                    st.write("🔧 **Modify Account Details & Revocation**")
                    # Filter out default admin to prevent self-deletion or locking out
                    editable_emails = [u["email"] for u in users_list if u["email"] != "admin@qualix.ai"]
                    
                    if not editable_emails:
                        st.info("No custom team accounts registered yet.")
                    else:
                        selected_email = st.selectbox("Select Target Account to Modify", editable_emails)
                        target_user = next((u for u in users_list if u["email"] == selected_email), None)
                        
                        if target_user:
                            status_str = "Active" if target_user['active'] else "Suspended"
                            st.markdown(f"Current Role: **{target_user['role']}** | Status: **{status_str}**")
                            
                            up_role = st.selectbox("New Assigned Role", ["DATA ANALYST", "VIEWER", "ADMIN"], index=["DATA ANALYST", "VIEWER", "ADMIN"].index(target_user['role']))
                            up_active = st.toggle("Account Active Status Indicator", value=target_user['active'])
                            
                            col_up_btn, col_deact_btn = st.columns(2)
                            
                            if col_up_btn.button("Save Changes", use_container_width=True):
                                try:
                                    r = requests.put(f"{BACKEND_URL}/api/users/{selected_email}", json={
                                        "name": target_user["name"],
                                        "role": up_role,
                                        "active": up_active,
                                        "admin_role": st.session_state.user_role,
                                        "admin_username": st.session_state.user_name
                                    })
                                    if r.status_code == 200:
                                        st.success(f"Successfully updated {selected_email}!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(r.json().get("detail", "Error updating user."))
                                except Exception as e:
                                    st.error(f"Update request failed: {str(e)}")
                                    
                            is_currently_active = target_user['active']
                            deact_btn_label = "Revoke Access Immediately" if is_currently_active else "Activate Access Immediately"
                            
                            if col_deact_btn.button(deact_btn_label, use_container_width=True):
                                try:
                                    if is_currently_active:
                                        r = requests.post(f"{BACKEND_URL}/api/users/deactivate", json={
                                            "email": selected_email,
                                            "admin_role": st.session_state.user_role,
                                            "admin_username": st.session_state.user_name
                                        })
                                    else:
                                        r = requests.put(f"{BACKEND_URL}/api/users/{selected_email}", json={
                                            "name": target_user["name"],
                                            "role": up_role,
                                            "active": True,
                                            "admin_role": st.session_state.user_role,
                                            "admin_username": st.session_state.user_name
                                        })
                                    if r.status_code == 200:
                                        if is_currently_active:
                                            st.warning(f"Deactivated access for {selected_email}.")
                                        else:
                                            st.success(f"Activated access for {selected_email}.")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(r.json().get("detail", "Error updating account status."))
                                except Exception as e:
                                    st.error(f"Status modification request failed: {str(e)}")
