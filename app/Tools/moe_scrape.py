# 環境省から広報記事を取得します

from typing import List
from datetime import datetime, timedelta
import re
import asyncio
from playwright.async_api import async_playwright, ElementHandle

import requests
from bs4 import BeautifulSoup

from ..Models.database import set_doc
from ..Models.articles import Article


from dataclasses import asdict

環境省プレスリリース一覧 = 'https://www.env.go.jp/press/index.html'


def decide_get_press_release() -> bool:
    res = requests.get(環境省プレスリリース一覧)
    soup = BeautifulSoup(res.text, 'html.parser')
    heading = soup.select('.p-press-release-list__heading')
    date_str = heading[0].text

    match = re.search(r'(\d{4})年(\d{2})月(\d{2})日発表', date_str)
    
    if match is None:raise ValueError("日付形式が正しくありません")

    year, month, day = match.groups()
    date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")

    return date.date() == datetime.now().date()

def 特定期間のnews_idを取得(期間:int) -> List[str]:
    res = requests.get(環境省プレスリリース一覧)
    soup = BeautifulSoup(res.text, 'html.parser')
    blocks = soup.select('.p-press-release-list__block')

    news_id_list = []
    for block in blocks:
        release_date_tag = block.select_one('.p-press-release-list__heading')
        if release_date_tag is None: continue

        release_date_str = release_date_tag.text
        release_date = datetime.strptime(release_date_str, '%Y年%m月%d日発表')
        if release_date.date() < datetime.now().date() - timedelta(days=期間):
            break

        link_set = block.select('.c-news-link__link')
        for link in link_set:
            href = link.get('href')
            news_id_list.append(href)

    print(news_id_list)

    return news_id_list

async def get_news(article_id_list:List[str]) -> List[Article]:
    article_list:list[Article] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        for article_id in article_id_list:
            article = Article()

            page = await browser.new_page()

            full_link = f'https://www.env.go.jp{article_id}'
            await page.goto(full_link)

            body_elem = await page.query_selector('.c-component')

            if body_elem is None: raise ValueError("記事本文が取得できません")

            article.article_id = 'moe' + article_id.replace('/','_')

            body = await body_elem.inner_text()
            article.content = body

            release_date_elem = await page.query_selector('.p-press-release-material__date')
            release_date_str = await release_date_elem.inner_text() if release_date_elem is not None else None
            release_date = datetime.strptime(release_date_str, '%Y年%m月%d日') if release_date_str is not None else None
            article.publish_date = release_date

            article.source = "環境省"

            # tag_elem = await body_elem.query_selector('.p-news-link__tag')
            # tag = await tag_elem.inner_text() if tag_elem is not None else None
            # article.keywords = [tag] if tag is not None else []

            title_elem = await body_elem.query_selector('.p-press-release-material__heading')
            title = await title_elem.inner_text() if title_elem is not None else None
            article.title = title if title is not None else ""

            summary_area = await body_elem.query_selector('.c-component__bg-area')
            summary = await summary_area.inner_text() if summary_area is not None else None
            article.summary = summary

            article_list.append(article)
    
    return article_list

    
def main():
    news_list =  特定期間のnews_idを取得(5)
    news = asyncio.run(get_news(news_list))
    for n in news:
        set_doc('articles',asdict(n))

# if __name__ == '__main__':
#     main()