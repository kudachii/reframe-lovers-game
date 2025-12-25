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
# 1. モデル取得ロジック（エラー対策の要）
# ----------------------------------------------------
def get_best_model():
    """環境で利用可能な最適なモデルを自動で探す"""
    try:
        # 利用可能なモデルを取得
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先順位をつけてモデルを探す
        priorities = [
            'models/gemini-1.5-flash-latest', 
            'models/gemini-1.5-flash', 
            'models/gemini-pro'
        ]
        
        for p in priorities:
            if p in available_models:
                return p
        # 見つからなければ最初に見つかったもの
        return available_models[0] if available_models else None
    except Exception:
        return 'models/gemini-1.5-flash' # フォールバック

# ----------------------------------------------------
# 2. セッション管理
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
        'last_change': 0
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 3. ロジック関数
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

    if favor >= 80:
        tone = "非常に親密。完璧な敬語の中に、深い信頼と独占欲が見える。"
    elif favor >= 50:
        tone = "丁寧な敬語。仕事のパートナーとしての信頼と気遣い。"
    else:
        tone = "冷徹な事務的敬語。感情を排した態度。"

    prompt = f"""
    あなたは「氷室 涼」です。相手：名前「{name}」、性別「{gender}」、自信Lv「{conf}/3」、好感度「{favor}/100」。
    【性格】{tone}
    【状況】会話{turn+1}回目。残業中のオフィス。
    【特別指示】自信Lvが{conf}であることを踏まえ、相手の「最近の成長ぶり」を評価または皮肉ってください。
    
    必ず以下のJSON形式でのみ出力。
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢", "score": 10}}
      ]
    }}
    ※choicesは必ず【{num_choices}個】生成し、地雷（score: -10）を1つ含めてください。
    """
    
    model_name = get_best_model()
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        st.error(f"モデル '{model_name}' での生成に失敗しました: {e}")
        return None

def handle_choice(score):
    conf_lv = st.session_state['confidence_level']
    change = score if score <= 0 else int(score * {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0))
    st.session_state['favor_ryo'] += change
    st.session_state['last_change'] = change
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. UI表示
# ----------------------------------------------------

st.markdown("## 🏙️ Reframe Lovers")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    uploaded_file = st.file_uploader("日記CSVを同期", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state['confidence_level'], st.session_state['diary_count'] = calculate_confidence(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.success(f"同期完了！ 自信Lv.{st.session_state['confidence_level']}")

    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    # ステータスバー表示
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write(f"❤️ **信頼度**")
        st.progress(min(max(st.session_state['favor_ryo'] / 100, 0.0), 1.0))
    with col_s2:
        st.write(f"✨ **自信**: {'⭐' * st.session_state['confidence_level']}{'⚪' * (3 - st.session_state['confidence_level'])}")
    
    if st.session_state['last_change'] != 0:
        st.toast(f"変化: {st.session_state['last_change']}")
        st.session_state['last_change'] = 0

    st.divider()

    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
        with st.spinner("AIが氷室の言葉を生成中..."):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()

    col_img, col_chat = st.columns([0.4, 0.6])
    with col_img:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg")
        else: st.info("氷室 涼")

    with col_chat:
        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            st.markdown(f"**氷室 涼**")
            st.info(last_turn['character_speech'])

    st.markdown("---")
    if st.session_state['conversation_history']:
        for i, choice in enumerate(st.session_state['conversation_history'][-1].get('choices', [])):
            st.button(choice['text'], key=f"c_{st.session_state['turn_count']}_{i}", on_click=handle_choice, args=(choice.get('score', 0),), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    # リザルト画面
    st.metric("最終信頼度", st.session_state['favor_ryo'])
    if st.button("もう一度挑戦"):
        st.session_state.clear()
        st.rerun()
