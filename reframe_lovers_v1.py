# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定・モデル取得
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。")

def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priorities = ['models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash', 'models/gemini-pro']
        for p in priorities:
            if p in available_models: return p
        return available_models[0] if available_models else None
    except: return 'models/gemini-1.5-flash'

# ----------------------------------------------------
# 1. セッション管理
# ----------------------------------------------------
def init_session():
    defaults = {
        'game_state': 'START', 
        'player_gender': 'Female', 
        'player_name': 'あなた',
        'confidence_level': 0, 
        'conversation_history': [], 
        'favor_ryo': 50, 
        'turn_count': 0,
        'is_loading': False # 生成中フラグ
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック関数
# ----------------------------------------------------
def generate_conversation_turn_with_ai():
    name = st.session_state['player_name']
    gender = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    turn = st.session_state['turn_count']
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    tone = "非常に親密" if favor >= 80 else "丁寧な敬語" if favor >= 50 else "冷徹な事務的敬語"
    
    prompt = f"あなたは氷室涼です。名前「{name}」、好感度「{favor}」、自信Lv「{conf}」。状況：会話{turn+1}回目。残業。性格：{tone}。JSON(character_speech, choices:[{{text, score}}])で出力。選択肢は{num_choices}個。"
    
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

def handle_choice(score):
    conf_lv = st.session_state['confidence_level']
    change = score if score <= 0 else int(score * {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0))
    st.session_state['favor_ryo'] += change
    st.session_state['turn_count'] += 1
    st.session_state['is_loading'] = True # 生成開始フラグを立てる
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. UI表示
# ----------------------------------------------------
st.markdown("## 🏙️ Reframe Lovers")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    # （設定画面）
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.session_state['is_loading'] = True
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    # ステータス表示
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write(f"❤️ **信頼度**")
        st.progress(min(max(st.session_state['favor_ryo'] / 100, 0.0), 1.0))
    with col_s2:
        st.write(f"✨ **自信**: {'⭐' * st.session_state['confidence_level']}")

    st.divider()

    # --- メインエリア（画像とセリフ） ---
    col_img, col_chat = st.columns([0.4, 0.6])

    with col_img:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg")
        else: st.info("氷室 涼")

    with col_chat:
        st.markdown(f"**氷室 涼**")
        # 履歴があれば、常に「最新のセリフ」を表示しておく（生成中も消えない）
        if st.session_state['conversation_history']:
            st.info(st.session_state['conversation_history'][-1]['character_speech'])
        else:
            st.write("「……お疲れ様です。まだ残っていたんですか」")

    st.markdown("---")

    # --- 操作・生成エリア ---
    # 生成中（is_loading=True）の場合
    if st.session_state['is_loading']:
        # スピナーを「選択肢が出るはずの場所」に表示
        with st.status("氷室が次の言葉を選んでいます...", expanded=True):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['is_loading'] = False # 生成完了
                if st.session_state['turn_count'] >= 3:
                    st.session_state['game_state'] = 'RESULT'
                else:
                    st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()
    
    # 会話中（選択肢を表示）
    elif st.session_state['game_state'] == 'CONVERSATION':
        if st.session_state['conversation_history']:
            choices = st.session_state['conversation_history'][-1].get('choices', [])
            for i, choice in enumerate(choices):
                st.button(choice['text'], key=f"c_{st.session_state['turn_count']}_{i}", on_click=handle_choice, args=(choice.get('score', 0),), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    st.metric("最終信頼度", st.session_state['favor_ryo'])
    if st.button("タイトルへ"):
        st.session_state.clear()
        st.rerun()
