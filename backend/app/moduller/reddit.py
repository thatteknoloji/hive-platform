import json
import os
from .api_key_manager import get_key, uyar
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

SUBREDDITS = [
    "r/Turkey", "r/istanbul", "r/seo", "r/digitalmarketing",
    "r/startups", "r/webdev", "r/socialmedia", "r/ecommerce",
]
COMMENT_TEMPLATES = [
    "Great point about {konu}! I'd add that...",
    "I've been following {konu} for a while. Here's my take:",
    "{konu} is really underrated. Thanks for sharing!",
    "Has anyone else tried {konu}? I had a different experience.",
    "The {konu} space is evolving fast. Good discussion.",
]

REDDIT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "reddit_data.json")

def _yukle():
    if not os.path.exists(REDDIT_DB_PATH):
        return {"posts": [], "comments": []}
    try:
        with open(REDDIT_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"posts": [], "comments": []}

def _kaydet(data):
    os.makedirs(os.path.dirname(REDDIT_DB_PATH), exist_ok=True)
    with open(REDDIT_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _praw_yorum_gonder(baslik: str, yorum: str, subreddit: str):
    try:
        import praw
        client_id = get_key("praw_client_id")
        client_secret = get_key("praw_client_secret")
        if not client_id or not client_secret:
            return None
        reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret,
            user_agent="HIVE/3.0 by HIVE Panel"
        )
        results = reddit.subreddit("all").search(baslik, limit=1)
        for submission in results:
            submission.reply(yorum)
            return {"durum": "praw_ile_gonderildi", "submission": submission.title, "subreddit": str(submission.subreddit)}
        return {"durum": "baslik_bulunamadi"}
    except ImportError:
        return None
    except Exception as e:
        return {"hata": str(e)}

def _praw_post_ac(konu: str, icerik: str, subreddit: str):
    try:
        import praw
        client_id = get_key("praw_client_id")
        client_secret = get_key("praw_client_secret")
        if not client_id or not client_secret:
            return None
        reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret,
            user_agent="HIVE/3.0 by HIVE Panel"
        )
        sub_name = subreddit.replace("r/", "")
        sub = reddit.subreddit(sub_name)
        submission = sub.submit(title=konu, selftext=icerik)
        return {"durum": "praw_ile_yayinda", "post_id": submission.id, "subreddit": subreddit, "url": f"https://reddit.com{submission.permalink}"}
    except ImportError:
        return None
    except Exception as e:
        return {"hata": str(e)}

def yorum_gonder(baslik: str, yorum: str = ""):
    try:
        if not baslik:
            return {"status": "hata", "hata": "Başlık belirtilmedi"}
        h = modul_hash(f"reddit_{baslik}_{simdi()}")
        sub = modul_sec(f"sub_{h}", SUBREDDITS)
        if not yorum:
            yorum = modul_sec(f"com_{h}", COMMENT_TEMPLATES).format(konu=baslik)
        praw_result = _praw_yorum_gonder(baslik, yorum, sub)
        if praw_result and "hata" not in praw_result:
            data = _yukle()
            data["comments"].append({"baslik": baslik, "subreddit": sub, "yorum": yorum[:200], "puan": (h % 50) - 10, "created_at": simdi(), "kaynak": "praw"})
            _kaydet(data)
            return {"durum": "gönderildi", "baslik": baslik, "subreddit": sub, "yorum_uzunlugu": len(yorum), "kaynak": "praw"}
        data = _yukle()
        kayit = {"baslik": baslik, "subreddit": sub, "yorum": yorum[:200], "puan": (h % 50) - 10, "created_at": simdi()}
        data["comments"].append(kayit)
        _kaydet(data)
        return {
            "durum": "gönderildi", "baslik": baslik, "subreddit": sub, "yorum_uzunlugu": len(yorum),
            "yorum_icerik": yorum[:200], "puan": kayit["puan"],
            "kaynak": "simulasyon",
            "uyari": f"{uyar('praw_client_id')}, simülasyon modu" if not get_key("praw_client_id") else None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def post_ac(konu: str, icerik: str = ""):
    try:
        if not konu:
            return {"status": "hata", "hata": "Konu belirtilmedi"}
        h = modul_hash(f"reddit_post_{konu}_{simdi()}")
        sub = modul_sec(f"sub_post_{h}", SUBREDDITS)
        if not icerik:
            icerik = f"Hey everyone, I wanted to discuss {konu}. What are your thoughts and experiences?"
        praw_result = _praw_post_ac(konu, icerik, sub)
        if praw_result and "hata" not in praw_result:
            data = _yukle()
            data["posts"].append({"konu": konu, "subreddit": sub, "icerik": icerik[:300], "created_at": simdi(), "kaynak": "praw", "url": praw_result.get("url", "")})
            _kaydet(data)
            return {"durum": "yayında", "baslik": konu, "subreddit": sub, "kaynak": "praw", **praw_result}
        data = _yukle()
        kayit = {"konu": konu, "subreddit": sub, "icerik": icerik[:300], "created_at": simdi()}
        data["posts"].append(kayit)
        _kaydet(data)
        return {
            "durum": "yayında", "baslik": konu, "subreddit": sub, "icerik_uzunlugu": len(icerik),
            "post_id": f"RP-{h % 100000:05d}",
            "kaynak": "simulasyon",
            "uyari": f"{uyar('praw_client_id')}, simülasyon modu" if not get_key("praw_client_id") else None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def yorum_listele(subreddit: str = ""):
    try:
        data = _yukle()
        liste = data.get("comments", [])
        if subreddit:
            liste = [c for c in liste if c.get("subreddit") == subreddit]
        liste.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "yorumlar": liste[-50:]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def yorum_sil(yorum_id: int):
    try:
        data = _yukle()
        comments = data.get("comments", [])
        if 0 <= yorum_id < len(comments):
            removed = comments.pop(yorum_id)
            data["comments"] = comments
            _kaydet(data)
            return {"durum": "silindi", "baslik": removed.get("baslik")}
        return {"status": "hata", "hata": "Yorum bulunamadı"}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}

def post_listele():
    try:
        data = _yukle()
        liste = data.get("posts", [])
        liste.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return {"toplam": len(liste), "postlar": liste[-30:]}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}
