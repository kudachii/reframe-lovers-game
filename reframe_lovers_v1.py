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
        'selected_model': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック関数
# ----------------------------------------------------
def calculate_confidence(df):
    if df is None or df.empty: return 0
    count = len(df)
    if count >= 7: return 3
    if count >= 3: return 2
    if count >= 1: return 1
    return 0

def get_available_model():
    current_model = st.session_state.get('selected_model')
    if current_model: return current_model
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_models = ['models/gemini-1.5-flash', 'gemini-1.5-flash']
        for pm in priority_models:
            if pm in available_models:
                st.session_state['selected_model'] = pm
                return pm
        return available_models[0] if available_models else None
    except: return None

def generate_conversation_turn_with_ai():
    name = st.session_state.get('player_name', 'あなた')
    gender = st.session_state.get('player_gender', 'Female')
    gender_label = "女性" if gender == "Female" else "男性"
    conf = st.session_state.get('confidence_level', 0)
    turn = st.session_state.get('turn_count', 0)
    
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)

    prompt = f"""
    あなたはスタートアップのエース「氷室 涼」です。
    相手：名前「{name}」、性別「{gender_label}」、自信レベル「Lv.{conf}/3」。
    
    【キャラクター指示】
    - 女性主人公には「同期としての配慮と微かな甘さ」、男性主人公には「高め合うライバルとしての熱さ」を持って接してください。
    
    【ルール】
    1. 会話の{turn+1}回目。状況：ミス発覚から解決への流れ。
    2. 選択肢を必ず【{num_choices}個】生成。
    3. ★重要★ 選択肢の中に必ず1つは、氷室の地雷を踏んで好感度が大きく下がる「地雷選択肢」を入れてください。
    
    必ず以下のJSON形式のみで出力。
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢", "score": 10, "type": "up"}},
        {{"text": "地雷選択肢", "score": -10, "type": "down"}}
      ]
    }}
    ※scoreは基本値（正の数または負の数）を設定してください。
    """
    
    target_model = get_available_model()
    if not target_model: return None
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

def handle_choice(score):
    conf_lv = st.session_state.get('confidence_level', 0)
    
    if score > 0:
        # 自信Lvに応じた係数を掛ける (Lv0:0.5倍, Lv1:1倍, Lv2:1.5倍, Lv3:2倍)
        multiplier = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0)
        st.session_state['favor_ryo'] += int(score * multiplier)
    else:
        # マイナス（地雷）の場合は係数関係なくガッツリ下がる
        st.session_state['favor_ryo'] += score
    
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. メインUI
# ----------------------------------------------------
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state['confidence_level'] = calculate_confidence(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.success(f"連動完了！ 自信Lv.{st.session_state['confidence_level']} (好感度倍率: x{{ {0:0.5, 1:1, 2:1.5, 3:2}[st.session_state['confidence_level']] }})")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        if st.session_state['game_state'] == 'START': st.session_state['confidence_level'] = 0
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    f_val = st.session_state.get('favor_ryo', 50)
    c_val = st.session_state.get('confidence_level', 0)
    t_val = st.session_state.get('turn_count', 0)
    st.write(f"👤 **{st.session_state['player_name']}** | ❤️ **好感度:** {f_val} | ⭐ **自信:** Lv.{c_val} | 💬 **進行:** {t_val+1}/3")
    
    col_left, col_right = st.columns([0.4, 0.6])
    with col_left:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg", use_container_width=True)
    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("氷室があなたの反応を見ています..."):
                new_turn = generate_conversation_turn_with_ai()
                if new_turn:
                    st.session_state['conversation_history'].append(new_turn)
                    st.session_state['game_state'] = 'CONVERSATION'
                    st.rerun()
        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            st.markdown(f"**氷室 涼**")
            st.info(last_turn['character_speech'])

    st.markdown("---")
    if st.session_state['conversation_history']:
        for i, choice in enumerate(st.session_state['conversation_history'][-1].get('choices', [])):
            st.button(choice['text'], key=f"c_{i}_{t_val}", on_click=handle_choice, args=(choice.get('score', 0),), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    # 結果表示（省略）
    st.write(f"最終好感度: {st.session_state['favor_ryo']}")
    if st.button("戻る"):
        st.session_state.clear()
        st.rerun()
