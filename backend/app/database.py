import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hive_data.json")

def _load():
    if not os.path.exists(DB_PATH):
        return {"logs": []}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_module_run(mod_id: str, mod_ad: str, inputs: dict, output: dict):
    data = _load()
    data["logs"].append({
        "mod_id": mod_id,
        "mod_ad": mod_ad,
        "timestamp": datetime.now().isoformat(),
        "inputs": {k: v for k, v in inputs.items() if v},
        "output": output
    })
    data["logs"] = data["logs"][-500:]
    _save(data)
    try:
        from app.moduller.brain_hooks import emit_brain_event
        emit_brain_event(f"/api/{mod_id}", inputs or {}, output or {}, module=mod_id)
    except Exception:
        pass

def get_module_history(mod_id: str, limit: int = 20):
    data = _load()
    logs = [l for l in data["logs"] if l["mod_id"] == mod_id]
    return logs[-limit:]

def get_all_logs(limit: int = 50):
    data = _load()
    return data["logs"][-limit:]

def get_module_stats(mod_id: str):
    logs = get_module_history(mod_id, 500)
    if not logs:
        return {"toplam": 0, "basarili": 0, "basarisiz": 0, "son_calisma": None}
    basarili = sum(1 for l in logs if l.get("output", {}).get("status") != "hata")
    return {
        "toplam": len(logs),
        "basarili": basarili,
        "basarisiz": len(logs) - basarili,
        "son_calisma": logs[-1]["timestamp"] if logs else None
    }

def delete_module_history(mod_id: str):
    data = _load()
    data["logs"] = [l for l in data["logs"] if l["mod_id"] != mod_id]
    _save(data)
    return {"deleted": True, "mod_id": mod_id}

def get_son_aktiviteler(limit: int = 10):
    logs = get_all_logs(limit)
    result = []
    for l in reversed(logs):
        result.append({
            "modul": l.get("mod_ad", l.get("mod_id", "")),
            "islem": str({k: v for k, v in l.get("inputs", {}).items() if v})[:60],
            "zaman": l.get("timestamp", ""),
            "durum": "basarili" if l.get("output", {}).get("status") != "hata" else "basarisiz"
        })
    return result

def get_gunluk_aktivite(limit: int = 7):
    logs = get_all_logs(500)
    gun_isim = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"]
    bugun = datetime.now()
    result = []
    for i in range(limit - 1, -1, -1):
        gun = bugun - timedelta(days=i)
        gun_str = gun.strftime("%Y-%m-%d")
        sayi = sum(1 for l in logs if l.get("timestamp", "")[:10] == gun_str)
        result.append({
            "gun": gun_isim[gun.weekday()],
            "islem": sayi,
            "tarih": gun_str
        })
    return result

def seed_demo_data():
    data = _load()
    if len(data["logs"]) > 0:
        return
    demo = [
        ("talon", "Talon", "kuşadası escort (kuşadası)"),
        ("seoaudit", "SEO Audit", "hedef-site.com"),
        ("ranktracker", "Rank Tracker", "rekabet analizi"),
        ("keywordresearch", "Keyword Research", "dijital pazarlama"),
        ("competitor", "Competitor Intel", "rakip analizi"),
        ("contentgen", "Content Generator", "SEO içerik stratejisi"),
        ("talon", "Talon", "istanbul SEO (istanbul)"),
        ("linkbuilder", "Link Builder", "backlink inşa"),
        ("reputation", "Reputation Shield", "marka itibarı"),
        ("trend", "Trend Analyzer", "yapay zeka trendleri"),
    ]
    for i, (mod_id, mod_ad, aksiyon) in enumerate(demo):
        data["logs"].append({
            "mod_id": mod_id,
            "mod_ad": mod_ad,
            "timestamp": (datetime.now() - timedelta(hours=i * 3)).isoformat(),
            "inputs": {"aksiyon": aksiyon},
            "output": {"status": "aktif"}
        })
    _save(data)

seed_demo_data()
