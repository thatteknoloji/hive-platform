#!/usr/bin/env python3
"""
Instagram hikayeleri — 24 sexy GIF seed (WP-CLI tetikleyici).

VPS'te: python3 seed-instagram-stories.py
"""
from __future__ import annotations

import subprocess
import sys

WP = ["docker", "exec", "hive_wordpress", "wp", "--allow-root", "--url=https://balkutusu.com"]


def wp(args: list[str]) -> str:
    r = subprocess.run(WP + args, capture_output=True, text=True)
    if r.returncode != 0 and r.stderr:
        print(r.stderr.strip(), file=sys.stderr)
    return (r.stdout or "").strip()


def main() -> None:
    wp(["option", "delete", "hive_ig_stories_v3"])
    wp(["option", "delete", "hive_ig_stories_v2"])
    out = wp([
        "eval",
        "hive_seed_instagram_stories(); "
        "$n = count(get_posts(array('post_type'=>'story','posts_per_page'=>-1,'post_status'=>'publish',"
        "'meta_query'=>array(array('key'=>'_story_permanent','value'=>'1'))))); "
        "echo 'seeded_stories=' . $n;",
    ])
    print(out)
    active = wp([
        "eval",
        "echo count(get_posts(array('post_type'=>'story','posts_per_page'=>-1,'post_status'=>'publish',"
        "'meta_query'=>array('relation'=>'OR',"
        "array('key'=>'_story_permanent','value'=>'1'),"
        "array('key'=>'_story_expires','value'=>time(),'compare'=>'>','type'=>'NUMERIC')))));",
    ])
    print(f"active_stories={active}")
    wp(["cache", "flush"])


if __name__ == "__main__":
    main()
