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
        'selected_model': None,
        'last_feedback': None # 直前の好感度変化を保存
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

    # 性別による振る舞い指示
    if gender == "Female":
        personality = f"氷室は{name}を『優秀だが放っておけない大切な同期』として見ています。配慮の中に微かな甘さを混ぜてください。"
    else:
        personality = f"氷室は{name}を『背中を預けられる最高のライバル』として見ています。対等で熱いプロ意識を持って接してください。"

    situations = [
        f"第1段階：ミス発覚直後。氷室が{name}に対し、鋭く正論を突きつけている状況。",
        f"第2段階：修正作業中。オフィスの静寂。氷室は{name}の粘り強さを評価し始めている。",
        f"第3段階（最終）：作業完了。達成感の中で氷室が心の壁を少し下げ、個人的な本音を語る。"
    ]

    prompt = f"""
    あなたはスタートアップのエース「氷室 涼」です。
    相手：名前「{name}」、性別「{gender_label}」、自信レベル「Lv.{conf}/3」。
    【キャラクター指示】{personality}
    
    【ルール】
    1. 会話の{turn+1}回目。状況：{situations[min(turn, 2)]}
    2. 選択肢を必ず【{num_choices}個】生成。
    3. 必ず1つは好感度が大きく下がる「地雷選択肢」を入れてください。
    
    必ず以下のJSON形式のみで出力。
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢", "score": 10}},
        {{"text": "地雷選択肢", "score": -10}}
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

def handle_choice(score):
    conf_lv = st.session_state.get('confidence_level', 0)
    change = 0
    if score > 0:
        multiplier = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0)
        change = int(score * multiplier)
    else:
        change = score # 地雷は一律
    
    st.session_state['favor_ryo'] += change
    st.session_state['last_feedback'] = f"好感度が {change} {'上がった' if change > 0 else '下がった'}..."
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. メインUI
# ----------------------------------------------------
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)

# --- 設定画面 ---
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            st.session_state['game_state'] = 'DIARY_LOADED'
            mult = {0:0.5, 1:1, 2:1.5, 3:2}[st.session_state['confidence_level']]
            st.success(f"データ連動完了！ 自信Lv.{st.session_state['confidence_level']} (好感度倍率: {mult}x)")
        except: st.error("CSV読み込み失敗")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        if st.session_state['game_state'] == 'START': st.session_state['confidence_level'] = 0
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# --- 会話画面 ---
elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    f_val = st.session_state.get('favor_ryo', 50)
    c_val = st.session_state.get('confidence_level', 0)
    t_val = st.session_state.get('turn_count', 0)
    p_name = st.session_state.get('player_name', 'あなた')
    
    st.write(f"👤 **{p_name}** | ❤️ **好感度:** {f_val} | ⭐ **自信:** Lv.{c_val} | 💬 **進行:** {t_val+1}/3")
    
    # 直前のフィードバック表示
    if st.session_state.get('last_feedback'):
        st.toast(st.session_state['last_feedback'])
        st.session_state['last_feedback'] = None

    col_left, col_right = st.columns([0.4, 0.6])
    with col_left:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg", use_container_width=True)
        else: st.warning("Image missing")

    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("氷室 涼が思考中..."):
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

# --- 結果画面 ---
elif st.session_state['game_state'] == 'RESULT':
    p_name = st.session_state.get('player_name', 'あなた')
    st.subheader(f"🏁 {p_name}さんの最終結果")
    favor = st.session_state.get('favor_ryo', 50)
    st.metric("最終好感度", favor)
    
    if favor >= 80:
        st.success(f"【ハッピーエンド】氷室は{p_name}さんの実力を認め、食事に誘ってくれました。「次はミスなしで。……期待していますよ」")
    elif favor >= 50:
        st.info(f"【ノーマルエンド】「お疲れ様。次は気をつけてください」氷室はそれだけ言って、いつも通り去っていきました。")
    else:
        st.error(f"【バッドエンド】「失望させないでください。……失礼。」氷室の目は冷たいままでした。")
    
    if st.button("タイトルへ戻る", use_container_width=True):
        st.session_state.clear()
        st.rerun()
