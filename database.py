# database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime

# Variáveis globais
engine = None
SessionLocal = None
Base = declarative_base()

# ---------- Modelos ----------
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    qnt_class = Column(Integer, default=0)
    evaluations = relationship("Evaluation", back_populates="user")

class News(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String, nullable=False)
    link = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    f1 = Column(String, nullable=False)
    f2 = Column(String, nullable=False)
    f3 = Column(String, nullable=False)
    evaluations = relationship("Evaluation", back_populates="news")

class Evaluation(Base):
    __tablename__ = 'evaluations'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    news_id = Column(Integer, ForeignKey('news.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    headline_sentiment = Column(Integer, nullable=False)
    headline_polarity = Column(Integer, nullable=False)
    sentence1_sentiment = Column(Integer, nullable=False)
    sentence1_polarity = Column(Integer, nullable=False)
    sentence2_sentiment = Column(Integer, nullable=False)
    sentence2_polarity = Column(Integer, nullable=False)
    sentence3_sentiment = Column(Integer, nullable=False)
    sentence3_polarity = Column(Integer, nullable=False)
    general_sentiment = Column(Integer, nullable=False)
    general_polarity = Column(Integer, nullable=False)

    user = relationship("User", back_populates="evaluations")
    news = relationship("News", back_populates="evaluations")

class Term(Base):
    __tablename__ = 'terms'
    id = Column(Integer, primary_key=True)
    news_index = Column(Integer, nullable=False)
    term = Column(String, nullable=False)

# ---------- Funções ----------
def init(db_url: str):
    """Inicializa a conexão com o banco e cria as tabelas."""
    global engine, SessionLocal
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

def ensure_admin_user() -> int:
    """Garante que existe um usuário fixo com id=999999."""
    session = SessionLocal()
    try:
        admin = session.query(User).filter_by(id=999999).first()
        if not admin:
            admin = User(id=999999, email="admin@local", qnt_class=0)
            session.add(admin)
            session.commit()
        return admin.id
    finally:
        session.close()

def create_evaluation(user_id: int, news_id: int,
                      headline_sentiment: int, headline_polarity: int,
                      sentence_sentiments: list, sentence_polarities: list,
                      general_sentiment: int, general_polarity: int) -> None:
    """Insere uma avaliação no banco."""
    session = SessionLocal()
    try:
        eval_obj = Evaluation(
            user_id=user_id,
            news_id=news_id,
            headline_sentiment=headline_sentiment,
            headline_polarity=headline_polarity,
            sentence1_sentiment=sentence_sentiments[0],
            sentence1_polarity=sentence_polarities[0],
            sentence2_sentiment=sentence_sentiments[1],
            sentence2_polarity=sentence_polarities[1],
            sentence3_sentiment=sentence_sentiments[2],
            sentence3_polarity=sentence_polarities[2],
            general_sentiment=general_sentiment,
            general_polarity=general_polarity,
            date=datetime.utcnow()
        )
        session.add(eval_obj)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_news_by_id(news_id: int):
    """Retorna uma notícia pelo ID."""
    session = SessionLocal()
    try:
        return session.query(News).filter(News.id == news_id).first()
    finally:
        session.close()

def create_terms(news_index: int, terms: list[str]) -> None:
    """Salva termos desconhecidos relacionados a uma notícia."""
    session = SessionLocal()
    try:
        for t in terms:
            t = t.strip()
            if not t:
                continue
            session.add(Term(news_index=news_index, term=t))
        session.commit()
    finally:
        session.close()

def get_next_unreviewed_news(user_id: int):
    """
    Retorna a próxima notícia ainda não avaliada por esse usuário.
    Se não houver, retorna None.
    """
    session = SessionLocal()
    try:
        # IDs das notícias que o usuário já avaliou
        reviewed_ids = session.query(Evaluation.news_id).filter(Evaluation.user_id == user_id).all()
        reviewed_ids = [r[0] for r in reviewed_ids]

        # Próxima notícia que ainda não foi avaliada
        next_news = session.query(News).filter(~News.id.in_(reviewed_ids)).order_by(News.id.asc()).first()
        return next_news
    finally:
        session.close()
