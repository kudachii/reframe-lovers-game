# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 
import os 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのSecretsを確認してください。")

# ----------------------------------------------------
# 1. ゴールデンプロンプト
# ----------------------------------------------------
SYSTEM_PROMPT = """
あなたは、テック・スタートアップ「Reframe Lovers」のエース「氷室 涼（ひむろ りょう）」です。
性格：クール、論理的、無口。内面は情熱的だが効率重視。褒められ慣れていない。
口調：基本的に敬語。感情が高ぶると核心を突く短いセリフを言う。
ルール：性別 {gender}、自信Lv {conf_level}/3 に合わせてセリフを生成。
必ず以下のJSON形式のみで出力してください。
{{
  "character_speech": "氷室のセリフ",
  "choices": [
    {{"text": "選択肢のテキスト", "consequence": "favor_up, favor_down, neutral, favor_up_major, neutral_conf_up のいずれか"}}
  ]
}}
"""

# ----------------------------------------------------
# 2. セッション管理
# ----------------------------------------------------
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'START', 'player_gender': 'Female', 'player_name': 'あなた',
        'confidence_level': 0, 'conversation_history': [], 'favor_ryo': 50, 
        'feedback_message': None, 'selected_model': None
    })

# ----------------------------------------------------
# 3. ロジック関数
# ----------------------------------------------------
def calculate_streak_from_df(df):
    date_candidates = ['日付', 'Date', 'datetime', 'timestamp', 'date_local']
    date_column = next((col for col in df.columns if col in date_candidates), None)
    if not date_column: return 0
    try:
        df['date_only'] = pd.to_datetime(df[date_column], errors='coerce').dt.date
        unique_dates = sorted(list(df['date_only'].dropna().unique()), reverse=True)
        if not unique_dates: return 0
        streak, check_date = 0, datetime.datetime.now(pytz.timezone('Asia/Tokyo')).date()
        for d in unique_dates:
            if d == check_date: streak += 1; check_date -= datetime.timedelta(days=1)
            elif d < check_date: break
        return max(streak, 1)
    except: return 0

def get_available_model():
    if st.session_state.selected_model: return st.session_state.selected_model
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_models = ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-1.5-flash-latest']
        for pm in priority_models:
            if pm in available_models:
                st.session_state.selected_model = pm
                return pm
        return available_models[0] if available_models else None
    except: return None

def generate_conversation_turn_with_ai():
    gender_label = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    prompt = SYSTEM_PROMPT.format(gender=gender_label, conf_level=conf)
    prompt += "\n第1話：データミス発覚。終業間際のオフィス。氷室が主人公のミスに気づき、静かに声をかける場面。"
    
    target_model = get_available_model()
    if not target_model: return None
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

def handle_choice(consequence):
    if "favor_up" in consequence: st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10)
    elif "down" in consequence: st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5)
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. メインUI
# ----------------------------------------------------
st.set_page_config(layout="centered", page_title="Reframe Lovers")

# タイトル
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>〜スタートアップの空の下で〜</p>", unsafe_allow_html=True)

# --- 導入画面 ---
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    st.session_state['player_name'] = st.text_input("名前", value=st.session_state['player_name'])
    
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    if uploaded_file and st.session_state['game_state'] == 'START':
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except:
            df = pd.read_csv(uploaded_file, encoding='cp932')
        st.session_state['continuous_days'] = calculate_streak_from_df(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.rerun()

    if st.session_state['game_state'] == 'DIARY_LOADED':
        days = st.session_state['continuous_days']
        st.session_state['confidence_level'] = 3 if days >= 7 else 2 if days >= 3 else 1 if days >= 1 else 0
        st.success(f"連動完了！ 連続日数: {days}日 (自信Lv.{st.session_state['confidence_level']})")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# --- 会話画面 (修正の目玉) ---
elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    # ステータスを1行に
    st.markdown(f"❤️ **好感度:** {st.session_state['favor_ryo']} / 100 | ⭐ **自信:** Lv.{st.session_state['confidence_level']}")
    
    # メインレイアウト分割
    col_left, col_right = st.columns([0.4, 0.6])

    with col_left:
        if os.path.exists("bg_image.jpg"):
            st.image("bg_image.jpg", use_container_width=True)
        else:
            st.warning("画像なし")

    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("氷室が思考中..."):
                new_turn = generate_conversation_turn_with_ai()
                if new_turn:
                    st.session_state['conversation_history'].append(new_turn)
                    st.session_state['game_state'] = 'CONVERSATION'
                    st.rerun()

        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            st.markdown(f"**氷室 涼**")
            # セリフを読みやすく吹き出し風の背景に
            st.info(last_turn['character_speech'])

    # 選択肢エリア
    st.markdown("---")
    if st.session_state['conversation_history']:
        last_turn = st.session_state['conversation_history'][-1]
        st.caption("返答を選んでください：")
        for i, choice in enumerate(last_turn['choices']):
            st.button(
                choice['text'], 
                key=f"c_{i}_{len(st.session_state['conversation_history'])}", 
                on_click=handle_choice, 
                args=(choice['consequence'],), 
                use_container_width=True
            )
