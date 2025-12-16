# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 

# ----------------------------------------------------
# 1. 多言語対応とセッションステートの初期化 (省略)
# ----------------------------------------------------
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

# セッションステートの初期化
st.session_state.setdefault('game_language', 'JA')
st.session_state.setdefault('continuous_days', 0)
st.session_state.setdefault('game_state', 'START') 
st.session_state.setdefault('player_gender', 'Female') 
st.session_state.setdefault('player_name', 'あなた')
st.session_state.setdefault('confidence_level', 1)
st.session_state.setdefault('conversation_history', []) 
st.session_state.setdefault('favor_ryo', 50)
st.session_state.setdefault('uploaded_image_data', None) 
st.session_state.setdefault(
    'conversation_theme', 
    "金曜日の終業間際、オフィスの休憩スペースにて。主人公は、自分が担当した重要資料に**致命的なデータミスを発見**し、報告するか黙って修正するか迷っている。氷室は、主人公が資料を前に押し黙っていることに気づき、声をかける。"
)

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (省略)
# ----------------------------------------------------
def calculate_streak_from_df(df):
    date_column = None
    if '日付' in df.columns:
        date_column = '日付'
    elif 'Date' in df.columns:
        date_column = 'Date'
    else:
        return 0
        
    df = df.dropna(subset=[date_column])
    
    try:
        df['date_only'] = pd.to_datetime(
            df[date_column], 
            errors='coerce', 
            infer_datetime_format=True
        ).dt.date
    except Exception as e:
        return 0

    df = df.dropna(subset=['date_only'])
    unique_dates = sorted(list(df['date_only'].unique()), reverse=True)
    
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
# 3. AI会話生成ロジック (省略)
# ----------------------------------------------------
def generate_conversation_turn(conversation_context):
    player_name = st.session_state['player_name']
    confidence_level = st.session_state['confidence_level']

    time.sleep(0.5) 
    current_turn_count = len(st.session_state['conversation_history']) + 1 
    
    if current_turn_count == 1:
        speech = "おはよう、あなたさん。今日のプロジェクトMTG、資料の準備は大丈夫ですか？"
        choices = [
            {"text": "資料チェックは完璧です！ (自信Lv.に関係なく選択)", "consequence": "neutral"},
            {"text": "(要Lv.3) この選択肢はロックされています...", "consequence": "lock"},
            {"text": "特にありません....", "consequence": "favor_down"}
        ]
    elif confidence_level >= 3:
        speech = f"[ターン {current_turn_count}] (自信Lv.3以上) 私は君が優秀なのは知っているが、その顔はどうした？ミスを恐れるな。正直に報告し、解決策を見つけろ。"
        choices = [
            {"text": "ミスを認め、すぐ上司に報告すると断言する (大胆)", "consequence": "favor_up"},
            {"text": "黙って修正できると主張し、自分で解決を試みる", "consequence": "favor_down"},
            {"text": "氷室にだけ、どうすべきか相談してみる", "consequence": "neutral"}
        ]
    else:
        speech = f"[ターン {current_turn_count}] (自信Lv.1) 進捗状況は？君が何かを隠しているように見える。クライアントへの資料は万全ですか？"
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
    if choice_consequence == "lock":
        st.warning("この選択肢は、自信レベルLv.3以上が必要です。")
        return 

    if choice_consequence == "favor_up":
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10)
        st.toast("好感度が少し上がりました！", icon='❤️')
    elif choice_consequence == "favor_down":
        st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5)
        st.toast("好感度が少し下がってしまいました...", icon='💔')
    elif choice_consequence == "neutral":
        st.toast("状況が変わりました。", icon='✅')

    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. Streamlit UIとアクション (メイン部分)
# ----------------------------------------------------

st.set_page_config(layout="centered", page_title=get_text("TITLE"))
st.title(get_text("TITLE"))

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    
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

    uploaded_file_csv = st.file_uploader( 
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
    """ゲームの会話画面をレンダリングする (ステータス表示移動版)"""
    
    st.markdown("## 🏢 第1話: エースの葛藤")
    st.markdown(f"目標: まずは氷室と壁を取り払おう。現在の自信ゲージ (Confidence): Lv.{st.session_state['confidence_level']}")
    st.markdown("---")
    
    col_img, col_choices = st.columns([1.5, 1])
    
    with col_img:
        st.markdown("### 氷室涼 (背景)")
        
        # 画像アップローダー
        uploaded_file = st.file_uploader( 
            "会話の背景画像ファイル (bg_image.jpg など) をアップロード", 
            type=['jpg', 'jpeg', 'png'],
            key="conversation_image_uploader" 
        )

        if uploaded_file is not None:
            st.session_state['uploaded_image_data'] = uploaded_file.getvalue()
            uploaded_file.seek(0) 

        # セッションステートから画像を表示
        if st.session_state['uploaded_image_data'] is not None:
            st.image(st.session_state['uploaded_image_data'], caption="", use_column_width="always")
        else:
            st.warning("⚠️ 会話の背景画像がアップロードされていません。画像をアップロードしてください。")

        # 🚨 修正点: 好感度と自信レベルを画像の下に配置 🚨
        st.markdown("---")
        st.markdown("### 📈 現在のステータス")
        st.markdown(f"❤️ **好感度**: **{st.session_state['favor_ryo']}** / 100")
        st.markdown(f"✨ **自信レベル**: **{st.session_state.get('confidence_level', 1)}** / 3")
        st.markdown("---") # ログとの区切りのため

    with col_choices:
        st.markdown("### ⭕ あなたの選択")
        
        current_turn = st.session_state['conversation_history'][-1] if st.session_state['conversation_history'] else None
        
        current_turn_index = len(st.session_state['conversation_history']) 
        unique_session_id = time.time() 

        if st.session_state['game_state'] == 'CONVERSATION' and current_turn:
            
            for i, choice in enumerate(current_turn['choices']):
                
                is_locked = (choice['consequence'] == 'lock') or \
                            (choice['text'].startswith('(要Lv.3)') and st.session_state['confidence_level'] < 3)
                
                button_text = choice['text']
                if is_locked:
                    st.button(button_text, disabled=True, key=f"choice_{current_turn_index}_{i}_{unique_session_id}")
                else:
                    st.button(
                        button_text, 
                        key=f"choice_{current_turn_index}_{i}_{unique_session_id}", 
                        on_click=handle_choice, 
                        args=(choice['consequence'],)
                    )
        
        # 好感度と自信レベルの表示をこちらからは削除

    # 🚨 会話ログは画面下部の独立した枠に配置 (前回の修正を維持) 🚨
    
    st.markdown("---")
    st.markdown("### 💬 氷室の会話ログ")
    
    st.markdown(
        """
        <style>
            .dialog-box {
                height: 180px; 
                overflow-y: auto; 
                border: 2px solid #333333; 
                background-color: #f0f0f0; 
                padding: 10px; 
                border-radius: 8px;
                font-size: 14px;
            }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    log_content = "<div class='dialog-box'>"
    
    for turn in st.session_state['conversation_history']:
        # HTMLでセリフを構築。改行<br>、太字<b>を使用
        log_content += f"<b>{turn['character_name']}</b>:<br>"
        log_content += f"{turn['character_speech']}<br>"
        log_content += "<hr style='margin: 5px 0; border-color: #aaaaaa;'>"

    log_content += "</div>"
    
    st.markdown(log_content, unsafe_allow_html=True)


    # 会話ロード中のインジケーター
    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
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
