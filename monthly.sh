#!/usr/bin/env bash
# รอบเดือน: ดึงข้อมูล -> เทียบกับรอบก่อน -> build -> ตรวจความปลอดภัย -> push
#
#   ./monthly.sh                   # หยิบ .xlsx ใหม่ล่าสุดใน input/ เอง
#   ./monthly.sh "path/ไฟล์.xlsx"  # ระบุเอง
#   ./monthly.sh --yes             # ไม่ต้องถามยืนยัน
#
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p input archive out

AUTO=0; XLSX=""
for a in "$@"; do
  case "$a" in --yes|-y) AUTO=1 ;; *) XLSX="$a" ;; esac
done

if [ -z "$XLSX" ]; then
  XLSX=$(ls -t input/*.xlsx 2>/dev/null | head -1 || true)
  [ -n "$XLSX" ] || { echo "[!] ไม่เจอ .xlsx ใน input/ — เอาไฟล์จาก Marketing มาวางก่อน"; exit 1; }
  echo "ใช้ไฟล์ล่าสุดใน input/: $(basename "$XLSX")"; echo
fi

echo "── 1. ดึงข้อมูล ──────────────────────────────"
python3 extract.py "$XLSX" --out data_new.json
STAMP=$(python3 -c "import json;print(json.load(open('data_new.json'))['as_of'][:7])")

echo
if [ -f data.json ]; then
  echo "── 2. เทียบกับรอบก่อน ────────────────────────"
  python3 diff.py data.json data_new.json || true
  OLD=$(python3 -c "import json;print(json.load(open('data.json'))['as_of'][:10])")
  cp data.json "archive/data_${OLD}.json"
  echo; echo "(เก็บรอบก่อนไว้ที่ archive/data_${OLD}.json)"
else
  echo "── 2. รอบแรก ไม่มีอะไรให้เทียบ ───────────────"
fi
mv data_new.json data.json

if [ "$AUTO" -eq 0 ]; then
  echo
  read -rp "ตัวเลขโอเคมั้ย จะ build ต่อเลยไหม [y/N] " ans
  [[ "${ans:-}" =~ ^[Yy]$ ]] || { echo "หยุดไว้ก่อน — data.json อัปเดตแล้ว มาสั่ง build ทีหลังได้"; exit 0; }
fi

echo
echo "── 3. build ไฟล์ ─────────────────────────────"
python3 publish.py                                 # -> docs/  (ลิงก์ลูกค้าคงเดิม)
python3 build.py --profiles profiles_internal.json --out "out/internal_${STAMP}.html"
echo "   internal_${STAMP}.html -> out/ (ใช้ภายใน ไม่ถูก push)"

if [ -d .git ]; then
  echo
  echo "── 4. ตรวจความปลอดภัยก่อน push ───────────────"
  python3 preflight.py || { echo; echo "[!] หยุด — แก้ให้ผ่านก่อนค่อย push"; exit 1; }

  if [ "$AUTO" -eq 0 ]; then
    echo
    read -rp "push ขึ้น GitHub เลยไหม [y/N] " ans2
    [[ "${ans2:-}" =~ ^[Yy]$ ]] || { echo "ยังไม่ push — สั่ง git push เองทีหลังได้"; exit 0; }
  fi
  git add docs
  git commit -qm "ราคาก๊าซ ${STAMP}" || echo "   (ไม่มีอะไรเปลี่ยน)"
  git push
  echo "   push แล้ว — ลูกค้ากดลิงก์เดิมได้เลย"
else
  echo
  echo "(ยังไม่ได้ทำเป็น git repo — ข้ามขั้นตอน push)"
fi

echo
echo "เช็คก่อนแจ้งลูกค้า: เปลี่ยนรหัสผ่านใน profiles.json แล้วหรือยัง"
