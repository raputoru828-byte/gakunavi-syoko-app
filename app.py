import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import random
import os

# --- 1. 環境設定と初期化 ---
# APIキーをos.environから取得（Secretsエディタのバグ回避のため）
API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    if not API_KEY:
        st.error("🚨 APIキーが設定されていません。環境変数に 'GEMINI_API_KEY' を設定してください。")
        st.stop()
except (AttributeError, KeyError):
    st.error("APIキーの取得中にエラーが発生しました。設定を確認してください。")
    st.stop()

# Geminiクライアントの初期化
client = genai.Client(api_key=API_KEY)

# 状態管理（セッションステート）の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_level" not in st.session_state:
    st.session_state.user_level = "general"
if "is_quizzing" not in st.session_state:
    st.session_state.is_quizzing = False
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "quiz_concept" not in st.session_state:
    st.session_state.quiz_concept = ""


# --- 2. 各機能のキーワード定義 ---
level_keywords = ["beginner", "intermediate", "expert", "general", "初心者", "中級", "上級", "一般"]
plan_keywords = ["勉強計画", "計画を立てて", "勉強法", "スケジュール"]

# --- 3. メインチャットボット関数 ---
def ultimate_chatbot(messages, uploaded_file=None):
    """
    最終版: 翻訳、画像認識、振り返り学習を含む全ての機能を統合したチャットボット
    """
    # 🌟 究極の防御: Gemini API形式に合わせたcontentsの完全な再構築 🌟
    contents = []
    for message in messages:
        if isinstance(message, dict) and 'role' in message and 'content' in message:
            if isinstance(message['content'], str) and message['content'].strip():
                contents.append({
                    "role": message['role'],
                    "parts": [{"text": message['content']}]
                })
    
    # メッセージが空の場合は処理をスキップ
    if not contents:
        return ""
    
    # ユーザーの最新の入力テキストを取得
    user_input = contents[-1]['parts'][0]['text'] if contents[-1]['role'] == 'user' and contents[-1]['parts'][0].get('text') else ""
    user_input_lower = user_input.lower().strip()
    user_level = st.session_state.user_level

    # --- 1. レベル設定ロジック ---
    for level in level_keywords:
        if level in user_input_lower:
            st.session_state.user_level = level.replace("初心者", "beginner").replace("中級", "intermediate").replace("上級", "expert").replace("一般", "general")
            return f"学習レベルを「**{st.session_state.user_level}**」に設定しました！"
            
    # アップロードされたファイルを最後のユーザーメッセージに追加
    if uploaded_file and contents and contents[-1]['role'] == 'user':
        contents[-1]['parts'].append(uploaded_file)
    
    # --- AI応答ロジック ---
    try:
        system_instruction = (
            f"あなたは「学ナビ -SYOKO-」という勉強支援AIです。現在の学習レベル（{user_level}）に合わせて、親しみやすい日本語で回答してください。"
            f"回答の最後に、そのトピックに関連する次の学習ステップや練習問題の提案を必ず一つ提案してください。"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents, 
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

    except APIError as e:
        # APIエラー発生時、デバッグ情報をログに出力
        print(f"API Error: {e}")
        return "ごめんなさい、AIとの通信に失敗しました。APIキーまたはネットワーク接続を確認してください。"
    except Exception as e:
        print(f"General Error: {e}")
        return "ごめんなさい、エラーが発生しました。"


# --- 4. Streamlit UIのメイン処理 ---
st.title("💡 学ナビ -SYOKO-")
st.caption("AIによる勉強計画、クイズ、画像解説、振り返り学習機能付き")

st.sidebar.markdown(f"**現在の学習レベル:** `{st.session_state.user_level.capitalize()}`")

uploaded_file = st.file_uploader("画像をアップロードして解説", type=['png', 'jpg', 'jpeg'])

# 過去のメッセージを表示 
for message in st.session_state.messages:
    if message.get("content"): 
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# メインチャット入力
if user_prompt := st.chat_input("質問を入力してください..."):
    
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant"):
        with st.spinner("🧠学ナビ -SYOKO- が考えています..."):
            # APIキーが空の場合にダミー応答を返す（デバッグ用）
            if not API_KEY:
                bot_response = "デバッグモード: APIキーがないため応答できません。"
            else:
                bot_response = ultimate_chatbot(st.session_state.messages, uploaded_file)
            
        if bot_response:
            st.markdown(bot_response)
        else:
            st.markdown("ごめんなさい、応答に失敗しました。再度お試しください。")

    if bot_response:
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
