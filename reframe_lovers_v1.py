# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 

# ----------------------------------------------------
# 1. 多言語対応とセッションステートの初期化
# ----------------------------------------------------
GAME_TRANSLATIONS = {
    # ... (GAME_TRANSLATIONSの定義は省略しませんが、スペース節約のためここでは中身を省略) ...
    "JA": {
        "TITLE": "Reframe Lovers 〜スタートアップの空の下で〜 (プロトタイプ)",
        "LANG_SELECT": "言語を選択 / Select Language",
        "GENDER_SELECT": "主人公の性別を選択",
        "GENDER_MALE": "男性 (Man)",
        "GENDER_FEMALE": "女性 (Woman)",
        "NAME_INPUT": "主人公の名前を入力してください",
        "CSV_HEADER": "🔗 ポジティブ日記データの連動",
        "CSV_UPLOAD": "ポジティブ日記の最新のCSVファイルをアップロードしてください",
        "CSV_HINT": "※このファイルから「自信ゲージ」を計算します。",
        "LOAD_BUTTON": "データをロードしてゲーム開始",
        "DATA_ERROR": "⚠️ データエラー：CSVをアップロードするか、ファイルが壊れていないか確認してください。",
        "DATA_SUCCESS": "✅ データロード成功！",
        "CONTINUOUS_DAYS": "連続記録日数:",
        "CONFIDENCE_GAUGE": "現在の自信ゲージ (Confidence):",
        "START_GAME": "ゲームを開始する ➡️"
    },
    "EN": {
        "TITLE": "Reframe Lovers ~Under the Startup Sky~ (Prototype)",
        "LANG_SELECT": "Select Language / 言語を選択",
        "GENDER_SELECT": "Select Player Gender",
        "GENDER_MALE": "Male",
        "GENDER_FEMALE": "Female",
        "NAME_INPUT": "Enter Player Name",
        "CSV_HEADER": "🔗 Link Positive Diary Data",
        "CSV_UPLOAD": "Please upload the latest CSV file from your Positive Diary App",
        "CSV_HINT": "※This file is used to calculate your Confidence Gauge.",
        "LOAD_BUTTON": "Load Data and Start Game",
        "DATA_ERROR": "⚠️ Data Error: Please upload a valid CSV file.",
        "DATA_SUCCESS": "✅ Data Load Successful!",
        "CONTINUOUS_DAYS": "Continuous Recording Days:",
        "CONFIDENCE_GAUGE": "Current Confidence Gauge:",
        "START_GAME": "Start Game ➡️"
    }
}
def get_text(key):
    lang = st.session_state.get('game_language', 'JA')
    return GAME_TRANSLATIONS.get(lang, GAME_TRANSLATIONS['JA']).get(key, f"MISSING TEXT: {key}")

# セッションステートの初期化
st.session_state.setdefault('game_language', 'JA')
st.session_state.setdefault('continuous_days', 0)
st.session_state.setdefault('game_state', 'START') 
st.session_state.setdefault('player_gender', 'Female') 
st.session_state.setdefault('player_name', 'あなた')
st.session_state.setdefault('confidence_level', 1)
st.session_state.setdefault('conversation_history', []) 
st.session_state.setdefault('favor_ryo', 50)
st.session_state.setdefault('uploaded_image_data', None) # 🚨 新規追加: 画像データ保持用
st.session_state.setdefault(
    'conversation_theme', 
    "金曜日の終業間際、オフィスの休憩スペースにて。主人公は、自分が担当した重要資料に**致命的なデータミスを発見**し、報告するか黙って修正するか迷っている。氷室は、主人公が資料を前に押し黙っていることに気づき、声をかける。"
)

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (省略)
# ----------------------------------------------------
def calculate_streak_from_df(df):
    # ... (省略) ...
    return 0 

# ----------------------------------------------------
# 3. AI会話生成ロジック (省略)
# ----------------------------------------------------

def generate_conversation_turn(conversation_context):
    player_name = st.session_state['player_name']
    confidence_level = st.session_state['confidence_level']

    time.sleep(0.5) 
    current_turn_count = len(st.session_state['conversation_history']) + 1 
    
    if confidence_level >= 3:
        speech = f"[ターン {current_turn_count}] {player_name}、まだ残っていたのか。珍しいな。その資料... 深刻な顔をしているが、まさか致命的なミスか？正直に話すべきだ。それが、お前（あなた）の役割だろ。"
        choices = [
            {"text": "ミスを認め、すぐ上司に報告すると断言する (大胆)", "consequence": "favor_up"},
            {"text": "黙って修正できると主張し、自分で解決を試みる", "consequence": "favor_down"},
            {"text": "氷室にだけ、どうすべきか相談してみる", "consequence": "neutral"}
        ]
    else:
        speech = f"[ターン {current_turn_count}] {player_name}、進捗状況は？君が何かを隠しているように見える。クライアントへの資料は万全ですか？"
        choices = [
            {"text": "資料をもう一度確認すると言って、その場を濁す (消極的)", "consequence": "favor_down"},
            {"text": "ミスはないと断言し、強がる", "consequence": "neutral"},
            {"text": "一歩踏み出し、具体的な解決策を提案する", "consequence": "favor_up"}
        ]

    return {
        "character_name": "氷室 涼",
        "character_speech": speech,
        "choices": choices,
        "current_status": {"confidence_level": confidence_level, "player_gender": st.session_state['player_gender']}
    }

def handle_choice(choice_consequence):
    """選択肢が選ばれた時の好感度・自信ゲージの処理と、次のターンへの遷移"""
    
    if choice_consequence == "favor_up":
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10)
        st.toast("好感度が少し上がりました！", icon='❤️')
    elif choice_consequence == "favor_down":
        st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5)
        st.toast("好感度が少し下がってしまいました...", icon='💔')
    elif choice_consequence == "confidence_up":
        st.session_state['confidence_level'] = min(3, st.session_state['confidence_level'] + 1)
        st.toast("自信が湧いてきました！", icon='✨')
        
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. Streamlit UIとアクション (メイン部分)
# ----------------------------------------------------

st.set_page_config(layout="centered", page_title=get_text("TITLE"))
st.title(get_text("TITLE"))

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    
    # --- 初期設定UI ---
    LANGUAGES = {"JA": "日本語", "EN": "English"}
    st.session_state['game_language'] = st.selectbox(
        get_text("LANG_SELECT"), 
        options=list(LANGUAGES.keys()), 
        format_func=lambda x: LANGUAGES[x]
    )
    st.markdown("---")

    st.subheader("👤 Character Setup")
    col_g, col_n = st.columns([0.4, 0.6])

    with col_g:
        st.session_state['player_gender'] = st.selectbox(
            get_text("GENDER_SELECT"), 
            options=["Female", "Male"],
            format_func=lambda x: get_text("GENDER_FEMALE") if x == "Female" else get_text("GENDER_MALE")
        )

    with col_n:
        st.session_state['player_name'] = st.text_input(
            get_text("NAME_INPUT"), 
            value=st.session_state['player_name'],
            max_chars=10
        )

    st.markdown("---")

    st.subheader(get_text("CSV_HEADER"))

    uploaded_file_csv = st.file_uploader( # 名前を uploaded_file_csv に変更
        get_text("CSV_UPLOAD"), 
        type="csv",
        help=get_text("CSV_HINT")
    )

    if uploaded_file_csv is not None and st.session_state['game_state'] == 'START':
        try:
            df = pd.read_csv(uploaded_file_csv)
            streak = calculate_streak_from_df(df)
            st.session_state['continuous_days'] = streak
            st.session_state['game_state'] = 'DIARY_LOADED'
            st.toast(get_text("DATA_SUCCESS"), icon='💾')
            st.rerun() 
            
        except Exception as e:
            st.error(get_text("DATA_ERROR") + f"\n{e}")
            st.session_state['continuous_days'] = 0
            st.session_state['game_state'] = 'START'

    if st.session_state['game_state'] == 'DIARY_LOADED':
        st.success(get_text("DATA_SUCCESS"))
        
        days = st.session_state['continuous_days']
        
        if days >= 7:
            confidence_level = 3
            confidence_text = "✨ HIGH (大胆な選択肢が出現！)" if st.session_state['game_language'] == 'JA' else "✨ HIGH (Bold choices available!)"
        elif days >= 3:
            confidence_level = 2
            confidence_text = "💪 MEDIUM (バランスの取れた選択肢)" if st.session_state['game_language'] == 'JA' else "💪 MEDIUM (Balanced choices)"
        else:
            confidence_level = 1
            confidence_text = "😥 LOW (消極的な選択肢が多い)" if st.session_state['game_language'] == 'JA' else "😥 LOW (Passive choices dominate)"
            
        st.session_state['confidence_level'] = confidence_level 
        
        st.markdown(f"**{get_text('CONTINUOUS_DAYS')}** **{days}** 日")
        st.markdown(f"**{get_text('CONFIDENCE_GAUGE')}**")
        st.progress(confidence_level / 3) 
        st.write(confidence_text)
        
        st.markdown("---")
        
        if st.button(get_text("START_GAME"), type="primary"):
            st.session_state['game_state'] = 'CONVERSATION_LOAD'
            st.rerun()


# --- 会話画面のレンダリング ---

def render_conversation_ui():
    """ゲームの会話画面をレンダリングする"""
    
    st.header("💬 Reframe Lovers")
    
    # 🚨 修正点: 画像アップローダーとセッションステートからの画像表示 🚨
    col_img_up, col_img_disp = st.columns([1, 2])
    
    with col_img_up:
        uploaded_file = st.file_uploader( 
            "背景画像 (unname(1).jpg) をアップロード", 
            type=['jpg', 'jpeg', 'png'],
            key="conversation_image_uploader" 
        )

        if uploaded_file is not None:
            # アップロードされたファイルをセッションステートに保存
            st.session_state['uploaded_image_data'] = uploaded_file.getvalue()
            # ファイルポインタをリセット
            uploaded_file.seek(0) 

    with col_img_disp:
        if st.session_state['uploaded_image_data'] is not None:
            st.image(st.session_state['uploaded_image_data'], caption="現在の状況", use_column_width="always")
        else:
            st.warning("⚠️ 会話の背景画像がアップロードされていません。")
        
    st.subheader(f"Day 1: 氷室 涼との会話")
    
    col_fav, col_conf = st.columns([0.5, 0.5])
    with col_fav:
        st.markdown(f"❤️ **好感度**: **{st.session_state['favor_ryo']}** / 100")
    with col_conf:
        st.markdown(f"✨ **自信レベル**: **{st.session_state.get('confidence_level', 1)}** / 3")
        
    st.markdown("---")
    
    # 🚨 デバッグ情報の表示 🚨
    st.info(f"🔄 **現在の会話履歴の長さ**: {len(st.session_state['conversation_history'])} | **ゲームステート**: **{st.session_state['game_state']}**")
    st.markdown("---")
    
    chat_container = st.container(height=350)

    # 履歴をすべて表示 
    with chat_container:
        for turn in st.session_state['conversation_history']:
            st.markdown(f"""
            <div style="background-color: #e6f7ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
                👤 **{turn['character_name']}**: {turn['character_speech']}
            </div>
            """, unsafe_allow_html=True)
            
    current_turn = st.session_state['conversation_history'][-1] if st.session_state['conversation_history'] else None
    
    current_turn_index = len(st.session_state['conversation_history']) 
    unique_session_id = time.time() 

    if st.session_state['game_state'] == 'CONVERSATION' and current_turn:
        
        st.markdown("---")
        st.write("➡️ あなたの選択...")
        
        cols = st.columns(len(current_turn['choices']))
        for i, choice in enumerate(current_turn['choices']):
            with cols[i]:
                st.button(
                    choice['text'], 
                    key=f"choice_{current_turn_index}_{i}_{unique_session_id}", 
                    on_click=handle_choice, 
                    args=(choice['consequence'],)
                )
                
    elif st.session_state['game_state'] == 'CONVERSATION_LOAD':
        
        st.info('⚙️ 氷室 涼が思考中... 次の会話を生成しています...')
        
        new_turn = generate_conversation_turn(st.session_state['conversation_theme']) 
        
        if new_turn:
            st.session_state['conversation_history'].append(new_turn) 
            st.session_state['game_state'] = 'CONVERSATION'
            st.rerun()
        else:
            st.error("会話の生成に失敗しました。AIの設定を確認してください。")

# --- メインロジックの末尾に会話レンダリングを追加 ---
if st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    render_conversation_ui()
