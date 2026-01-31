# -*- coding: utf-8 -*-
import streamlit as st
import google.generativeai as genai
import os

# --- ページ設定 ---
st.set_page_config(page_title="Empire Gate - 帝国検問所", page_icon="👑", layout="wide")

# --- API設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーをStreamlitのSecretsに設定してください。")

def get_best_model():
    return 'models/gemini-1.5-flash' # 最速のFlashモデルを推奨

# --- 帝国検問AI：システムプロンプト（皇帝の魂） ---
SYSTEM_PROMPT = """
あなたは「くだちい帝国」の検問AIです。
入力されたnoteのURLや内容を、皇帝（1969年生まれ、泥臭さ重視、あんこ好き）の審美眼で、超辛口に判定してください。

【判定の絶対基準】
1. 一次体験（自分の汗と涙）があるか？（合格：ロジウラ、無名S）
2. 上から目線のコーチング、誘導、成功自慢ではないか？（不合格：コーチゆう、Hase、りょうた）
3. 文面に「体温」があるか？AIやテンプレのコピペではないか？

【出力フォーマット（必ず厳守せよ）】
■擬態設定：相手を皮肉る二つ名
■騎士団の声：
  ・Gemini（論理的だが容赦ない毒舌）
  ・ギャル先生（直感でブッタ斬るギャル語）
  ・女王セレスティア（裏の罵声と真の慈愛を織り交ぜる）
■判定ランク：S（騎士）〜 F（追放）
■皇帝の最終決断：トドメを刺す引導。あんこの甘さや泥臭い生き様を尊ぶ言葉で締めろ。
"""

# --- 審判ロジック ---
def judge_content(user_input):
    try:
        model = genai.GenerativeModel(get_best_model())
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\n検問対象の内容：\n{user_input}")
        return response.text
    except Exception as e:
        return f"審判不能。不浄な力が干渉しているようだ。（エラー: {str(e)}）"

# --- UI表示 ---
st.title("👑 Empire Gate - 帝国検問所 -")
st.markdown("### 「その言葉に、体温はあるか？」")
st.write("ここは数と権威で着飾った不浄を焼き払い、魂ある言葉を選別する聖域である。")

st.divider()

# サイドバー：皇帝のステータス
with st.sidebar:
    st.title("🏙️ くだちい帝国")
    st.image("https://images.unsplash.com/photo-1599422315624-8015e917d52a?auto=format&fit=crop&q=80&w=300")
    st.metric("🔥 帝国純度", "100%")
    st.success("🌺 ギャル先生:「不浄な奴はマジでお断り！✨」")
    st.info("🏛️ 女王セレスティア:「真実を語る覚悟はよろしくて？」")

# メインエリア：URL/テキスト入力
target_input = st.text_area("検問対象のURL、またはプロフィール文章を入力せよ", height=150, placeholder="https://note.com/...")

if st.button("審判を下す（公開処刑）", type="primary", use_container_width=True):
    if target_input:
        with st.spinner("……魂をスキャン中。不浄の匂いがするな。"):
            result = judge_content(target_input)
            
            # 判定結果の表示
            st.markdown("---")
            st.subheader("📜 帝国からの布告")
            
            # 結果をコンテナで装飾
            with st.container(border=True):
                st.markdown(result)
            
            st.toast("審判が下された。")
    else:
        st.warning("検問対象が空だ。逃げ出すつもりか？")

# 4. フッター
st.divider()
st.caption("© 2026 くだちい帝国 - 全ての偽善者に引導を。")
