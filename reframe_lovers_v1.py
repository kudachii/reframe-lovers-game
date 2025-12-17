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
# 0. Gemini APIの設定 (Streamlit CloudのSecretsを使用)
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのSettings > Secretsに 'GEMINI_API_KEY' を登録してください。")

# ----------------------------------------------------
# 1. ゴールデンプロンプト（システム命令）
# ----------------------------------------------------
SYSTEM_PROMPT = """
あなたは、近未来のテック・スタートアップ「Reframe Lovers」のシステム開発部門のエース「氷室 涼（ひむろ りょう）」として振る舞ってください。

【氷室 涼の設定】
- 性格：クール、論理的思考、無口。内面は非常に情熱的で努力家だが、効率を重視しすぎるため、周囲に誤解されやすい。褒められることに慣れていない。
- 口調：基本的に敬語。感情が高ぶると稀にタメ口になる。セリフは短く、核心をつくる。
- 主人公への態度：仕事中は厳しい。しかし、主人公の努力やポジティブな変化（自信レベル）を誰よりもよく見ている。

【ゲームルールと動的生成】
- 主人公の性別：{gender}（男性なら切磋琢磨するライバル、女性ならクールな中に配慮が見える同期として接する）
- 主人公の自信レベル：Lv.{conf_level}/3（このレベルが高いほど、氷室は主人公を認め、対等な議論を好むようになる）
- 自信レベルに応じた選択肢の数：
  - Lv.0: 2択（消極的、または守りの選択肢）
  - Lv.1: 3択
  - Lv.2: 4択
  - Lv.3: 5択（大胆で情熱的、あるいは氷室を驚かせるような核心を突く選択肢を含める）

【出力形式】
必ず以下のJSON形式のみで出力してください。他の説明文は一切不要です。
{{
  "character_speech": "氷室のセリフ",
  "choices": [
    {{"text": "選択肢のテキスト", "consequence": "favor_up, favor_down, neutral, favor_up_major, neutral_conf_up のいずれか"}},
    ...
  ]
}}
"""

# ----------------------------------------------------
# 2. 基本設定とセッション管理
# ----------------------------------------------------
st.set_page_config(layout="centered", page_title="Reframe Lovers")

# セッションステート初期化
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_language': 'JA',
        'continuous_days': 0,
        'game_state': 'START',
        'player_gender': 'Female',
        'player_name': 'あなた',
        'confidence_level': 0,
        'conversation_history': [],
        'favor_ryo': 50,
        'feedback_message': None
    })

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
        return max(streak, 1)
    except: return 0

def generate_conversation_turn_with_ai():
    gender_label = "女性" if st.session_state['player_gender'] == "Female" else "男性"
    conf = st.session_state['confidence_level']
    
    prompt = SYSTEM_PROMPT.format(gender=gender_label, conf_level=conf)
    prompt += "\n現在の状況：第1話「エースの葛藤」。金曜日の終業間際、オフィスにて。君（氷室）が担当した重要資料にミスがあることを君は察知しており、主人公の様子を伺いながら声をかける場面。"

    # --- 404エラー対策用モデルリスト ---
    model_names = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'models/gemini-1.5-flash']
    
    last_error = None
    for m_name in model_names:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            last_error = e
            continue # 次のモデル名を試す
            
    st.error(f"全モデル名で生成に失敗しました。最後のメッセージ: {last_error}")
    return None

def handle_choice(consequence):
    if consequence == "favor_up_major": 
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 15)
        st.session_state['feedback_message'] = ("success", "💖 氷室の表情がわずかに和らいだ！ (+15)")
    elif consequence == "favor_up": 
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10)
        st.session_state['feedback_message'] = ("success", "❤️ 好感度が上がった。 (+10)")
    elif consequence == "favor_down": 
        st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5)
        st.session_state['feedback_message'] = ("error", "💔 氷室はため息をついた... (-5)")
    elif consequence == "neutral_conf_up": 
        st.session_state['confidence_level'] = min(3, st.session_state['confidence_level'] + 1)
        st.session_state['feedback_message'] = ("info", "💪 自分の意見を伝えたことで、少し自信がついた。")
    
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. メインUI
# ----------------------------------------------------
st.title("🏙️ Reframe Lovers")
st.caption("〜スタートアップの空の下で〜 (AI Prototype)")

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state['player_gender'] = st.selectbox("主人公の性別", ["Female", "Male"], 
                                                        format_func=lambda x: "女性" if x == "Female" else "男性")
    with col2:
        st.session_state['player_name'] = st.text_input("名前", value=st.session_state['player_name'])
    
    st.markdown("---")
    st.subheader("🔗 ポジティブ日記データを連動")
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")
    
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
        st.success(f"データロード成功！ 連続記録: {days}日")
        st.write(f"**現在の自信Lv:** {st.session_state['confidence_level']} / 3")
        st.progress(st.session_state['confidence_level'] / 3.0)

    if st.button("ゲームを開始する ➡️", type="primary", use_container_width=True):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("❤️ 好感度", st.session_state['favor_ryo'])
    col_s2.metric("⭐ 自信Lv", st.session_state['confidence_level'])
    
    if st.session_state['feedback_message']:
        m_type, m_txt = st.session_state['feedback_message']
        if m_type == "success": st.success(m_txt)
        elif m_type == "error": st.error(m_txt)
        else: st.info(m_txt)

    st.markdown("---")

    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
        with st.spinner("氷室 涼が言葉を選んでいます..."):
            new_turn = generate_conversation_turn_with_ai()
            if new_turn:
                st.session_state['conversation_history'].append(new_turn)
                st.session_state['game_state'] = 'CONVERSATION'
                st.rerun()

    if st.session_state['conversation_history']:
        last_turn = st.session_state['conversation_history'][-1]
        with st.chat_message("assistant"):
            st.write(f"**氷室 涼**")
            st.write(last_turn['character_speech'])
        
        st.write(" ")
        st.caption("あなたの返答を選択してください:")
        
        for i, choice in enumerate(last_turn['choices']):
            st.button(
                choice['text'], 
                key=f"choice_{i}_{len(st.session_state['conversation_history'])}", 
                on_click=handle_choice, 
                args=(choice['consequence'],), 
                use_container_width=True
            )
