#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
เทียบ data.json รอบใหม่กับรอบก่อน — ดูว่าอะไรเปลี่ยนก่อนส่งลูกค้า

    python3 diff.py archive/data_2026-07.json data.json
"""
import json, sys

MON = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
       "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
TOL = 0.01


def lab(k):
    """(ปี, เดือน) -> 'ต.ค. 69'"""
    y, m = k
    return f"{MON[m-1]} {str(y + 543)[2:]}"


def series(g, year):
    """คืน {((ปี, เดือน), ชื่อชุด): (ราคา, สถานะ)}
    ไฟล์รุ่นเก่าที่มีปีเดียวไม่มีฟิลด์ year ในแต่ละเดือน -> ใช้ปีของไฟล์แทน"""
    out = {}
    for m in g["months"]:
        k = (m.get("year", year), m["month"])
        if g["kind"] == "cogen":
            out[(k, "")] = (m["price"], m["status"])
        else:
            for b in m["blocks"]:
                out[(k, b["label"])] = (b["price"], m["status"])
    return out


def span(d):
    e = d.get("end_year", d["year"])
    return f"ปี {d['year']}" if e == d["year"] else f"ปี {d['year']}–{e}"


def main():
    if len(sys.argv) != 3:
        sys.exit("ใช้: python3 diff.py <ไฟล์เก่า.json> <ไฟล์ใหม่.json>")
    old, new = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])

    print(f"เก่า : {old['source_file']}  (ณ {old['as_of']}, {span(old)})")
    print(f"ใหม่ : {new['source_file']}  (ณ {new['as_of']}, {span(new)})")
    print("(เทียบเฉพาะเดือนที่มีทั้งสองรอบ)\n")

    o = {g["id"]: g for g in old["groups"]}
    total_moved = 0

    for gn in new["groups"]:
        if gn["id"] not in o:
            print(f"■ {gn['name']}  — กลุ่มใหม่ ไม่มีในรอบก่อน\n")
            continue
        go = o[gn["id"]]
        so, sn = series(go, old["year"]), series(gn, new["year"])

        firmed, moved = [], []
        for k, (pn, stn) in sn.items():
            if k not in so:
                continue
            po, sto = so[k]
            if sto == "forecast" and stn == "actual" and k[1] in ("", "Block 1"):
                firmed.append(k[0])
            if po is not None and pn is not None and abs(pn - po) > TOL:
                moved.append((k, po, pn))

        print(f"■ {gn['name']}")
        if firmed:
            print(f"    ประมาณการ → ราคาจริง: {', '.join(lab(k) for k in sorted(set(firmed)))}")
        if not moved:
            print("    ราคาไม่เปลี่ยน\n")
            continue

        total_moved += len(moved)
        # สรุปรายเดือน โดยใช้ Block 1 เป็นตัวแทนของกลุ่ม block
        rep = [(k, a, b) for k, a, b in moved if k[1] in ("", "Block 1")]
        for (k, lbl), po, pn in sorted(rep):
            d = pn - po
            arrow = "▲" if d > 0 else "▼"
            flag = "  ← เดือนที่แจ้งไปแล้วว่าเป็นราคาจริง" if so[(k, lbl)][1] == "actual" else ""
            print(f"    {lab(k):<9} {po:>8.2f} → {pn:>8.2f}   {arrow}{abs(d):>7.2f}"
                  f" ({d/po*100:+.1f}%){flag}")
        others = len(moved) - len(rep)
        if others:
            print(f"    (Block อื่นขยับด้วยอีก {others} ค่า)")
        print()

    if total_moved == 0:
        print("สรุป: ไม่มีตัวเลขไหนเปลี่ยนเลย")
    else:
        print(f"สรุป: มี {total_moved} ค่าที่เปลี่ยน — เช็คบรรทัดที่มี ← ให้ดี "
              f"เพราะเป็นเดือนที่เคยแจ้งลูกค้าว่าเป็นราคาจริงแล้ว")


if __name__ == "__main__":
    main()
