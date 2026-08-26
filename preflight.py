#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ตรวจก่อน push ว่าไม่มีความลับหลุดขึ้น git

    python3 preflight.py

เช็ค 3 อย่าง
  1. ไฟล์ลับถูก .gitignore กันจริงไหม
  2. ในสิ่งที่ staged/tracked มีรหัสผ่านหรือราคาแบบ plaintext ปนไหม
  3. ประวัติ git ที่ผ่านมาเคยมีไฟล์ลับหลุดไปแล้วหรือยัง
"""
import json, os, subprocess, sys

SECRETS = ["profiles.json", "profiles_internal.json", "data.json",
           "data_new.json", "archive/", "input/", "out/"]

def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main():
    if git("rev-parse", "--git-dir")[0] != 0:
        sys.exit("[!] โฟลเดอร์นี้ยังไม่ใช่ git repo — รัน git init ก่อน")

    bad = []

    # 1) .gitignore กันได้จริงไหม
    print("1. ตรวจ .gitignore")
    for p in SECRETS:
        if p.endswith("/") and not os.path.isdir(p):
            continue
        if not p.endswith("/") and not os.path.exists(p):
            continue
        if git("check-ignore", "-q", p)[0] == 0:
            print(f"   ok   {p}")
        else:
            print(f"   [!]  {p}  ไม่ถูกกัน")
            bad.append(f".gitignore ไม่ได้กัน {p}")

    # 2) ไฟล์ที่ tracked อยู่ตอนนี้
    print("\n2. ตรวจไฟล์ที่ git กำลังติดตาม")
    tracked = git("ls-files")[1].splitlines()
    for f in tracked:
        if any(f == s or f.startswith(s) for s in SECRETS):
            print(f"   [!]  {f}  ถูก track อยู่")
            bad.append(f"{f} ถูก track อยู่ — สั่ง git rm --cached {f}")
    else:
        if not bad:
            print(f"   ok   {len(tracked)} ไฟล์ ไม่มีของลับ")

    # 3) รหัสผ่านโผล่ในไฟล์ที่ tracked ไหม
    print("\n3. ตรวจว่ารหัสผ่านโผล่ในไฟล์ที่จะ push ไหม")
    pws = []
    for src in ("profiles.json", "profiles_internal.json"):
        if os.path.exists(src):
            raw = json.load(open(src, encoding="utf-8"))
            pws += [p["password"] for p in
                    (raw["profiles"] if isinstance(raw, dict) else raw)]
    hits = 0
    for f in tracked:
        try:
            body = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for pw in pws:
            if pw and pw in body:
                print(f"   [!]  เจอรหัส '{pw}' ในไฟล์ {f}")
                bad.append(f"รหัสผ่านโผล่ใน {f}")
                hits += 1
    if not hits:
        print(f"   ok   ไม่เจอรหัสผ่านใน {len(tracked)} ไฟล์")

    # 4) ประวัติเก่า
    print("\n4. ตรวจประวัติ git ย้อนหลัง")
    code, hist = git("log", "--all", "--pretty=format:", "--name-only")
    if code == 0 and hist:
        past = {f for f in hist.splitlines() if f}
        leaked = sorted(f for f in past
                        if any(f == s or f.startswith(s) for s in SECRETS))
        if leaked:
            print("   [!]  เคยหลุดขึ้น git ไปแล้ว:")
            for f in leaked:
                print(f"          {f}")
            bad.append("มีไฟล์ลับอยู่ในประวัติ git — ลบไฟล์เฉย ๆ ไม่พอ")
        else:
            print("   ok   ไม่เคยมีไฟล์ลับใน history")
    else:
        print("   ok   ยังไม่มี commit")

    print()
    if bad:
        print("=" * 55)
        print("อย่าเพิ่ง push — เจอปัญหา " + str(len(bad)) + " ข้อ\n")
        for b in dict.fromkeys(bad):
            print("  • " + b)
        print("\nถ้ารหัสผ่านหลุดขึ้น remote ไปแล้ว การลบ commit ไม่พอ")
        print("ต้องถือว่ารหัสนั้นตายแล้ว เปลี่ยนรหัสใน profiles.json แล้ว build ใหม่")
        print("=" * 55)
        sys.exit(1)

    print("ผ่านหมด — push ได้")


if __name__ == "__main__":
    main()
