from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.llms import GradientLLM

import moe_scrape
import asyncio

import sqlite3


from openai import OpenAI

client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of the United States?"},
        {"role": "system", "content": "The capital of the United States is Washington, D.C."},
    ],
)

app = FastAPI()

def scrape_env_news():
    pass

env_news_tool = Tool(
    name="環境省ニュース",
    func=scrape_env_news,
    description="環境省のホームページから過去3日分のニュース記事を取得します"
)

def get_top_5():
    # 本来は"https://funky802.com/hot100/"から呼び出す。ここではダミーデータを返す
    """ヒット曲のランキングを取得して返します"""
    ranks = [
        {'rank': 1, 'title': 'I wonder', 'artist': 'Da-iCE'},
        {'rank': 2, 'title': '会いに行くのに', 'artist': 'あいみょん'},
        {'rank': 3, 'title': '毎日', 'artist': '米津玄師'},
        {'rank': 4, 'title': 'CYAN', 'artist': 'フレデリック'},
        {'rank': 5, 'title': 'Bling-Bang-Bang-Born', 'artist': 'Creepy Nuts'}
    ]
    return ranks

def adjust_ranking(ranks, preference):
    """ユーザーの嗜好に基づいて、ランキングを調整します"""
    for song in ranks:
        if song['artist'] == preference:
            song['rank'] = 1
        else:
            song['rank'] += 1
    return ranks

tools = [
    Tool(
        name="FM802 OSAKAN HOT 100 Top 5",
        func=get_top_5,
        description="Get the top 5 songs from FM802 OSAKAN HOT 100"
    ),
    Tool(
        name="Adjust Ranking",
        func=adjust_ranking,
        description="Adjust the ranking based on user preference"
    )
]

llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    verbose=True
    )

@app.get("/tops")
async def get_tops():
    preference = "あいみょん" # 本来はメモリから呼び出す
    result = agent.run(f"ヒット曲のランキングを取得してください。{ranks}次に、そのランキングをユーザーの嗜好:{preference}に基づいてランクを調整してください")
    return result

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

