from typing import List
from datetime import datetime, timedelta
import re
import asyncio
from playwright.async_api import async_playwright, ElementHandle

import requests
from bs4 import BeautifulSoup

import sqlite3

環境省プレスリリース一覧 = 'https://www.env.go.jp/press/index.html'


class News:
    def __init__(self, release_date:datetime|None, tag:str|None, title:str|None, summary:str|None, body:str):
        self.release_date = release_date
        self.tag = tag
        self.title = title
        self.summary = summary
        self.body = body

    def __str__(self):
        return f'{self.release_date} {self.title} {self.body}'

    def to_dict(self):
        return {
            'release_date': self.release_date,
            'tag': self.tag,
            'title': self.title,
            'summary': self.summary,
            'body': self.body
        }

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

    return news_id_list

async def get_news(news_id_list:List[str]) -> List[News]:
    news_list = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        for news_id in news_id_list:
            page = await browser.new_page()

            full_link = f'https://www.env.go.jp{news_id}'
            await page.goto(full_link)

            body_elem = await page.query_selector('.c-component')

            if body_elem is None: raise ValueError("記事本文が取得できません")

            body = await body_elem.inner_text()

            release_date_elem = await page.query_selector('.p-press-release-material__date')
            release_date_str = await release_date_elem.inner_text() if release_date_elem is not None else None
            release_date = datetime.strptime(release_date_str, '%Y年%m月%d日') if release_date_str is not None else None

            tag_elem = await body_elem.query_selector('.p-news-link__tag')
            tag = await tag_elem.inner_text() if tag_elem is not None else None

            title_elem = await body_elem.query_selector('.p-press-release-material__heading')
            title = await title_elem.inner_text() if title_elem is not None else None

            summary_area = await body_elem.query_selector('.c-component__bg-area')
            summary = await summary_area.inner_text() if summary_area is not None else None

            news_list.append(News(release_date, tag, title, summary, body))
    
    return news_list


def save_news_to_sqlite(news_list:List[News]):
    columns = ('release_date', 'tag', 'title', 'summary', 'body')

    conn = sqlite3.connect('articles.db')
    c = conn.cursor()

    c.execute(f'CREATE TABLE IF NOT EXISTS articles ({", ".join([f"{col} text" for col in columns])})')

    placeholders = ", ".join(["?"] * len(columns))
    for news in news_list:
        values = [news.to_dict()[col] for col in columns]
        c.execute(f"INSERT INTO articles VALUES ({placeholders})", values)

    conn.commit()
    conn.close()

    
def main():
    news_list =  特定期間のnews_idを取得(4)
    news = asyncio.run(get_news(news_list))
    save_news_to_sqlite(news)


if __name__ == '__main__':
    main()