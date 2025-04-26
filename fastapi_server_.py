from fastapi import FastAPI, Request, Form
import openai
import os
import requests

app = FastAPI()

# 환경변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

openai.api_key = OPENAI_API_KEY

@app.get("/", response_class="HTMLResponse")
async def home():
    return "<h1>환영합니다! 여기는 HepiNet 서버입니다!</h1>"

def ask_gpt(question):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 부동산 경매 전문 코치입니다. 항상 한국어로 답변하세요."},
            {"role": "user", "content": question}
        ]
    )
    return response['choices'][0]['message']['content']

def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)
    
    
def search_youtube_video(query):
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")  # 환경변수에서 유튜브 키 읽어옴
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={query}&key={youtube_api_key}&type=video"

    response = requests.get(url)
    items = response.json().get('items')

    if not items:
        return "유튜브에서 결과를 찾을 수 없습니다."

    video_id = items[0]['id']['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    return video_url

    
    
    
user_question_count = {}
MAX_QUESTIONS = 10
    
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"]["text"]

        if chat_id not in user_question_count:
            user_question_count[chat_id] = 0

        if user_question_count[chat_id] < MAX_QUESTIONS:
            model = "gpt-4"
        else:
            model = "gpt-3.5-turbo"

        # 유튜브 관련 요청 처리
        if "유튜브" in text or "영상" in text:
            answer = search_youtube_video(text)
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "당신은 부동산 경매 전문 비서입니다. 사용자의 요청을 정확히 분석해서 필요한 작업을 찾아야 합니다."},
                    {"role": "user", "content": text}
                ]
            )
            answer = response['choices'][0]['message']['content']

        user_question_count[chat_id] += 1
        remaining = MAX_QUESTIONS - user_question_count[chat_id]
        if remaining <= 0:
            remaining = "무제한 (GPT 3.5 버전 사용)"

        final_answer = f"{answer}\n\n(오늘 남은 질문: {remaining})"
        send_message(chat_id, final_answer)

    except Exception as e:
        print(f"에러 발생: {e}")
        try:
            send_message(chat_id, "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.")
        except:
            pass

    return {"ok": True}