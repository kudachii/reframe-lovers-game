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
# 1. セッション管理（すべての設定変数をここで初期化）
# ----------------------------------------------------
def init_session():
    defaults = {
        'game_state': 'START', 
        'player_gender': 'Female', 
        'player_name': 'あなた',
        'continuous_days': 0,
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
def calculate_streak_from_df(df):
    date_candidates = ['日付', 'Date', 'datetime', 'timestamp', 'date_local']
    date_column = next((col for col in df.columns if col in date_candidates), None)
    if not date_column: return 0
    try:
        df['date_only'] = pd.to_datetime(df[date_column], errors='coerce').dt.date
        unique_dates = sorted(list(df['date_only'].dropna().unique()), reverse=True)
        if not unique_dates: return 0
        streak, check_date = datetime.datetime.now(pytz.timezone('Asia/Tokyo')).date(), 0 # ダミー
        streak_count = 0
        check_date = unique_dates[0] # 最新の日付から数える簡易版
        # 本来は今日との比較が必要ですが、デモ用にリストの連続性を優先
        streak_count = len(unique_dates) 
        return streak_count
    except: return 0

def get_available_model():
    current_model = st.session_state.get('selected_model')
    if current_model: return current_model
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_models = ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-1.5-flash-latest']
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
    
    situations = [
        f"第1段階：ミスが発覚した直後。氷室が{name}のミスを冷徹に指摘し、問い詰めている。",
        f"第2段階：二人で修正作業中。オフィスの静寂の中、氷室は{name}の仕事ぶりを横目で観察している。",
        f"第3段階（最終）：作業完了。疲れきった{name}に対し、氷室がふと椅子を回して個人的な話を切り出す。"
    ]
    current_sit = situations[min(turn, 2)]

    prompt = f"""
    あなたは、テック・スタートアップ「Reframe Lovers」のエース「氷室 涼」です。
    性格：クール、論理的、無口。内面は情熱的。
    相手の情報：名前「{name}」、性別「{gender}」、自信Lv「{conf}/3」。
    状況：{current_sit}
    
    指示：会話の{turn+1}回目として、{name}のこれまでの態度を踏まえたセリフを生成してください。
    必ず以下のJSON形式のみで出力。
    {{
      "character_speech": "セリフの内容。適宜相手の名前を呼んでください。",
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

# --- 設定・導入画面 ---
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    st.markdown("---")
    st.subheader("🔗 データの連動")
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード（自信に影響します）", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except:
            df = pd.read_csv(uploaded_file, encoding='cp932')
        st.session_state['continuous_days'] = calculate_streak_from_df(df)
        st.session_state['game_state'] = 'DIARY_LOADED'

    if st.session_state['game_state'] == 'DIARY_LOADED':
        days = st.session_state['continuous_days']
        st.session_state['confidence_level'] = min(3, days // 2) # 簡易計算
        st.success(f"データ連動完了！ {st.session_state['player_name']}さんの自信Lv: {st.session_state['confidence_level']}")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# --- 会話画面 ---
elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    name = st.session_state.get('player_name', 'あなた')
    st.write(f"👤 **{name}** | ❤️ **好感度:** {st.session_state['favor_ryo']} | 💬 **進行:** {st.session_state['turn_count']+1}/3")
    
    col_left, col_right = st.columns([0.4, 0.6])
    with col_left:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg", use_container_width=True)
    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner(f"氷室 涼が{name}に向き合っています..."):
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
        for i, choice in enumerate(st.session_state['conversation_history'][-1].get('choices', [])):
            st.button(choice['text'], key=f"c_{i}_{st.session_state['turn_count']}", on_click=handle_choice, args=(choice['consequence'],), use_container_width=True)

# --- 結果画面 ---
elif st.session_state['game_state'] == 'RESULT':
    name = st.session_state.get('player_name', 'あなた')
    st.subheader(f"🏁 {name}さんの結果")
    favor = st.session_state.get('favor_ryo', 50)
    st.write(f"最終好感度: {favor}")
    
    if favor >= 80:
        st.success(f"【ハッピーエンド】氷室は{name}さんの目を見て言いました。「…次は、二人で祝杯を上げましょう。期待していますよ」")
    elif favor >= 50:
        st.info(f"【ノーマルエンド】「お疲れ様。{name}さん。また明日。」氷室はいつも通り、静かにオフィスを去りました。")
    else:
        st.error(f"【バッドエンド】「失望させないでください。…失礼。」氷室の足音だけが空虚に響きました。")
    
    if st.button("タイトルへ戻る"):
        st.session_state.clear()
        st.rerun()
