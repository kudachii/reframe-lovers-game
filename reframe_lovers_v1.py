# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz

# ----------------------------------------------------
# 1. 多言語対応とセッションステートの初期化
# ----------------------------------------------------

# 多言語対応用の静的テキスト定義 (ゲームUI用)
GAME_TRANSLATIONS = {
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

if 'game_language' not in st.session_state:
    st.session_state['game_language'] = 'JA'
if 'continuous_days' not in st.session_state:
    st.session_state['continuous_days'] = 0
if 'game_state' not in st.session_state:
    st.session_state['game_state'] = 'START' # START / DIARY_LOADED / CONVERSATION

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (日記アプリと同じ)
# ----------------------------------------------------

def calculate_streak_from_df(df):
    """データフレームから連続記録日数を計算する"""
    
    # '日付'カラムが存在しない場合はエラーを返す
    if '日付' not in df.columns and 'Date' not in df.columns:
        st.error(f"CSVファイルに '日付' または 'Date' カラムが見つかりません。")
        return 0
        
    # 日本語か英語かによってカラム名を決定
    date_column = '日付' if '日付' in df.columns else 'Date'
    
    # NaNや不正な日付を削除し、一意な日付リストを作成
    df = df.dropna(subset=[date_column])
    
    # 日付形式を '%Y/%m/%d' と仮定してパースし、日付オブジェクトに変換
    try:
        df['date_only'] = pd.to_datetime(df[date_column], format='%Y/%m/%d').dt.date
    except Exception as e:
        st.error(f"日付形式の解析エラーが発生しました。CSVの日付形式が '%Y/%m/%d' であることを確認してください。: {e}")
        return 0

    unique_dates = sorted(list(set(df['date_only'])), reverse=True)
    
    if not unique_dates:
        return 0

    streak = 0
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.datetime.now(jst).date()
    current_date_to_check = today
    
    for entry_date in unique_dates:
        if entry_date == current_date_to_check:
            streak += 1
            current_date_to_check -= datetime.timedelta(days=1)
        elif entry_date < current_date_to_check:
            break
            
    return streak

# ----------------------------------------------------
# 3. Streamlit UIとアクション
# ----------------------------------------------------

st.set_page_config(layout="centered", page_title=get_text("TITLE"))
st.title(get_text("TITLE"))

# --- 言語選択 ---
LANGUAGES = {"JA": "日本語", "EN": "English"}
st.session_state['game_language'] = st.selectbox(
    get_text("LANG_SELECT"), 
    options=list(LANGUAGES.keys()), 
    format_func=lambda x: LANGUAGES[x]
)
st.markdown("---")

# --- 主人公情報入力 ---
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
        value="あなた",
        max_chars=10
    )

st.markdown("---")

# --- CSVアップロードとデータロード ---
st.subheader(get_text("CSV_HEADER"))

uploaded_file = st.file_uploader(
    get_text("CSV_UPLOAD"), 
    type="csv",
    help=get_text("CSV_HINT")
)

if uploaded_file is not None and st.session_state['game_state'] == 'START':
    try:
        # ファイル読み込み
        df = pd.read_csv(uploaded_file)
        
        # 連続記録日数の計算
        streak = calculate_streak_from_df(df)
        st.session_state['continuous_days'] = streak
        st.session_state['game_state'] = 'DIARY_LOADED'
        st.toast(get_text("DATA_SUCCESS"), icon='💾')
        st.rerun() 
        
    except Exception as e:
        st.error(get_text("DATA_ERROR") + f"\n{e}")
        st.session_state['continuous_days'] = 0
        st.session_state['game_state'] = 'START'

# --- 読み込み結果の表示とゲーム開始ボタン ---
if st.session_state['game_state'] == 'DIARY_LOADED' or st.session_state['continuous_days'] > 0:
    st.success(get_text("DATA_SUCCESS"))
    
    days = st.session_state['continuous_days']
    
    # 連続記録日数の表示
    st.markdown(f"**{get_text('CONTINUOUS_DAYS')}** **{days}** 日")
    
    # 自信ゲージの計算と表示 (連続日数に基づいて)
    # 例：0-2日=低, 3-6日=中, 7日以上=高
    if days >= 7:
        confidence_level = 3
        confidence_text = "✨ HIGH (大胆な選択肢が出現！)" if st.session_state['game_language'] == 'JA' else "✨ HIGH (Bold choices available!)"
    elif days >= 3:
        confidence_level = 2
        confidence_text = "💪 MEDIUM (バランスの取れた選択肢)" if st.session_state['game_language'] == 'JA' else "💪 MEDIUM (Balanced choices)"
    else:
        confidence_level = 1
        confidence_text = "😥 LOW (消極的な選択肢が多い)" if st.session_state['game_language'] == 'JA' else "😥 LOW (Passive choices dominate)"
        
    st.session_state['confidence_level'] = confidence_level # ゲームで使用するレベルを保存
    
    st.markdown(f"**{get_text('CONFIDENCE_GAUGE')}**")
    st.progress(confidence_level / 3) # プログレスバーで視覚化
    st.write(confidence_text)
    
    st.markdown("---")
    
    # ゲーム開始ボタン
    if st.button(get_text("START_GAME"), type="primary"):
        st.session_state['game_state'] = 'CONVERSATION'
        st.rerun()


# --- デバッグ情報 (ゲーム開始状態の場合は表示しない) ---
if st.session_state['game_state'] == 'START':
    st.caption("※ 上記は初期画面です。データをロードするとゲーム画面に進みます。")
