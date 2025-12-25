# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定
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
        'is_loading': False,
        'free_chat_count': 0, 
        'free_chat_history': [] 
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック関数（ご提案のルールを反映）
# ----------------------------------------------------

def get_free_chat_config(favor):
    """好感度に応じた上限回数と氷室の態度を返す"""
    if favor >= 100:
        return 999, "あなたの声を聞いていると、落ち着くんです……。もう少しだけ、こうしていても？"
    elif favor >= 90:
        return 10, "……あともう少しだけなら、付き合ってもいいですよ。何か話したいことでも？"
    elif favor >= 80:
        return 5, "……5分だけですよ。効率は落ちますが、あなたの話なら聞く価値がある。"
    elif favor >= 31:
        return 3, "手短にお願いします。今は業務時間内ですので。"
    else:
        return 0, "私用の会話は禁止されています。仕事に戻ってください。"

def generate_free_chat_response(user_input):
    favor = st.session_state['favor_ryo']
    name = st.session_state['player_name']
    _, message = get_free_chat_config(favor)
    
    prompt = f"""あなたは氷室涼です。現在プレイヤーの{name}と「私語」をしています。
    好感度は{favor}点です。
    【基本スタンス】{message}
    相手の入力「{user_input}」に対して、好感度に見合った冷徹さ、あるいは密かな情熱を込めて返答してください。"""
    
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(prompt)
        return response.text
    except: return "……今は話すことはありません。"

# (メインシナリオ生成用 - Step 2.2と同様)
def generate_conversation_turn_with_ai():
    # 省略（前回のロジックを維持）
    name = st.session_state['player_name']
    gender = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    turn = st.session_state['turn_count']
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    prompt = f"氷室涼として振る舞い、状況に応じたセリフと選択肢{num_choices}個をJSONで出力してください。好感度は{favor}、自信Lvは{conf}です。"
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

# ----------------------------------------------------
# 3. UI表示
# ----------------------------------------------------

# (タイトル・設定画面は前回と同様のため省略)
# ...

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD', 'FREE_CHAT']:
    # ステータス表示
    st.write(f"❤️ **信頼度**: {st.session_state['favor_ryo']} | ✨ **自信**: {'⭐' * st.session_state['confidence_level']}")
    st.progress(min(max(st.session_state['favor_ryo'] / 100, 0.0), 1.0))
    st.divider()

    col_img, col_chat = st.columns([0.4, 0.6])
    with col_img:
        st.info("氷室 涼") # ここに画像を表示

    with col_chat:
        st.markdown(f"**氷室 涼**")
        # フリートーク表示
        if st.session_state['game_state'] == 'FREE_CHAT':
            max_c, ryo_msg = get_free_chat_config(st.session_state['favor_ryo'])
            if not st.session_state['free_chat_history']:
                 st.info(ryo_msg) # 最初の拒絶/受容セリフ
            for chat in st.session_state['free_chat_history'][-4:]:
                role = "あなた" if chat['role'] == "user" else "氷室"
                st.write(f"**{role}**: {chat['content']}")
        elif st.session_state['conversation_history']:
            st.info(st.session_state['conversation_history'][-1]['character_speech'])

    st.markdown("---")

    # シナリオ選択肢中
    if st.session_state['game_state'] == 'CONVERSATION':
        choices = st.session_state['conversation_history'][-1].get('choices', [])
        for i, choice in enumerate(choices):
            if st.button(choice['text'], key=f"c_{st.session_state['turn_count']}_{i}", use_container_width=True):
                st.session_state['favor_ryo'] += choice.get('score', 0)
                st.session_state['turn_count'] += 1
                # 0-30点なら即、次へ。31点以上ならフリートークへ。
                max_c, _ = get_free_chat_config(st.session_state['favor_ryo'])
                if max_c > 0:
                    st.session_state['game_state'] = 'FREE_CHAT'
                    st.session_state['free_chat_count'] = 0
                    st.session_state['free_chat_history'] = []
                else:
                    st.session_state['game_state'] = 'CONVERSATION_LOAD'
                    st.session_state['is_loading'] = True
                st.rerun()

    # フリートーク中
    elif st.session_state['game_state'] == 'FREE_CHAT':
        max_c, _ = get_free_chat_config(st.session_state['favor_ryo'])
        current_c = st.session_state['free_chat_count']
        
        if current_c < max_c:
            user_msg = st.chat_input("話しかける...")
            if user_msg:
                st.session_state['free_chat_history'].append({"role": "user", "content": user_msg})
                resp = generate_free_chat_response(user_msg)
                st.session_state['free_chat_history'].append({"role": "assistant", "content": resp})
                st.session_state['free_chat_count'] += 1
                st.rerun()
        else:
            st.warning("これ以上は業務の支障になります（ラリー上限です）")
            
        if st.button("次の展開へ進む", use_container_width=True, type="primary"):
            if st.session_state['turn_count'] >= 3:
                st.session_state['game_state'] = 'RESULT'
            else:
                st.session_state['game_state'] = 'CONVERSATION_LOAD'
                st.session_state['is_loading'] = True
            st.rerun()
