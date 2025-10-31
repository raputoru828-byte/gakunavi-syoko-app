import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import random
import os

# --- 1. 環境設定と初期化 ---
# Google Gemini APIキーをStreamlit Secretsから取得
try:
    # 🚨 最終チェック: キーが空でないことを確認 🚨
    API_KEY = st.secrets["GEMINI_API_KEY"]
    if not API_KEY or API_KEY.startswith('"') or API_KEY.endswith('"'):
        st.error("APIキーの設定に誤りがあります。Secretsから「ダブルクォーテーション」を外し、再度保存してください。")
        st.stop()
except (AttributeError, KeyError):
    st.error("APIキーが設定されていません。Streamlit Secretsに 'GEMINI_API_KEY' を設定してください。")
    st.stop()

# Geminiクライアントの初期化
client = genai.Client(api_key=API_KEY)

# 状態管理（セッションステート）の初期化
# 🚨 最終対策: すべてのキーを強制的にリセットする 🚨
if "reset_flag" not in st.session_state:
    st.session_state.reset_flag = True

if st.session_state.reset_flag:
    # 既存の不正なメッセージ履歴をクリア
    st.session_state.messages = []
    st.session_state.is_quizzing = False
    st.session_state.current_answer = ""
    st.session_state.quiz_concept = ""
    st.session_state.user_level = "general" # 初期レベル
    st.session_state.reset_flag = False # リセットは初回のみ実行

# 残りのキーが設定されていない場合のみ初期化
if "is_quizzing" not in st.session_state:
    st.session_state.is_quizzing = False
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "quiz_concept" not in st.session_state:
    st.session_state.quiz_concept = ""
if "user_level" not in st.session_state:
    st.session_state.user_level = "general" 


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
    # 1. messagesリストのクリーンアップ
    messages = [m for m in messages if isinstance(m, dict)]

    # 2. 会話履歴が空の場合は処理をスキップ
    if not messages:
        return "" 
    
    # 3. ユーザーの最新の入力テキストを取得と変数定義
    user_input = messages[-1].get("content") or messages[-1].get("text") or ""
    user_input_lower = user_input.lower().strip()
    is_quizzing = st.session_state.is_quizzing
    user_level = st.session_state.user_level
    current_answer = st.session_state.current_answer

    # 4. 入力チェックの安全装置
    if not user_input.strip() and uploaded_file is None:
        return "画像をアップロードするか、質問を入力してください。"
    
    # --- 1. レベル設定ロジック ---
    for level in level_keywords:
        if level in user_input_lower:
            st.session_state.user_level = level.replace("初心者", "beginner").replace("中級", "intermediate").replace("上級", "expert").replace("一般", "general")
            return f"学習レベルを「**{st.session_state.user_level}**」に設定しました！これで、あなたに合った難易度でサポートできます。"

    # --- 2. クイズ解答ロジック ---
    if is_quizzing:
        if user_input.lower().strip() == current_answer.lower().strip():
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
            # 🌟 究極の防御: contentsの完全な再構築 🌟
            contents = []
            for message in messages:
                if isinstance(message, dict) and 'role' in message and 'content' in message:
                    if isinstance(message['content'], str) and message['content'].strip():
                        contents.append({
                            "role": message['role'],
                            "parts": [{"text": message['content']}]
                        })
            
            # アップロードされたファイルを最後のユーザーメッセージに追加
            if uploaded_file and contents and contents[-1]['role'] == 'user':
                contents[-1]['parts'].append(uploaded_file)
            
            plan_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents, 
                config=genai.types.GenerateContentConfig(
                    system_instruction=plan_system_instruction
                )
            )
            return plan_response.text
        except APIError:
            pass 

    # --- 4. 翻訳・画像認識・AI応答ロジック ---
    if client:
        try:
            # 翻訳キーワードチェック
            is_translate = any(k in user_input_lower for k in translate_keywords)
            
            system_instruction = ""
            
            # 翻訳設定
            if is_translate and uploaded_file is None:
                system_instruction = "あなたは高性能な翻訳AIです。依頼された文章を正確に翻訳し、翻訳結果のみを提示してください。翻訳以外の余計な言葉は一切含めないでください。"
            else:
                # 一般・画像認識プロンプト
                system_instruction = (
                    f"あなたは「学ナビ -SYOKO-」という勉強支援AIです。現在の学習レベル（{user_level}）に合わせて、親しみやすい日本語で回答してください。"
                    f"回答の最後に、そのトピックに関連する次の学習ステップや練習問題の提案を必ず一つ提案してください。"
                )
            
            # 🌟 究極の防御: contentsの完全な再構築 🌟
            contents = []
            for message in messages:
                if isinstance(message, dict) and 'role' in message and 'content' in message:
                    if isinstance(message['content'], str) and message['content'].strip():
                        contents.append({
                            "role": message['role'],
                            "parts": [{"text": message['content']}]
                        })

            # アップロードされたファイルを最後のユーザーメッセージに追加
            if uploaded_file and contents and contents[-1]['role'] == 'user':
                contents[-1]['parts'].append(uploaded_file)
            
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
            # APIエラー発生時に、デバッグ情報をログに出力し、デフォルトメッセージを返す
            print("API Error occurred in general chatbot path.")
            pass 

    # --- 5. デフォルトの応答 ---
    return "ごめんなさい、わかりませんでした。他に聞きたいことはありますか？"


# --- 6. Streamlit UIのメイン処理 ---
st.title("💡 学ナビ -SYOKO-")
st.caption("AIによる勉強計画、クイズ、画像解説、振り返り学習機能付き")

# レベル表示
st.sidebar.markdown(f"**現在の学習レベル:** `{st.session_state.user_level.capitalize()}`")

# 🚨 最終修正: 画像アップロードウィジェットのキーを動的に変更 🚨
uploaded_file = st.file_uploader("画像をアップロードして解説", type=['png', 'jpg', 'jpeg'], key=f'image_upload_{st.session_state.user_level}')


# 過去のメッセージを表示 
for message in st.session_state.messages:
    # ユーザーとAIのメッセージのうち、内容（content）が空ではないものだけを表示
    if isinstance(message, dict) and message.get("content"): 
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# メインチャット入力
if user_prompt := st.chat_input("質問を入力してください..."):
    
    # ユーザーメッセージを履歴に追加
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # ボットの応答を生成
    with st.chat_message("assistant"):
        with st.spinner("🧠学ナビ -SYOKO- が考えています..."):
            bot_response = ultimate_chatbot(st.session_state.messages, uploaded_file)
            
        if bot_response:
            st.markdown(bot_response)
        else:
            st.markdown("ごめんなさい、応答に失敗しました。再度お試しください。")

    # ボットの応答を履歴に追加
    if bot_response:
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
