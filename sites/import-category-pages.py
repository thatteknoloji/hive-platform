#!/usr/bin/env python3
"""
Her companion_category için WordPress sayfası oluşturur/günceller.
- Tam SEO içerik (H2/H3/SSS) — generate-seo-content.py ile aynı motor
- Kategori arşivine link + öne çıkan ilanlar shortcode
- Sadece ilanı olan kategoriler (hide_empty) veya --all ile tümü

VPS:
  python3 sites/import-category-pages.py --host 13.140.138.135 --url https://balkutusu.com
  python3 sites/import-category-pages.py --url https://balkutusu.com --limit 50
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WP_BASE = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]


def load_seo_module():
    spec = importlib.util.spec_from_file_location("seo_gen", SCRIPT_DIR / "generate-seo-content.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def wp(args: list[str], url: str, host: str | None, ssh_pass: str) -> str:
    cmd = WP_BASE + args + [f"--url={url}"]
    if host:
        full = ["sshpass", "-p", ssh_pass, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{host}"] + cmd
    else:
        full = cmd
    r = subprocess.run(full, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(r.stderr[:300], file=sys.stderr)
    return (r.stdout or "").strip()


def get_terms(url: str, host: str | None, ssh_pass: str, hide_empty: bool) -> list[dict]:
    empty = "true" if hide_empty else "false"
    raw = wp(
        [
            "eval",
            f"""
$terms = get_terms(array('taxonomy'=>'companion_category','hide_empty'=>{empty},'number'=>0));
$out = array();
foreach ($terms as $t) {{
  if (preg_match('/^\\d+$/', $t->name)) continue;
  $children = get_terms(array('taxonomy'=>'companion_category','parent'=>$t->term_id,'hide_empty'=>false,'fields'=>'ids'));
  if (!empty($children)) continue;
  $out[] = array(
    'term_id' => (int)$t->term_id,
    'name' => $t->name,
    'slug' => $t->slug,
    'count' => (int)$t->count,
    'meta' => array(
      'hive_cat_group' => get_term_meta($t->term_id,'hive_cat_group',true),
      'hive_geo_mahalle' => get_term_meta($t->term_id,'hive_geo_mahalle',true),
      'hive_geo_street' => get_term_meta($t->term_id,'hive_geo_street',true),
      'hive_variant' => get_term_meta($t->term_id,'hive_variant',true),
      'hive_loc_type' => get_term_meta($t->term_id,'hive_loc_type',true),
    ),
  );
}}
echo json_encode($out);
""",
        ],
        url,
        host,
        ssh_pass,
    )
    try:
        return json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []


def page_exists(slug: str, url: str, host: str | None, ssh_pass: str) -> str | None:
    out = wp(["post", "list", "--post_type=page", f"--name={slug}", "--field=ID", "--format=ids", "--post_status=any"], url, host, ssh_pass)
    return out.split()[0] if out else None


def save_page(term: dict, body: str, url: str, host: str | None, ssh_pass: str) -> None:
    page_slug = f"rehber-{term['slug']}"
    title = f"{term['name']} — Kuşadası Escort Rehberi"
    term_link = f"/profil-kategori/{term['slug']}/"
    intro = (
        f'<p><strong>{term["name"]}</strong> kategorisinde güncel Kuşadası escort ilanları. '
        f'<a href="{term_link}">Tüm ilanları kategori arşivinde görüntüleyin</a>.</p>'
    )
    shortcode = f'[hive_category_profiles term_id="{term["term_id"]}" limit="6"]'
    content = intro + shortcode + body
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    pid = page_exists(page_slug, url, host, ssh_pass)
    if pid:
        wp(
            [
                "eval",
                f"""
$post_id = {int(pid)};
wp_update_post(array('ID'=>$post_id,'post_title'=>{json.dumps(title)},'post_content'=>base64_decode('{b64}'),'post_status'=>'publish'));
update_post_meta($post_id,'_hive_category_term_id',{int(term['term_id'])});
""",
            ],
            url,
            host,
            ssh_pass,
        )
    else:
        wp(
            [
                "eval",
                f"""
$post_id = wp_insert_post(array(
  'post_type'=>'page',
  'post_status'=>'publish',
  'post_title'=>{json.dumps(title)},
  'post_name'=>{json.dumps(page_slug)},
  'post_content'=>base64_decode('{b64}'),
));
if ($post_id && !is_wp_error($post_id)) {{
  update_post_meta($post_id,'_hive_category_term_id',{int(term['term_id'])});
}}
echo $post_id;
""",
            ],
            url,
            host,
            ssh_pass,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--url", default="https://balkutusu.com")
    ap.add_argument("--ssh-pass", default="Fadafx35")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all", action="store_true", help="Boş kategoriler dahil (yaprak)")
    args = ap.parse_args()

    seo = load_seo_module()
    terms = get_terms(args.url, args.host, args.ssh_pass, hide_empty=not args.all)
    print(f"Yaprak kategori: {len(terms)}", flush=True)

    n = 0
    for t in terms:
        ctx = seo.term_context(t)
        body = seo.generate_body(ctx)
        seo.save_term_meta(str(t["term_id"]), body, args.url, args.host)
        save_page(t, body, args.url, args.host, args.ssh_pass)
        n += 1
        if n % 20 == 0 or n <= 3:
            print(f"  [{n}] {t['name'][:55]} — {seo.word_count(body)} kelime", flush=True)
        if args.limit and n >= args.limit:
            break

    print(f"Tamam: {n} kategori sayfası + SEO meta", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
