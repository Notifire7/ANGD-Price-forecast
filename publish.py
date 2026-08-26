#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build ไฟล์สำหรับ GitHub Pages ลง docs/ โดย **ลิงก์ของลูกค้าไม่เปลี่ยนทุกเดือน**

    python3 publish.py

ได้หน้าเดียว รวมทุกกลุ่มไว้ในไฟล์เดียว แยกกันด้วยรหัสผ่าน:

    docs/index.html   -> https://<user>.github.io/<repo>/

ลูกค้าทุกกลุ่มใช้ลิงก์เดียวกัน ต่างกันแค่รหัส
แต่ละรหัสถอดได้เฉพาะข้อมูลกลุ่มตัวเอง (กุญแจคนละดอก ดู build.py)
ไม่ใช่แค่ซ่อนบนหน้าจอ — กลุ่มอื่นเป็น ciphertext ที่เปิดไม่ได้เลย

แจกลิงก์ครั้งเดียวจบ เดือนหน้าแค่ push ทับ ลูกค้ากดลิงก์เดิมได้เลย
ไฟล์ internal ไม่ถูกเผยแพร่ (ตั้งใจ — มันเห็นครบทุกกลุ่ม)
"""
import json, os, shutil, subprocess, sys

DOCS = "docs"

# โฟลเดอร์รายกลุ่มจากสมัยที่ยังแตกเป็น 4 หน้า — เก็บไว้กวาดทิ้งให้ docs/ สะอาด
OLD_SLUGS = ["fo", "cogen-8", "lpg", "cogen3"]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "profiles.json"
    raw = json.load(open(src, encoding="utf-8"))
    profiles = raw["profiles"] if isinstance(raw, dict) else raw

    if not profiles:
        sys.exit(f"[!] {src} ไม่มี profile เลย")

    # กันพลาด: หน้าที่ส่งลูกค้าต้องไม่มี profile ที่เห็นหลายกลุ่ม (นั่นคือไฟล์ internal)
    wide = [p["label"] for p in profiles if len(p.get("view", [])) > 1]
    if wide:
        sys.exit(f"[!] profile ต่อไปนี้เห็นมากกว่า 1 กลุ่ม: {wide}\n"
                 f"    หน้าที่ส่งลูกค้าห้ามมี profile แบบนี้ — "
                 f"ถ้าจะ build ไฟล์ internal ใช้ build.py ออกไปที่ out/ แทน")

    os.makedirs(DOCS, exist_ok=True)
    open(f"{DOCS}/.nojekyll", "w").close()

    subprocess.run(["python3", "build.py", "--profiles", src,
                    "--out", f"{DOCS}/index.html"], check=True,
                   stdout=subprocess.DEVNULL)

    removed = []
    for slug in OLD_SLUGS:
        d = f"{DOCS}/{slug}"
        if os.path.isdir(d):
            shutil.rmtree(d)
            removed.append(slug)

    size = os.path.getsize(f"{DOCS}/index.html") / 1024
    print(f"เขียนลง {DOCS}/index.html แล้ว ({size:.0f} KB) "
          f"· {len(profiles)} กลุ่ม {len(profiles)} รหัส\n")
    if removed:
        print(f"(ลบโฟลเดอร์รายกลุ่มแบบเก่าทิ้ง: {', '.join(removed)})\n")

    print("ลิงก์เดียวแจกได้ทุกกลุ่ม (แทน <user>/<repo> ด้วยของจริง)\n")
    print("  https://<user>.github.io/<repo>/\n")
    print("รหัสของแต่ละกลุ่ม\n")
    w = max(len(p["label"]) for p in profiles)
    for p in profiles:
        print(f"  {p['label']:<{w}}  {p['password']}")
    print("\nขั้นต่อไป:  python3 preflight.py && git add docs "
          "&& git commit -m 'update' && git push")


if __name__ == "__main__":
    main()
