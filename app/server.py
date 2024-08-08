from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.llms import GradientLLM

import sqlite3
from datetime import datetime, timedelta

from database import fetch_recent_articles

from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of the United States?"},
        {"role": "system", "content": "The capital of the United States is Washington, D.C."},
    ],
)

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Nuxtのデフォルトポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/articles")
async def get_articles():
    conn = sqlite3.connect('sustainai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles ORDER BY fetch_date DESC")
    articles = cursor.fetchall()
    conn.close()
    
    # 結果をディクショナリのリストに変換
    articles_list = []
    for article in articles:
        articles_list.append({
            "id": article[0],
            "fetch_date": article[1],
            "source": article[2],
            "title": article[3],
            "keywords": article[4],
            "summary": article[5],
            "content": article[6],
            "ai_interest_level": article[7],
            "user_interest_level": article[8]
        })
    
    return {"articles": articles_list}

def getRecentlyArticles():
    '''一週間以内に取得したデータを返します'''
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    # データベースに接続してクエリを実行
    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()
        c.execute('''
            SELECT * FROM articles
            WHERE release_date >= ?
        ''', (one_week_ago.isoformat(),))

        # 結果を取得
        rows = c.fetchall()

    return rows


tools = [
    Tool(
        name="一週間以内に取得したデータを返す",
        func=getRecentlyArticles,
        description="一週間以内に取得したデータを返します"
    )
]

llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    verbose=True
    )

model = ChatOpenAI(model="gpt-3.5-turbo-0125")

template = """
以下は環境省のニュース記事のリストです:
{news_items}

これらの記事のタイトルとリンクを箇条書きでリストアップしてください。
"""

prompt = PromptTemplate(
    input_variables=["news_items"],
    template=template
)

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

@app.get("/articles")
async def articles():
    rows = fetch_recent_articles(db_path='articles.db',days=7)
    return rows


add_routes(
    app,
    prompt | model,
    path="/env-news"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

