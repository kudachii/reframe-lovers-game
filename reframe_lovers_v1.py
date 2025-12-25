# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os 
import google.generativeai as genai

# --- API設定 ---
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

# --- セッション初期化 ---
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'START', 
        'player_name': 'あなた',
        'confidence_level': 0, 
        'favor_ryo': 50, 
        'turn_count': 0,
        'conversation_history': [], 
        'free_chat_history': [],
        'free_chat_count': 0,
        'is_loading': False
    })

# --- ロジック関数 ---
def get_free_chat_config(favor):
    """好感度に応じた上限回数とメッセージ"""
    if favor >= 100: return 999, "あなたの声を聞いていると、落ち着くんです……。もう少しだけ、こうしていても？"
    if favor >= 90: return 10, "……あともう少しだけなら、付き合ってもいいですよ。"
    if favor >= 80: return 5, "……5分だけですよ。あなたの話なら聞く価値がある。"
    if favor >= 31: return 3, "手短にお願いします。今は業務時間内ですので。"
    return 0, "私用の会話は禁止されています。仕事に戻ってください。"

def generate_free_chat_response(user_input):
    favor = st.session_state['favor_ryo']
    _, message = get_free_chat_config(favor)
    prompt = f"あなたは氷室涼。好感度{favor}。態度：{message}。相手：{user_input}。短く返答して。"
    try:
        model = genai.GenerativeModel(get_best_model())
        return model.generate_content(prompt).text
    except: return "……今は話せません。"

def generate_main_scenario():
    # シナリオ生成（省略版）
    conf = st.session_state['confidence_level']
    num = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    prompt = f"氷室涼としてセリフと選択肢{num}個をJSON(character_speech, choices:[{{text, score}}])で出力。"
    try:
        model = genai.GenerativeModel(get_best_model())
        res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(res.text)
    except: return None

# --- UI表示 ---
st.title("🏙️ Reframe Lovers")

# 1. スタート画面
if st.session_state['game_state'] == 'START':
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['confidence_level'] = st.slider("自信レベル（日記同期の代わり）", 0, 3, 0)
    if st.button("氷室に会いに行く"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# 2. 会話読み込み
elif st.session_state['game_state'] == 'CONVERSATION_LOAD':
    with st.spinner("氷室が言葉を選んでいます..."):
        new_turn = generate_main_scenario()
        if new_turn:
            st.session_state['conversation_history'].append(new_turn)
            st.session_state['game_state'] = 'MAIN_PLAY'
            st.rerun()

# 3. メインプレイ画面（私語モードもここに含まれる）
elif st.session_state['game_state'] in ['MAIN_PLAY', 'FREE_CHAT']:
    # ステータス
    st.write(f"❤️ 信頼度: {st.session_state['favor_ryo']} | ✨ 自信: {'⭐' * st.session_state['confidence_level']}")
    st.progress(st.session_state['favor_ryo'] / 100.0)
    st.divider()

    col_img, col_chat = st.columns([0.4, 0.6])
    with col_img: st.info("氷室 涼")
    
    with col_chat:
        st.markdown("**氷室 涼**")
        # フリートーク中はフリートーク履歴、そうでなければ最新のセリフ
        if st.session_state['game_state'] == 'FREE_CHAT':
            for m in st.session_state['free_chat_history'][-4:]:
                st.write(f"**{m['role']}**: {m['content']}")
        else:
            st.info(st.session_state['conversation_history'][-1]['character_speech'])

    # --- 操作エリア ---
    st.divider()
    
    # 選択肢モード
    if st.session_state['game_state'] == 'MAIN_PLAY':
        choices = st.session_state['conversation_history'][-1]['choices']
        for i, c in enumerate(choices):
            if st.button(c['text'], key=f"btn_{i}", use_container_width=True):
                st.session_state['favor_ryo'] += c['score']
                st.session_state['turn_count'] += 1
                
                # ここで私語モードへの分岐判定
                max_c, ryo_msg = get_free_chat_config(st.session_state['favor_ryo'])
                if max_c > 0:
                    st.session_state['game_state'] = 'FREE_CHAT'
                    st.session_state['free_chat_history'] = [{"role": "氷室", "content": ryo_msg}]
                    st.session_state['free_chat_count'] = 0
                else:
                    # 30以下なら拒絶メッセージをトーストで出して次へ
                    st.toast(ryo_msg)
                    st.session_state['game_state'] = 'CONVERSATION_LOAD'
                st.rerun()

    # 私語モード
    elif st.session_state['game_state'] == 'FREE_CHAT':
        max_c, _ = get_free_chat_config(st.session_state['favor_ryo'])
        
        # 入力欄（回数制限内なら表示）
        if st.session_state['free_chat_count'] < max_c:
            chat_input = st.chat_input("氷室に話しかける...")
            if chat_input:
                st.session_state['free_chat_history'].append({"role": "あなた", "content": chat_input})
                res = generate_free_chat_response(chat_input)
                st.session_state['free_chat_history'].append({"role": "氷室", "content": res})
                st.session_state['free_chat_count'] += 1
                st.rerun()
        else:
            st.warning("「……そろそろ、仕事に戻りませんか」")

        if st.button("次の展開へ進む", type="primary", use_container_width=True):
            if st.session_state['turn_count'] >= 3:
                st.session_state['game_state'] = 'RESULT'
            else:
                st.session_state['game_state'] = 'CONVERSATION_LOAD'
            st.rerun()

# 4. リザルト
elif st.session_state['game_state'] == 'RESULT':
    st.header("RESULT")
    st.metric("最終信頼度", st.session_state['favor_ryo'])
    if st.button("最初から"):
        st.session_state.clear()
        st.rerun()
