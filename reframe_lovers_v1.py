# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 
import os 
import random 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定 (GitHub Secrets/Streamlit Cloud Secrets)
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのSecretsに 'GEMINI_API_KEY' を登録してください。")

# ----------------------------------------------------
# 1. ゴールデンプロンプト（システム命令）
# ----------------------------------------------------
SYSTEM_PROMPT = """
あなたは、近未来のテック・スタートアップ「Reframe Lovers」のシステム開発部門のエース「氷室 涼（ひむろ りょう）」として振る舞ってください。

【氷室 涼の設定】
- 年齢：20代後半
- 性格：クール、論理的思考、無口。内面は非常に情熱的で努力家だが、効率を重視しすぎるため、周囲に誤解されやすい。褒められることに慣れていない。
- 口調：基本的に敬語。感情が高ぶるとタメ口になる。セリフは短く核心を突く。
- 主人公への態度：仕事中は厳しく私情を挟まないが、主人公の努力や「自信」の変化を誰よりもよく見ている。

【ゲームルールと動的生成】
- 主人公の性別：{gender}（男性ならライバル、女性なら同期としてのトーンに調整）
- 主人公の自信レベル：Lv.{conf_level}/3（記録日数に基づく）
- 自信レベルに応じた選択肢の数：
  - Lv.0: 2択（消極的な行動のみ）
  - Lv.1: 3択
  - Lv.2: 4択
  - Lv.3: 5択（大胆で核心を突く提案を含む）

【出力形式】
必ず以下のJSON形式のみで出力してください。
{{
  "character_speech": "氷室のセリフ",
  "choices": [
    {{"text": "選択肢のテキスト", "consequence": "favor_up, favor_down, neutral, favor_up_major, neutral_conf_up のいずれか"}},
    ...
  ]
}}
"""

# ----------------------------------------------------
# 2. 多言語対応
# ----------------------------------------------------
GAME_TRANSLATIONS = {
    "JA": {
        "TITLE": "Reframe Lovers 〜スタートアップの空の下で〜",
        "LANG_SELECT": "言語を選択",
        "GENDER_SELECT": "主人公の性別を選択",
        "GENDER_MALE": "男性 (Man)",
        "GENDER_FEMALE": "女性 (Woman)",
        "NAME_INPUT": "主人公の名前を入力してください",
        "CSV_HEADER": "🔗 ポジティブ日記データの連動",
        "CSV_UPLOAD": "ポジティブ日記のCSVファイルをアップロード",
        "LOAD_BUTTON": "データをロードしてゲーム開始",
        "DATA_SUCCESS": "✅ データロード成功！",
        "CONTINUOUS_DAYS": "連続記録日数:",
        "CONFIDENCE_GAUGE": "現在の自信ゲージ (Confidence):",
        "START_GAME": "ゲームを開始する ➡️"
    }
}

def get_text(key):
    lang = st.session_state.get('game_language', 'JA')
    return GAME_TRANSLATIONS["JA"].get(key, key)

# セッションステート初期化
for key, val in {
    'game_language': 'JA', 'continuous_days': 0, 'game_state': 'START',
    'player_gender': 'Female', 'player_name': 'あなた', 'confidence_level': 0,
    'conversation_history': [], 'favor_ryo': 50, 'feedback_message': None
}.items():
    st.session_state.setdefault(key, val)

# ----------------------------------------------------
# 3. ロジック（連続日数計算・AI生成）
# ----------------------------------------------------
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
        return streak if streak > 0 else 1 # データがあれば最低1日
    except: return 0

def generate_conversation_turn_with_ai():
    gender = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    
    prompt = SYSTEM_PROMPT.format(gender=gender, conf_level=conf)
    prompt += "\nシチュエーション：第1話。金曜日の終業間際、君が担当した重要資料にミスを発見し、氷室が声をかけてきた場面。"

    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        return {"character_name": "氷室 涼", "character_speech": data["character_speech"], "choices": data["choices"]}
    except Exception as e:
        st.error(f"AI生成エラー: {e}")
        return None

def handle_choice(consequence):
    if consequence == "favor_up_major": st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 15); st.session_state['feedback_message'] = ("success", "💖 好感度が大きく上がった！")
    elif consequence == "favor_up": st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10); st.session_state['feedback_message'] = ("success", "❤️ 好感度が上がった！")
    elif consequence == "favor_down": st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5); st.session_state['feedback_message'] = ("error", "💔 氷室の眉がピクリと動いた...")
    elif consequence == "neutral_conf_up": st.session_state['confidence_level'] = min(3, st.session_state['confidence_level'] + 1); st.session_state['feedback_message'] = ("info", "💪 確かな手応えを感じた。")
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. UIレンダリング
# ----------------------------------------------------
st.set_page_config(layout="centered", page_title=get_text("TITLE"))
st.title(get_text("TITLE"))

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.session_state['player_gender'] = st.selectbox(get_text("GENDER_SELECT"), ["Female", "Male"], format_func=lambda x: get_text("GENDER_FEMALE") if x == "Female" else get_text("GENDER_MALE"))
    st.session_state['player_name'] = st.text_input(get_text("NAME_INPUT"), value=st.session_state['player_name'])
    
    uploaded_file = st.file_uploader(get_text("CSV_UPLOAD"), type="csv")
    if uploaded_file and st.session_state['game_state'] == 'START':
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except:
            df = pd.read_csv(uploaded_file, encoding='cp932')
        st.session_state['continuous_days'] = calculate_streak_from_df(df)
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.rerun()

    if st.session_state['game_state'] == 'DIARY_LOADED':
        days = st.session_state['continuous_days']
        st.session_state['confidence_level'] = 3 if days >= 7 else 2 if days >= 3 else 1 if days >= 1 else 0
        st.markdown(f"**{get_text('CONTINUOUS_DAYS')}** {days}日 / **自信Lv:** {st.session_state['confidence_level']}")
        st.progress(st.session_state['confidence_level'] / 3.0)

    if st.button(get_text("START_GAME"), type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    st.subheader(f"❤️ 好感度: {st.session_state['favor_ryo']} | ⭐ 自信: Lv.{st.session_state['confidence_level']}")
    
    if st.session_state['feedback_message']:
        m_type, m_txt = st.session_state['feedback_message']
        if m_type == "success": st.success(m_txt)
        elif m_type == "error": st.error(m_txt)
        else: st.info(m_txt)

    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
        with st.spinner("氷室 涼が思考中..."):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()

    if st.session_state['conversation_history']:
        last_turn = st.session_state['conversation_history'][-1]
        st.chat_message("assistant").write(last_turn['character_speech'])
        
        for i, choice in enumerate(last_turn['choices']):
            st.button(choice['text'], key=f"c_{i}_{time.time()}", on_click=handle_choice, args=(choice['consequence'],), use_container_width=True)
