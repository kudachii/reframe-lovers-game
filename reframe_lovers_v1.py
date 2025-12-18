# -*- coding: utf-8 -*-
import streamlit as st
import pd as pd
import pandas as pd
import datetime
import pytz
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
        'continuous_days': 0,
        'confidence_level': 0, # CSVなしは 0
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
    """CSVの内容から自信レベル(0-3)を計算"""
    if df is None or df.empty:
        return 0
    # 簡易的に行数で判定（例：1行以上でLv1, 3行以上でLv2, 7行以上でMAX）
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
    gender = "女性" if st.session_state.get('player_gender') == "Female" else "男性"
    conf = st.session_state.get('confidence_level', 0)
    turn = st.session_state.get('turn_count', 0)
    
    # 自信レベルに応じた選択肢の数を決定
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)

    situations = [
        f"第1段階：ミスが発覚。氷室が{name}を冷徹に指摘している。",
        f"第2段階：修正作業中。氷室は{name}の隣で無言でPCを叩いているが、時折こちらを見ている。",
        f"第3段階（最終）：作業完了。氷室が少しだけ肩の力を抜き、{name}に言葉をかける。"
    ]
    current_sit = situations[min(turn, 2)]

    prompt = f"""
    あなたは、テック・スタートアップ「Reframe Lovers」のエース「氷室 涼」です。クールで論理的ですが、内面は情熱的。
    相手：名前「{name}」、性別「{gender}」、自信レベル「Lv.{conf}/3」。
    状況：{current_sit}
    
    【重要ルール】
    1. 会話の{turn+1}回目として、相手に返答してください。
    2. 自信レベルに基づき、選択肢を必ず【{num_choices}個】生成してください。
    3. 自信レベルが高いほど、より専門的、あるいは氷室を驚かせるような堂々とした選択肢を含めてください。
    
    必ず以下のJSON形式のみで出力。
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢のテキスト", "consequence": "favor_up, favor_down, neutral, favor_up_major のいずれか"}}
      ]
    }}
    """
    
    target_model = get_available_model()
    if not target_model: return None
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

def handle_choice(consequence):
    if "favor_up_major" in consequence: st.session_state['favor_ryo'] += 15
    elif "favor_up" in consequence: st.session_state['favor_ryo'] += 10
    elif "down" in consequence: st.session_state['favor_ryo'] -= 5
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. メインUI
# ----------------------------------------------------
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    st.markdown("---")
    st.subheader("🔗 データの連動")
    st.caption("※CSVなしで開始すると自信Lv.0（選択肢2つ）になります。")
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            st.session_state['game_state'] = 'DIARY_LOADED'
            st.success(f"データ連動完了！ 自信Lv.{st.session_state['confidence_level']} で開始します。")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        if st.session_state['game_state'] == 'START':
             st.session_state['confidence_level'] = 0 # CSVなし確定
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    st.write(f"👤 **{st.session_state['player_name']}** | ❤️ **好感度:** {st.session_state['favor_ryo']} | ⭐ **自信:** Lv.{st.session_state['confidence_level']} | 💬 **進行:** {st.session_state['turn_count']+1}/3")
    
    col_left, col_right = st.columns([0.4, 0.6])
    with col_left:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg", use_container_width=True)
    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("思考中..."):
                new_turn = generate_conversation_turn_with_ai()
                if new_turn:
                    st.session_state['conversation_history'].append(new_turn)
                    st.session_state['game_state'] = 'CONVERSATION'
                    st.rerun()
        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            st.markdown("**氷室 涼**")
            st.info(last_turn['character_speech'])

    st.markdown("---")
    if st.session_state['conversation_history']:
        choices = st.session_state['conversation_history'][-1].get('choices', [])
        for i, choice in enumerate(choices):
            st.button(choice['text'], key=f"c_{i}_{st.session_state['turn_count']}", on_click=handle_choice, args=(choice['consequence'],), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    st.subheader(f"🏁 結果発表")
    favor = st.session_state.get('favor_ryo', 50)
    st.write(f"最終好感度: {favor}")
    if favor >= 80: st.success("【ハッピーエンド】氷室と特別な関係になれました。")
    elif favor >= 50: st.info("【ノーマルエンド】良い同僚として認められました。")
    else: st.error("【バッドエンド】厳しい評価のまま終わりました。")
    if st.button("タイトルへ戻る"):
        st.session_state.clear()
        st.rerun()
