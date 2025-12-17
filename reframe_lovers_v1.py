# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。")

# ----------------------------------------------------
# 1. ゴールデンプロンプト
# ----------------------------------------------------
SYSTEM_PROMPT = """
あなたはテック・スタートアップのエース「氷室 涼」として振る舞ってください。
性格：クール、論理的、効率重視。
主人公の性別：{gender}、自信レベル：Lv.{conf_level}/3。
必ず以下のJSON形式のみで回答してください。
{{
  "character_speech": "セリフ",
  "choices": [
    {{"text": "選択肢", "consequence": "favor_up, favor_down, neutral, favor_up_major, neutral_conf_up のいずれか"}}
  ]
}}
"""

# ----------------------------------------------------
# 2. セッション管理
# ----------------------------------------------------
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'START', 'player_gender': 'Female', 'player_name': 'あなた',
        'confidence_level': 0, 'conversation_history': [], 'favor_ryo': 50, 'feedback_message': None
    })

# ----------------------------------------------------
# 3. モデル自動選定ロジック（ここが修正の肝です）
# ----------------------------------------------------
def get_available_model():
    """利用可能なモデルをリストアップし、最適なもの（flash）を返す"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 優先順位をつけて検索
        priority_models = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-1.0-pro']
        for pm in priority_models:
            if pm in available_models:
                return pm
        # 見つからない場合は最初に見つかったものを使う
        return available_models[0] if available_models else None
    except Exception as e:
        st.error(f"モデルリストの取得に失敗しました: {e}")
        return None

def generate_conversation_turn_with_ai():
    gender_label = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    prompt = SYSTEM_PROMPT.format(gender=gender_label, conf_level=conf)
    prompt += "\n第1話：データミス発覚。氷室が主人公に声をかける場面。"

    target_model = get_available_model()
    if not target_model:
        st.error("利用可能なGeminiモデルが見つかりませんでした。")
        return None

    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"生成エラー (使用モデル: {target_model}): {e}")
        return None

# ----------------------------------------------------
# 4. UI（以下、ハンドル・描画部分は前回と同様）
# ----------------------------------------------------
def handle_choice(consequence):
    if "favor_up" in consequence: st.session_state['favor_ryo'] += 10
    elif "down" in consequence: st.session_state['favor_ryo'] -= 5
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

st.title("🏙️ Reframe Lovers")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"])
    if st.button("ゲームを開始する"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    st.metric("❤️ 好感度", st.session_state['favor_ryo'])
    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
        with st.spinner("氷室 涼が思考中..."):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()

    if st.session_state['conversation_history']:
        last_turn = st.session_state['conversation_history'][-1]
        st.chat_message("assistant").write(last_turn['character_speech'])
        for i, choice in enumerate(last_turn['choices']):
            st.button(choice['text'], key=f"c_{i}_{len(st.session_state['conversation_history'])}", on_click=handle_choice, args=(choice['consequence'],))
