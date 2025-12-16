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
st.session_state.setdefault('conversation_history', []) # 履歴を蓄積
st.session_state.setdefault('favor_ryo', 50)
st.session_state.setdefault('uploaded_image_data', None) # 画像データ保持用
st.session_state.setdefault(
    'conversation_theme', 
    "金曜日の終業間際、オフィスの休憩スペースにて。主人公は、自分が担当した重要資料に**致命的なデータミスを発見**し、報告するか黙って修正するか迷っている。氷室は、主人公が資料を前に押し黙っていることに気づき、声をかける。"
)

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (省略)
# ----------------------------------------------------
def calculate_streak_from_df(df):
    return 0 

# ----------------------------------------------------
# 3. AI会話生成ロジック
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
    """選択肢が選ばれた時の好感度・自信ゲージの処理と、次のターンへの遷移"""
    
    if choice_consequence == "lock":
        st.warning("この選択肢は、自信レベルLv.3以上が必要です。")
        return # ロックされている選択肢は遷移しない

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
    # --- 初期設定UIは省略 ---
    pass

# --- 会話画面のレンダリング ---

def render_conversation_ui():
    """ゲームの会話画面をレンダリングする"""
    
    st.markdown("## 🏢 第1話: エースの葛藤")
    st.markdown(f"目標: まずは氷室と壁を取り払おう。現在の自信ゲージ (Confidence): Lv.{st.session_state['confidence_level']}")
    st.markdown("---")
    
    col_img, col_log = st.columns([1.5, 1])
    
    with col_img:
        st.markdown("### 氷室涼")
        
        # 🚨 修正点: アップローダーのヒントテキストを変更 🚨
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
            st.image(st.session_state['uploaded_image_data'], caption="現在の状況", use_column_width="always")
        else:
            st.warning("⚠️ 会話の背景画像がアップロードされていません。画像をアップロードしてください。")

    with col_log:
        st.markdown("### 📝 会話ログ")
        
        # 会話ログ表示エリア
        chat_container = st.container(height=250)
        with chat_container:
            for turn in st.session_state['conversation_history']:
                st.markdown(f"**{turn['character_name']}**:")
                st.markdown(f"> {turn['character_speech']}")
                st.markdown("---", divider='off')
                
        st.markdown("---")
        st.markdown("### ⭕ 選択肢 (次の行動)")
        
        current_turn = st.session_state['conversation_history'][-1] if st.session_state['conversation_history'] else None
        
        current_turn_index = len(st.session_state['conversation_history']) 
        unique_session_id = time.time() 

        if st.session_state['game_state'] == 'CONVERSATION' and current_turn:
            
            for i, choice in enumerate(current_turn['choices']):
                
                # ロックされている選択肢の判定
                is_locked = (choice['consequence'] == 'lock') or \
                            (choice['text'].startswith('(要Lv.3)') and st.session_state['confidence_level'] < 3)
                
                button_text = choice['text']
                if is_locked:
                    # ロックされている場合はボタンを無効化
                    st.button(button_text, disabled=True)
                else:
                    # ロックされていない場合はボタンを有効化し、アクションを設定
                    st.button(
                        button_text, 
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
