# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os 
import google.generativeai as genai

# --- API設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。")

def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priorities = ['models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash', 'models/gemini-pro']
        for p in priorities:
            if p in available_models: return p
        return available_models[0] if available_models else None
    except: return 'models/gemini-1.5-flash'

# --- セッション初期化 ---
if 'game_state' not in st.session_state:
    st.session_state.update({
        'game_state': 'START', 
        'player_name': 'あなた',
        'player_gender': '女性',
        'confidence_level': 0, 
        'favor_ryo': 50, 
        'turn_count': 0,
        'conversation_history': [], 
        'free_chat_history': [],
        'free_chat_count': 0,
        'is_loading': False
    })

# --- 自信Lv計算ロジック ---
def calculate_confidence(df):
    if df is None or df.empty: return 0
    count = len(df)
    if count >= 7: return 3
    if count >= 3: return 2
    if count >= 1: return 1
    return 0

# --- 私語モードの設定判定 ---
def get_free_chat_config(favor):
    if favor >= 100: return 999, "あなたの声を聞いていると、落ち着くんです……。もう少しだけ、こうしていても？"
    if favor >= 90: return 10, "……あともう少しだけなら、付き合ってもいいですよ。何か話したいことでも？"
    if favor >= 80: return 5, "……5分だけですよ。効率は落ちますが、あなたの話なら聞く価値がある。"
    if favor >= 31: return 3, "手短にお願いします。今は業務時間内ですので。"
    return 0, "私用の会話は禁止されています。仕事に戻ってください。"

# --- AI生成（私語） ---
def generate_free_chat_response(user_input):
    favor = st.session_state['favor_ryo']
    _, message = get_free_chat_config(favor)
    prompt = f"氷室涼(好感度{favor})として回答。態度:{message}。入力:{user_input}。短く返して。"
    try:
        model = genai.GenerativeModel(get_best_model())
        return model.generate_content(prompt).text
    except: return "……今は話せません。"

# --- AI生成（メイン） ---
def generate_main_scenario():
    name = st.session_state['player_name']
    gender = st.session_state['player_gender']
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    num = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    prompt = f"氷室涼として{gender}の{name}に接して。好感度{favor}。自信Lv{conf}。JSON(character_speech, choices:[{{text, score}}])で出力。選択肢は{num}個。"
    try:
        model = genai.GenerativeModel(get_best_model())
        res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(res.text)
    except: return None

# --- UI表示 ---
st.title("🏙️ Reframe Lovers")

# 1. スタート・設定画面 (修正版)
# game_stateが 'START' または 'DIARY_LOADED' の間は、設定項目を表示し続ける
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.radio("性別", ["女性", "男性", "その他"], horizontal=True)
    
    st.markdown("---")
    st.subheader("🔗 ポジティブ日記の同期")
    st.caption("CSVをアップロードすると、自信レベルが星（⭐）として反映されます。")
    
    # 常にアップローダーを表示
    uploaded_file = st.file_uploader("日記CSVをアップロード", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            # 状態を更新するが、画面は切り替えない
            st.session_state['game_state'] = 'DIARY_LOADED'
            st.success(f"同期完了！ 現在の自信Lv: {'⭐' * st.session_state['confidence_level']}")
        except Exception as e:
            st.error(f"CSVの読み取りに失敗しました: {e}")

    st.markdown("---")
    # すべての設定が終わったらこのボタンでゲーム開始
    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()
        
# 2. 会話読み込み
elif st.session_state['game_state'] == 'CONVERSATION_LOAD':
    with st.spinner("氷室が言葉を選んでいます..."):
        new_turn = generate_main_scenario()
        if new_turn:
            st.session_state['conversation_history'].append(new_turn)
            st.session_state['game_state'] = 'MAIN_PLAY'
            st.rerun()

# 3. メイン・私語プレイ画面
elif st.session_state['game_state'] in ['MAIN_PLAY', 'FREE_CHAT']:
    st.write(f"❤️ 信頼度: {st.session_state['favor_ryo']} | ✨ 自信: {'⭐' * st.session_state['confidence_level']}")
    st.progress(st.session_state['favor_ryo'] / 100.0)
    st.divider()

    col_img, col_chat = st.columns([0.4, 0.6])
    with col_img: st.info("氷室 涼") # ここに画像
    
    with col_chat:
        st.markdown("**氷室 涼**")
        if st.session_state['game_state'] == 'FREE_CHAT':
            for m in st.session_state['free_chat_history'][-4:]:
                st.write(f"**{m['role']}**: {m['content']}")
        else:
            st.info(st.session_state['conversation_history'][-1]['character_speech'])

    st.divider()
    
    # 選択肢ボタン
    if st.session_state['game_state'] == 'MAIN_PLAY':
        choices = st.session_state['conversation_history'][-1]['choices']
        for i, c in enumerate(choices):
            if st.button(c['text'], key=f"btn_{i}", use_container_width=True):
                # 好感度加算（自信Lvによる倍率反映）
                score = c['score']
                change = score if score <= 0 else int(score * {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(st.session_state['confidence_level'], 1.0))
                st.session_state['favor_ryo'] += change
                st.session_state['turn_count'] += 1
                
                # 私語モード判定
                max_c, ryo_msg = get_free_chat_config(st.session_state['favor_ryo'])
                if max_c > 0:
                    st.session_state['game_state'] = 'FREE_CHAT'
                    st.session_state['free_chat_history'] = [{"role": "氷室", "content": ryo_msg}]
                    st.session_state['free_chat_count'] = 0
                else:
                    st.toast(ryo_msg) # 拒絶メッセージ
                    st.session_state['game_state'] = 'CONVERSATION_LOAD'
                st.rerun()

    # 私語入力欄
    elif st.session_state['game_state'] == 'FREE_CHAT':
        max_c, _ = get_free_chat_config(st.session_state['favor_ryo'])
        if st.session_state['free_chat_count'] < max_c:
            chat_input = st.chat_input("話しかける...")
            if chat_input:
                st.session_state['free_chat_history'].append({"role": "あなた", "content": chat_input})
                res = generate_free_chat_response(chat_input)
                st.session_state['free_chat_history'].append({"role": "氷室", "content": res})
                st.session_state['free_chat_count'] += 1
                st.rerun()
        
        if st.button("次の展開へ進む", type="primary", use_container_width=True):
            if st.session_state['turn_count'] >= 3:
                st.session_state['game_state'] = 'RESULT'
            else:
                st.session_state['game_state'] = 'CONVERSATION_LOAD'
            st.rerun()

# 4. リザルト
elif st.session_state['game_state'] == 'RESULT':
    st.header("攻略完了")
    st.metric("氷室からの信頼度", st.session_state['favor_ryo'])
    if st.button("最初から"):
        st.session_state.clear()
        st.rerun()
