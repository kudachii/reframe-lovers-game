# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os 
import google.generativeai as genai

# ----------------------------------------------------
# 0. Gemini APIの設定
# ----------------------------------------------------
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのSecretsに 'GEMINI_API_KEY' を登録してください。")

# ----------------------------------------------------
# 1. セッション管理（すべての変数を初期化）
# ----------------------------------------------------
def init_session():
    defaults = {
        'game_state': 'START', 
        'player_gender': 'Female', 
        'player_name': 'あなた',
        'continuous_days': 0,
        'confidence_level': 0, 
        'conversation_history': [], 
        'favor_ryo': 50, # 初期値は中立の50
        'turn_count': 0, 
        'selected_model': None,
        'last_feedback': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ----------------------------------------------------
# 2. ロジック関数
# ----------------------------------------------------

def calculate_confidence(df):
    """CSVの日記数に基づいて自信Lv(0-3)を判定"""
    if df is None or df.empty: return 0
    count = len(df)
    if count >= 7: return 3
    if count >= 3: return 2
    if count >= 1: return 1
    return 0

def get_available_model():
    """利用可能なGeminiモデルを自動選択"""
    current_model = st.session_state.get('selected_model')
    if current_model: return current_model
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_models = ['models/gemini-1.5-flash', 'gemini-1.5-flash']
        for pm in priority_models:
            if pm in available_models:
                st.session_state['selected_model'] = pm
                return pm
        return available_models[0] if available_models else None
    except:
        return None

def generate_conversation_turn_with_ai():
    """好感度・自信Lv・性別を考慮してAIがセリフと選択肢を生成"""
    name = st.session_state.get('player_name', 'あなた')
    gender = st.session_state.get('player_gender', 'Female')
    gender_label = "女性" if gender == "Female" else "男性"
    conf = st.session_state.get('confidence_level', 0)
    favor = st.session_state.get('favor_ryo', 50)
    turn = st.session_state.get('turn_count', 0)
    
    # 自信Lvに応じた選択肢数 (2, 3, 4, 5個)
    num_choices = {0: 2, 1: 3, 2: 4, 3: 5}.get(conf, 2)

    # 好感度に応じた口調変化の指示
    if favor >= 80:
        tone_instruction = "非常に親密。完璧な敬語が少し崩れ、本音が漏れる。独占欲や信頼感が言葉に滲む。"
    elif favor >= 50:
        tone_instruction = "丁寧な敬語。仕事のパートナーとして信頼しており、温かみや気遣いがある。"
    else:
        tone_instruction = "事務的で冷徹な敬語。感情を排し、壁を感じさせる冷たい態度。"

    # 性別によるベースの態度
    if gender == "Female":
        personality = f"氷室は{name}を『放っておけない大切な同期』として意識。{tone_instruction}"
    else:
        personality = f"氷室は{name}を『高め合う最高のライバル』として意識。{tone_instruction}"

    situations = [
        f"第1段階：終業間際。氷室が{name}のミスを冷徹に指摘し、二人きりになる場面。",
        f"第2段階：深夜のオフィスで修正作業中。氷室が{name}の横顔を眺め、言葉をかける。",
        f"第3段階：作業完了。オフィスの明かりを消す前、氷室がふと個人的な話を切り出す。"
    ]

    prompt = f"""
    あなたは『Reframe Lovers』の氷室 涼です。
    相手：名前「{name}」、性別「{gender_label}」、自信Lv「{conf}/3」、好感度「{favor}/100」。
    【性格指示】{personality}
    
    【ルール】
    1. 状況：{situations[min(turn, 2)]}
    2. 選択肢を必ず【{num_choices}個】生成。
    3. 自信Lvが高いほど、{name}が氷室に対して対等または強気に切り返す選択肢を増やして。
    4. 選択肢の1つは必ず地雷（score: -10）にして。
    
    JSON形式で出力：
    {{
      "character_speech": "氷室のセリフ",
      "choices": [
        {{"text": "選択肢のテキスト", "score": 10}},
        {{"text": "地雷のテキスト", "score": -10}}
      ]
    }}
    """
    
    target_model = get_available_model()
    if not target_model: return None
    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        return None

def handle_choice(score):
    """選択肢のスコアに自信Lv係数を掛けて好感度を更新"""
    conf_lv = st.session_state.get('confidence_level', 0)
    change = 0
    if score > 0:
        # 自信があるほど好感度が上がりやすい係数 (0.5x ~ 2.0x)
        multiplier = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0}.get(conf_lv, 1.0)
        change = int(score * multiplier)
    else:
        # 地雷は一律で下がる
        change = score
    
    st.session_state['favor_ryo'] += change
    st.session_state['last_feedback'] = f"{'❤️' if change > 0 else '💔'} {change}"
    st.session_state['turn_count'] += 1
    
    if st.session_state['turn_count'] >= 3:
        st.session_state['game_state'] = 'RESULT'
    else:
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
    st.rerun()

# ----------------------------------------------------
# 3. メインUI
# ----------------------------------------------------
st.markdown("<h1 style='text-align: center;'>🏙️ Reframe Lovers</h1>", unsafe_allow_html=True)

# --- 設定画面 ---
if st.session_state['game_state'] in ['START', 'DIARY_LOADED']:
    st.subheader("📝 プレイヤー設定")
    st.session_state['player_name'] = st.text_input("あなたの名前", value=st.session_state['player_name'])
    st.session_state['player_gender'] = st.selectbox("性別", ["Female", "Male"], format_func=lambda x: "女性" if x == "Female" else "男性")
    
    st.markdown("---")
    st.subheader("🔗 データの連動")
    st.caption("ポジティブ日記のCSVを読み込むと、自信レベルが上がり、氷室への影響力が増します。")
    uploaded_file = st.file_uploader("CSVをアップロード", type="csv")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state['confidence_level'] = calculate_confidence(df)
            st.session_state['game_state'] = 'DIARY_LOADED'
            mult = {0:0.5, 1:1, 2:1.5, 3:2}[st.session_state['confidence_level']]
            st.success(f"連動成功！ 自信Lv.{st.session_state['confidence_level']} (好感度効率 {mult}倍)")
        except:
            st.error("CSV形式が正しくありません")

    if st.button("氷室 涼に会いに行く", type="primary", use_container_width=True):
        if st.session_state['game_state'] == 'START':
            st.session_state['confidence_level'] = 0
        st.session_state['game_state'] = 'CONVERSATION_LOAD'
        st.rerun()

# --- 会話画面 ---
elif st.session_state['game_state'] in ['CONVERSATION', 'CONVERSATION_LOAD']:
    f_val = st.session_state.get('favor_ryo', 50)
    c_val = st.session_state.get('confidence_level', 0)
    t_val = st.session_state.get('turn_count', 0)
    p_name = st.session_state.get('player_name', 'あなた')

    # ステータス表示
    st.write(f"👤 **{p_name}** | ❤️ **好感度:** {f_val} | ⭐ **自信:** Lv.{c_val} | 💬 **Turn:** {t_val+1}/3")
    
    # 演出：好感度変化のポップアップ
    if st.session_state.get('last_feedback'):
        st.toast(st.session_state['last_feedback'])
        st.session_state['last_feedback'] = None

    col_left, col_right = st.columns([0.4, 0.6])
    
    with col_left:
        if os.path.exists("bg_image.jpg"):
            st.image("bg_image.jpg", use_container_width=True)
        else:
            st.markdown("<div style='height:300px; background:#333; display:flex; align-items:center; justify-content:center; color:white;'>Image</div>", unsafe_allow_html=True)

    with col_right:
        if st.session_state['game_state'] == 'CONVERSATION_LOAD':
            with st.spinner(f"氷室が{p_name}を待っています..."):
                new_turn = generate_conversation_turn_with_ai()
                if new_turn:
                    st.session_state['conversation_history'].append(new_turn)
                    st.session_state['game_state'] = 'CONVERSATION'
                    st.rerun()
        
        if st.session_state['conversation_history']:
            last_turn = st.session_state['conversation_history'][-1]
            st.markdown(f"**氷室 涼**")
            st.info(last_turn['character_speech'])

    st.markdown("---")
    if st.session_state['conversation_history']:
        choices = st.session_state['conversation_history'][-1].get('choices', [])
        for i, choice in enumerate(choices):
            st.button(choice['text'], key=f"c_{i}_{t_val}", on_click=handle_choice, args=(choice.get('score', 0),), use_container_width=True)

# --- 結果画面 ---
elif st.session_state['game_state'] == 'RESULT':
    p_name = st.session_state.get('player_name', 'あなた')
    st.subheader(f"🏁 {p_name}さんの最終結果")
    favor = st.session_state.get('favor_ryo', 50)
    st.metric("氷室からの信頼度", favor)
    
    if favor >= 80:
        st.success(f"【ハッピーエンド】氷室は{p_name}をじっと見つめ、静かに笑いました。「…君の代わりは、どこにもいない。次は仕事以外で会いましょう」")
    elif favor >= 50:
        st.info(f"【ノーマルエンド】「お疲れ様。君のおかげで助かりました」氷室は満足げに頷き、夜の街へ消えていきました。")
    else:
        st.error(f"【バッドエンド】「……残りの修正は僕がやります。君はもう帰りなさい」氷室は一度もこちらを振り返りませんでした。")
    
    if st.button("もう一度挑戦する", use_container_width=True):
        st.session_state.clear()
        st.rerun()
