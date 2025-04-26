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

@app.post("/ask")
async def ask_gpt(question: str = Form(...)):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 부동산 경매 전문가입니다."},
            {"role": "user", "content": question}
        ]
    )
    return {"answer": response['choices'][0]['message']['content']}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    chat_id = data["message"]["chat"]["id"]
    text = data["message"]["text"]

    # 텔레그램 봇에 받은 메세지 다시 보내기
    send_message(chat_id, f"받은 메세지: {text}")

    return {"ok": True}

def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)
    
    user_question_count = {}
MAX_QUESTIONS = 10

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    chat_id = str(data["message"]["chat"]["id"])
    text = data["message"]["text"]

    # 사용자 질문횟수 초기화
    if chat_id not in user_question_count:
        user_question_count[chat_id] = 0

    # 질문횟수에 따라 GPT 모델 선택
    if user_question_count[chat_id] < MAX_QUESTIONS:
        model = "gpt-4"
    else:
        model = "gpt-3.5-turbo"

    # GPT에게 자연어 문장 보내기
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 부동산 경매 전문 비서입니다. 사용자의 요청을 정확히 분석해서 필요한 작업을 찾아야 합니다."},
            {"role": "user", "content": text}
        ]
    )
    gpt_answer = response['choices'][0]['message']['content']

    # 사용자 질문횟수 +1
    user_question_count[chat_id] += 1

    # 남은 질문 횟수 계산
    remaining = MAX_QUESTIONS - user_question_count[chat_id]
    if remaining < 0:
        remaining = "무제한 (GPT 3.5 버전 사용)"

    # 텔레그램으로 최종 답변 보내기
    final_answer = f"{gpt_answer}\n\n(오늘 남은 질문: {remaining})"
    send_message(chat_id, final_answer)

    return {"ok": True}