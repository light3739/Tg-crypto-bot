import requests
from datetime import datetime
from translate import Translator
import psycopg2
from config import DATABASE_URL


def fetch_latest_news(api_key):
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=blockchain&apikey={api_key}'
    response = requests.get(url)
    data = response.json()

    if 'feed' in data and data['feed']:
        latest_article = data['feed'][0]
        title = latest_article.get('title', 'Нет заголовка')
        summary = latest_article.get('summary', 'Нет краткого содержания')
        article_url = latest_article.get('url', 'Нет URL')
        time_published = latest_article.get('time_published', 'Нет времени публикации')
        authors = latest_article.get('authors', 'Нет авторов')

        if time_published != 'Нет времени публикации':
            dt = datetime.strptime(time_published, '%Y%m%dT%H%M%S')
            human_readable_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            human_readable_date = 'Нет времени публикации'

        translator = Translator(to_lang="ru")
        title_ru = translator.translate(title)
        summary_ru = translator.translate(summary)

        simplified_message = (
            f"{title_ru}\n\n{summary_ru}[Читать далее]({article_url}\n\n{human_readable_date}\n\n{authors})"
        )

        return {
            "title": title,
            "summary": summary,
            "article_url": article_url,
            "time_published": dt,
            "authors": authors,
            "simplified_message": simplified_message
        }
    else:
        return None


def save_news_to_db(news_article):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO crypto_news (title, summary, article_url, time_published, authors)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (title) DO NOTHING
    """, (news_article["title"], news_article["summary"], news_article["article_url"], news_article["time_published"],
          news_article["authors"]))
    conn.commit()
    cur.close()
    conn.close()


def get_last_fetched_news_time():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT MAX(fetched_at) FROM crypto_news")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None
