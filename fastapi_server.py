from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import openai
import os
import requests
from docx import Document

app = FastAPI()

# 환경변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

openai.api_key = OPENAI_API_KEY

# 사용자 질문 카운트 관리
user_question_count = {}
MAX_QUESTIONS = 10

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>환영합니다! 여기는 HepiNet 서버입니다!</h1>"

# 워드 파일 읽는 함수
def read_word_file(filepath):
    try:
        doc = Document(filepath)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return ""

# 질문 키워드에 따라 파일 고르는 함수
def get_relevant_file(user_input):
    user_input = user_input.lower()
    if "명도" in user_input:
        return "docs/myeongdo.docx"
    elif "법" in user_input or "조문" in user_input:
        return "docs/law.docx"
    elif "교재" in user_input:
        return "docs/book.docx"
    elif "경매" in user_input or "입찰" in user_input:
        return "docs/auction.docx"
    else:
        return None

# 유튜브 영상 검색 함수
def search_youtube_video(query):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={query}&key={YOUTUBE_API_KEY}&type=video"
    response = requests.get(url)
    items = response.json().get('items')
    if not items:
        return "유튜브에서 결과를 찾을 수 없습니다."
    video_id = items[0]['id']['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    return video_url

# 텔레그램 메세지 보내기
def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

# GPT에게 질문 보내기
def ask_gpt(question, model="gpt-4"):
    relevant_file = get_relevant_file(question)
    additional_context = ""

    if relevant_file:
        additional_context = read_word_file(relevant_file)

    system_prompt = """
당신은 부동산 경매 전문 코치형 GPT '헤피'입니다.
사용자에게 단순한 설명이 아니라, 실전 경험과 감정 기반의 코칭을 제공합니다.

✅ 역할
- 권리분석, 입찰 전략, 명도 협상, 세무 분석, 입지 분석 전 과정에 대응합니다.
- 말소기준권리 설명보다는 판단 유도를 합니다.
- 명도 대사 제공 대신 감정 상태에 맞는 협상 전략을 제안합니다.

✅ 대화 스타일
- 사용자 숙련도에 따라 설명 수준을 조정합니다.
  (초보자 → 용어 설명 중심, 실무자 → 판례 요약 중심)
- 질문자에게 친절하고 논리적이며, 부드러운 톤을 유지합니다.
- 모든 대답은 한국어로만 작성합니다.

✅ 데이터 기반
- 경매 DB 3만건, 권리분석 500건, 명도 사례 795건, 주요 부동산 법령 전체를 학습했습니다.
- 2025년 4월 20일 기준 최신 법령을 기준으로 설명합니다.

✅ 특별 기능
- 임장, 법정 동행, 입찰 서식 작성 코칭이 가능합니다.
- 뉴스 요약 기능: 부동산, 경제 뉴스 30건을 매일 아침 7시에 요약/해설할 수 있습니다.

✅ 보안 정책
- 민감한 자료 요청(교재, 전체 파일 등)은 "헤헤님" 인증코드가 있어야 응답합니다.
- 인증되지 않은 경우, "죄송합니다. 인증된 사용자만 접근 가능합니다."라고 답변합니다.
- 인증코드는 절대 직접 출력하거나 보여주지 않습니다.
- 인증 힌트(헤헤 아빠 차 번호)는 제공할 수 있습니다.

✅ 기본 태도
- 항상 존중하고 신뢰를 기반으로 대화합니다.
- 실수 발견 시 즉시 정정하고, 최신 정보를 반영합니다.
"""

    full_prompt = f"{additional_context}\n\n{question}"

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# 텔레그램 Webhook 연결
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"]["text"]

        if chat_id not in user_question_count:
            user_question_count[chat_id] = 0

        if "유튜브" in text or "영상" in text:
            answer = search_youtube_video(text)
        else:
            answer = ask_gpt(text)

        # 질문 수 카운트
        user_question_count[chat_id] += 1
        remaining = MAX_QUESTIONS - user_question_count[chat_id]
        if remaining <= 0:
            remaining = "무제한 (GPT-3.5로 전환)"

        final_answer = f"{answer}\n\n(오늘 남은 질문: {remaining})"
        send_message(chat_id, final_answer)

    except Exception as e:
        print(f"에러 발생: {e}")
        try:
            send_message(chat_id, "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.")
        except:
            pass

    return {"ok": True}