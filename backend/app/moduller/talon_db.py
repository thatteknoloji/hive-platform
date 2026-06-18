import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "talon.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Search(Base):
    __tablename__ = "searches"
    id = Column(String(16), primary_key=True)
    ana_kelime = Column(String(255), nullable=False)
    sehir = Column(String(100), nullable=False)
    adet = Column(Integer, default=10)
    negatif_filtre = Column(Text, default="")
    kelime_sayisi = Column(Integer, default=0)
    api_kullanildi = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_id = Column(String(16), nullable=False)
    kelime = Column(String(500), nullable=False)
    rekabet = Column(String(20), default="orta")
    arama_hacmi = Column(String(20), default="100-500")
    rakip_var = Column(Boolean, default=False)
    cpc = Column(String(20), default="0")
    grup = Column(String(50), default="diger")

class Favorite(Base):
    __tablename__ = "favorites"
    kelime = Column(String(500), primary_key=True)
    rekabet = Column(String(20), default="orta")
    arama_hacmi = Column(String(20), default="100-500")
    rakip_var = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)

class ApiKey(Base):
    __tablename__ = "api_keys"
    service = Column(String(50), primary_key=True)
    value = Column(String(500), default="")
    aktif = Column(Boolean, default=False)

Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()

def search_kaydet(search_id, ana_kelime, sehir, adet, negatif_filtre, kelime_sayisi, api_kullanildi):
    session = get_session()
    try:
        kayit = Search(
            id=search_id, ana_kelime=ana_kelime, sehir=sehir,
            adet=adet, negatif_filtre=negatif_filtre or "",
            kelime_sayisi=kelime_sayisi, api_kullanildi=api_kullanildi,
        )
        session.add(kayit)
        session.commit()
        return kayit
    except:
        session.rollback()
        raise
    finally:
        session.close()

def keyword_toplu_kaydet(keywords):
    session = get_session()
    try:
        for kw in keywords:
            k = Keyword(**kw)
            session.add(k)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def search_to_dict(s: Search) -> dict:
    return {
        "id": s.id,
        "ana_kelime": s.ana_kelime,
        "sehir": s.sehir,
        "adet": s.adet,
        "negatif_filtre": s.negatif_filtre or "",
        "kelime_sayisi": s.kelime_sayisi,
        "api_kullanildi": bool(s.api_kullanildi),
        "timestamp": s.timestamp.isoformat() if s.timestamp else None,
    }


def keyword_to_dict(k: Keyword) -> dict:
    return {
        "kelime": k.kelime,
        "rekabet": k.rekabet,
        "arama_hacmi": k.arama_hacmi,
        "rakip_var": bool(k.rakip_var),
        "cpc": k.cpc or "0",
        "grup": k.grup or "diger",
    }


def search_listele(limit=50):
    session = get_session()
    try:
        rows = session.query(Search).order_by(Search.timestamp.desc()).limit(limit).all()
        return [search_to_dict(s) for s in rows]
    finally:
        session.close()


def search_getir(search_id):
    session = get_session()
    try:
        s = session.query(Search).filter(Search.id == search_id).first()
        if not s:
            return None
        kws = session.query(Keyword).filter(Keyword.search_id == search_id).all()
        return {
            "arama": search_to_dict(s),
            "kelimeler": [keyword_to_dict(k) for k in kws],
        }
    finally:
        session.close()

def search_sil(search_id):
    session = get_session()
    try:
        session.query(Keyword).filter(Keyword.search_id == search_id).delete()
        session.query(Search).filter(Search.id == search_id).delete()
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def favori_ekle(kelime, rekabet, arama_hacmi, rakip_var):
    session = get_session()
    try:
        var = session.query(Favorite).filter(Favorite.kelime == kelime).first()
        if var:
            return False
        fav = Favorite(kelime=kelime, rekabet=rekabet, arama_hacmi=arama_hacmi, rakip_var=rakip_var)
        session.add(fav)
        session.commit()
        return True
    except:
        session.rollback()
        raise
    finally:
        session.close()

def favori_kaldir(kelime):
    session = get_session()
    try:
        fav = session.query(Favorite).filter(Favorite.kelime == kelime).first()
        if not fav:
            return False
        session.delete(fav)
        session.commit()
        return True
    except:
        session.rollback()
        raise
    finally:
        session.close()

def favori_listele():
    session = get_session()
    try:
        rows = session.query(Favorite).order_by(Favorite.timestamp.desc()).all()
        return [
            {
                "kelime": f.kelime,
                "rekabet": f.rekabet,
                "arama_hacmi": f.arama_hacmi,
                "rakip_var": bool(f.rakip_var),
                "timestamp": f.timestamp.isoformat() if f.timestamp else None,
            }
            for f in rows
        ]
    finally:
        session.close()

def api_key_getir(service):
    session = get_session()
    try:
        k = session.query(ApiKey).filter(ApiKey.service == service).first()
        return k.value if k else ""
    finally:
        session.close()

def api_key_kaydet(service, value):
    session = get_session()
    try:
        k = session.query(ApiKey).filter(ApiKey.service == service).first()
        if k:
            k.value = value
        else:
            k = ApiKey(service=service, value=value, aktif=bool(value))
            session.add(k)
        session.commit()
        return True
    except:
        session.rollback()
        raise
    finally:
        session.close()

def api_durum_listele():
    from app import config
    from .talon_utils import DataForSEOService, SerpAPIService, OllamaService
    from .talon_stack.providers.base import provider_health

    session = get_session()
    try:
        keys = session.query(ApiKey).all()
        key_map = {k.service: k.value for k in keys}
        durum = {}
        ph = provider_health()

        durum["searxng"] = {"ad": "SearXNG", "var": ph.get("searxng") == "configured", "aktif": ph.get("searxng") == "configured"}
        durum["tavily"] = {"ad": "Tavily", "var": ph.get("tavily") == "configured", "aktif": ph.get("tavily") == "configured"}
        durum["exa"] = {"ad": "Exa", "var": ph.get("exa") == "configured", "aktif": ph.get("exa") == "configured"}
        durum["openstreetmap"] = {"ad": "OpenStreetMap", "var": True, "aktif": True}
        durum["autocomplete"] = {"ad": "Google Autocomplete", "var": True, "aktif": True}
        durum["openrouter"] = {"ad": "OpenRouter", "var": ph.get("openrouter") == "configured", "aktif": ph.get("openrouter") == "configured"}

        legacy = (config.get("TALON_USE_LEGACY_APIS") or "").lower() in ("1", "true", "yes")
        dfs_env = bool((config.get("DATAFORSEO_LOGIN") or "").strip() and (config.get("DATAFORSEO_PASSWORD") or "").strip())
        durum["dataforseo"] = {
            "ad": "DataForSEO (legacy)",
            "var": legacy and dfs_env,
            "aktif": legacy and dfs_env,
            "deprecated": True,
        }
        serp_env = bool((config.get("SERPAPI_KEY") or "").strip())
        durum["serpapi"] = {
            "ad": "SerpAPI (legacy)",
            "var": legacy and serp_env,
            "aktif": legacy and serp_env,
            "deprecated": True,
        }

        ollama_db = bool(key_map.get("ollama_host"))
        ollama_env = bool((config.get("OLLAMA_URL") or "").strip())
        ollama = ollama_db or ollama_env or OllamaService.is_configured()
        durum["ollama"] = {
            "ad": "Ollama",
            "var": ollama,
            "aktif": ollama,
            "kaynak": "env" if ollama_env else ("sqlite" if ollama_db else ""),
        }
        v2_ready = (
            ph.get("tavily") == "configured"
            or ph.get("exa") == "configured"
            or ph.get("searxng") == "configured"
        )
        durum["stack"] = {"ad": "Talon V2", "var": v2_ready, "aktif": v2_ready}
        return durum
    finally:
        session.close()
