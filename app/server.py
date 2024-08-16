from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
# from langchain.agents import initialize_agent, Tool, AgentType

from typing import Optional, List

# from .database import Article, fetch_recent_articles
from .Models.articles import Article
from .Models.users import User
from .Models.preferences import Preference

from .Models.database import setup_database, get_doc, get_docs, set_doc, update_doc

from dataclasses import asdict

from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Nuxtのデフォルトポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = ChatOpenAI(model="gpt-4o-mini")


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

# 完成
@app.get("/setup_tables")
async def setup_tables():
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
        result = chain.invoke(input={"content":item.content})
        keywords_str = str(result.content)

        set_doc('articles',{'article_id':item.article_id,'keywords':keywords_str})

    return 'OK'

# ユーザーの嗜好に基づいて、記事をスコアリング
def set_score_to_articles():
    user_id = "user1"
    
    # 記事一覧から、カレントユーザーの嗜好がまだ評価されていない記事を取り出す
    preferences_of_current_user:List[Preference] = get_docs("preferences",("user_id","==",user_id))
    graded_article_ids = [ p.article_id for p in preferences_of_current_user]
    articles:List[Article] = get_docs("articles",("article_id","NOT IN",graded_article_ids))


    # preference.dbのuser1から、そのユーザーの嗜好性（キーワードと±10点のスコア）を取得
    user:User = get_doc("preferences",user_id)
    preference = user.preference
    
    # ユーザーの嗜好性に基づいて、記事をスコアリング
    template = """
    あなたはユーザーの関心事に基づいてニュース記事を採点するAIです。

    # 要望
    ユーザーは大量の記事から、自分にとって関心のある記事だけをフィルターをかけて読みたいと思っています。
    ユーザーは、普段は0点以上の記事を読みますが、時間がない時にはプラス点数のついた記事だけを読みます。
    マイナス点数がついた記事は邪魔なので、普段は表示しません。
    このような使い方ができるよう、ユーザーの関心事に合わせて、ニュース記事に採点してください。

    # 採点方法
    ユーザーの関心については以下のようなキーワードと関心度合いのペアで渡します。
    例:'地域経済:2,製造業:1,補助金:-2'
    各キーワードに対する関心度合いは-2,-1,0,1,2の5段階で、プラスは関心があるのでぜひ表示してほしいトピック、マイナスは邪魔なので除外してほしいトピックを示しています。
    単純に単語の有無で判断するのではなく、意味的な距離や上位・下位概念も加味してください

    # データ
    文章:{content}
    ユーザーの関心:{preference}

    # 出力
    -2から2の5段階評価です。
    -2はユーザーにとって邪魔なので表示させない、0は中立、2はユーザーにとって重要です。
    数値だけを出力してください
    """

    prompt = PromptTemplate.from_template(template=template)

    chain = prompt | model

    for article in articles:
        new_pref:Preference = Preference()
        result = chain.invoke(input={"content":article.content,"preference":preference})
        new_pref.ai_score = int(str(result.content))

        # DBへの書き込み。本当はまとめてやるべき
        set_doc("preferences", asdict(new_pref))


# articlesを取得。デフォルトはユーザー嗜好が0以上のみ
@app.get("/articles")
async def articles(all:Optional[bool] = False):
    user_id = "user1"
    if all:
        return get_docs("articles",None)
    else:
        current_user_preferences:List[Preference] = get_docs("preferences",("user_id","==",user_id))
        plus_article_ids = [p.article_id for p in current_user_preferences if p.ai_score >= 0]
        return get_docs("articles",("article_id","IN",plus_article_ids))


### ユーザーが評価した点数でAIをトレーニング
@app.post("/articles_training/")
async def articles_training(preferences:List[Preference]):
    print('received data:',preferences)

    return 'OK'



# add_routes(
#     app,
#     prompt | model,
#     path="/question"
# )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

