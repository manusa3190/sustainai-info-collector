from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
# from langchain.agents import initialize_agent, Tool, AgentType

from typing import Optional, List, Dict, TypedDict, Any

import json
from datetime import datetime, timedelta

# from .database import Article, fetch_recent_articles
from .Models.articles import Article
from .Models.users import User
from .Models.preferences import Preference

from .Models.database import setup_database, get_doc, get_docs, set_doc, set_docs, update_doc

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

        set_doc('articles',{'row_num':item.row_num,'keywords':keywords_str})

    return 'OK'

#【完成】ユーザーの嗜好に基づいて、記事をスコアリング
@app.get("/set_score_to_articles")
def set_score_to_articles()->None:
    users:List[User] = get_docs('users')

    for user in users:
        user_id = user.user_id
        
        # 記事一覧から、カレントユーザーの嗜好がまだ評価されていない記事を取り出す
        preferences_of_current_user:List[Preference] = get_docs("preferences",("user_id","==",user_id))
        graded_article_ids = [ p.article_id for p in preferences_of_current_user]
        articles:List[Article] = get_docs("articles",("article_id","NOT IN",graded_article_ids))
        
        # ユーザーの嗜好性に基づいて、記事をスコアリング
        template = """
        あなたはユーザーの関心事に基づいてニュース記事を採点するAIです。

        # 要望
        ユーザーは大量の記事から、自分にとって重要な記事だけをフィルターをかけて読みたいと思っています。
        ユーザーは、普段は3点以上の記事を読みますが、時間がない時には4点以上のついた記事だけを読みます。
        2点以下がついた記事はユーザーにとって関係性がないので、普段は表示しません。
        このような使い方ができるよう、ユーザーの関心事に合わせて、ニュース記事に採点してください。

        # 採点方法
        ユーザーの関心については以下のようなキーワードと関心度合いのペアで渡します。
        例:'地域経済:2,製造業:1,補助金:-2'
        各キーワードに対する関心度合いは-2,-1,0,1,2の5段階で、プラスは関心があるので重要と採点してほしいトピック、マイナスは関係性がないので減点してほしいトピックを示しています。
        単純に単語の有無で判断するのではなく、意味的な距離や上位・下位概念も加味してください。

        # データ
        文章:{content}
        ユーザーの関心:{preference}

        # 出力
        1から5の5段階評価です。
        1はユーザーにとって関係性が低い、3は中立、2はユーザーにとって重要な記事を意味します。
        数値だけを出力してください
        """

        prompt = PromptTemplate.from_template(template=template)

        chain = prompt | model

        data = []
        for article in articles:
            result = chain.invoke(input={"content":article.content,"preference":user.preference})

            new_pref:Preference = Preference(
                user_id = user_id,
                article_id = article.article_id,
                ai_score = result.content,
                user_score = None
            )
            data.append( asdict(new_pref) )

        # DBへの書き込み
        set_docs("preferences",data)


#【完成】 articlesを取得。デフォルトはユーザー嗜好が0以上のみ。all=Trueなら全て取得
@app.get("/articles")
async def articles(user_id:str, source:str, acquition_duration:int,ai_score:int,user_score:int,word:str):

    today = datetime.today()
    acquition_after_date = today - timedelta(days=30*acquition_duration)
    acquition_after_date = acquition_after_date.strftime('%Y-%m-%d')

    articles = get_docs("articles",("acquition_date",">",acquition_after_date))

    # sourceでフィルタ
    source = json.loads(source)    
    articles = [ a for a in articles if a.source in source ]

    # wordでフィルタ
    articles = [ a for a in articles if word in a.content ]

    # ユーザーの嗜好性を取得
    current_user_preferences:List[Preference] = get_docs("preferences",("user_id","==",user_id))
    # article_idをkeyにしたdictに変換
    preferences_dict = {pref.article_id: pref for pref in current_user_preferences}

    # 各記事にcurrentUserのai_scoreとuser_scoreをつける
    records = [
        asdict(art) | {
            "preference_id":preferences_dict.get(art.article_id, Preference()).preference_id,
            "ai_score": preferences_dict.get(art.article_id, Preference()).ai_score,
            "user_score": preferences_dict.get(art.article_id, Preference()).user_score
        }
        for art in articles
    ]

    # ai_scoreでフィルタ
    records = [ r for r in records if r["ai_score"] >= ai_score]

    # user_scoreでフィルタ
    if user_score == 0: return records

    res = []    
    for r in records:
        if r["user_score"] is not None:
            if r["user_score"] >= user_score:
                res.append(r)
    return res


@app.get("/user")
async def user(user_id:int):
    user = get_doc('users',user_id)
    return user

@app.post("/user_post")
async def user_post(data:Dict):
    set_doc('users',data)
    return {'result':'success','data':data}

@app.get("/article")
async def article(article_id:str):
    user_id = 1
    article:Article = get_doc("articles",article_id)
    current_user_preferences:Preference = get_docs("preferences",("user_id",'==',user_id))
    preferences_dict = {pref.article_id: pref for pref in current_user_preferences}
    res = asdict(article) | {
            "preference_id":preferences_dict.get(article.article_id, Preference()).preference_id,
            "ai_score"  : preferences_dict.get(article.article_id, Preference()).ai_score,
            "user_score": preferences_dict.get(article.article_id, Preference()).user_score
        }
    return res

### ユーザーが評価した点数でAIをトレーニング
class PreferenceData(TypedDict):
    preference_id: int
    user_score: int
    preference_adjust: Dict[str, int]

@app.post("/training/")
async def training(data:Dict[str,str]):
    # preferenceにuser_scoreを書き込み
    preference:Preference = get_doc("preferences",data["preference_id"])
    preference.user_score = int(data["user_score"])
    set_doc("preferences", asdict(preference))

    # userのpreferenceの点数調整
    user:User = get_doc("users",preference.user_id)
    user_preference:Dict[str,int] = json.loads( user.preference)
    
    preference_adjust:Dict[str,int] = json.loads(data["preference_adjust"])

    for k,v in preference_adjust.items():
        p = user_preference.get(k)
        user_preference[k] = p + v if p is not None else v
    
    user.preference = json.dumps(user_preference,ensure_ascii=False)
    set_doc("users", asdict(user))

    return {
        'result':'success',
        'data':{
            'preference_id': preference.preference_id,
            'ai_score':preference.ai_score,
            'user_score':preference.user_score}
    }



# add_routes(
#     app,
#     prompt | model,
#     path="/question"
# )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

