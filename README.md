# Parking Lab — Phase 1

เว็บทดลองเครื่องมือจัดผังที่จอดรถ สำหรับเตรียมเปรียบเทียบ RL/QRL ในระยะถัดไป

## เปิดใช้งาน

ใช้ Python 3.9 ขึ้นไป ไม่ต้องติดตั้ง package เพิ่ม เปิด terminal ในโฟลเดอร์นี้แล้วรัน:

```sh
python3 main.py
```

เปิด [Parking Lab บนเครื่อง](http://127.0.0.1:8000) เปลี่ยน port ได้ด้วย `python3 main.py --port 8001` หยุดด้วย Ctrl+C

## วิธีทดลอง

### ลากวางแบบเกม

- เมนู **BUILD MENU** มีช่อง 90°, 45°, ขนาน และถนน 3.5/6 เมตร ลากการ์ดลงผังเพื่อวาง หรือคลิกเลือกการ์ดแล้วคลิกตำแหน่งบนผังเพื่อวางซ้ำได้
- เลือก **เลือก / ย้าย** แล้วลากอุปกรณ์เดิมเพื่อย้าย รักษาระยะจากจุดที่จับเพื่อไม่ให้อุปกรณ์กระโดด
- ปรับความยาวถนนที่ช่อง **ความยาวถนน (m)** ก่อนวาง และใช้ปุ่มหมุนหรือ `R` เพื่อหมุนครั้งละ 90° ใช้ `Esc` ยกเลิกการลากและกลับสู่โหมดเลือก
- ถอนอุปกรณ์ที่เลือกด้วยปุ่ม **ถอนที่เลือก** หรือ `Delete` โดยปุ่มลัดไม่ทำงานระหว่างกรอกข้อมูล
- ระหว่างลากมีป้ายอุปกรณ์ตามเมาส์ตั้งแต่ออกจากเมนู และเงาเหลืองตาม pointer ทันทีเมื่อเข้าผัง ระหว่างรอ `/api/propose` ไป snap และตรวจ policy ใน Python: เขียวผ่าน แดงปฏิเสธ หากเรียก server ไม่สำเร็จ เงาเหลืองยังคงอยู่พร้อมข้อความแจ้ง การตรวจเงาไม่เปลี่ยนผังและไม่นับ action เมื่อปล่อยจะตรวจซ้ำก่อน commit ถ้าถูกปฏิเสธ ผังเดิมจะคงอยู่และมี rejection ใน log; การปล่อยนอกผัง/ยกเลิกไม่นับ action
- เมนูติดด้านบนขณะเลื่อนหน้า ใช้เมาส์หรือ pointer บนอุปกรณ์สัมผัสได้ หน้า Model runs และ Replay ไม่เปิดการลากแก้ผัง

### กรอกพิกัดโดยตรง

1. หน้า **ทดสอบเครื่องมือ** แสดงผังสี่เหลี่ยม 48 × 30 เมตร มีถนนเริ่มต้นเชื่อมประตูสองฝั่ง (Action 1)
2. เปิดแถบ **เครื่องมือจัดวาง / Session settings** เหนือผัง
3. เลือกชนิด slot/road, รูปแบบ, พิกัดกึ่งกลาง X/Y และ rotation แล้วกดวาง คลิกพื้นที่ว่างเพื่อกรอกพิกัดได้
4. สำหรับ seed 42 ถนนอยู่ Y=9 กว้าง 6 เมตร: ทดลอง 90° ที่ X=8, Y=14.75, rotation=0; 45° ที่ X=16, Y=15; parallel ที่ X=26, Y=13.25 (grid 0.25)
5. วางซ้ำตำแหน่งเดิมเพื่อทดสอบ rejection ดูเหตุผลที่ด้านขวาและ log ด้านซ้าย
6. เลือก object จากผังหรือรายการ แก้ X/Y และ rotation แล้วกดย้าย หรือกดถอน การย้ายคงชนิด/ขนาดเดิมไว้
7. ทางรถวางเป็นสี่เหลี่ยมแนว 0/90° กว้าง 3.5/6 m ปรับความยาวได้ ห้ามถนนทับกัน แต่ต่อชนขอบกันได้ ทุก slot ต้องติดถนนที่ต่อกับ entry และ exit
8. กด **บันทึกผล JSON** ก่อนเริ่ม session ใหม่ ผลทดสอบมืออยู่ `Outputs/manual_*.json`
9. หน้า **ผลลัพธ์ / Replay** เลือกไฟล์ กดเปิดผลลัพธ์ แล้วใช้ slider หรือ Play เพื่อดูแต่ละ action การปฏิเสธยังมี frame ของตนเอง

`reset` ล้างอุปกรณ์และนับเป็น action แต่ไม่รีเซ็ต budget ส่วน **สร้างผัง / เริ่ม session ใหม่** เริ่มประวัติใหม่ตาม seed, grid และ limit ที่เลือก การเปลี่ยนค่า grid ในฟอร์มจะมีผลเมื่อเริ่ม session ใหม่เท่านั้น ค่าเริ่มต้น 200 actions รวมคำสั่งที่ถูกปฏิเสธ

## ขอบเขต

รองรับ 90°, 45°, parallel ขนาดจริง 5.5 × 2.5 m; grid 0.1/0.25/0.50 m ข้อมูลตัวอย่างถูกบันทึกใน `Layouts/rectangle_<seed>.json` ค่า seed เดิมให้ผังเดิม

UI รับ event และวาดภาพเท่านั้น คำสั่งผ่าน `main.py` ไป `Arrange_tools/controller.py` และ policy modules เครื่องมือไม่ยอม commit การเปลี่ยนที่ทำให้ผังผิดกฎ

หน้า **Model runs** และโฟลเดอร์โมเดลเป็น scaffold ยังไม่มี RL/QRL หรือการฝึกจริง ผลใน `Outputs/Model_RL` และ `Outputs/Model_QRL` จะใช้ใน Phase 2 การ preview รองรับ schema กลาง โดยไม่ต้องรันโมเดล

ต้นแบบตรวจ geometry และ connectivity เบื้องต้น ยังไม่ตรวจการเลี้ยวรถจริง ค่ามิติเป็น experimental profile ของผู้ใช้ ไม่ใช่แบบที่รับรองมาตรฐานก่อสร้างหรือข้อกำหนดไทย อ่านเหตุผลและข้อจำกัดใน `AI_README.md` และเอกสารอ้างอิงใน `LITERATURE.md`

## โครงสร้าง

```text
main.py                       ประกอบระบบและรับผิดชอบ session/load/save
Arrange_tools/controller.py   วาง ย้าย ถอน reset
Arrange_tools/geometries.py   polygon / collision geometry
Arrange_tools/grid.py         snap และ sparse occupancy
Arrange_tools/Policies/       กฎแยกตามหน้าที่
Arrange_tools/Slot_layouts/    templates JSON
UI/                           HTTP transport / HTML / CSS / rendering
Models/environment.py         interface กลางสำหรับ Phase 2
Models/Model_RL/               model.py / adapter.py / config.json
Models/Model_QRL/              model.py / adapter.py / config.json
Layouts/                      generator / repository / case JSON
Outputs/                      repository / manual JSON / model directories
Tests/                        tests สำหรับพฤติกรรมเครื่องมือ
```

## ทดสอบ

```sh
python3 -m unittest discover -s Tests -v
```

API สำหรับตรวจเครื่องมือ: `GET /api/state`, `GET /api/grid`, `GET /api/outputs`, `POST /api/action`, `POST /api/session`, `POST /api/save`, `POST /api/preview` ใช้งานบน local server เท่านั้น `/api/grid` ส่ง cell coordinates แบบ sparse แยก obstacles/roads/slots ขนาดจริงยังเก็บเป็นเมตร

Output schema version 1 ฝัง `layout`, `policies`, `templates`, `resolution`, `max_actions`, `initial_items`, `history`, `final_items`, `metrics` แต่ละ history event มี `step`, `timestamp`, `elapsed_seconds`, `command`, `accepted`, `reason`, `before`, `after` ชื่อไฟล์ manual ไม่เขียนทับกันและ preview ไม่เปลี่ยน live session

## Shared placement policies (version 2)

`Arrange_tools/Policies/snapping.py` snaps the centre anchor to the selected grid. Real dimensions and rotated corners are preserved. `collisions.py` rejects every positive-area overlap, including road-road intersections. Edge contact is allowed.

`POST /api/propose` and `/api/action` share Controller preparation and validation through `main.py`. Preview returns snapped geometry and accepted/reason without changing state, history or budget. Commit always checks the latest state again. Earlier saved outputs remain historical replay data; replay does not certify them against the latest policy.
