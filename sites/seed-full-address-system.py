#!/usr/bin/env python3
"""
Kuşadası tam adres kategori ağacı:
  Mahalle → Cadde/Sokak → Hizmet varyantı (Türk, Rus, Anal, CIM/CIF…)

VPS: python3 seed-full-address-system.py --host 13.140.138.135
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import subprocess
import sys
import zlib

from kusadasi_geo import MAHALLELER, VARIANTS

WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]
URL_DEFAULT = "https://balkutusu.com"


def wp(args: list[str], url: str, host: str | None, ssh_pass: str = "Fadafx35") -> str:
    cmd = WP + args + [f"--url={url}"]
    if host:
        import shutil
        if shutil.which("sshpass"):
            full = ["sshpass", "-p", ssh_pass, "ssh", "-o", "StrictHostKeyChecking=no", f"root@{host}"] + cmd
        else:
            full = cmd
    else:
        full = cmd
    r = subprocess.run(full, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(r.stderr[:500], file=sys.stderr)
    return (r.stdout or "").strip()


def wp_eval(php: str, url: str, host: str | None) -> str:
    compressed = base64.b64encode(zlib.compress(php.encode("utf-8"), 9)).decode("ascii")
    runner = f"""
$data = @gzuncompress(base64_decode('{compressed}'));
if ($data === false) {{ echo 'zlib fail'; return; }}
eval($data);
"""
    return wp(["eval", runner], url, host)


def build_tree() -> list[dict]:
    """Tüm kategori kayıtlarını üret."""
    items: list[dict] = []
    for mslug, mname, streets in MAHALLELER:
        items.append({
            "slug": mslug,
            "name": mname,
            "parent": 0,
            "group": "mahalle",
            "mahalle": mname,
            "street": "",
            "variant": "",
            "loc_type": "",
        })
        for sslug, sname, ltype in streets:
            loc_slug = f"{mslug}-{sslug}"
            items.append({
                "slug": loc_slug,
                "name": sname,
                "parent_slug": mslug,
                "group": "location",
                "mahalle": mname,
                "street": sname,
                "variant": "",
                "loc_type": ltype,
            })
            for vslug, vname in VARIANTS:
                leaf_slug = f"{loc_slug}-{vslug}"
                leaf_name = f"Kuşadası {mname} {sname} {vname}"
                items.append({
                    "slug": leaf_slug,
                    "name": leaf_name,
                    "parent_slug": loc_slug,
                    "group": "variant",
                    "mahalle": mname,
                    "street": sname,
                    "variant": vname,
                    "loc_type": ltype,
                })
        # Mahalle düzeyinde hizmet varyantları (cadde seçmeden)
        for vslug, vname in VARIANTS:
            mleaf = f"{mslug}-{vslug}"
            items.append({
                "slug": mleaf,
                "name": f"Kuşadası {mname} {vname}",
                "parent_slug": mslug,
                "group": "variant_mahalle",
                "mahalle": mname,
                "street": "",
                "variant": vname,
                "loc_type": "",
            })
    return items


def seed_batch(items: list[dict], url: str, host: str | None) -> dict:
    payload = json.dumps(items, ensure_ascii=False)
    b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    php = f"""
$batch = json_decode(base64_decode('{b64}'), true);
$map = array();
$created = 0; $skipped = 0; $meta = 0;
foreach ($batch as $row) {{
    $slug = $row['slug'];
    $existing = get_term_by('slug', $slug, 'companion_category');
    if ($existing) {{
        $map[$slug] = (int)$existing->term_id;
        $skipped++;
        continue;
    }}
    $parent = 0;
    if (!empty($row['parent_slug'])) {{
        $p = get_term_by('slug', $row['parent_slug'], 'companion_category');
        if ($p && !is_wp_error($p)) $parent = (int)$p->term_id;
    }}
    $r = wp_insert_term($row['name'], 'companion_category', array(
        'slug' => $slug,
        'parent' => $parent,
    ));
    if (is_wp_error($r)) {{
        $ex = get_term_by('slug', $slug, 'companion_category');
        if ($ex) $map[$slug] = (int)$ex->term_id;
        continue;
    }}
    $tid = (int)$r['term_id'];
    $map[$slug] = $tid;
    $created++;
    update_term_meta($tid, 'hive_cat_group', $row['group']);
    if (!empty($row['mahalle'])) update_term_meta($tid, 'hive_geo_mahalle', $row['mahalle']);
    if (!empty($row['street'])) update_term_meta($tid, 'hive_geo_street', $row['street']);
    if (!empty($row['variant'])) update_term_meta($tid, 'hive_variant', $row['variant']);
    if (!empty($row['loc_type'])) update_term_meta($tid, 'hive_loc_type', $row['loc_type']);
    $meta++;
}}
echo json_encode(array('created'=>$created,'skipped'=>$skipped,'meta'=>$meta,'map_size'=>count($map)));
"""
    raw = wp_eval(php, url, host)
    try:
        return json.loads(raw.split("\n")[-1] if "\n" in raw else raw)
    except json.JSONDecodeError:
        return {"raw": raw[:300]}


def assign_profiles(url: str, host: str | None, per_leaf: int = 6) -> None:
    php = f"""
$pids = get_posts(array('post_type'=>'companion_profile','posts_per_page'=>-1,'fields'=>'ids','post_status'=>'publish'));
if (!$pids) {{ echo 'no profiles'; return; }}
$terms = get_terms(array('taxonomy'=>'companion_category','hide_empty'=>false,'meta_query'=>array(
  array('key'=>'hive_cat_group','value'=>array('variant','variant_mahalle'),'compare'=>'IN'),
)));
$assigned = 0;
foreach ($terms as $term) {{
  if (is_wp_error($term)) continue;
  $n = rand({max(4, per_leaf-2)}, {per_leaf+4});
  $shuffled = $pids;
  shuffle($shuffled);
  foreach (array_slice($shuffled, 0, $n) as $pid) {{
    wp_set_object_terms((int)$pid, (int)$term->term_id, 'companion_category', true);
    $assigned++;
  }}
}}
echo 'assigned:'.$assigned;
"""
    print(wp_eval(php, url, host))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--url", default=URL_DEFAULT)
    ap.add_argument("--batch-size", type=int, default=400)
    ap.add_argument("--skip-profiles", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tree = build_tree()
    print(f"Toplam kategori planı: {len(tree)}", flush=True)
    if args.dry_run:
        return 0

    passes = [
        ("mahalle", [x for x in tree if x["group"] == "mahalle"]),
        ("location", [x for x in tree if x["group"] == "location"]),
        ("variant", [x for x in tree if x["group"] in ("variant", "variant_mahalle")]),
    ]

    total_created = 0
    for pname, items in passes:
        print(f"=== {pname}: {len(items)} ===", flush=True)
        for i in range(0, len(items), args.batch_size):
            batch = items[i : i + args.batch_size]
            res = seed_batch(batch, args.url, args.host)
            c = res.get("created", 0)
            total_created += c
            print(f"  {pname} batch {i//args.batch_size + 1}: +{c} (skip {res.get('skipped',0)})", flush=True)

    print(f"Oluşturulan: ~{total_created}", flush=True)

    if not args.skip_profiles:
        print("Profil ataması…", flush=True)
        assign_profiles(args.url, args.host)

    wp(["rewrite", "flush"], args.url, args.host)
    cnt = wp(["term", "list", "companion_category", "--format=count"], args.url, args.host)
    print(f"Toplam kategori: {cnt}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
