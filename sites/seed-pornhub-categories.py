#!/usr/bin/env python3
"""
Pornhub tarzı EN + TR kategoriler, ilan atama.
VPS: python3 seed-pornhub-categories.py
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys

from pornhub_categories import CATEGORIES

WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]
URL = "https://balkutusu.com"


def wp(args: list[str]) -> str:
    r = subprocess.run(WP + args + [f"--url={URL}"], capture_output=True, text=True)
    return (r.stdout or "").strip()


def wp_eval(php: str) -> str:
    r = subprocess.run(WP + ["eval", php, f"--url={URL}"], capture_output=True, text=True)
    return (r.stdout or "").strip()


def main() -> int:
    rows = []
    for en_slug, en_name, tr_slug, tr_name in CATEGORIES:
        rows.append({
            "slug": f"en-{en_slug}",
            "name": f"Kuşadası {en_name} Escort",
            "group": "porn_en",
            "lang": "en",
            "label": en_name,
            "pair": en_slug,
        })
        rows.append({
            "slug": f"tr-{tr_slug}",
            "name": f"Kuşadası {tr_name} Escort",
            "group": "porn_tr",
            "lang": "tr",
            "label": tr_name,
            "pair": en_slug,
        })

    payload = base64.b64encode(json.dumps(rows, ensure_ascii=False).encode()).decode()
    php = f"""
$rows = json_decode(base64_decode('{payload}'), true);
$created = 0; $skip = 0;
foreach ($rows as $row) {{
  $ex = get_term_by('slug', $row['slug'], 'companion_category');
  if ($ex) {{ $skip++; continue; }}
  $r = wp_insert_term($row['name'], 'companion_category', array('slug' => $row['slug'], 'parent' => 0));
  if (is_wp_error($r)) {{ continue; }}
  $tid = (int)$r['term_id'];
  update_term_meta($tid, 'hive_cat_group', $row['group']);
  update_term_meta($tid, 'hive_porn_label', $row['label']);
  update_term_meta($tid, 'hive_porn_lang', $row['lang']);
  update_term_meta($tid, 'hive_porn_pair', $row['pair']);
  $created++;
}}
echo "created:$created skip:$skip";
"""
    print(wp_eval(php), flush=True)

    # Rastgele ilan
    php2 = """
$pids = get_posts(array('post_type'=>'companion_profile','posts_per_page'=>-1,'fields'=>'ids','post_status'=>'publish'));
if (!$pids) { echo 'no profiles'; return; }
$terms = get_terms(array('taxonomy'=>'companion_category','hide_empty'=>false,'meta_query'=>array(
  array('key'=>'hive_cat_group','value'=>array('porn_en','porn_tr'),'compare'=>'IN'),
)));
$n = 0;
foreach ($terms as $term) {
  if (is_wp_error($term)) continue;
  $shuffled = $pids; shuffle($shuffled);
  $c = rand(8, 14);
  foreach (array_slice($shuffled, 0, $c) as $pid) {
    wp_set_object_terms((int)$pid, (int)$term->term_id, 'companion_category', true);
    $n++;
  }
}
echo 'assigned:'.$n;
"""
    print(wp_eval(php2), flush=True)
    wp(["rewrite", "flush"])
    print("total:", wp(["term", "list", "companion_category", "--format=count"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
