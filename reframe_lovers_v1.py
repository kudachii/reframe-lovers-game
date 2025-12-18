# -*- coding: utf-8 -*-
import streamlit as st
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
    """CSVから自信レベル(0-3)を計算。単なる数だけでなく継続性を意識"""
    if df is None or df.empty:
        return 0
    count = len(df)
    # 1週間以上継続(7行)でMAX、3日で中級、1日で初級
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
    except:
        return None

def generate_conversation_turn_with_ai():
    name = st.session_state.get('player_name', 'あなた')
    gender = st.session_state.get('player_gender', 'Female')
    gender_label = "女性" if gender == "Female" else "男性"
    conf = st.session_state.get('confidence_level', 0)
    turn = st.session_state.get('turn_count', 0)
    
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)

    # 性別による振る舞いの詳細指示
    if gender == "Female":
        personality_directive = f"氷室は{name}を『優秀だが危なっかしい大切な同期』として見ています。クールな中にも、ふとした瞬間に彼女を守ろうとする甘さや配慮を見せてください。"
    else:
        personality_directive = f"氷室は{name}を『背中を預けられる唯一のライバル』として見ています。馴れ合いはしませんが、彼の実力を誰よりも高く評価しており、対等で熱い議論を好みます。"

    situations = [
        f"第1段階：ミス発覚直後。氷室が{name}に対し、淡々と、しかし逃げ場のない正論で状況を問うている。",
        f"第2段階：修正作業中。オフィスの静寂。氷室は{name}の仕事ぶりを横目で見て、その成長を感じ取っている。",
        f"第3段階（最終）：作業完了。達成感の中で氷室の心の壁が少しだけ低くなり、本音を漏らす。"
    ]
    current_sit = situations[min(turn, 2)]

    prompt = f"""
    あなたはテック・スタートアップ「Reframe Lovers」のエース「氷室 涼」です。
    相手の情報：名前「{name}」、性別「{gender_label}」、自信レベル「Lv.{conf}/3」。
    
    【キャラクター指示】
    {personality_directive}
    口調は基本敬語ですが、自信レベル{conf}が高い場合、あるいは好感度が高い場合は少し距離が近づきます。
    
    【ルール】
    1. 状況：{current_sit}
    2. 選択肢を必ず【{num_choices}個】生成してください。
    3. 自信レベルが高いほど、{name}が氷室に対して堂々と意見を言い、彼を感心させるような選択肢を含めてください。
    
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
    except:
        return None

# (handle_choice, UI部分は前回のものを維持しつつ、性別の扱いを最適化)
def handle_choice(consequence):
    if "favor_up_major" in consequence: st.session_state['favor_ryo'] += 15
    elif "favor_up" in consequence: st.session_state['favor_ryo'] += 10
    elif "down" in consequence: st.session_state['favor_ryo'] -= 5
    st.session_state['turn_count'] += 1
    st.session_state['game_state'] = 'RESULT' if st.session_state['turn_count'] >= 3 else 'CONVERSATION_LOAD'
    st.rerun()

# --- UI (会話画面での性別アイコン表示など) ---
st.markdown("<h2 style='text-align: center;'>🏙️ Reframe Lovers</h2>", unsafe_allow_html=True)

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    st.markdown("---")
    st.subheader("🔗 データの連動")
    st.caption("CSVの日記データが多いほど、氷室に対して堂々とした態度（選択肢増）が取れるようになります。")
    uploaded_file = st.file_uploader("ポジティブ日記CSVをアップロード", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            st.session_state['game_state'] = 'DIARY_LOADED'
            st.success(f"連動完了！ 自信Lv.{st.session_state['confidence_level']}。氷室の見る目が変わるかもしれません。")
        except:
            st.error("CSV読み込みエラー")

    if st.button("ゲームを開始する", type="primary", use_container_width=True):
        if st.session_state['game_state'] == 'START':
            st.session_state['confidence_level'] = 0
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    f_val = st.session_state.get('favor_ryo', 50)
    c_val = st.session_state.get('confidence_level', 0)
    t_val = st.session_state.get('turn_count', 0)
    p_name = st.session_state.get('player_name', 'あなた')
    gender_icon = "👩" if st.session_state.get('player_gender') == "Female" else "👦"
    
    st.write(f"{gender_icon} **{p_name}** | ❤️ **好感度:** {f_val} | ⭐ **自信:** Lv.{c_val} | 💬 **進行:** {t_val+1}/3")
    
    col_left, col_right = st.columns([0.4, 0.6])
    with col_left:
        if os.path.exists("bg_image.jpg"): st.image("bg_image.jpg", use_container_width=True)
    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner("氷室 涼があなたの言葉を待っています..."):
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
        choices = st.session_state['conversation_history'][-1].get('choices', [])
        for i, choice in enumerate(choices):
            st.button(choice['text'], key=f"c_{i}_{t_val}", on_click=handle_choice, args=(choice['consequence'],), use_container_width=True)

# (RESULT画面は前回同様のため省略可能ですが、ロジック維持)
elif st.session_state['game_state'] == 'RESULT':
    st.subheader("🏁 結果発表")
    favor = st.session_state.get('favor_ryo', 50)
    if favor >= 80: st.success("【ハッピーエンド】氷室は微笑みました。")
    elif favor >= 50: st.info("【ノーマルエンド】良い関係を築けました。")
    else: st.error("【バッドエンド】厳しい評価でした。")
    if st.button("タイトルへ"):
        st.session_state.clear()
        st.rerun()
