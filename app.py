import streamlit as st
from google import genai
from google.genai.errors import APIError
from PIL import Image
import random
import os

# --- 1. 環境設定と初期化 ---
# 🚨 最終手段: APIキーを直接埋め込み、Streamlit Cloudのバグを回避 🚨
# (このキーはあなたが最後に提供された有効なキーです)
API_KEY = "AIzaSyCE95wGJhcj84fQtx4doY-qLD_7nKO4eXE" 

try:
    if not API_KEY:
        st.error("🚨 APIキーが設定されていません。コード内にキーが正しく埋め込まれているか確認してください。")
        st.stop()
except Exception:
    st.error("APIキーの初期化中にエラーが発生しました。")
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
quiz_keywords = ["クイズ", "問題出して", "テストして"] 


# --- 3. メインチャットボット関数 ---
def ultimate_chatbot(messages, uploaded_file=None):
    """
    最終版: 翻訳、画像認識、振り返り学習、クイズ、計画機能を含む全ての機能を統合したチャットボット
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
    
    if not contents:
        return ""
    
    user_input = contents[-1]['parts'][0]['text'] if contents[-1]['role'] == 'user' and contents[-1]['parts'][0].get('text') else ""
    user_input_lower = user_input.lower().strip()
    user_level = st.session_state.user_level

    # --- 1. レベル設定ロジック ---
    for level in level_keywords:
        if level in user_input_lower:
            st.session_state.user_level = level.replace("初心者", "beginner").replace("中級", "intermediate").replace("上級", "expert").replace("一般", "general")
            return f"学習レベルを「**{st.session_state.user_level}**」に設定しました！"

    # --- 1.5 クイズ解答ロジック ---
    if st.session_state.is_quizzing:
        correct_answer_lower = st.session_state.current_answer.lower().strip()
        
        if correct_answer_lower in user_input_lower or user_input_lower == correct_answer_lower:
            st.session_state.is_quizzing = False 
            st.session_state.current_answer = ""
            return f"**大正解です！🎉** クイズの概念は「{st.session_state.quiz_concept}」でした。素晴らしいですね！\n\n**次のステップ**として、この概念を応用した練習問題か、関連する次の学習ステップに進みましょうか？"
        else:
            return "答えが違います。もう一度考えてみましょうか？ヒントが必要ですか？"


    # --- 2. クイズ生成ロジック ---
    if any(k in user_input_lower for k in quiz_keywords):
        quiz_concept = user_input.replace("クイズ", "").replace("問題出して", "").replace("テストして", "").strip()
        if not quiz_concept:
            return "クイズを出したい概念やトピックを教えてください！例: 「**二次関数**のクイズを出して」"
            
        quiz_system_instruction = (
            f"あなたは、学習支援AIです。ユーザーのレベル（{user_level}）に合わせて、「{quiz_concept}」に関するクイズを一問だけ出してください。"
            f"必ず**問題文の直前**に【クイズ】と書き、答えは**絶対に出力しないでください**。"
            f"問題を出した後、ユーザーのレベルに合わせて「答えを待っています」などの励ましの言葉を添えてください。"
        )
        
        try:
            quiz_contents = [
                {"role": "user", "parts": [{"text": f"レベル{user_level}のユーザーに、「{quiz_concept}」についてクイズを出してください。"}]}
            ]
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=quiz_contents, 
                config=genai.types.GenerateContentConfig(
                    system_instruction=quiz_system_instruction
                )
            )
            
            answer_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[{"role": "user", "parts": [{"text": f"今生成したクイズ「{response.text}」の**正しい答え**だけを出力してください。答え以外の余計な言葉は一切含めないでください。"}]}],
            )

            st.session_state.is_quizzing = True
            st.session_state.current_answer = answer_response.text.strip()
            st.session_state.quiz_concept = quiz_concept
            
            return response.text 

        except APIError:
            return "クイズの生成中にエラーが発生しました。再度お試しください。"
        except Exception:
            return "クイズ生成中に予期せぬエラーが発生しました。"
            

    # --- 3. 勉強計画ロジック (今回追加分) ---
    if any(k in user_input_lower for k in plan_keywords):
        
        plan_system_instruction = (
            "あなたは学生の勉強をサポートするプロの家庭教師AIです。ユーザーの最新のメッセージ（目標など）に基づき、"
            f"現在の学習レベル（{user_level}）に合わせて、以下の手順で具体的な**勉強計画**を提案してください。\n"
            "1. **目標の確認**: ユーザーが明確な目標を持っているか確認する。"
            "2. **現状の把握**: ユーザーの学習レベルと、使える時間を確認する。"
            "3. **具体的な計画の提案**: 計画は、**期間、目標、内容、評価方法**を明確に含めること。計画は箇条書きで見やすくすること。"
            "4. **フィードバック**: ユーザーに追加で質問し、計画を洗練させる。"
        )
        try:
            plan_contents = contents
            
            plan_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=plan_contents, 
                config=genai.types.GenerateContentConfig(
                    system_instruction=plan_system_instruction
                )
            )
            return plan_response.text
        except APIError:
            return "勉強計画の生成中にエラーが発生しました。再度お試しください。" 
        except Exception:
            return "勉強計画生成中に予期せぬエラーが発生しました。"


    # アップロードされたファイルを最後のユーザーメッセージに追加
    if uploaded_file and contents and contents[-1]['role'] == 'user':
        contents[-1]['parts'].append(uploaded_file)
    
    # --- 4. 一般応答ロジック ---
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
        print(f"API Error occurred: {e}")
        return "ごめんなさい、AIとの通信に失敗しました。APIキーを確認してください。"
    except Exception as e:
        print(f"General Error: {e}")
        return "ごめんなさい、エラーが発生しました。"


# --- 5. Streamlit UIのメイン処理 ---
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
            bot_response = ultimate_chatbot(st.session_state.messages, uploaded_file)
            
        if bot_response:
            st.markdown(bot_response)
        else:
            st.markdown("ごめんなさい、応答に失敗しました。再度お試しください。")

    if bot_response:
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
