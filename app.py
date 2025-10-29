import streamlit as st
import os
import random
import re
import requests
from PIL import Image
from io import BytesIO

# Google Gemini SDK
from google import genai
from google.genai.errors import APIError

# --- 状態変数の定義（st.session_stateを使用） ---
if "is_quizzing" not in st.session_state:
    st.session_state.is_quizzing = False
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "user_level" not in st.session_state:
    st.session_state.user_level = 'general'
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- APIクライアントの初期化 ---
try:
    if 'GEMINI_API_KEY' in st.secrets:
        client = genai.Client(api_key=st.secrets['GEMINI_API_KEY'])
        model = 'gemini-2.5-flash'
    else:
        client = None 
except Exception as e:
    client = None

# --- データ定義（以前のコードから引き継ぎ） ---
default_response = "ごめんなさい、よくわかりませんでした。他に聞きたいことはありますか？"
response_rules = {"こんにちは": "こんにちは！", "ありがとう": "どういたしまして！"}
knowledge_base_multi_level = {
    "原子": {"general": "物質の最小単位。", "elementary": "ものを細かくしていった時の、とても小さなつぶ。"}, 
    "光合成": {"general": "植物が太陽の光のエネルギーを使って、養分と酸素を作る働き。", "elementary": "葉っぱが太陽の光を浴びて、ごはんを作る魔法。 "},
}
level_keywords = {"一般": "general", "専門": "expert", "小学生": "elementary"}
translate_keywords = ["を翻訳して", "に訳して", "翻訳", "translate"]


def ultimate_chatbot(user_input, uploaded_file=None):
    """
    最終版：翻訳、画像認識、掘り下げ学習を含む全ての機能を統合したチャットボット（Streamlit対応）
    """
    
    is_quizzing = st.session_state.is_quizzing
    user_level = st.session_state.user_level
    current_answer = st.session_state.current_answer

    user_input_lower = user_input.lower().strip()
    
    # --- 0. 計算機能ロジック ---
    if any(c.isdigit() for c in user_input_lower) and any(op in user_input_lower for op in ['+', '-', '*', '/']):
        cleaned_input = user_input_lower.replace(' ', '').replace('　', '').replace('=', '')
        try:
            result = eval(cleaned_input)
            return f"計算結果は... **{result}** です！"
        except:
            pass
            
    # --- 1. レベル設定ロジック ---
    for key, level_code in level_keywords.items():
        if f"レベルは{key}" in user_input_lower or f"を{key}" in user_input_lower:
            st.session_state.user_level = level_code
            return f"✅ 学習レベルを **{key} 向け**に設定しました！"

    # --- 2. 正誤判定ロジック ---
    if is_quizzing:
        if user_input_lower == current_answer.lower():
            st.session_state.is_quizzing = False
            st.session_state.current_answer = ""
            return "🎉 正解です！素晴らしい！"
        else:
            if "答え" in user_input_lower or "やめ" in user_input_lower:
                correct = current_answer
                st.session_state.is_quizzing = False
                st.session_state.current_answer = ""
                return f"💡 正しい答えは **'{correct}'** でした！"
            else:
                return "🤔 残念、違います。もう一度考えてみましょう。または '答え' と入力すると教えますよ。"

    # --- 3. クイズ機能の起動ロジック ---
    if "クイズ" in user_input_lower:
        concepts = list(knowledge_base_multi_level.keys())
        quiz_concept = random.choice(concepts)
        quiz_definition = knowledge_base_multi_level[quiz_concept].get(user_level, "定義が見つかりません。")
        st.session_state.is_quizzing = True
        st.session_state.current_answer = quiz_concept
        return f"💡 クイズです！現在のレベル（{user_level}）で出題します。\nこの定義が表す言葉は何でしょう？\n\n「{quiz_definition}」"


    # --- 4. 翻訳・画像認識・AI応答ロジック ---
    if client: 
        try:
            is_translate = any(k in user_input_lower for k in translate_keywords)
            contents = [user_input]
            system_instruction = ""
            
            # --- プロンプト設定 ---
            if is_translate and not uploaded_file:
                # 翻訳専用プロンプト
                system_instruction = "あなたは高性能な翻訳AIです。依頼された文章を正確に翻訳し、翻訳結果のみを提示してください。翻訳以外の余計な言葉は不要です。"
            else:
                # 掘り下げ学習を含む一般・画像応答プロンプト
                system_instruction = (
                    f"あなたは「学ナビ -SYOKO-」という勉強支援AIです。現在の学習レベル（{user_level}）に合わせて、親しみやすい日本語で回答してください。"
                    f"回答の最後に、そのトピックに関連する次の学習ステップや深掘り質問を必ず一つ提案してください。"
                )
            
            # --- 画像処理 ---
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                
                text_prompt = user_input if user_input else "この画像の内容を解説してください。"
                contents = [text_prompt, image]
            
            # --- Gemini API呼び出し ---
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            return response.text
            
        except APIError as e:
            return default_response
        except Exception as e:
            return default_response 
    
    # --- 5. AI失敗/未接続時の応答 ---
    for keyword, response in response_rules.items():
        if keyword in user_input_lower:
            return response
            
    return default_response


# --- 画面構成 ---
st.title("🌟 学ナビ -SYOKO- (AI搭載 学習支援ボット)")
st.caption(f"現在の学習レベル: {st.session_state.user_level}")
st.write("計算、レベル変更（例: レベルは小学生）、クイズ、翻訳、画像の解説ができます。")


# --- 履歴の表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 画像アップロード欄 ---
uploaded_file = st.file_uploader("画像をアップロードして解説", type=['png', 'jpg', 'jpeg'], key="image_upload")

# --- メインチャット入力欄 ---
if user_prompt := st.chat_input("質問を入力してください..."):
    # ユーザーメッセージを履歴に追加
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # 画面にユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # ボットの応答を生成
    with st.chat_message("assistant"):
        with st.spinner("🤖 学ナビ -SYOKO- が考えています..."):
            bot_response = ultimate_chatbot(user_prompt, uploaded_file)
            st.markdown(bot_response)

    # ボットの応答を履歴に追加
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
    
    # 画像は一度使うと消去
    if uploaded_file is not None:
         st.session_state.image_upload = None
