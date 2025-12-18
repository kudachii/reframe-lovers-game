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
    st.error("APIキーが設定されていません。")

# ----------------------------------------------------
# 1. セッション管理（ターン管理を追加）
# ----------------------------------------------------
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'START', 
        'player_gender': 'Female', 
        'player_name': 'あなた',
        'continuous_days': 0,
        'confidence_level': 0, 
        'conversation_history': [], 
        'favor_ryo': 50, 
        'turn_count': 0, # 何回目の会話か
        'selected_model': None
    })

# ----------------------------------------------------
# 2. ロジック関数
# ----------------------------------------------------

# (calculate_streak_from_df, get_available_model は変更なしのため省略可能ですが、全体版として維持)
def calculate_streak_from_df(df):
    date_candidates = ['日付', 'Date', 'datetime', 'timestamp', 'date_local']
    date_column = next((col for col in df.columns if col in date_candidates), None)
    if not date_column: return 0
    try:
        df['date_only'] = pd.to_datetime(df[date_column], errors='coerce').dt.date
        unique_dates = sorted(list(df['date_only'].dropna().unique()), reverse=True)
        if not unique_dates: return 0
        streak, check_date = 0, datetime.datetime.now(pytz.timezone('Asia/Tokyo')).date()
        for d in unique_dates:
            if d == check_date: streak += 1; check_date -= datetime.timedelta(days=1)
            elif d < check_date: break
        return max(streak, 1)
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
    gender_label = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    turn = st.session_state['turn_count']
    
    # ターンに応じたシチュエーション設定
    situations = [
        "第1段階：ミスが発覚した直後。氷室が冷徹に状況を指摘している。",
        "第2段階：二人で修正作業中。少し疲れが見えるが、氷室はあなたの仕事ぶりを観察している。",
        "第3段階（最終）：作業完了。オフィスの明かりが消え始める中、氷室がふと本音を漏らす。"
    ]
    current_sit = situations[min(turn, 2)]

    prompt = f"""
    あなたは、テック・スタートアップ「Reframe Lovers」のエース「氷室 涼」です。
    性格：クール、論理的、無口。
    設定：性別 {gender_label}、自信Lv {conf}/3。
    状況：{current_sit}
    
    指示：会話の{turn+1}回目として、相手の前の選択を汲み取ったセリフを生成してください。
    必ず以下のJSON形式のみで出力。
    {{
      "character_speech": "セリフ",
      "choices": [
        {{"text": "選択肢", "consequence": "favor_up, favor_down, neutral, favor_up_major, neutral_conf_up のいずれか"}}
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
    # 好感度計算
    if "favor_up_major" in consequence: st.session_state['favor_ryo'] += 15
    elif "favor_up" in consequence: st.session_state['favor_ryo'] += 10
    elif "down" in consequence: st.session_state['favor_ryo'] -= 5
    
    # ターンを進める
    st.session_state['turn_count'] += 1
    
    # 3ターン終わったらリザルトへ
    if st.session_state['turn_count'] >= 3:
        st.session_state['game_state'] = 'RESULT'
    else:
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. UI表示
# ----------------------------------------------------
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    # (導入画面は変更なし)
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state['continuous_days'] = calculate_streak_from_df(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
    if st.button("ゲームを開始する"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    st.write(f"❤️ 好感度: {st.session_state['favor_ryo']} | 💬 Progress: {st.session_state['turn_count']+1}/3")
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
            st.markdown(f"**氷室 涼**")
            st.info(last_turn['character_speech'])
    st.markdown("---")
    if st.session_state['conversation_history']:
        for i, choice in enumerate(st.session_state['conversation_history'][-1]['choices']):
            st.button(choice['text'], key=f"c_{i}_{st.session_state['turn_count']}", on_click=handle_choice, args=(choice['consequence'],), use_container_width=True)

elif st.session_state['game_state'] == 'RESULT':
    st.subheader("🎉 Result")
    favor = st.session_state['favor_ryo']
    st.write(f"最終好感度: {favor}")
    if favor >= 80:
        st.success("【ハッピーエンド】氷室はあなたの実力を認め、食事に誘ってくれました。「次はミスなしで。……期待していますよ」")
    elif favor >= 50:
        st.info("【ノーマルエンド】「お疲れ様。次は気をつけてください」氷室はそれだけ言って去っていきました。")
    else:
        st.error("【バッドエンド】「……明日、再提出を。失礼します」氷室の目は冷たいままでした。")
    
    if st.button("もう一度プレイする"):
        st.session_state.clear()
        st.rerun()
