# validar_avaliacoes.py
import streamlit as st
import pandas as pd
from database import (
    init, get_news_by_id, create_evaluation, create_terms,
    ensure_admin_user, get_next_unreviewed_news
)

# ---------- Inicialização ----------
DATABASE_URL = st.secrets["postgres"]["url"]
init(DATABASE_URL)

# Garante que o usuário padrão existe e retorna o ID dele
ADMIN_USER_ID = int(ensure_admin_user())

st.title("Validação das Avaliações")

# --- Configurações ---
EMOTIONS = [
    'Não selecionado', 'Felicidade', 'Tristeza', 'Nojo',
    'Raiva', 'Medo', 'Surpresa', 'Desprezo', 'Neutro'
]
POLARITIES = ['Não selecionado', 'Positivo', 'Neutro', 'Negativo']

CSV_PATH = "avaliacoes.csv"

# ---------- Carregar CSV ----------
@st.cache_data
def load_csv():
    return pd.read_csv(CSV_PATH)

df = load_csv()
if df.empty:
    st.info("O arquivo avaliacoes.csv está vazio.")
    st.stop()

# ---------- Funções utilitárias ----------
SELECT_KEYS = ["h_sent", "h_pol", "g_sent", "g_pol"] + \
              [f"sent_{i}" for i in range(1, 4)] + [f"pol_{i}" for i in range(1, 4)]

def reset_widget_keys():
    for k in SELECT_KEYS:
        st.session_state.pop(k, None)

def safe_code(code, maxlen):
    try:
        c = int(code)
    except Exception:
        return 0
    return c if 0 <= c < maxlen else 0

def select(label, options, key, default_idx=0):
    idx = safe_code(default_idx, len(options))
    return st.selectbox(label, options, index=idx, key=key)

def go_next():
    """Vai para a próxima notícia não avaliada."""
    reset_widget_keys()
    # Remove a notícia atual para pegar a próxima
    if "news" in st.session_state:
        del st.session_state["news"]

# ---------- Obter notícia não avaliada ----------
if "news" not in st.session_state:
    news = get_next_unreviewed_news(ADMIN_USER_ID)
    if not news:
        st.info("Você já avaliou todas as notícias!")
        st.stop()
    st.session_state.news = news
else:
    news = st.session_state.news

# ---------- Linha correspondente no CSV ----------
row = df[df.iloc[:,0] == news.id].iloc[0]

# ---------- Exibir notícia ----------
st.subheader(news.headline)
sentences = [news.f1, news.f2, news.f3]

# ---------- Selects com defaults do CSV ----------
cols = st.columns(2)
with cols[0]:
    headline_sent = select('Sentimento da Manchete', EMOTIONS, 'h_sent', row.get('headline_sentiment', 0))
with cols[1]:
    headline_pol = select('Polaridade da Manchete', POLARITIES, 'h_pol', row.get('headline_polarity', 0))

st.write("---")

sentiments = []
polarities = []
for i, sent in enumerate(sentences, 1):
    st.text(f"Frase {i}: {sent}")
    cols = st.columns(2)
    with cols[0]:
        sentiments.append(select(f'Sentimento {i}', EMOTIONS, f'sent_{i}', row.get(f'sentence{i}_sentiment', 0)))
    with cols[1]:
        polarities.append(select(f'Polaridade {i}', POLARITIES, f'pol_{i}', row.get(f'sentence{i}_polarity', 0)))
    st.write("---")

cols = st.columns(2)
with cols[0]:
    general_sent = select('Sentimento Geral', EMOTIONS, 'g_sent', row.get('general_sentiment', 0))
with cols[1]:
    general_pol = select('Polaridade Geral', POLARITIES, 'g_pol', row.get('general_polarity', 0))

st.write("---")

# ---------- Botões ----------
bcols = st.columns(2)

# Salvar avaliação no banco
if bcols[0].button("Salvar avaliação ✅", use_container_width=True):
    values = [headline_sent, headline_pol, general_sent, general_pol] + sentiments + polarities
    if all(v != 'Não selecionado' for v in values):
        create_evaluation(
            user_id=ADMIN_USER_ID,
            news_id=news.id,
            headline_sentiment=EMOTIONS.index(headline_sent),
            headline_polarity=POLARITIES.index(headline_pol),
            sentence_sentiments=[EMOTIONS.index(s) for s in sentiments],
            sentence_polarities=[POLARITIES.index(p) for p in polarities],
            general_sentiment=EMOTIONS.index(general_sent),
            general_polarity=POLARITIES.index(general_pol),
        )
        unknown_terms = row.get("unknown_terms", "")
        if unknown_terms:
            create_terms(news.id, [t.strip() for t in unknown_terms.split(',') if t.strip()])
        st.success("Avaliação enviada para o banco de dados! ✅")
        st.session_state.pop("news")  # limpa notícia atual para pegar a próxima
        go_next()
    else:
        st.error("Preencha todos os campos antes de enviar para o banco.")

# Pular avaliação
if bcols[1].button("Pular ⏭️", use_container_width=True):
    st.session_state.pop("news")
    go_next()
