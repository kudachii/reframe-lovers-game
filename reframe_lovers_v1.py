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

# --- 私語モードも「氷室らしさ」を徹底 ---
def generate_free_chat_response(user_input):
    favor = st.session_state['favor_ryo']
    prompt = f"""あなたは氷室涼です。現在{st.session_state['player_name']}と私事の話をしています。
    好感度{favor}に基づいた態度をとってください。
    - 80未満: 「時間の無駄です」「本件に関係ありますか？」と冷たく。
    - 90以上: 「……あなたの話は、なぜか耳に残る。不思議だ」と少しだけ心を開く。
    絶対に弱気な発言や、媚びるような態度は見せないでください。
    入力: {user_input}"""
    try:
        model = genai.GenerativeModel(get_best_model())
        return model.generate_content(prompt).text
    except: return "……今は話す必要を感じません。"

# --- AI生成（メイン）のプロンプトを硬派に修正 ---
def generate_main_scenario():
    name = st.session_state['player_name']
    gender = st.session_state['player_gender']
    conf = st.session_state['confidence_level']
    favor = st.session_state['favor_ryo']
    num = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)
    
    # 性格設定をより具体的に
    prompt = f"""あなたは氷室涼（ひむろ りょう）です。
    【性格】32歳、戦略コンサルタント。極めて合理的で冷徹。仕事に厳しく、無駄を嫌う。
    【状況】部下（または同僚）の{name}({gender})と会話中。好感度{favor}/100。
    【口調】基本は「……」「ふむ。それで？」といった無愛想な敬語。
    【自信Lvによる変化】
    - 自信Lv.{conf}が低いと、あなたは相手を「無能」と見なし、より厳しく接します。
    - 自信Lvが高いと、わずかに相手の能力を認め、対等に話そうとします。
    
    JSON(character_speech, choices:[{{text, score}}])で出力。選択肢は{num}個。
    ※弱気な態度は一切禁止です。常に優位に立ってください。"""
    
    try:
        model = genai.GenerativeModel(get_best_model())
        res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(res.text)
    except: return None

# --- UI表示 ---
st.title("🏙️ Reframe Lovers")

# 【修正①】設定・CSV画面の表示ロジックを安定化
# CONVERSATION_LOAD以降になるまで、この画面を維持します
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("プレイヤー名", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.radio("性別", ["女性", "男性", "その他"], horizontal=True)
    
    st.markdown("---")
    st.subheader("🔗 ポジティブ日記の同期")
    uploaded_file = st.file_uploader("日記CSVをアップロード", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            # 状態を更新しても画面は維持
            st.session_state['game_state'] = 'DIARY_LOADED'
            st.success(f"同期完了！ 自信Lv.{st.session_state['confidence_level']}")
        except:
            st.error("CSV読み込みエラー")

# --- 1. 設定画面（ここが前のifブロック） ---
    if st.button("氷室に会いに行く", use_container_width=True, type="primary"):
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# --- 2. 会話読み込み画面 ---
elif st.session_state['game_state'] == 'CONVERSATION_LOAD':
    with st.spinner("氷室が言葉を選んでいます..."):
        new_turn = generate_main_scenario()
        if new_turn:
            st.session_state['conversation_history'].append(new_turn)
            st.session_state['game_state'] = 'MAIN_PLAY'
            st.rerun()

elif st.session_state['game_state'] in ['MAIN_PLAY', 'FREE_CHAT']:
    # --- 1. サイドバー（設定・ステータス） ---
    with st.sidebar:
        st.title("🏙️ Reframe Lovers")
        st.divider()
        st.subheader("📊 Status")
        favor_val = st.session_state['favor_ryo']
        st.metric("❤️ 信頼度", f"{favor_val}%")
        st.progress(min(max(favor_val / 100.0, 0.0), 1.0))
        st.write(f"✨ 自信: {'⭐' * st.session_state['confidence_level']}")
        st.divider()
        # ギャル先生メッセージ
        if st.session_state['confidence_level'] <= 1:
            st.info("🌺 ギャル先生:「日記で自分をアゲてこ！✨」")
        else:
            st.success("🌺 ギャル先生:「マジいい感じ！🔥」")
        if st.button("タイトルに戻る"):
            st.session_state.clear()
            st.rerun()

    # --- 2. メイン画面（垂直コンパクトレイアウト） ---
    
    # ① 画像：高さを抑えて全体が見えるようにする
    image_path = "bg_image.jpg"
    # widthを調整（例：300px）することで、縦長になりすぎるのを防ぎます
    col_left, col_mid, col_right = st.columns([1, 2, 1]) # 中央に寄せる
    with col_mid:
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.image("https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&q=80&w=400", 
                     caption="氷室 涼", use_container_width=True)

    # ② チャット欄：高さを250pxに抑える（スクロール可能）
    st.markdown(f"##### 氷室 涼") # 少し文字を小さく
    chat_container = st.container(height=250) 
    
    with chat_container:
        if st.session_state['game_state'] == 'FREE_CHAT':
            for m in st.session_state['free_chat_history']:
                label = "氷室" if m['role'] in ['氷室', 'assistant'] else "あなた"
                st.chat_message("assistant" if label == "氷室" else "user").write(m['content'])
        else:
            if st.session_state.get('conversation_history'):
                latest = st.session_state['conversation_history'][-1]
                speech = latest.get('character_speech') or latest.get('speech') or "……。"
                st.chat_message("assistant").write(speech)
            else:
                st.chat_message("assistant").write("「……お疲れ様です。まだ残っていたんですか」")

    # ③ 操作エリア（ボタンを横に並べて高さを節約）
    if st.session_state['game_state'] == 'MAIN_PLAY':
        if st.session_state['conversation_history']:
            choices = st.session_state['conversation_history'][-1].get('choices', [])
            # 選択肢が多い場合は2列にするなどして高さを抑える
            cols = st.columns(len(choices))
            for i, c in enumerate(choices):
                with cols[i]:
                    if st.button(c['text'], key=f"btn_{st.session_state['turn_count']}_{i}", use_container_width=True):
                        score = c.get('score', 0)
                        mult = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(st.session_state['confidence_level'], 1.0)
                        st.session_state['favor_ryo'] += int(score * mult) if score > 0 else score
                        st.session_state['turn_count'] += 1
                        
                        max_c, ryo_msg = get_free_chat_config(st.session_state['favor_ryo'])
                        if max_c > 0:
                            st.session_state['game_state'] = 'FREE_CHAT'
                            st.session_state['free_chat_history'] = [{"role": "氷室", "content": ryo_msg}]
                            st.session_state['free_chat_count'] = 0
                        else:
                            st.toast(ryo_msg)
                            st.session_state['game_state'] = 'CONVERSATION_LOAD'
                        st.rerun()

    elif st.session_state['game_state'] == 'FREE_CHAT':
        # 入力欄とボタン
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

    elif st.session_state['game_state'] == 'FREE_CHAT':
        max_c, _ = get_free_chat_config(st.session_state['favor_ryo'])
        if st.session_state['free_chat_count'] < max_c:
            chat_input = st.chat_input("氷室に話しかける...")
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

# --- 4. 結果画面 ---
elif st.session_state['game_state'] == 'RESULT':
    st.header("攻略完了")
    st.metric("信頼度", st.session_state['favor_ryo'])
    if st.button("最初から"):
        st.session_state.clear()
        st.rerun()



   
