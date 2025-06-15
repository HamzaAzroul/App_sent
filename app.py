import streamlit as st
import pandas as pd
import plotly.express as px
import hydralit_components as hc
#import matplotlib.pyplot as plt
from prometheus_client import start_http_server, Summary, Counter, generate_latest, multiprocess, CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry
from prometheus_client.exposition import generate_latest
import threading
from fastapi import FastAPI
from fastapi.responses import Response
import datetime
#from prometheus_flask_exporter import PrometheusMetrics
from utils import fetch_live_reddit_comments, fetch_live_tweets, plot_sentiment_distribution
from processing import (
    load_data,
    filter_data_by_keywords_and_language,
    # Individual preprocessing steps
    step_deduplicate_and_lowercase,
    step_remove_urls,
    step_remove_mentions,
    step_remove_hashtags_words,
    step_remove_tickers_words,
    step_remove_punctuation_numbers_special,
    step_tokenize_tweets,
    step_remove_short_words_from_tokens,
    step_rejoin_tokens,
    # Sentiment analysis function
    analyze_sentiment_vader
)

app = FastAPI()

REQUEST_TIME = None
TWEET_ANALYSIS_COUNT = None
registry = None
def get_metrics():
    global REQUEST_TIME, TWEET_ANALYSIS_COUNT, registry
    if REQUEST_TIME is None or TWEET_ANALYSIS_COUNT is None:
        registry = CollectorRegistry()
        REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=registry)
        TWEET_ANALYSIS_COUNT = Counter('tweet_analysis_count', 'Number of tweets analyzed', registry=registry)
    return REQUEST_TIME, TWEET_ANALYSIS_COUNT, registry

REQUEST_TIME, TWEET_ANALYSIS_COUNT, registry = get_metrics()
@app.get("/metrics")
def metrics():
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

@REQUEST_TIME.time()
def analyze_sentiment_with_metrics(df):
    df = preprocess_dataframe(df)
    df = analyze_sentiment_vader(df)
    TWEET_ANALYSIS_COUNT.inc(len(df))  # Count each analyzed tweet
    return df

def start_prometheus_exporter():
    start_http_server(8000)  # Exposes metrics at http://localhost:8000/metrics
# Run this once
if 'prometheus_started' not in st.session_state:
    threading.Thread(target=start_prometheus_exporter, daemon=True).start()
    st.session_state.prometheus_started = True
# --- UI: Navigation Bar ---
def navBar():
    menu_data = [
        {'id': "Scrape Data From Twitter", 'icon': "fab fa-twitter", 'label': "Récupérer les données de Twitter"},
        {'id': "Sentiment Analysis", 'icon': "far fa-chart-bar", 'label': "Analyse des sentiments"},
        {'id': "Sentiment Analysis live", 'icon': "far fa-chart-bar", 'label': "Analyse des sentiments en temps reel"}
    ]
    over_theme = {'txc_inactive': '#FFFFFF'}
    menu_id = hc.nav_bar(menu_definition=menu_data, override_theme=over_theme, first_select=0)
    return menu_id

st.set_page_config(page_title='Sentiment Analyzer', layout="wide")
def preprocess_dataframe(df):
    df = step_deduplicate_and_lowercase(df)
    df = step_remove_urls(df)
    df = step_remove_mentions(df)
    df = step_remove_hashtags_words(df)
    df = step_remove_tickers_words(df)
    df = step_remove_punctuation_numbers_special(df)
    df = step_tokenize_tweets(df)
    df = step_remove_short_words_from_tokens(df)
    df = step_rejoin_tokens(df)
    if 'clean_tweet_tokens' in df.columns:
        df.drop(columns=['clean_tweet_tokens'], inplace=True)
    return df
def display_analysis_results(df_analyzed, selected_keywords=None):
    # Reuse most of the else block visualization and display here
    if df_analyzed.empty or 'Sentiment' not in df_analyzed.columns:
        st.warning("L'analyse n'a produit aucun résultat pertinent.")
        return 
    # Display dataframe with optional columns
    with st.expander('plus de détails sur les tweets analysés'):
        cols_to_display = ['Text', 'clean_tweet', 'Sentiment', 'Compound_Score']
        optional_cols = ['Username', 'LikeCount', 'Language', 'hashtag', 'User']
        for col in optional_cols:
            if col in df_analyzed.columns:
                cols_to_display.append(col)
        existing_cols_display = [col for col in cols_to_display if col in df_analyzed.columns]
        st.dataframe(df_analyzed[existing_cols_display])
        cols_to_csv = ['clean_tweet', 'Sentiment', 'Compound_Score']
        existing_cols_csv = [col for col in cols_to_csv if col in df_analyzed.columns]
        if existing_cols_csv:
            csv_data = df_analyzed[existing_cols_csv].to_csv(index=False).encode('utf-8')
            st.download_button(label='Télécharger CSV Analysé', data=csv_data, file_name='sentiments_data.csv', mime='text/csv')

    # Stats & visualization
    st.write('------------------------------')
    title_text = f'Analyse des Sentiments'
    if selected_keywords:
        title_text += f' sur :green[{" & ".join(selected_keywords)}]'
    st.title(title_text)
    st.write('------------------------------')

    sentiment_counts = df_analyzed['Sentiment'].value_counts()
    total_analyzed_count = sentiment_counts.sum()
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    if total_analyzed_count > 0:
        pos_perc = (sentiment_counts.get('Positive', 0) / total_analyzed_count) * 100
        neg_perc = (sentiment_counts.get('Negative', 0) / total_analyzed_count) * 100
        neu_perc = (sentiment_counts.get('Neutral', 0) / total_analyzed_count) * 100
        stat_col1.subheader(f"Positif (%): {pos_perc:.2f}%")
        stat_col2.subheader(f"Négatif (%): {neg_perc:.2f}%")
        stat_col3.subheader(f"Neutre (%): {neu_perc:.2f}%")
    else:
        stat_col1.subheader(f"Positif (%): N/A")
        stat_col2.subheader(f"Négatif (%): N/A")
        stat_col3.subheader(f"Neutre (%): N/A")
    stat_col4.subheader(f"Total Tweets: {len(df_analyzed)}")
    st.write('------------------------------')
    st.subheader('Visualisation du Résultat')
    with st.spinner("Génération des graphiques...."):
        if not sentiment_counts.empty:
            df_grouped_for_charts = pd.DataFrame({'Sentiment': sentiment_counts.index, 'Count': sentiment_counts.values})
            chart_row1_col1, chart_row1_col2 = st.columns(2)
            with chart_row1_col1:
                fig_hist = px.histogram(df_grouped_for_charts, x='Sentiment', y='Count', color='Sentiment', 
                    title="Distribution des Sentiments (Histogramme)", 
                    color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                st.plotly_chart(fig_hist, use_container_width=True)
            with chart_row1_col2: # Pie chert
                fig_pie = px.pie(df_grouped_for_charts, values='Count', names='Sentiment', 
                    title='Répartition des Sentiments (Circulaire)', color='Sentiment', 
                    color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                st.plotly_chart(fig_pie, use_container_width=True)
            chart_row2_col1, chart_row2_col2 = st.columns(2) 
            with chart_row2_col1: # Scatter plot
                if 'LikeCount' in df_analyzed.columns and 'Compound_Score' in df_analyzed.columns and pd.api.types.is_numeric_dtype(df_analyzed['LikeCount']):
                    fig_scatter = px.scatter(df_analyzed, x='LikeCount', y='Compound_Score', color='Sentiment', 
                        title='Likes vs. Score de Polarité', labels={'LikeCount': 'Nombre de Likes', 'Compound_Score': 'Score de Polarité'}, 
                        hover_data=['Text'], color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.caption("Graphique Likes vs Score non généré.")
            with chart_row2_col2: # Line chart
                if 'Datetime' in df_analyzed.columns and 'Sentiment' in df_analyzed.columns:
                    try:
                        df_analyzed['Datetime'] = pd.to_datetime(df_analyzed['Datetime'], errors='coerce')
                        df_analyzed.dropna(subset=['Datetime'], inplace=True)
                        if not df_analyzed.empty:
                            df_analyzed['Date'] = df_analyzed['Datetime'].dt.date
                            sentiment_over_time = df_analyzed.groupby(['Date', 'Sentiment']).size().reset_index(name='Count')
                            if not sentiment_over_time.empty:
                                fig_line = px.line(sentiment_over_time, x='Date', y='Count', color='Sentiment', 
                                title='Tendance des Sentiments au Fil du Temps', color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                                st.plotly_chart(fig_line, use_container_width=True)
                            else:
                                st.caption("Tendance non générée: Pas de données groupées.")
                        else:
                            st.caption("Tendance non générée: Pas de dates valides.")
                    except Exception as e:
                        st.warning(f"Tendance non générée: Erreur Datetime - {e}")
                else:
                    st.caption("Tendance non générée: Colonnes manquantes.")
        else:
            st.info("Aucune donnée de sentiment à visualiser.")
# --- Data Loading ---
if 'df_global' not in st.session_state:
    df_loaded, error_msg = load_data()
    if error_msg:
        st.error(error_msg)
        st.session_state.df_global = pd.DataFrame()
        st.session_state.data_load_error = True
    else:
        st.session_state.df_global = df_loaded
        st.session_state.data_load_error = False
if 'keyword_select' not in st.session_state:
    st.session_state.keyword_select = ['#ChatGPT']
# --- Navigation ---
menu_id = navBar()
# --- Page Content ---
if menu_id == "Scrape Data From Twitter":
    st.header("Récupérer les données de Twitter (Filtrage)")
    if st.session_state.data_load_error:
        st.warning("Impossible d'afficher cette page car les données initiales n'ont pas pu être chargées.")
    elif st.session_state.df_global.empty:
        st.warning("Le fichier de données est vide. Aucune donnée à explorer.")
    else:
        st.session_state.keyword_select = st.multiselect(
            label="Sélectionnez un ou plusieurs mots clés",
            options=['#ChatGPT'],
            default=st.session_state.keyword_select,
            key='multiselect_keywords_explorer'
        )
        selected_keywords = st.session_state.keyword_select
        if selected_keywords:
            with st.spinner("Filtrage des données..."):
                df_filtered_display = filter_data_by_keywords_and_language(
                    st.session_state.df_global, selected_keywords
                )
            if not df_filtered_display.empty:
                st.write(df_filtered_display)
                st.success(f"{len(df_filtered_display)} tweets se chargent avec succès !")
            else:
                st.warning("Aucune donnée disponible pour les mots-clés sélectionnés (en langue anglaise).")
        else:
            st.warning("Veuillez sélectionner au moins un mot-clé.")

elif menu_id == "Sentiment Analysis live":
    st.header("Analyse des Sentiments")
    if st.session_state.data_load_error:
        st.warning("Impossible de procéder car les données initiales n'ont pas pu être chargées.")
    elif st.session_state.df_global.empty:
        st.warning("Le fichier de données est vide. Aucune analyse possible.")
    else:
        selected_keywords = st.session_state.get('keyword_select', [])
        if not selected_keywords:
            st.subheader("⚡ Analyse en Temps Réel (Twitter / Reddit)")

        platform_choice = st.selectbox("Choisissez la plateforme :", ["Twitter", "Reddit"])
        real_time_keyword = st.text_input("Entrez un mot-clé pour l'analyse en direct :", "")
    # Then your main logic:

    if st.button("Lancer l'analyse en temps réel") and real_time_keyword:
        with st.spinner("Récupération des données en temps réel..."):

            if platform_choice == "Twitter":
                # Twitter live fetch
                tweets_live_df = fetch_live_tweets(real_time_keyword)  # à implémenter
                source_df = tweets_live_df

                if source_df.empty:
                    st.warning("Aucune donnée récupérée.")
                else:
                    st.success(f"{len(source_df)} données récupérées en direct depuis {platform_choice}")
                    cleaned_df = preprocess_dataframe(source_df)
                    analyzed_df = analyze_sentiment_vader(cleaned_df)

                    st.subheader("Aperçu des résultats")
                    st.dataframe(analyzed_df[['Text', 'clean_tweet', 'Sentiment', 'Compound_Score']].head(1000))

                    st.subheader("Distribution des sentiments")
                    #plot_sentiment_distribution(analyzed_df)

            elif platform_choice == "Reddit":
                # Reddit live fetch
                reddit_df = fetch_live_reddit_comments(real_time_keyword)  # à implémenter
                source_df = reddit_df

                if source_df.empty:
                    st.warning("Aucune donnée récupérée.")
                else:
                    st.success(f"{len(source_df)} données récupérées en direct depuis {platform_choice}")
                    cleaned_df = preprocess_dataframe(source_df)
                    analyze_sentiment_with_metrics(cleaned_df)
                    analyzed_df = analyze_sentiment_vader(cleaned_df)

                    # Here use the **default else block style display** instead of the simpler one
                    display_analysis_results(analyzed_df, selected_keywords=[real_time_keyword])

    else:
        # Your existing else block for keyword-filtered analysis
        # Keep it unchanged but just call display_analysis_results at the end

        with st.spinner("Filtrage des données pour l'analyse..."):
            df_for_analysis_initial = filter_data_by_keywords_and_language(
                st.session_state.df_global, selected_keywords
            )

        if not df_for_analysis_initial.empty:
            st.info(f"Analyse des sentiments pour {len(df_for_analysis_initial)} tweets correspondant à '{', '.join(selected_keywords)}'.")
            df = df_for_analysis_initial.copy() 

            # ... (all your preprocessing steps unchanged) ...

            df_processed_for_sentiment = df 

            st.subheader('Comparaison entre les tweets avant et après le nettoyage')
            with st.expander('plus de détails'):
                if 'Text' in df_for_analysis_initial.columns and 'clean_tweet' in df_processed_for_sentiment.columns:
                    st.table(df_processed_for_sentiment[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

            st.subheader('Tweets après Analyse')
            df_analyzed = pd.DataFrame()
            with st.spinner("Analyse des sentiments en cours..."):
                df_analyzed = analyze_sentiment_vader(df_processed_for_sentiment)

            display_analysis_results(df_analyzed, selected_keywords=selected_keywords)

        else:
            st.warning("Aucune donnée disponible pour les mots-clés sélectionnés après filtrage.")
elif menu_id == "Sentiment Analysis":
    st.header("Analyse des Sentiments")
    if st.session_state.data_load_error:
        st.warning("Impossible de procéder car les données initiales n'ont pas pu être chargées.")
    elif st.session_state.df_global.empty:
        st.warning("Le fichier de données est vide. Aucune analyse possible.")
    else:
        selected_keywords = st.session_state.get('keyword_select', [])
        if not selected_keywords:
            st.warning("Veuillez d'abord sélectionner des mots-clés dans la section 'Récupérer les données de Twitter'.")
        else:
            with st.spinner("Filtrage des données pour l'analyse..."):
                df_for_analysis_initial = filter_data_by_keywords_and_language(
                    st.session_state.df_global, selected_keywords
                )

            if not df_for_analysis_initial.empty:
                st.info(f"Analyse des sentiments pour {len(df_for_analysis_initial)} tweets correspondant à '{', '.join(selected_keywords)}'.")
                df = df_for_analysis_initial.copy() 

                st.subheader('Pré-traitement des données textuelles')
                with st.spinner("Traitement du texte en cours...."):
                    with st.expander('plus de détails'):
                        # Step 1: Deduplicate and Lowercase
                        st.subheader('Supprimer les fichiers en double et convertir tous les :blue[tweets] en minuscules :')
                        df = step_deduplicate_and_lowercase(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 2: Remove URLs
                        st.subheader("Suppression de l'URL des :blue[tweets]")
                        df = step_remove_urls(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 3: Remove Mentions
                        st.subheader('Suppression des identifiants Twitter (@user)')
                        df = step_remove_mentions(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 4: Remove Hashtag Words
                        st.subheader('Suppression des identifiants :blue[Twitter] (#hashtag)')
                        df = step_remove_hashtags_words(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 5: Remove Ticker Words
                        st.subheader('Suppression des identifiants :blue[Twitter] ($tickers)')
                        df = step_remove_tickers_words(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 6: Remove Punctuation, Numbers, Special Chars
                        st.subheader('Suppression de la ponctuation (!,?,..), des chiffres et des caractères spéciaux')
                        df = step_remove_punctuation_numbers_special(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                        # Step 7: Tokenization (display part)
                        st.subheader('Tokénisation des :blue[tweets]: ')
                        df_display_tokens = df[['Text', 'clean_tweet']].copy() # Use current state of clean_tweet
                        if 'clean_tweet' in df_display_tokens.columns:
                            df_display_tokens['clean_tweet_display'] = df_display_tokens['clean_tweet'].str.split()
                            st.table(df_display_tokens[['Text', 'clean_tweet_display']].head(10).reset_index(drop=True))
                        df = step_tokenize_tweets(df) 

                        # Step 8: Remove Short Words (display part)
                        st.subheader('Suppression des mots courts : ')
                        df_display_short_words = df[['Text']].copy() 
                        if 'clean_tweet_tokens' in df.columns:
                            temp_tokens_for_display = df['clean_tweet_tokens'].copy()
                            def filter_short_words_pandas(token_list):
                                return [word for word in token_list if len(word) >= 2] if isinstance(token_list, list) else []
                            df_display_short_words['clean_tweet_display'] = temp_tokens_for_display.apply(filter_short_words_pandas)
                            st.table(df_display_short_words[['Text', 'clean_tweet_display']].head(10).reset_index(drop=True))
                        df = step_remove_short_words_from_tokens(df) 

                        # Step 9: Rejoin Tokens
                        st.subheader('Recoller les jetons ensemble ')
                        df = step_rejoin_tokens(df)
                        if 'clean_tweet' in df.columns: st.table(df[['Text', 'clean_tweet']].head(10).reset_index(drop=True))
                        
                        # Final cleanup of token column if it exists
                        if 'clean_tweet_tokens' in df.columns:
                            df = df.drop(columns=['clean_tweet_tokens'])

                # This is the fully preprocessed DataFrame now
                df_processed_for_sentiment = df 

                st.subheader('Comparaison entre les tweets avant et après le nettoyage')
                with st.expander('plus de détails'):
                    if 'Text' in df_for_analysis_initial.columns and 'clean_tweet' in df_processed_for_sentiment.columns:
                        st.table(df_processed_for_sentiment[['Text', 'clean_tweet']].head(10).reset_index(drop=True))

                # --- Sentiment Analysis Execution ---
                st.subheader('Tweets après Analyse')
                df_analyzed = pd.DataFrame()
                with st.spinner("Analyse des sentiments en cours..."):
                     df_analyzed = analyze_sentiment_vader(df_processed_for_sentiment)

                with st.expander('plus de détails sur les tweets analysés'):
                    if not df_analyzed.empty and 'Sentiment' in df_analyzed.columns:
                        cols_to_display = ['Text', 'clean_tweet', 'Sentiment', 'Compound_Score']
                        optional_cols = ['Username', 'LikeCount', 'Language', 'hashtag', 'User']
                        for col in optional_cols:
                            if col in df_analyzed.columns: cols_to_display.append(col)
                        existing_cols_display = [col for col in cols_to_display if col in df_analyzed.columns]
                        st.dataframe(df_analyzed[existing_cols_display])
                        cols_to_csv = ['clean_tweet', 'Sentiment', 'Compound_Score']
                        existing_cols_csv = [col for col in cols_to_csv if col in df_analyzed.columns]
                        if existing_cols_csv:
                            csv_data = df_analyzed[existing_cols_csv].to_csv(index=False).encode('utf-8')
                            st.download_button(label='Télécharger CSV Analysé', data=csv_data, file_name='sentiments_data.csv', mime='text/csv')
                    else:
                        st.write("Aucun résultat d'analyse à afficher.")

                # --- Visualization --- 
                st.write('------------------------------')
                title_col1, title_col2, title_col3 = st.columns((1, 8, 2))
                with title_col2:
                    st.title(f'Analyse des Sentiments Twitter sur :green[{" & ".join(selected_keywords)}]')
                with title_col3:
                    try:
                        st.image('image.png', width=100)
                    except FileNotFoundError:
                        st.caption("image.png non trouvée")
                st.write('------------------------------')

                if not df_analyzed.empty and 'Sentiment' in df_analyzed.columns:
                    sentiment_counts = df_analyzed['Sentiment'].value_counts()
                    total_analyzed_count = sentiment_counts.sum()
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    if total_analyzed_count > 0:
                        pos_perc = (sentiment_counts.get('Positive', 0) / total_analyzed_count) * 100
                        neg_perc = (sentiment_counts.get('Negative', 0) / total_analyzed_count) * 100
                        neu_perc = (sentiment_counts.get('Neutral', 0) / total_analyzed_count) * 100
                        stat_col1.subheader(f"Positif (%): {pos_perc:.2f}%")
                        stat_col2.subheader(f"Négatif (%): {neg_perc:.2f}%")
                        stat_col3.subheader(f"Neutre (%): {neu_perc:.2f}%")
                    else:
                        stat_col1.subheader(f"Positif (%): N/A")
                        stat_col2.subheader(f"Négatif (%): N/A")
                        stat_col3.subheader(f"Neutre (%): N/A")
                    stat_col4.subheader(f"Total Tweets: {len(df_analyzed)}")
                    st.write('------------------------------')
                    st.subheader('Visualisation du Résultat')
                    with st.spinner("Génération des graphiques...."):
                        if not sentiment_counts.empty:
                            df_grouped_for_charts = pd.DataFrame({'Sentiment': sentiment_counts.index, 'Count': sentiment_counts.values})
                            chart_row1_col1, chart_row1_col2 = st.columns(2)
                            with chart_row1_col1: # Histogram
                                fig_hist = px.histogram(df_grouped_for_charts, x='Sentiment', y='Count', color='Sentiment', title="Distribution des Sentiments (Histogramme)", color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                                st.plotly_chart(fig_hist, use_container_width=True)
                            with chart_row1_col2: # Pie chart
                                fig_pie = px.pie(df_grouped_for_charts, values='Count', names='Sentiment', title='Répartition des Sentiments (Circulaire)', color='Sentiment', color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                                st.plotly_chart(fig_pie, use_container_width=True)
                            chart_row2_col1, chart_row2_col2 = st.columns(2) 
                            with chart_row2_col1: # Scatter plot
                                if 'LikeCount' in df_analyzed.columns and 'Compound_Score' in df_analyzed.columns and pd.api.types.is_numeric_dtype(df_analyzed['LikeCount']):
                                    fig_scatter = px.scatter(df_analyzed, x='LikeCount', y='Compound_Score', color='Sentiment', title='Likes vs. Score de Polarité', labels={'LikeCount': 'Nombre de Likes', 'Compound_Score': 'Score de Polarité'}, hover_data=['Text'], color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                                    st.plotly_chart(fig_scatter, use_container_width=True)
                                else: st.caption("Graphique Likes vs Score non généré.")
                            with chart_row2_col2: # Line chart
                                if 'Datetime' in df_analyzed.columns and 'Sentiment' in df_analyzed.columns:
                                    try:
                                        df_analyzed['Datetime'] = pd.to_datetime(df_analyzed['Datetime'], errors='coerce')
                                        df_analyzed.dropna(subset=['Datetime'], inplace=True)
                                        if not df_analyzed.empty:
                                            df_analyzed['Date'] = df_analyzed['Datetime'].dt.date
                                            sentiment_over_time = df_analyzed.groupby(['Date', 'Sentiment']).size().reset_index(name='Count')
                                            if not sentiment_over_time.empty:
                                                fig_line = px.line(sentiment_over_time, x='Date', y='Count', color='Sentiment', title='Tendance des Sentiments au Fil du Temps', color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'grey'})
                                                st.plotly_chart(fig_line, use_container_width=True)
                                            else: st.caption("Tendance non générée: Pas de données groupées.")
                                        else: st.caption("Tendance non générée: Pas de dates valides.")
                                    except Exception as e: st.warning(f"Tendance non générée: Erreur Datetime - {e}")
                                else: st.caption("Tendance non générée: Colonnes manquantes.")
                        else: st.info("Aucune donnée de sentiment à visualiser.")
                else: st.warning("L'analyse n'a produit aucun résultat pertinent.")
            else: st.warning("Aucune donnée disponible pour les mots-clés sélectionnés après filtrage.")
# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>Sentiment Analyzer © 2025</p>", unsafe_allow_html=True)
@REQUEST_TIME.time()
def analyze_sentiment_with_metrics(df):
    df = preprocess_dataframe(df)
    df = analyze_sentiment_vader(df)
    TWEET_ANALYSIS_COUNT.inc(len(df))  # Count each analyzed tweet
    return df
def start_prometheus_exporter():
    start_http_server(8000)  # Exposes metrics at http://localhost:8000/metrics
# Run this once
if 'prometheus_started' not in st.session_state:
    threading.Thread(target=start_prometheus_exporter, daemon=True).start()
    st.session_state.prometheus_started = True
    
# def get_metrics():
#     if 'metrics_initialized' not in st.session_state:
#         registry = CollectorRegistry()
#         st.session_state.REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', registry=registry)
#         st.session_state.TWEET_ANALYSIS_COUNT = Counter('tweet_analysis_count', 'Number of tweets analyzed', registry=registry)
#         st.session_state.registry = registry
#         st.session_state.metrics_initialized = True

#     return st.session_state.REQUEST_TIME, st.session_state.TWEET_ANALYSIS_COUNT, st.session_state.registry

# def get_metrics():
#     if 'metrics_initialized' not in st.session_state:
#         # Optional: create a new registry if needed
#         st.session_state.registry = CollectorRegistry()

#         st.session_state.REQUEST_TIME = Summary(
#             'request_processing_seconds',
#             'Time spent processing request',
#             registry=st.session_state.registry  # Avoid default global registry
#         )

#         st.session_state.TWEET_ANALYSIS_COUNT = Counter(
#             'tweets_analyzed_total',
#             'Total number of tweets analyzed',
#             registry=st.session_state.registry
#         ),
#         st.session_state.REDDIT_ANALYSIS_COUNT = Counter(
#             'reddit_analyzed_total',
#             'Total number of reddit analyzed',
#             registry=st.session_state.registry
#         )

#         st.session_state.metrics_initialized = True

#     return st.session_state.REQUEST_TIME, st.session_state.TWEET_ANALYSIS_COUNT, st.session_state.registry

# Only call this once per run; Streamlit reruns but preserves session state

# REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')
# TWEET_ANALYSIS_COUNT = Counter('tweets_analyzed_total', 'Total number of tweets analyzed')

# def plot_sentiment_distribution(df):
#     sentiment_counts = df['Sentiment'].value_counts()
#     fig, ax = plt.subplots()
#     sentiment_counts.plot(kind='bar', color=['green', 'red', 'blue'], ax=ax)
#     ax.set_title('Sentiment Distribution')
#     ax.set_xlabel('Sentiment')
#     ax.set_ylabel('Number of Entries')
#     ax.set_xticklabels(sentiment_counts.index, rotation=0)
#     plt.tight_layout()
    
#     # Use this line to display in Streamlit:
#     st.pyplot(fig)
# --- Main App Logic ---

# @app.post("/predict/")
# def predict_sentiment(item: TextInput, db: Session = Depends(get_db)):
#     sentiment, score = classify_sentiment(item.text)
#     tweet = Tweet(text=item.text, clean_tweet=clean_tweet(item.text),
#                   sentiment=sentiment, compound_score=score)
#     db.add(tweet)
#     db.commit()
#     return {"sentiment": sentiment, "compound_score": score}