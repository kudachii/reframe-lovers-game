# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
import pytz
import json
import time 
import os 

# ----------------------------------------------------
# 1. 多言語対応とセッションステートの初期化 (変更なし)
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
# 2. 連続記録日数を計算するコアロジック (変更なし)
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
# 3. AI会話生成ロジック (変更なし)
# ----------------------------------------------------
def generate_conversation_turn(conversation_context):
    confidence_level = st.session_state['confidence_level']
    continuous_days = st.session_state['continuous_days'] 

    time.sleep(0.5) 
    current_turn_count = len(st.session_state['conversation_history']) + 1 
    
    # 選択肢の全パターン（ベース）
    base_choices = [
        {"text": "ミスはないと断言し、強がる (好感度 ±0)", "consequence": "neutral"},
        {"text": "資料をもう一度確認すると言って、その場を濁す (好感度 -5)", "consequence": "favor_down"},
        {"text": "一歩踏み出し、具体的な解決策を提案する (好感度 +10)", "consequence": "favor_up"},
        # Lv.2で追加される選択肢 (4つ目)
        {"text": "（Lv.2以上）リスクを理解した上で、この件を自分が責任を持つと宣言する (好感度 ±0, 自信 +5)", "consequence": "neutral_conf_up"},
        # Lv.3で追加される選択肢 (5つ目)
        {"text": "（Lv.3以上）ミスを認め、すぐ上司に報告すると断言する (大胆/好感度 +15)", "consequence": "favor_up_major"}
    ]
    
    # --- 選択肢の動的な絞り込みと追加 ---
    
    if continuous_days == 0:
        # 日数0日（CSVなし）: 2択
        speech = f"[ターン {current_turn_count}] (自信Lv.1 / 記録日数0日) どうしたらいい...？と動揺している。この場を離れたい気分だ...。"
        
        # 好感度DOWNと中立の2つに限定
        choices = [c for c in base_choices if c['consequence'] in ['neutral', 'favor_down']]
        
    elif confidence_level == 1:
        # 日数1〜2日: 3択
        speech = f"[ターン {current_turn_count}] (自信Lv.1 / 記録日数1日以上) 進捗状況は？何かを隠しているように見えますよ。資料に問題はないか、今一度確認を。"
        
        # 基本の3つ（neutral, favor_down, favor_up）
        choices = [c for c in base_choices if c['consequence'] in ['neutral', 'favor_down', 'favor_up']]
        
    elif confidence_level == 2:
        # 日数3〜6日: 4択 (中間レベルの恩恵)
        speech = f"[ターン {current_turn_count}] (自信Lv.2) 資料は万全ですか？君が何かを隠しているように見える。ミスを恐れず、状況を説明してください。"
        
        # 基本の3つ + 4つ目 (neutral_conf_up) を追加
        choices = [c for c in base_choices if c['consequence'] in ['neutral', 'favor_down', 'favor_up', 'neutral_conf_up']]
        
    elif confidence_level >= 3:
        # 日数7日以上: 5択 (最高レベルの恩恵)
        speech = f"[ターン {current_turn_count}] (自信Lv.3以上) 私は君の能力を信頼しています。ミスを恐れずに、解決策を見つけることが重要だ。"
        
        # 基本の3つ + 4つ目 (neutral_conf_up) + 5つ目 (favor_up_major) を追加
        choices = [c for c in base_choices if c['consequence'] in ['neutral', 'favor_down', 'favor_up', 'neutral_conf_up', 'favor_up_major']]


    # 会話ターン1の特殊処理（導入）
    if current_turn_count == 1:
        # 導入ターンは、上記ロジックで決定されたセリフと選択肢をそのまま使用
        pass 

    return {
        "character_name": "氷室 涼",
        "character_speech": speech,
        "choices": choices,
        "current_status": {"confidence_level": confidence_level, "player_gender": st.session_state['player_gender']}
    }

def handle_choice(choice_consequence):
    # 好感度UP/DOWNの度合いを定義
    if choice_consequence == "favor_up_major":
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 15)
        st.toast("好感度が大きく上がりました！", icon='💖')
    elif choice_consequence == "favor_up":
        st.session_state['favor_ryo'] = min(100, st.session_state['favor_ryo'] + 10)
        st.toast("好感度が少し上がりました！", icon='❤️')
    elif choice_consequence == "favor_down":
        st.session_state['favor_ryo'] = max(0, st.session_state['favor_ryo'] - 5)
        st.toast("好感度が少し下がってしまいました...", icon='💔')
    elif choice_consequence == "neutral_conf_up":
        # Lv.2で追加された特殊な選択肢（好感度は変わらないが、自信レベルが上がる）
        st.session_state['confidence_level'] = min(3, st.session_state['confidence_level'] + 1)
        st.toast("状況は変わりませんが、少し自信がつきました。", icon='💪')
    elif choice_consequence == "neutral":
        st.toast("状況が変わりました。", icon='✅')

    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 4. Streamlit UIとアクション (メイン部分)
# ----------------------------------------------------

st.set_page_config(layout="centered", page_title=get_text("TITLE"))
st.title(get_text("TITLE"))

# --- ゲーム開始ボタンを押した際の処理を定義 ---
def start_game_action():
    if st.session_state['game_state'] == 'START':
        st.session_state['continuous_days'] = 0 
        st.session_state['confidence_level'] = 1
        st.toast("CSVデータなしでゲームを開始します。自信レベルはLv.1、選択肢は2つからスタートです。", icon='ℹ️')
    
    st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun() 
# ------------------------------------------------

if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    # (スタート画面のロジックは変更なし)
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
            confidence_text = "✨ HIGH (選択肢は最大**5つ**に増加！)" if st.session_state['game_language'] == 'JA' else "✨ HIGH (5 choices available!)"
        elif days >= 3:
            confidence_level = 2
            confidence_text = "💪 MEDIUM (選択肢が**4つ**に増加！)" if st.session_state['game_language'] == 'JA' else "💪 MEDIUM (4 choices available!)"
        else:
            confidence_level = 1
            confidence_text = "😥 LOW (選択肢は**3つ**。基礎的な選択肢)" if st.session_state['game_language'] == 'JA' else "😥 LOW (3 choices available)"
            
        st.session_state['confidence_level'] = confidence_level 
        
        st.markdown(f"**{get_text('CONTINUOUS_DAYS')}** **{days}** 日")
        st.markdown(f"**{get_text('CONFIDENCE_GAUGE')}**")
        st.progress(confidence_level / 3) 
        st.write(confidence_text)
        
        st.markdown("---")
        
    else:
        st.info("💡 ポジティブ日記のCSVをアップロードすると、自信レベルが上がり、選択肢が最大5つに増加します。アップロードなしで開始する場合、**自信レベルLv.1 (日数0日)**となり、**選択肢は2つ**に限定されます。")
        st.markdown("---")


    st.button(
        get_text("START_GAME"), 
        type="primary", 
        on_click=start_game_action 
    )


# --- 会話画面のレンダリング (大幅修正) ---

def render_conversation_ui():
    """ゲームの会話画面をレンダリングする (コンパクトな新しいレイアウト)"""
    
    st.markdown("## 🏢 第1話: エースの葛藤")
    st.markdown("---")
    
    col_img, col_dialogue = st.columns([1, 1.2]) # 画像エリアを少し狭く、会話エリアを広く

    # --- 1. 画像とステータス表示エリア ---
    with col_img:
        
        # 氷室涼の画像
        IMAGE_PATH = "bg_image.jpg" 
        
        if os.path.exists(IMAGE_PATH):
            try:
                st.image(IMAGE_PATH, caption="", use_column_width="always")
            except:
                # 画像の代わりにプレースホルダー
                st.warning(f"⚠️ ファイルが見つかりません: '{IMAGE_PATH}' をGitHubに配置してください。")
        else:
            # プレースホルダーのHTML/Markdown
            st.markdown(
                """
                <div style="height: 300px; background-color: #333333; 
                border: 1px solid #cccccc; border-radius: 5px; 
                display: flex; justify-content: center; align-items: center; 
                color: #ffffff; font-weight: bold;">
                    [氷室 涼 画像エリア]
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # 好感度と自信レベルの表示
        st.markdown("---")
        col_favor, col_conf = st.columns(2)
        
        with col_favor:
            st.markdown(f"❤️ **好感度**: **{st.session_state['favor_ryo']}**")
        
        with col_conf:
            st.markdown(f"⭐ **自信レベル**: **{st.session_state.get('confidence_level', 1)}** / 3")
        
        st.markdown("---")

    # --- 2. 会話ログと選択肢エリア ---
    with col_dialogue:
        
        st.markdown("### 💬 氷室の会話ログ")
        
        # 会話ログボックスのスタイル
        st.markdown(
            """
            <style>
                .dialog-box-right {
                    height: 150px; 
                    overflow-y: auto; 
                    border: 1px solid #cccccc; 
                    background-color: #ffffff; 
                    padding: 10px; 
                    border-radius: 5px;
                    font-size: 15px;
                    margin-bottom: 20px;
                }
            </style>
            """, 
            unsafe_allow_html=True
        )
        
        log_content = "<div class='dialog-box-right'>"
        
        # 最新の会話のみを表示（画像のデザインに合わせてシンプルに）
        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            log_content += f"**{last_turn['character_name']}**: {last_turn['character_speech']}"
            
        log_content += "</div>"
        
        st.markdown(log_content, unsafe_allow_html=True)
        
        
        st.markdown("### ⭕ あなたの選択 (次の行動)")
        
        current_turn = st.session_state['conversation_history'][-1] if st.session_state['conversation_history'] else None
        
        current_turn_index = len(st.session_state['conversation_history']) 
        unique_session_id = time.time() 

        if st.session_state['game_state'] == 'CONVERSATION' and current_turn:
            
            # 画像のレイアウトに合わせて選択肢を縦に配置
            for i, choice in enumerate(current_turn['choices']):
                button_text = choice['text']
                
                # 選択肢ボタンの表示
                st.button(
                    button_text, 
                    key=f"choice_{current_turn_index}_{i}_{unique_session_id}", 
                    on_click=handle_choice, 
                    args=(choice['consequence'],),
                    use_container_width=True # 幅いっぱいにする
                )
        
    # 会話ロード中のインジケーター (全体カラムの下に表示)
    if st.session_state['game_state'] == 'CONVERSATION_LOAD':
        st.markdown("---")
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
