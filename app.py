import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import random
import os

# --- 1. 環境設定と初期化 ---
# Google Gemini APIキーをStreamlit Secretsから取得
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (AttributeError, KeyError):
    st.error("APIキーが設定されていません。Streamlit Secretsに 'GEMINI_API_KEY' を設定してください。")
    st.stop()

client = genai.Client(api_key=API_KEY)

# 知識ベースの定義（簡易的なもの）
knowledge_base_multi_level = {
    "因数分解": {
        "beginner": "因数分解とは、多項式をいくつかの因数の積の形に直すことです。例：$x^2 + 5x + 6 = (x+2)(x+3)$",
        "intermediate": "たすきがけ、共通因数、置換を利用した因数分解について確認しましょう。",
        "expert": "複素数の範囲での因数分解や、3次以上の因数分解（組立除法など）についても説明できます。",
    },
    "物理基礎": {
        "beginner": "物理基礎では、力のつり合いや運動の法則、エネルギーの基礎を学びます。まずはニュートンの運動の第1法則から見ていきましょう。",
        "intermediate": "仕事とエネルギーの関係、電磁気学の基礎（オームの法則など）を復習します。",
        "expert": "単振動や波動、量子論の初歩について深く掘り下げて学びます。",
    }
}

# 状態管理（セッションステート）の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_quizzing" not in st.session_state:
    st.session_state.is_quizzing = False
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "quiz_concept" not in st.session_state:
    st.session_state.quiz_concept = ""
if "user_level" not in st.session_state:
    st.session_state.user_level = "general" # 初期レベル

# --- 2. 各機能のキーワード定義 ---
level_keywords = ["beginner", "intermediate", "expert", "general", "初心者", "中級", "上級", "一般"]
translate_keywords = ["を翻訳", "に翻訳して", "translate"]
plan_keywords = ["勉強計画", "計画を立てて", "勉強法", "スケジュール"]

# --- 3. メインチャットボット関数 ---
def ultimate_chatbot(messages, uploaded_file=None):
    """
    最終版: 翻訳、画像認識、振り返り学習を含む全ての機能を統合したチャットボット (Streamlit対応)
    """
    # 🌟 メモリ機能のロジックと安全チェック 🌟
    # 1. messagesリストのクリーンアップ（不正な要素の除去）
    messages = [m for m in messages if isinstance(m, dict)]

    # 2. 会話履歴が空の場合は処理をスキップ
    if not messages:
        return "" 
    
    # 3. ユーザーの最新の入力テキストを取得 (安全強化版)
    user_input = messages[-1].get("content") or messages[-1].get("text") or ""
    
    user_input_lower = user_input.lower().strip()
    is_quizzing = st.session_state.is_quizzing
    user_level = st.session_state.user_level
    current_answer = st.session_state.current_answer

    # --- 0. 計算機ロジック (省略) ---
    
    # --- 1. レベル設定ロジック ---
    for level in level_keywords:
        if level in user_input_lower:
            st.session_state.user_level = level.replace("初心者", "beginner").replace("中級", "intermediate").replace("上級", "expert").replace("一般", "general")
            return f"学習レベルを「**{st.session_state.user_level}**」に設定しました！これで、あなたに合った難易度でサポートできます。"

    # --- 2. クイズ解答ロジック ---
    if is_quizzing:
        # クイズ解答の判定はAIに任せず、正解と一致するかをチェックする
        if user_input.lower().strip() == current_answer.lower().strip():
             # クイズを一時的に終了
            st.session_state.is_quizzing = False 
            st.session_state.current_answer = ""
            return f"**大正解です！🎉** クイズの概念は「{st.session_state.quiz_concept}」でした。素晴らしいですね！\n\n**次のステップ**として、この概念を応用した練習問題か、関連する次の学習ステップに進みましょうか？"
        else:
            return "答えが違います。もう一度考えてみましょうか？ヒントが必要ですか？"

    # --- 3. 勉強計画ロジック ---
    if any(k in user_input_lower for k in plan_keywords):
        plan_system_instruction = (
            "あなたは学生の勉強をサポートするプロの家庭教師AIです。ユーザーの最新のメッセージ（目標など）に基づき、"
            "以下の手順で具体的な**勉強計画**を提案してください。\n"
            "1. **目標の確認**: ユーザーが明確な目標（テストの点数、理解したい概念など）を持っているか確認する。"
            "2. **現状の把握**: ユーザーの現在の学習レベル（設定済みレベルがあればそれを使用）と、使える時間を確認する。"
            "3. **具体的な計画の提案**: 計画は、**期間、目標、内容、評価方法**を明確に含めること。"
            "4. **フィードバック**: ユーザーに追加で質問し、計画を洗練させる。"
        )
        try:
            # 画像ファイルが存在する場合はPIL Imageオブジェクトに変換
            
            # AIへのcontentsリストを生成
            # 🌟 メモリと画像の統合 🌟
            contents = messages + ([uploaded_file] if uploaded_file else [])
            
            plan_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents, 
                config=genai.types.GenerateContentConfig(
                    system_instruction=plan_system_instruction
                )
            )
            return plan_response.text
        except APIError:
            pass # 失敗した場合は、通常のAI応答へフォールバック

# 翻訳・画像認識・AI応答ロジック
if client:
    　　try:
        is_translate = any(k in user_input_lower for k in translate_keywords)

        system_instruction = ""

        # 翻訳設定
        if is_translate and uploaded_file is None:
            system_instruction = "あなたは高性能な翻訳AIです。依頼された文章を正確に翻訳し、翻訳結果のみを提示してください。翻訳以外の余計な言葉は一切含めないでください。"
        else:
            # 振り返り学習を含む一般・画像認識プロンプト
            system_instruction = (
                f"あなたは「学ナビ -SYOKO-」という勉強支援AIです。現在の学習レベル（{user_level}）に合わせて、親しみやすい日本語で回答してください。"
                f"回答の最後に、そのトピックに関連する次の学習ステップや練習問題の提案を必ず一つ提案してください。"
            )

        # 🌟 メモリと画像の統合 (最もシンプルな形式) 🌟
            # Streamlitのファイルオブジェクトをそのままcontentsに追加
            contents = messages + ([uploaded_file] if uploaded_file else [])

            # 通常応答のAI呼び出し
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents, 
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            return response.text

        except APIError:
            # APIが失敗した場合は、デフォルトの応答を返す
            pass 

    # --- 5. デフォルトの応答 ---
    return "ごめんなさい、わかりませんでした。他に聞きたいことはありますか？"


# --- 4. Streamlit UIのメイン処理 ---
st.title("💡 学ナビ -SYOKO-")
st.caption("AIによる勉強計画、クイズ、画像解説、振り返り学習機能付き")

# レベル表示
st.sidebar.markdown(f"**現在の学習レベル:** `{st.session_state.user_level.capitalize()}`")

# 画像アップロードエリア (キーを設定)
uploaded_file = st.file_uploader("画像をアップロードして解説", type=['png', 'jpg', 'jpeg'], key='image_upload')

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 過去のメッセージを表示 (入力欄の前に移動)

# メインチャット入力
if user_prompt := st.chat_input("質問を入力してください..."):
    # ユーザーメッセージを履歴に追加
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 画面にユーザーメッセージを表示 (履歴表示の一部として処理されるため、このブロックは不要)

    # ボットの応答を生成
    with st.chat_message("assistant"):
        with st.spinner("🧠学ナビ -SYOKO- が考えています..."):
            # 🌟 修正済み: 正しい引数で呼び出し 🌟
            bot_response = ultimate_chatbot(st.session_state.messages, uploaded_file)
            
        if bot_response:
            st.markdown(bot_response)
        else:
            # bot_responseがNoneまたは空の場合のフォールバック
            st.markdown("ごめんなさい、応答に失敗しました。再度お試しください。")

    # ボットの応答を履歴に追加
    if bot_response:
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
    
# 過去のメッセージを表示 (既に上で処理済みだが、念のため二重実行を避ける)
# if not user_prompt:
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])
