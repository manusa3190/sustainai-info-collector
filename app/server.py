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

@app.get("/env-news")
async def res_env_news():
    # moe_news.dbの中身を取得して返す
    conn = sqlite3.connect('moe_news.db')
    c = conn.cursor()
    c.execute('SELECT * FROM articles')
    news_list = c.fetchall()
    conn.close()

    news_list = [dict(zip(['release_date', 'tag', 'title', 'summary', 'body'], news)) for news in news_list]

    print(news_list)
    return news_list



add_routes(
    app,
    prompt | model,
    path="/env-news"
)

if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    data = getRecentlyArticles()
    print(data)

