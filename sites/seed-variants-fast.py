#!/usr/bin/env python3
"""Sokak/mahalle başına toplu varyant oluşturma (hızlı)."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import zlib

from kusadasi_geo import MAHALLELER, VARIANTS

WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root"]
URL = "https://balkutusu.com"


def wp_eval(php: str) -> str:
    compressed = base64.b64encode(zlib.compress(php.encode("utf-8"), 9)).decode("ascii")
    runner = f"$d=@gzuncompress(base64_decode('{compressed}')); if($d) eval($d);"
    r = subprocess.run(WP + ["eval", runner, f"--url={URL}"], capture_output=True, text=True)
    return (r.stdout or "").strip()


def seed_street_variants(mslug: str, mname: str, sslug: str, sname: str, ltype: str) -> int:
    loc_slug = f"{mslug}-{sslug}"
    rows = []
    for vslug, vname in VARIANTS:
        rows.append({
            "slug": f"{loc_slug}-{vslug}",
            "name": f"Kuşadası {mname} {sname} {vname}",
            "vslug": vslug,
            "vname": vname,
        })
    payload = base64.b64encode(json.dumps(rows, ensure_ascii=False).encode()).decode()
    php = f"""
$loc = get_term_by('slug', '{loc_slug}', 'companion_category');
if (!$loc) {{ echo '0'; return; }}
$pid = (int)$loc->term_id;
$rows = json_decode(base64_decode('{payload}'), true);
$c = 0;
foreach ($rows as $row) {{
  if (get_term_by('slug', $row['slug'], 'companion_category')) continue;
  $r = wp_insert_term($row['name'], 'companion_category', array('slug'=>$row['slug'],'parent'=>$pid));
  if (is_wp_error($r)) continue;
  $tid = (int)$r['term_id'];
  update_term_meta($tid,'hive_cat_group','variant');
  update_term_meta($tid,'hive_geo_mahalle','{mname.replace("'", "\\'")}');
  update_term_meta($tid,'hive_geo_street','{sname.replace("'", "\\'")}');
  update_term_meta($tid,'hive_variant',$row['vname']);
  update_term_meta($tid,'hive_loc_type','{ltype}');
  $c++;
}}
echo $c;
"""
    out = wp_eval(php)
    try:
        return int(out.strip().split()[-1])
    except ValueError:
        return 0


def seed_mahalle_variants(mslug: str, mname: str) -> int:
    rows = [{"slug": f"{mslug}-{vslug}", "name": f"Kuşadası {mname} {vname}", "vname": vname} for vslug, vname in VARIANTS]
    payload = base64.b64encode(json.dumps(rows, ensure_ascii=False).encode()).decode()
    php = f"""
$p = get_term_by('slug', '{mslug}', 'companion_category');
if (!$p) {{ echo '0'; return; }}
$pid = (int)$p->term_id;
$rows = json_decode(base64_decode('{payload}'), true);
$c = 0;
foreach ($rows as $row) {{
  if (get_term_by('slug', $row['slug'], 'companion_category')) continue;
  $r = wp_insert_term($row['name'], 'companion_category', array('slug'=>$row['slug'],'parent'=>$pid));
  if (is_wp_error($r)) continue;
  $tid = (int)$r['term_id'];
  update_term_meta($tid,'hive_cat_group','variant_mahalle');
  update_term_meta($tid,'hive_geo_mahalle','{mname.replace("'", "\\'")}');
  update_term_meta($tid,'hive_variant',$row['vname']);
  $c++;
}}
echo $c;
"""
    out = wp_eval(php)
    try:
        return int(out.strip().split()[-1])
    except ValueError:
        return 0


def main() -> int:
    total = 0
    for mslug, mname, streets in MAHALLELER:
        for sslug, sname, ltype in streets:
            n = seed_street_variants(mslug, mname, sslug, sname, ltype)
            total += n
            print(f"  {mslug}/{sslug}: +{n}", flush=True)
        n2 = seed_mahalle_variants(mslug, mname)
        total += n2
        print(f"  {mslug} mahalle varyant: +{n2}", flush=True)
    print(f"Toplam yeni varyant: {total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
