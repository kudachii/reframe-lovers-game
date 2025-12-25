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
        'diary_count': 0,
        'conversation_history': [], 
        'favor_ryo': 50, 
        'turn_count': 0, 
        'last_feedback': None,
        'last_change': 0
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック・演出関数
# ----------------------------------------------------

def calculate_confidence(df):
    if df is None or df.empty: return 0, 0
    count = len(df)
    if count >= 7: return 3, count
    if count >= 3: return 2, count
    if count >= 1: return 1, count
    return 0, count

def generate_conversation_turn_with_ai():
    name = st.session_state['player_name']
    gender = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    turn = st.session_state['turn_count']
    
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)

    # 好感度による態度
    if favor >= 80:
        tone = "非常に親密。完璧な敬語の中に、あなたへの深い信頼と独占欲が見える。"
    elif favor >= 50:
        tone = "丁寧な敬語。仕事のパートナーとしての信頼。時折見せる気遣い。"
    else:
        tone = "冷徹な事務的敬語。感情を出さず、相手を突き放すような態度。"

    prompt = f"""
    あなたは「氷室 涼」です。相手：名前「{name}」、性別「{gender}」、自信Lv「{conf}/3」、好感度「{favor}/100」。
    【最優先】{tone}
    【状況】会話{turn+1}回目。残業中のオフィス。
    【特別ルール】自信Lvが{conf}であることを踏まえ、相手の「最近の成長ぶり（日記の成果）」をセリフの端々で評価または皮肉ってください。
    
    JSON形式で出力：
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢", "score": 10}}
      ]
    }}
    ※選択肢は必ず{num_choices}個。地雷（-10）を1つ含めてください。
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except: return None

def handle_choice(score):
    conf_lv = st.session_state['confidence_level']
    change = 0
    if score > 0:
        multiplier = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0)
        change = int(score * multiplier)
    else:
        change = score
    
    st.session_state['favor_ryo'] += change
    st.session_state['last_change'] = change
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. UI表示（演出強化）
# ----------------------------------------------------

st.markdown("### 🏙️ Reframe Lovers")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    # 設定・アップロード画面（省略なしの統合版）
    st.session_state['player_name'] = st.text_input("名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    uploaded_file = st.file_uploader("ポジティブ日記CSVを同期", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state['confidence_level'], st.session_state['diary_count'] = calculate_confidence(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.success(f"同期成功！ 日記数: {st.session_state['diary_count']} | 自信Lv: {st.session_state['confidence_level']}")

    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    # --- ステータスバー演出 ---
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.write(f"❤️ **氷室の信頼度**")
        st.progress(min(max(st.session_state['favor_ryo'] / 100, 0.0), 1.0))
    with col_stat2:
        conf_icons = "⭐" * st.session_state['confidence_level'] + "⚪" * (3 - st.session_state['confidence_level'])
        st.write(f"✨ **あなたの自信**: {conf_icons}")
    
    # 前回の変化をトーストで表示
    if st.session_state['last_change'] != 0:
        c = st.session_state['last_change']
        st.toast(f"{'好感度アップ！' if c > 0 else '好感度ダウン...'} ({c})")
        st.session_state['last_change'] = 0

    st.divider()

    col_img, col_chat = st.columns([0.4, 0.6])
    with col_img:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg")
        else: st.empty()
    
    with col_chat:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("氷室があなたの言葉を待っています..."):
                new_turn = generate_conversation_turn_with_ai()
                if new_turn:
                    st.session_state['conversation_history'].append(new_turn)
                    st.session_state['game_state'] = 'CONVERSATION'
                    st.rerun()
        
        if st.session_state['conversation_history']:
            turn_data = st.session_state['conversation_history'][-1]
            st.markdown(f"**氷室 涼**")
            st.info(turn_data['character_speech'])

    # 選択肢ボタン
    if st.session_state['game_state'] == 'CONVERSATION':
        for i, choice in enumerate(st.session_state['conversation_history'][-1]['choices']):
            st.button(choice['text'], key=f"btn_{i}", on_click=handle_choice, args=(choice['score'],), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    # リザルト（前回の演出を維持）
    st.balloons() if st.session_state['favor_ryo'] >= 80 else None
    st.header("RESULT")
    st.metric("最終信頼度", st.session_state['favor_ryo'])
    # (エンディングメッセージ表示ロジック...)
    if st.button("タイトルへ"):
        st.session_state.clear()
        st.rerun()
