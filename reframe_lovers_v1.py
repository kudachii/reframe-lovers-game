# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
from io import StringIO
import base64 # 画像のBase64エンコード用

# ----------------------------------------------------
# 0. 画像データの準備 (氷室 涼の画像と背景画像)
# ----------------------------------------------------

# (ユーザー様が以前アップロードされた氷室涼の画像)
# この画像をBase64でエンコードし、コードに埋め込むことで、Streamlit Cloud上で画像を直接表示できます。

# ユーザーがアップロードした氷室涼の画像のBase64エンコード (例としてダミーを記述。実際はユーザー様の画像をエンコードします)
# 通常、Streamlit CloudでGitHubリポジトリに画像を保存し、st.image()で読み込むのが最も簡単です。
# 今回はプロトタイプとして、Streamlitのst.image()機能を使います。
CHARACTER_IMAGE_PATH = "unnamed (1).jpg"  # ユーザー様のアップロード画像ファイル名に置き換えてください
BACKGROUND_IMAGE_PATH = "office_background.jpg" # 背景画像（適当なオフィス画像）をGitHubにアップロードしてください

# ----------------------------------------------------
# 1. 多言語対応とセッションステートの初期化
# ----------------------------------------------------

# (Step 1-1 で定義した GAME_TRANSLATIONS は省略します)
# (簡略化のため、このセクションのコードは Step 1-1 のものを使用してください)

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
        "DATA_SUCCESS": "✅ データロード成功！",
        "CONTINUOUS_DAYS": "連続記録日数:",
        "CONFIDENCE_GAUGE": "現在の自信ゲージ (Confidence):",
        "START_GAME": "ゲームを開始する ➡️",
        "GAME_SCENE_TITLE": "🏢 第1話: エースの視線",
        "CHARACTER_NAME_RYO": "氷室 涼",
        "PLAYER_TURN": "（あなたのターン）",
        "GOAL_PROMPT": "目標: まずは氷室との壁を取り払おう。"
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
        "DATA_SUCCESS": "✅ Data Load Successful!",
        "CONTINUOUS_DAYS": "Continuous Recording Days:",
        "CONFIDENCE_GAUGE": "Current Confidence Gauge:",
        "START_GAME": "Start Game ➡️",
        "GAME_SCENE_TITLE": "🏢 Episode 1: The Ace's Gaze",
        "CHARACTER_NAME_RYO": "Ryo Himuro",
        "PLAYER_TURN": "(Your Turn)",
        "GOAL_PROMPT": "Goal: Break down the wall between you and Himuro."
    }
}

def get_text(key):
    lang = st.session_state.get('game_language', 'JA')
    return GAME_TRANSLATIONS.get(lang, GAME_TRANSLATIONS['JA']).get(key, f"MISSING TEXT: {key}")

if 'game_language' not in st.session_state:
    st.session_state['game_language'] = 'JA'
if 'continuous_days' not in st.session_state:
    st.session_state['continuous_days'] = 0
if 'confidence_level' not in st.session_state:
    st.session_state['confidence_level'] = 1
if 'game_state' not in st.session_state:
    st.session_state['game_state'] = 'START' # START / DIARY_LOADED / CONVERSATION
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = []

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (Step 1-1から変更なし)
# ----------------------------------------------------

def calculate_streak_from_df(df):
    """データフレームから連続記録日数を計算する"""
    # (Step 1-1 の calculate_streak_from_df 関数と同じ内容を貼り付けてください)
    # ... 省略 ...
    # ----------------------------------------------------
    if '日付' not in df.columns and 'Date' not in df.columns:
        #st.error(f"CSVファイルに '日付' または 'Date' カラムが見つかりません。")
        return 0
        
    date_column = '日付' if '日付' in df.columns else 'Date'
    
    df = df.dropna(subset=[date_column])
    
    try:
        # CSVから読み込んだ日付カラムをpd.to_datetimeで日付オブジェクトに変換
        # errors='coerce'で不正な値をNaTに変換し、dropnaで削除
        df['date_only'] = pd.to_datetime(df[date_column], errors='coerce').dt.date
    except Exception as e:
        #st.error(f"日付形式の解析エラーが発生しました。: {e}")
        return 0

    df = df.dropna(subset=['date_only']) # 不正な日付を削除
    
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
    

# ----------------------------------------------------
# 3. Streamlit UI (スタート画面)
# ----------------------------------------------------

def display_start_screen():
    """ゲーム開始前の設定画面を表示する"""
    st.set_page_config(layout="centered", page_title=get_text("TITLE"))
    st.title(get_text("TITLE"))

    # --- 言語選択 ---
    LANGUAGES = {"JA": "日本語", "EN": "English"}
    st.session_state['game_language'] = st.selectbox(
        get_text("LANG_SELECT"), 
        options=list(LANGUAGES.keys()), 
        format_func=lambda x: LANGUAGES[x],
        key="lang_select"
    )
    st.markdown("---")

    # --- 主人公情報入力 ---
    st.subheader("👤 Character Setup")
    col_g, col_n = st.columns([0.4, 0.6])

    with col_g:
        st.session_state['player_gender'] = st.selectbox(
            get_text("GENDER_SELECT"), 
            options=["Female", "Male"],
            format_func=lambda x: get_text("GENDER_FEMALE") if x == "Female" else get_text("GENDER_MALE"),
            key="gender_select"
        )

    with col_n:
        st.session_state['player_name'] = st.text_input(
            get_text("NAME_INPUT"), 
            value="あなた",
            max_chars=10,
            key="name_input"
        )

    st.markdown("---")

    # --- CSVアップロードとデータロード ---
    st.subheader(get_text("CSV_HEADER"))
    uploaded_file = st.file_uploader(
        get_text("CSV_UPLOAD"), 
        type="csv",
        help=get_text("CSV_HINT"),
        key="csv_uploader"
    )

    if uploaded_file is not None and st.session_state['game_state'] == 'START':
        # CSVを読み込み、連続日数を計算し、セッションに保存
        try:
            # StringIOでファイルの内容をメモリに読み込む (Streamlit Cloud対策)
            string_data = StringIO(uploaded_file.getvalue().decode("utf-8"))
            df = pd.read_csv(string_data)
            
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
        st.markdown(f"**{get_text('CONTINUOUS_DAYS')}** **{days}** 日")
        
        # 自信ゲージの計算と表示
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
        st.progress(confidence_level / 3)
        st.write(confidence_text)
        
        st.markdown("---")
        
        # ゲーム開始ボタン
        if st.button(get_text("START_GAME"), type="primary"):
            st.session_state['game_state'] = 'CONVERSATION'
            st.rerun()
            
    st.caption(get_text('START_GAME_HINT') if st.session_state.get('game_state') == 'START' else "")


# ----------------------------------------------------
# 4. Streamlit UI (ゲーム画面)
# ----------------------------------------------------

def display_game_screen():
    """メインのゲーム画面（会話シーン）を表示する"""
    st.set_page_config(layout="wide", page_title=get_text("TITLE"))
    
    st.title(get_text("GAME_SCENE_TITLE"))
    st.caption(f"**{get_text('GOAL_PROMPT')}** | {get_text('CONFIDENCE_GAUGE')} **Lv.{st.session_state['confidence_level']}**")
    
    # 画面を分割 (キャラクターエリア、会話履歴、選択肢エリア)
    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        # キャラクター画像表示エリア (氷室 涼)
        st.subheader(get_text('CHARACTER_NAME_RYO'))
        
        # GitHubにアップロードした画像ファイル名に置き換えてください
        try:
            st.image("unnamed (1).jpg", caption="氷室 涼", use_column_width=True)
        except:
            st.warning("⚠️ 画像ファイル 'unnamed (1).jpg' が見つかりません。GitHubにアップロードされているか確認してください。")

    with col2:
        # ゲーム情報と会話履歴
        st.subheader("📚 Conversation Log")
        
        # ダミーの会話履歴
        if not st.session_state['conversation_history']:
            st.session_state['conversation_history'].append({
                "speaker": get_text('CHARACTER_NAME_RYO'),
                "text": "おはよう、[PLAYER_NAME]さん。今日のプロジェクトMTG、資料の準備は万全ですか？"
            })
        
        # 会話履歴の表示
        chat_placeholder = st.empty()
        
        full_log = ""
        for entry in st.session_state['conversation_history']:
            # プレイヤー名に置き換え
            text = entry['text'].replace("[PLAYER_NAME]", st.session_state['player_name'])
            
            if entry['speaker'] == get_text('CHARACTER_NAME_RYO'):
                full_log += f"**{entry['speaker']}**:\n> *{text}*\n\n"
            else:
                full_log += f"**{get_text('PLAYER_TURN')}**:\n>{text}\n\n"
        
        chat_placeholder.markdown(full_log)
        
        # 選択肢エリア (Step 2でAIが生成した選択肢をここに配置する)
        st.markdown("---")
        st.subheader("💭 選択肢 (Next Action)")
        
        # ダミーの選択肢ボタン (次のステップでAI生成に置き換え)
        st.button("1. 資料チェックは完璧です！ (自信Lvに関係なく選べる)", key="choice_1")
        
        # 自信Lvが高い場合のみ表示されるダミーの選択肢
        if st.session_state['confidence_level'] >= 3:
             st.button("2. （高Lv専用）資料チェックより、氷室さんの懸念点を先に聞かせてください！ (大胆)", key="choice_2")
        else:
             st.button("2. （要Lv.3）この選択肢はロックされています...", disabled=True)
             
        st.button("3. 特にありません...", key="choice_3")


# ----------------------------------------------------
# 5. メイン実行ロジック
# ----------------------------------------------------

# ゲーム状態に応じて表示画面を切り替える
if st.session_state['game_state'] == 'CONVERSATION':
    display_game_screen()
else:
    display_start_screen()
