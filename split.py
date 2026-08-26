#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""อ่าน profiles.json แล้วออกไฟล์ dashboard เดี่ยวให้ทีละ profile

    python3 split.py [profiles.json]
"""
import json, subprocess, sys, os, re

src = sys.argv[1] if len(sys.argv) > 1 else "profiles.json"
raw = json.load(open(src, encoding="utf-8"))
profiles = raw["profiles"] if isinstance(raw, dict) else raw

for pr in profiles:
    stem = "-".join(pr["view"]) if len(pr["view"]) <= 2 else \
           re.sub(r"[^A-Za-z0-9_-]+", "_", pr["label"]).strip("_")
    out = f"ngd_{stem}.html"
    json.dump({"profiles": [pr]}, open("_tmp_profile.json", "w"), ensure_ascii=False)
    subprocess.run(["python3", "build.py", "--profiles", "_tmp_profile.json",
                    "--out", out], check=True)

os.remove("_tmp_profile.json")
print(f"\nเสร็จ {len(profiles)} ไฟล์")
