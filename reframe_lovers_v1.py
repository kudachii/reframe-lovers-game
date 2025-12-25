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
        'free_chat_count': 0, # フリートークの現在の往復数
        'free_chat_history': [] # フリートークの内容
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック関数
# ----------------------------------------------------

def get_max_free_chats(favor):
    """好感度に応じたフリートークの最大往復数を返す"""
    if favor >= 100: return 9999 # 無制限
    if favor >= 90: return 10
    if favor >= 80: return 5
    return 0

def generate_free_chat_response(user_input):
    """フリートーク専用のAI生成"""
    favor = st.session_state['favor_ryo']
    name = st.session_state['player_name']
    
    # 状況に応じた口調設定
    tone = "非常に親密。あなたのことが愛おしくてたまらない様子。" if favor >= 80 else "丁寧な敬語。仕事の合間の雑談。"
    
    prompt = f"""あなたは氷室涼です。現在、プレイヤーの「{name}」とフリートークをしています。
    【性格・状況】{tone} 好感度は{favor}/100です。
    【ルール】相手の言葉に短く、かつカレらしい冷徹さと情熱を混ぜて返してください。
    【入力】{user_input}
    """
    
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(prompt)
        return response.text
    except: return "……すみません、少し考え事をしていました。"

def generate_conversation_turn_with_ai():
    # (メインシナリオ用の生成ロジック - Step 2-2と同じ)
    name = st.session_state['player_name']
    gender = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    turn = st.session_state['turn_count']
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    tone = "非常に親密" if favor >= 80 else "丁寧な敬語" if favor >= 50 else "冷徹な事務的敬語"
    
    prompt = f"あなたは氷室涼です。名前「{name}」、好感度「{favor}」、自信Lv「{conf}」。状況：会話{turn+1}回目。JSON(character_speech, choices:[{{text, score}}])で出力。"
    
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

# ----------------------------------------------------
# 3. UI表示
# ----------------------------------------------------
st.markdown("## 🏙️ Reframe Lovers")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    # 設定画面（省略）
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    uploaded_file = st.file_uploader("日記CSVを同期（自信Lvに反映）", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state['confidence_level'] = min(len(df), 3)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.success(f"同期完了！ 自信Lv.{st.session_state['confidence_level']}")

    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.session_state['is_loading'] = True
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD', 'FREE_CHAT']:
    # ステータス表示
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write(f"❤️ **信頼度**: {st.session_state['favor_ryo']}")
        st.progress(min(max(st.session_state['favor_ryo'] / 100, 0.0), 1.0))
    with col_s2:
        st.write(f"✨ **自信**: {'⭐' * st.session_state['confidence_level']}")

    st.divider()

    col_img, col_chat = st.columns([0.4, 0.6])

    with col_img:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg")
        else: st.info("氷室 涼")

    with col_chat:
        st.markdown(f"**氷室 涼**")
        # フリートーク中はトーク履歴を表示、そうでなければ最新シナリオを表示
        if st.session_state['game_state'] == 'FREE_CHAT':
            for chat in st.session_state['free_chat_history'][-3:]: # 直近3件
                st.write(f"{'あなた' if chat['role']=='user' else '氷室'}: {chat['content']}")
        elif st.session_state['conversation_history']:
            st.info(st.session_state['conversation_history'][-1]['character_speech'])

    # --- 操作エリア ---
    st.markdown("---")

    # A. 次の会話を生成中
    if st.session_state['is_loading']:
        with st.status("氷室が次の言葉を選んでいます..."):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['is_loading'] = False
                st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()

    # B. メインシナリオの選択肢
    elif st.session_state['game_state'] == 'CONVERSATION':
        choices = st.session_state['conversation_history'][-1].get('choices', [])
        for i, choice in enumerate(choices):
            if st.button(choice['text'], key=f"c_{st.session_state['turn_count']}_{i}", use_container_width=True):
                # 好感度反映
                change = choice.get('score', 0)
                st.session_state['favor_ryo'] += change
                st.session_state['turn_count'] += 1
                # 私語モードへ移行するか判定
                max_chats = get_max_free_chats(st.session_state['favor_ryo'])
                if max_chats > 0:
                    st.session_state['game_state'] = 'FREE_CHAT'
                    st.session_state['free_chat_count'] = 0
                    st.session_state['free_chat_history'] = []
                else:
                    st.session_state['game_state'] = 'CONVERSATION_LOAD'
                    st.session_state['is_loading'] = True
                st.rerun()

    # C. 私語モード（フリートーク）
    elif st.session_state['game_state'] == 'FREE_CHAT':
        max_chats = get_max_free_chats(st.session_state['favor_ryo'])
        current_chats = st.session_state['free_chat_count']
        
        st.write(f"💬 私語モード（あと {max_chats - current_chats} 回）")
        
        user_msg = st.chat_input("氷室に話しかける...")
        if user_msg:
            st.session_state['free_chat_history'].append({"role": "user", "content": user_msg})
            response = generate_free_chat_response(user_msg)
            st.session_state['free_chat_history'].append({"role": "assistant", "content": response})
            st.session_state['free_chat_count'] += 1
            st.rerun()
            
        if st.button("次の展開へ進む", use_container_width=True):
            if st.session_state['turn_count'] >= 3:
                st.session_state['game_state'] = 'RESULT'
            else:
                st.session_state['game_state'] = 'CONVERSATION_LOAD'
                st.session_state['is_loading'] = True
            st.rerun()

elif st.session_state['game_state'] == 'RESULT':
    st.metric("最終信頼度", st.session_state['favor_ryo'])
    if st.button("タイトルへ"):
        st.session_state.clear()
        st.rerun()
