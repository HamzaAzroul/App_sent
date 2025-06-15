import pandas as pd
import re
import nltk
import streamlit as st

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:  # Corrected: Use LookupError
    print("Downloading 'punkt' tokenizer...") # Optional: for feedback
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('sentiment/vader_lexicon.zip') 
except LookupError:
    try:
       nltk.data.find('sentiment/vader_lexicon.xml') 
    except LookupError:
       print("Downloading 'vader_lexicon'...") 
       nltk.download('vader_lexicon', quiet=True) 

from nltk.sentiment.vader import SentimentIntensityAnalyzer
# --- Data Loading ---
def load_data(file_path='chatgpt1.csv'):
    try:
        df = pd.read_csv(file_path)
        return df, None
    except FileNotFoundError:
        return pd.DataFrame(), f"Error: {file_path} not found."
    except Exception as e:
        return pd.DataFrame(), f"Error loading {file_path}: {e}"
def filter_data_by_keywords_and_language(df, selected_keywords, language='en'):
    if df is None or df.empty or not selected_keywords:
        return pd.DataFrame()
    if 'Language' not in df.columns or 'hashtag' not in df.columns:
        return pd.DataFrame()
    pattern = '|'.join([re.escape(kw.lower()) for kw in selected_keywords])
    df_filtered = df[
        (df['Language'].astype(str).str.lower() == language.lower()) &
        (df['hashtag'].astype(str).str.lower().str.contains(pattern, na=False))
    ].copy()
    return df_filtered
# --- Text Cleaning Steps (callable individually) ---
def step_deduplicate_and_lowercase(df_input):
    if df_input is None or 'Text' not in df_input.columns: return df_input
    df = df_input.copy().drop_duplicates(subset=['Text'])
    df['clean_tweet'] = df['Text'].astype(str).str.lower()
    return df
def step_remove_urls(df_input):
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet'].str.replace(r"http\S+", "", regex=True)
    return df
def step_remove_mentions(df_input):
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet'].str.replace(r"@\S+", "", regex=True)
    return df
def _remove_prefix_words_helper(text, prefix): 
    if not isinstance(text, str): return ""
    words = text.split()
    processed_words = [word if not word.startswith(prefix) else ' ' for word in words]
    return re.sub(r'\s+', ' ', " ".join(processed_words)).strip()
def step_remove_hashtags_words(df_input):
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet'].apply(lambda x: _remove_prefix_words_helper(x, '#'))
    return df
def step_remove_tickers_words(df_input):
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet'].apply(lambda x: _remove_prefix_words_helper(x, '$'))
    return df
def step_remove_punctuation_numbers_special(df_input):
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet'].str.replace(r'[^a-zA-Z\s]', '', regex=True)
    df['clean_tweet'] = df['clean_tweet'].str.replace(r'\s+', ' ', regex=True).str.strip()
    return df
def step_tokenize_tweets(df_input): 
    if df_input is None or 'clean_tweet' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet_tokens'] = df['clean_tweet'].str.split()
    return df
def step_remove_short_words_from_tokens(df_input):
    if df_input is None or 'clean_tweet_tokens' not in df_input.columns: return df_input
    df = df_input.copy()
    def filter_short_words(token_list):
        return [word for word in token_list if len(word) >= 2] if isinstance(token_list, list) else []
    df['clean_tweet_tokens'] = df['clean_tweet_tokens'].apply(filter_short_words)
    return df
def step_rejoin_tokens(df_input):
    if df_input is None or 'clean_tweet_tokens' not in df_input.columns: return df_input
    df = df_input.copy()
    df['clean_tweet'] = df['clean_tweet_tokens'].apply(lambda x: ' '.join(x) if isinstance(x, list) else x)
    return df
# --- Sentiment Analysis ---
@st.cache_resource
def get_sentiment_analyzer():
    return SentimentIntensityAnalyzer()
@st.cache_data
def analyze_sentiment_vader(df_input_processed):
    if df_input_processed is None or df_input_processed.empty or 'clean_tweet' not in df_input_processed.columns:
        return df_input_processed
    df = df_input_processed.copy()
    sia = get_sentiment_analyzer()
    df['clean_tweet'] = df['clean_tweet'].astype(str).fillna('')
    sentiments = []
    compound_scores = []
    for text_cleaned in df['clean_tweet']:
        scores = sia.polarity_scores(text_cleaned)
        compound = scores['compound']
        compound_scores.append(compound)
        if compound >= 0.05: sentiment = 'Positive'
        elif compound <= -0.05: sentiment = 'Negative'
        else: sentiment = 'Neutral'
        sentiments.append(sentiment)
    df['Sentiment'] = sentiments
    df['Compound_Score'] = compound_scores
    return df
