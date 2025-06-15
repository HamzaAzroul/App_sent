import requests
import pandas as pd
import praw
#from models import Base, Review, Message, Source
from sqlalchemy.orm import Session
import matplotlib.pyplot as plt
from nltk.sentiment import SentimentIntensityAnalyzer


def fetch_live_tweets(keyword: str, max_results=1000) -> pd.DataFrame:
    BEARER_TOKEN = "TON_BEARER_TOKEN_ICI"
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    query_params = {
        'query': keyword,
        'max_results': max_results,
        'tweet.fields': 'created_at,public_metrics,lang',
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    response = requests.get(search_url, headers=headers, params=query_params)
    
    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json().get("data", [])
    tweets = [{
        "Source": "twitter",
        "Text": tweet["text"],
        "Datetime": tweet["created_at"],
        "LikeCount": tweet.get("public_metrics", {}).get("like_count", 0),
        "Language": tweet.get("lang", "und")
    } for tweet in data]

    return pd.DataFrame(tweets)

def fetch_live_reddit_comments(keyword: str, max_comments=1000) -> pd.DataFrame:
    reddit = praw.Reddit(
        client_id="JnJyM4bGNliB7-pfld1Kpg",
        client_secret="iUwGdjTOVkFiMd9_JfkrNaPQJZW-vA",
        user_agent="sentiment-analysis-app"
    )
    
    comments_data = []
    for comment in reddit.subreddit("all").search(keyword, limit=max_comments):
        comments_data.append({
            "Source": "reddit",
            "Text": comment.title + " " + comment.selftext,
            "Datetime": str(comment.created_utc),
            "LikeCount": comment.score,
            "Language": "en"  # facultatif ici
        })
    return pd.DataFrame(comments_data)


# MAJ
def analyze_and_store(df: pd.DataFrame, source_name: str, db: Session):
    sid = SentimentIntensityAnalyzer()
    source = db.query(Source).filter(Source.name == source_name).first()
    if not source:
        source = Source(name=source_name)
        db.add(source)
        db.commit()
        db.refresh(source)
    
    for _, row in df.iterrows():
        scores = sid.polarity_scores(row['Text'])
        sentiment = sentiment(
            source_id=source.id,
            text=row['Text'],
            clean_tweet=row['Text'],  # mettre ici le nettoyage si existant
            sentiment='pos' if scores['compound'] > 0 else 'neg' if scores['compound'] < 0 else 'neu',
            compound_score=scores['compound'],
            like_count=row.get('LikeCount'),
            language=row.get('Language'),
            hashtag=row.get('hashtag'),
            user_info=row.get('User')
        )
        db.add(sentiment)
    db.commit()
  
def plot_sentiment_distribution(df):
    sentiment_counts = df['Sentiment'].value_counts()
    sentiment_counts.plot(kind='bar', color=['green', 'red', 'blue'])
    plt.title('Sentiment Distribution')
    plt.xlabel('Sentiment')
    plt.ylabel('Number of Entries')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()

# def plot_source_distribution(df):
#     source_counts = df['Source'].value_counts()
#     source_counts.plot(kind='bar', color=['green', 'red', 'blue'])
#     plt.title('Source Distribution')
#     plt.xlabel('Source')
#     plt.ylabel('Number of Entries')
#     plt.xticks(rotation=0)
#     plt.tight_layout()
#     plt.show()