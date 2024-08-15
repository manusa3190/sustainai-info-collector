from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType

from typing import Optional, List, Type, Dict, Union

import sqlite3
from datetime import datetime, timedelta

# from .database import Article, fetch_recent_articles
from .Models.articles import Article, fetch_recent_articles, getItems, updateItem

from .Models.preferences import Preference, setup_database as initialize_preferences, adjust_score

from dataclasses import dataclass, field, fields

import json

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

llm = ChatOpenAI(model="gpt-4o-mini")

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    verbose=True
    )

model = ChatOpenAI(model="gpt-4o-mini")

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

# 完成
@app.get("/setup_tables")
async def setup_tables():
    from .Models.database import setup_database
    setup_database()

# 完成
@app.get("/scrape_moe")
def scrape_moe():
    print('scrape moe run!')
    from .Tools.moe_scrape import main
    main()
    print('scrape moe done!')

# 完成
@app.post("/extract_keywords_with_ai")
async def extract_keywords_with_ai():
    # DBからデータ取り出し"
    from .Models.database import get_docs, set_doc
    items:List[Article] = get_docs('articles',("keywords","==","[]"))

    # プロンプトの作成
    template = """
        あなたにニュース記事を渡しますので、キーワードを5つまで抽出してください。
        
        # データ
        記事:{content}

        # 出力
        抽出したキーワードは配列形式で返してください。マークアップは不要です。
        例:["環境","水質汚染"]
    """

    for item in items:
        if(item.content is None):continue

        # AIによるキーワード抽出
        prompt = PromptTemplate.from_template(
            template=template
        )

        chain = prompt | model
        result = chain.invoke(input=item.content)
        keywords_str = result.content

        set_doc('articles',{'article_id':item.article_id,'keywords':keywords_str})

    return 'OK'

# ユーザーの嗜好に基づいて、記事をスコアリング
def set_score_to_articles():
    # preference.dbのuser1から、そのユーザーの嗜好性（キーワードと±10点のスコア）を取得

    # ユーザーの嗜好性に基づいて、記事をスコアリング

    # DBへの書き込み
    pass

# articlesを取得
@app.get("/articles")
async def articles():
    field_names = [ f.name for f in fields(Article)]
    # print(fieldNames)
    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM articles")
        rows = c.fetchall()

        records = [
            {field_name: value for field_name, value in zip(field_names, row)}
            for row in rows
        ]
        return records

### ユーザーが評価した点数でAIをトレーニング
@dataclass
class Item:
    id:str
    user_scored_interest_level: str


from typing import List
@app.post("/articles_training/")
async def articles_training(items:List[Item]):
    print('received data:',items)

    return 'OK'

### ユーザーが好むor好まないキーワードを保存
@app.get('/setup_pref')
async def setup_pref():
    initialize_preferences('user1')

add_routes(
    app,
    prompt | model,
    path="/question"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

