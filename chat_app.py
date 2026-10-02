import streamlit as st
from google import genai
from google.genai import types
import kizaemon_tools
import datetime

# --- 1. 初期設定 ---
st.set_page_config(page_title="Kizaemon Store Assistant", page_icon="🍣")
st.title("🍣 Kizaemon AI アシスタント")
st.caption("完全無料版: Gemini 2.5 Flash搭載。売上予測や在庫について聞いてください。")

api_key = kizaemon_tools.ENV.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 2. AIに渡すツール（Python関数）の定義 ---
def get_raw_sales_data(days: int = 7) -> str:
    """直近の売上、客数、天気、売り切れ商品などの生データを取得します。"""
    return kizaemon_tools.get_raw_sales_data(days)

def get_sales_statistics(group_by: str = "day_of_week") -> str:
    """売上の統計データを取得します。group_byは 'day_of_week' または 'weather' を指定。"""
    return kizaemon_tools.get_sales_statistics(group_by)

def calculate_baseline_forecast(target_date: str) -> str:
    """指定した日付(YYYY/MM/DD)の統計的な予測ベースラインを取得します。"""
    return kizaemon_tools.calculate_baseline_forecast(target_date)

# --- 3. AIモデルの初期化 ---
today_str = datetime.datetime.now().strftime("%Y/%m/%d")
sys_prompt = f"""あなたは飲食店の優秀な店長アシスタントです。今日の日付は {today_str} です。ユーザーから日付を尋ねる必要はありません。
売上の予測を求められた際は、必ず以下のステップを自動で踏んでください：
1. `calculate_baseline_forecast` を使って、その曜日のベースラインを取得する。
2. `get_raw_sales_data` (days=7) を使って、直近1週間の売上トレンドを取得する。
3. ベースラインに対して、直近のトレンド（例：最近はベースより売上が伸びている、客数が落ちている等）を加味し、AIとしての最終的な「予測金額」と「客数」を算出して提示する。
ユーザーに「直近のデータを加味しますか？」などと質問せず、最初から全て調べて、完璧に分析した回答を1回で出してください。"""

if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=sys_prompt,
            tools=[get_raw_sales_data, get_sales_statistics, calculate_baseline_forecast]
        )
    )

# --- 4. チャット画面の構築 ---
for message in st.session_state.chat.get_history():
    role = "assistant" if message.role == "model" else "user"
    text = ""
    for part in message.parts:
        if part.text:
            text += part.text
    if text:
        with st.chat_message(role):
            st.markdown(text)

prompt = st.chat_input("例: 明日の売上を予測して")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Supabaseから複数種類のデータを取得して複合的に分析しています..."):
            try:
                response = st.session_state.chat.send_message(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
