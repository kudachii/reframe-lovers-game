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
    # ... (省略) ...
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
st.session_state.setdefault(
    'conversation_theme', 
    "金曜日の終業間際、オフィスの休憩スペースにて。主人公は、自分が担当した重要資料に**致命的なデータミスを発見**し、報告するか黙って修正するか迷っている。氷室は、主人公が資料を前に押し黙っていることに気づき、声をかける。"
)

# ----------------------------------------------------
# 2. 連続記録日数を計算するコアロジック (省略)
# ----------------------------------------------------
# calculate_streak_from_df関数は省略

# ----------------------------------------------------
# 3. AI会話生成ロジック
# ----------------------------------------------------

def generate_conversation_turn(conversation_context):
    player_name = st.session_state['player_name']
    confidence_level = st.session_state['confidence_level']

    time.sleep(0.5) # スピードアップのため短縮

    # 🚨 修正点: ターン数をspeechに含め、ユニーク性を確保
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
    # ... (初期設定UIコードは省略) ...
    # ... (CSV処理コードは省略) ...
    pass # 省略した初期設定UIコードをここに含める
    
    # 連続記録日数計算関数は外部定義のため、ここでは省略

    if st.session_state['game_state'] == 'DIARY_LOADED':
        # ... (データロード後のUI表示コードは省略) ...
        pass # 省略したロード後UIコードをここに含める


# --- 会話画面のレンダリング ---

def render_conversation_ui():
    """ゲームの会話画面をレンダリングする"""
    
    st.header("💬 Reframe Lovers")
    st.subheader(f"Day 1: 氷室 涼との会話")
    
    col_fav, col_conf = st.columns([0.5, 0.5])
    with col_fav:
        st.markdown(f"❤️ **好感度**: **{st.session_state['favor_ryo']}** / 100")
    with col_conf:
        st.markdown(f"✨ **自信レベル**: **{st.session_state.get('confidence_level', 1)}** / 3")
        
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
        
        # 🚨 修正箇所
        st.info('⚙️ 氷室 涼が思考中... 次の会話を生成しています...')
        
        # generate_conversation_turn は time.sleep(0.5) を含んでいます
        new_turn = generate_conversation_turn(st.session_state['conversation_theme']) 
        
        if new_turn:
            st.session_state['conversation_history'].append(new_turn) 
            st.session_state['game_state'] = 'CONVERSATION' # 状態を CONVERSATION に確定させる
            st.rerun()
        else:
            st.error("会話の生成に失敗しました。AIの設定を確認してください。")

# --- メインロジックの末尾に会話レンダリングを追加 ---
if st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    render_conversation_ui()
