import requests
from datetime import datetime
from translate import Translator

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

        # Convert the published time to a human-readable format
        if time_published != 'Нет времени публикации':
            dt = datetime.strptime(time_published, '%Y%m%dT%H%M%S')
            human_readable_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            human_readable_date = 'Нет времени публикации'

        # Translate the title and summary to Russian
        translator = Translator(to_lang="ru")
        title_ru = translator.translate(title)
        summary_ru = translator.translate(summary)

        # Simplify the message to exclude "Title", "Summary", and "URL"
        simplified_message = (
            f"{title_ru}\n\n{summary_ru}[Читать далее]({article_url}\n\n{human_readable_date}\n\n{authors})"
        )

        return simplified_message
    else:
        return "Новостные статьи не найдены."
