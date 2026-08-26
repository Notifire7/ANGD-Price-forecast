#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ประกอบ data.json + template.html -> dashboard ไฟล์เดียว
รองรับหลายรหัสผ่าน แต่ละรหัสเปิดดูได้คนละกลุ่ม

  python3 build.py --profiles profiles.json --out dashboard.html

โครงสร้างการเข้ารหัส
  - ข้อมูลแต่ละกลุ่ม  -> เข้ารหัส AES-256-GCM ด้วยกุญแจสุ่มของตัวเอง (คนละดอก)
  - แต่ละรหัสผ่าน     -> เก็บ "พวงกุญแจ" เฉพาะกลุ่มที่มีสิทธิ์ เข้ารหัสด้วยคีย์จากรหัสผ่าน
  => รหัสที่ไม่มีสิทธิ์ ถอดก้อนข้อมูลกลุ่มนั้นไม่ได้เลย ไม่ใช่แค่ซ่อนหน้าจอ
"""
import argparse, base64, json, os, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 250_000
b64 = lambda b: base64.b64encode(b).decode()


def seal(key: bytes, obj) -> dict:
    iv = os.urandom(12)
    blob = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False,
                                              separators=(",", ":")).encode(), None)
    return {"iv": b64(iv), "data": b64(blob)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--template", default="template.html")
    ap.add_argument("--profiles", help="ไฟล์ JSON กำหนดรหัสผ่าน/สิทธิ์")
    ap.add_argument("--password", help="โหมดง่าย: รหัสเดียวเห็นทุกกลุ่ม")
    ap.add_argument("--out", default="dashboard.html")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    by_id = {g["id"]: g for g in data["groups"]}

    # ---- โหลดสิทธิ์
    if args.profiles:
        raw = json.load(open(args.profiles, encoding="utf-8"))
        profiles = raw["profiles"] if isinstance(raw, dict) else raw
    elif args.password:
        profiles = [{"label": "ทุกกลุ่ม", "password": args.password, "view": list(by_id)}]
    else:
        sys.exit("[!] ต้องระบุ --profiles หรือ --password อย่างใดอย่างหนึ่ง")

    seen = set()
    for p in profiles:
        for k in ("label", "password", "view"):
            if k not in p:
                sys.exit(f"[!] profile '{p.get('label','?')}' ขาดฟิลด์ {k}")
        bad = [g for g in p["view"] if g not in by_id]
        if bad:
            sys.exit(f"[!] '{p['label']}' อ้างถึงกลุ่มที่ไม่มีอยู่: {bad}\n"
                     f"    กลุ่มที่มี: {list(by_id)}")
        if len(p["password"]) < 10:
            print(f"[เตือน] รหัสของ '{p['label']}' สั้นกว่า 10 ตัว เดาง่าย")
        if p["password"] in seen:
            sys.exit(f"[!] รหัสผ่านซ้ำกัน: {p['password']}")
        seen.add(p["password"])

    used = sorted({g for p in profiles for g in p["view"]}, key=list(by_id).index)

    # ---- เข้ารหัสข้อมูลรายกลุ่ม กุญแจคนละดอก
    gkeys = {gid: os.urandom(32) for gid in used}
    enc_groups = {gid: seal(gkeys[gid], by_id[gid]) for gid in used}

    meta = {k: data[k] for k in ("year", "as_of", "source_file", "unit")}

    # ---- ห่อพวงกุญแจด้วยรหัสผ่าน (salt ร่วม -> ฝั่ง browser คำนวณ PBKDF2 ครั้งเดียว)
    salt = os.urandom(16)
    enc_profiles = []
    for p in profiles:
        kek = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=ITER).derive(p["password"].encode())
        view = sorted(p["view"], key=used.index)
        enc_profiles.append(seal(kek, {
            "label": p["label"],
            "view": view,
            "keys": {gid: b64(gkeys[gid]) for gid in view},
            "meta": meta,
        }))

    enc = json.dumps({"salt": b64(salt), "iter": ITER,
                      "groups": enc_groups, "profiles": enc_profiles},
                     ensure_ascii=False)

    title = args.title or f"ราคาก๊าซธรรมชาติ {data['year']}"
    html = open(args.template, encoding="utf-8").read()
    html = html.replace("__ENC__", enc).replace("__TITLE__", title)
    open(args.out, "w", encoding="utf-8").write(html)

    print(f"สร้าง {args.out}  ({os.path.getsize(args.out)/1024:.0f} KB)")
    print(f"  บรรจุข้อมูล {len(used)} กลุ่ม · {len(profiles)} รหัสผ่าน\n")
    w = max(len(p["label"]) for p in profiles)
    for p in profiles:
        names = " + ".join(by_id[g]["name"] for g in sorted(p["view"], key=used.index))
        print(f"  {p['label']:<{w}}  {p['password']:<24}  ->  {names}")


if __name__ == "__main__":
    main()
