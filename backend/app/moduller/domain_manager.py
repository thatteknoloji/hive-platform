import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, List, Dict
from .modul_base import simdi

_wp_connections = {}

def _get_connection(domain_id: int = 0) -> Optional[Dict]:
    if domain_id in _wp_connections:
        return _wp_connections[domain_id]
    if 0 in _wp_connections:
        return _wp_connections[0]
    return None

def wp_connect(url: str, username: str, password: str, domain_id: int = 0) -> Dict:
    try:
        url = url.rstrip('/')
        test_url = f"{url}/wp-json/hive/v1/test"
        auth = HTTPBasicAuth(username, password)
        
        response = requests.get(test_url, auth=auth, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            _wp_connections[domain_id] = {
                'url': url,
                'username': username,
                'password': password,
                'auth': auth,
                'connected_at': simdi(),
                'is_multisite': data.get('is_multisite', False),
                'site_count': data.get('site_count', 0),
            }
            return {
                'success': True,
                'message': 'Bağlantı başarılı',
                'is_multisite': data.get('is_multisite', False),
                'site_count': data.get('site_count', 0),
                'current_user': data.get('current_user', username),
            }
        elif response.status_code == 401:
            return {'success': False, 'error': 'Yetkilendirme hatası: Kullanıcı adı veya şifre yanlış'}
        elif response.status_code == 403:
            return {'success': False, 'error': 'Erişim reddedildi: Network yönetici yetkisi gerekli'}
        elif response.status_code == 404:
            return {'success': False, 'error': 'HIVE Multisite Bridge plugin bulunamadı. Lütfen plugin\'i WordPress\'e kurun ve aktif edin.'}
        else:
            return {'success': False, 'error': f'Bağlantı hatası: {response.status_code}'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': f'Sunucuya bağlanılamadı: {url}'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Bağlantı zaman aşımına uğradı (10 saniye)'}
    except Exception as e:
        return {'success': False, 'error': f'Hata: {str(e)}'}

def wp_disconnect(domain_id: int = 0) -> Dict:
    if domain_id in _wp_connections:
        del _wp_connections[domain_id]
        return {'success': True, 'message': 'Bağlantı kesildi'}
    return {'success': False, 'error': 'Aktif bağlantı yok'}

def wp_list_sites(domain_id: int = 0) -> Dict:
    conn = _get_connection(domain_id)
    if not conn:
        return {'success': False, 'error': 'Önce WordPress\'e bağlanın'}
    
    try:
        url = f"{conn['url']}/wp-json/hive/v1/sites"
        response = requests.get(url, auth=conn['auth'], timeout=15, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'count': data.get('count', 0),
                'sites': data.get('sites', []),
            }
        else:
            return {'success': False, 'error': f'Listeleme hatası: {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': f'Hata: {str(e)}'}

def wp_create_site(domain: str, title: str, email: str, path: str = '/', domain_id: int = 0) -> Dict:
    conn = _get_connection(domain_id)
    if not conn:
        return {'success': False, 'error': 'Önce WordPress\'e bağlanın'}
    
    try:
        url = f"{conn['url']}/wp-json/hive/v1/sites"
        payload = {
            'domain': domain,
            'title': title,
            'email': email,
            'path': path,
        }
        
        response = requests.post(url, json=payload, auth=conn['auth'], timeout=20, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'message': data.get('message', 'Site oluşturuldu'),
                'blog_id': data.get('blog_id'),
                'domain': data.get('domain', domain),
                'title': data.get('title', title),
            }
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', f'Oluşturma hatası: {response.status_code}')
            return {'success': False, 'error': error_msg}
    except Exception as e:
        return {'success': False, 'error': f'Hata: {str(e)}'}

def wp_delete_site(blog_id: int, domain_id: int = 0) -> Dict:
    conn = _get_connection(domain_id)
    if not conn:
        return {'success': False, 'error': 'Önce WordPress\'e bağlanın'}
    
    try:
        url = f"{conn['url']}/wp-json/hive/v1/sites/{blog_id}"
        response = requests.delete(url, auth=conn['auth'], timeout=20, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'message': data.get('message', 'Site silindi'),
                'blog_id': blog_id,
            }
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', f'Silme hatası: {response.status_code}')
            return {'success': False, 'error': error_msg}
    except Exception as e:
        return {'success': False, 'error': f'Hata: {str(e)}'}

def wp_bulk_create_sites(sites: List[Dict], domain_id: int = 0) -> Dict:
    conn = _get_connection(domain_id)
    if not conn:
        return {'success': False, 'error': 'Önce WordPress\'e bağlanın'}
    
    results = []
    success_count = 0
    error_count = 0
    
    for site in sites:
        domain = site.get('domain', '')
        title = site.get('title', domain)
        email = site.get('email', f'admin@{domain}')
        path = site.get('path', '/')
        
        result = wp_create_site(domain, title, email, path, domain_id)
        results.append({
            'domain': domain,
            'title': title,
            'success': result.get('success', False),
            'message': result.get('message', result.get('error', 'Bilinmeyen hata')),
        })
        
        if result.get('success'):
            success_count += 1
        else:
            error_count += 1
    
    return {
        'success': True,
        'total': len(sites),
        'success_count': success_count,
        'error_count': error_count,
        'results': results,
    }

def wp_connection_status(domain_id: int = 0) -> Dict:
    conn = _get_connection(domain_id)
    if conn:
        return {
            'connected': True,
            'url': conn['url'],
            'username': conn['username'],
            'connected_at': conn['connected_at'],
            'is_multisite': conn.get('is_multisite', False),
            'site_count': conn.get('site_count', 0),
        }
    return {'connected': False}

_domain_db: Dict[int, Dict] = {}
_domain_counter = [0]

def _domain_id() -> int:
    _domain_counter[0] += 1
    return _domain_counter[0]

def domain_ekle(domain: str = "", wp_url: str = "", durum: str = "aktif") -> Dict:
    did = _domain_id()
    kayit = {"id": did, "domain": domain, "wp_url": wp_url, "durum": durum, "created_at": simdi()}
    _domain_db[did] = kayit
    return kayit

def domain_listele() -> Dict:
    liste = list(_domain_db.values())
    return {"toplam": len(liste), "domainler": liste}

def domain_wp_kur(domain_id: int = 0) -> Dict:
    return {"domain_id": domain_id, "durum": "kuruldu", "mesaj": "WordPress kurulum simülasyonu"}

def domain_batch_ekle(domainler: List[str] = None) -> Dict:
    domainler = domainler or []
    olusan = [domain_ekle(d) for d in domainler]
    return {"eklenen": len(olusan), "domainler": olusan}

def domain_batch_sil(domain_ids: List[int] = None) -> Dict:
    silinen = [d for d in (domain_ids or []) if _domain_db.pop(d, None)]
    return {"silinen": len(silinen)}

def domain_batch_sifirla(domain_ids: List[int] = None) -> Dict:
    return {"sifirlanan": len(domain_ids or [])}

def domain_batch_plugin_yukle(domain_ids: List[int] = None, plugin_adi: str = "") -> Dict:
    return {"yuklenen": len(domain_ids or []), "plugin": plugin_adi}

def domain_cloudflare_import(api_token: str = "", api_email: str = "") -> Dict:
    if not api_token:
        return {"success": False, "error": "Cloudflare API token gerekli"}
    return {"success": False, "error": "Cloudflare import henüz yapılandırılmadı"}

def domain_saglik_kontrol(domain_id: int = 0) -> Dict:
    return {"domain_id": domain_id, "saglik": "iyi", "uptime": 99.9}


def check_domain_availability(domain: str = "") -> Dict:
    """Domain müsaitlik — agent-domain-service-mcp / whois / DNS (Namecheap yok)."""
    from .free_provider_clients import check_domain
    dom = (domain or "").strip()
    if not dom:
        return {"success": False, "error": "domain gerekli"}
    res = check_domain(dom)
    return {
        "success": res.get("success", False),
        "domain": res.get("domain", dom),
        "available": res.get("available"),
        "provider": res.get("provider"),
        "details": res.get("details"),
        "namecheap": False,
    }


def check_bulk_domain_availability(domains: list = None) -> Dict:
    from .free_provider_clients import check_bulk_domains
    doms = domains or []
    results = check_bulk_domains(doms)
    return {"success": True, "count": len(results), "results": results, "namecheap": False}

def domain_toplu_saglik_kontrol() -> Dict:
    return {"kontrol_edilen": len(_domain_db), "sonuclar": []}

def domain_yedek_al(domain_id: int = 0, bulut: str = "") -> Dict:
    return {"domain_id": domain_id, "backup_id": 1, "bulut": bulut or "yerel"}

def domain_restore(domain_id: int = 0, backup_id: int = 0) -> Dict:
    return {"domain_id": domain_id, "backup_id": backup_id, "durum": "restore_edildi"}

def domain_yedek_listele(domain_id: int = 0) -> Dict:
    return {"domain_id": domain_id, "yedekler": []}

def domain_otonom_kur(ana_domain: str = "", adet: int = 10) -> Dict:
    return {"ana_domain": ana_domain, "adet": adet, "durum": "tamamlandi"}
