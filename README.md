## Classical DQN: Train / Test พร้อมใช้งาน

- `Models/Model_RL/model.py`: CNN + remaining-budget MLP, masked epsilon-greedy DQN, replay buffer, Huber TD loss, gradient clipping, hard target sync. CPU implementation for reproducibility and low setup overhead.
- `Models/Model_RL/adapter.py`: calls only shared Environment APIs; no placement/policy logic in UI or model.
- `Models/Model_RL/trainer.py`: independent background jobs, train/evaluation loops, cooperative stop after current action, checkpoints and per-episode JSON snapshots. Manual workspace stays intact while learning.
- `Models/Model_RL/config.json`: pilot 100 episodes, maximum 50 actions/episode, training seeds 42/43/44, evaluation seeds 101/102/105 every 50 episodes. Shared environment default action limit is also 50; manual Tools session remains at 200. Episode can finish early or stop when no placement action remains.
- In Model runs, use **เริ่ม Train DQN**, observe reward / verified-slot charts, then select a saved checkpoint and **Test โมเดลที่เลือก**. Test uses epsilon=0 and does not call optimizer/replay learning. Same shared geometry, audit and reward rules for training and test.
- `Outputs/Model_RL/<run id>/`: `checkpoint.pt` (last), `best.pt` (best training verified slots, not selected on held-out scores), `metrics.json`, `manifest.json`, and train/evaluation/test episode JSON files. Replay reads snapshots without rerunning. Config, catalogue hash, policy and vehicle profile are recorded. Checkpoint loading rejects environment signature mismatch.
- Checkpoints support evaluation; restarting training is a fresh run. Replay buffer and random-generator state are not persisted, so this is not exact training resume.
- New runs use the finite existing catalogue: full horizontal roads and 90°/45° rows, fixed candidate anchors. Parallel is supported in manual tools but is not yet an RL action. No remove/move actions in this first DQN baseline. Model_QRL remains unimplemented.
- Rewards count vehicle-verified slots only. Vehicle search is bounded: unknown gets no positive slot reward. Planner speed and incomplete search are methodological limitations. Runtime and learning quality must be measured; implementation tests do not prove convergence or quantum advantage.
- Torch is in `requirements.txt`; run with the project virtual environment. Training is opt-in: no 100-episode job automatically starts on opening the UI. Short smoke tests verify that real neural weights update and checkpoints reload.

## แก้พื้นที่เข้าช่องก้างปลา 45°
พื้นที่เชื่อมปากช่องกับถนนต้องขยายตามแกนยาวของรถเฉียง ไม่ใช่ฉายในแนวดิ่ง การฉายเดิมตัดมุมท้ายรถออกจากพื้นที่อนุญาตจนไม่มีเส้นทางทั้งที่วางช่องถูกกฎแล้ว แก้ใน `Arrange_tools/Policies/turnings.py` โดยยังตัดสิ่งกีดขวาง ช่องข้างเคียง และขอบเขตออกเช่นเดิม มี regression ตำแหน่ง x=44.75, y=15, rotation=0 ในผังมาตรฐาน

## อัปเดตทิศทางถนนและการค้นหาเส้นทางรถ

- ถนน 3.5 m เป็น **ทางเดียว** ตาม rotation: 0° ตะวันออก →, 90° ใต้ ↓, 180° ตะวันตก ←, 270° เหนือ ↑; ถนน 6 m เป็นสองทาง
- Palette และผังแสดงลูกศร ONE WAY ซ้ำตลอดถนน หมุนด้วย R เพื่อเปลี่ยนทิศ ไม่มีการเปลี่ยนทิศถนนเก่าโดยอัตโนมัติ
- `Policies/traffics.py` ตรวจทิศจริง และ `accesses.py` ตรวจกราฟแบบมีทิศ อนุญาตถอยสวนลูกศรเฉพาะเข้าจอดใกล้ช่องเมื่อรถหันตามทิศการจราจร
- `Policies/paths.py` เพิ่ม bounded hybrid A* บน rear-axle bicycle poses สำหรับถนนเชื่อม/เลี้ยวและจอดขนาน ใช้ swept-body check เดียวกับ templates; ค้นหาจากท่าจอดจริงไปประตูทั้งสองและย้อน controls สำหรับเส้นทางเข้า
- ใช้ search budget 12,000 expansions ต่อการค้นหาและ discretization; ไม่พบเส้นทางยังเป็น unknown ไม่ใช่ข้อพิสูจน์ว่าจอดไม่ได้ ไม่ให้ reward ช่องที่ยังไม่ผ่าน
- รีสตาร์ต Python server เพื่อโหลด policy ใหม่ แล้วตรวจผลเดิมใหม่; JSON ที่เคยบันทึกเป็นผลตามเวอร์ชันเดิม

# Parking Lab — Phase 1

## ใหม่: ตรวจรถเข้า–ออก

เปิดด้วย virtual environment แล้วกด **ตรวจรถเข้า–ออก** หลังจัดผัง เลือกช่องที่ผ่านเพื่อดูทางเข้า (เขียว), ทางออก (น้ำเงิน) และ footprint ของรถตามเส้นทาง เปิดผลตรวจรายช่องเพื่อดูเหตุผล

- รถทดลองตั้งค่าที่ `Arrange_tools/vehicle.json`: 4.5 × 1.8 m, wheelbase 2.7 m, max steering 30°, clearance 0.05 m เป็นสมมติฐานทดลอง
- ผ่าน = พบเส้นทางเข้าและออกใน low-speed bicycle model; ไม่ผ่าน = ขัดข้อกำหนดแน่นอน; ยังยืนยันไม่ได้ = ไม่พบในชุดเส้นทางจำกัดหรือยังไม่รองรับกรณีนั้น
- ช่องจอดอื่นถือว่ามีรถจอดอยู่แล้ว ผล audit ไม่เปลี่ยนการวางหรือใช้ action budget แต่จะถูกล้างเมื่อแก้ผัง
- Environment reward ปรับเป็นจำนวนช่อง **ที่พบเส้นทางผ่านเพิ่มขึ้นจริง** ส่วนช่องที่ geometry ผ่านแต่รถ failed/unknown ไม่ได้ slot reward Action mask ยังเป็นการกรอง geometry/topology เบื้องต้น
- วิธีนี้ลอง forward/reverse single-arc maneuvers เท่านั้น ไม่ใช่ complete motion planner ตัวอย่าง 45° บางกรณียังได้ unknown และต้องเพิ่มวิธีค้นหา ไม่ใช่หลักฐานว่าจอดไม่ได้
- ยังไม่ตรวจความชัน รถขนาดอื่นนอก profile วัตถุเคลื่อนที่ และกฎหมายก่อสร้าง ผลที่พบไม่ใช่การรับรองทางวิศวกรรม

เพิ่ม Shapely ใน requirements แล้ว ใช้ `../parking_qrl-env/bin/python -m pip install -r requirements-lock.txt` หากสร้าง environment ใหม่ และรีสตาร์ต Python server เพื่อโหลด policy ใหม่

หากเห็นเมนูแถวแต่ log แจ้ง `Unknown action` ให้บันทึก JSON แล้วรีสตาร์ต Python server ด้วย virtual environment การรีเฟรชหน้าเว็บอย่างเดียวไม่อัปเดต Python ที่รันค้างอยู่ รุ่นใหม่มีข้อความเตือนกรณีนี้ หากต้องการเปิด manual session ที่บันทึกไว้ต่อ ใช้ `../parking_qrl-env/bin/python main.py --resume Outputs/manual_<ชื่อไฟล์จริง>.json` จากโฟลเดอร์นี้ ระบบจะตรวจผังสุดท้ายกับ policy ปัจจุบันก่อนเปิดต่อ

## ใหม่: Parking Row และ RL Environment

ในโฟลเดอร์ `parking_qrl` ให้เปิดด้วย virtual environment ของโปรเจกต์:

```sh
../parking_qrl-env/bin/python main.py
```

หากสร้าง environment ใหม่ ให้ติดตั้ง `requirements-lock.txt` (เวอร์ชันที่ตรวจแล้ว) หรือ `requirements.txt` ก่อน เว็บเครื่องมือเดิมยังรันด้วย Python standard library ได้ แต่การทดลอง Environment ต้องมี NumPy และ Gymnasium

- **ทดสอบเครื่องมือ:** เลือกการ์ดแถว 90° หรือแถว 45° ตั้งความยาวถนน/แถวแล้วลากลงผัง จุดจับอยู่กลางช่องแรก ทั้งแถวตรวจพร้อมกัน ถ้าไม่ผ่านจะไม่วางสักช่อง และนับเพียงหนึ่ง action ต่อครั้ง ถนนต้องวางและต่อ entry/exit ก่อน
- **Model runs → Reset Environment:** เริ่มผังว่าง ไม่มีถนน, grid 0.5 m, budget 200 actions เลือกคำสั่งถนนที่เชื่อมประตูทั้งสองแล้วกด Step จากนั้นเลือกคำสั่ง `place_row` ที่ผ่าน mask เพื่อดู reward หน้าเดียวกัน ปุ่ม Train ยังถูกปิดไว้
- reward ตั้งต้น: +1 ต่อช่องเพิ่ม, -1 สำหรับ action ผิดกฎ, -0.01 ทุก action รวม finish ปรับที่ `Models/config.json` ค่านี้ยังไม่ผ่านการ tune
- เลือก finish เพื่อจบ episode หรือใช้ครบ budget ระบบจะแยก terminated/truncated บันทึกผลด้วยปุ่ม JSON แล้วเปิดใน Replay ได้ เป็น environment test ไม่ใช่ผลของโมเดล
- ระหว่าง environment test แก้มือไม่ได้ หากต้องการกลับไปลากวาง ให้ไปหน้าเครื่องมือ เปิด Session settings แล้วเริ่ม session ใหม่
- แถวที่สร้างยังเลือกย้าย/ถอน **รายช่อง** ได้ใน manual mode ยังไม่มีคำสั่งย้าย/ถอนทั้งกลุ่มแถว

ตัวอย่างแถวใน seed 42/manual grid 0.25: 90° ที่ X=8, Y=14.75, length=15, rotation=0 ได้ 6 ช่อง; 45° ที่ X=8, Y=15, length=15, rotation=0 ได้ 3 ช่อง ทดลองคนละ session เพื่อหลีกเลี่ยงการทับกัน

Environment มี action catalogue 659 รายการสำหรับผังตัวอย่าง 48 × 30 m ใช้ candidate stride 6 m แม้ geometry snap ที่ 0.5 m ไม่ได้แปลว่าครอบคลุมทุกจุด grid มี observation เป็น 5-channel grid + remaining budget และ `action_masks()` แยกต่างหาก ก่อนทำ DQN ต้องนำ mask ไปใช้ทั้งตอนเลือก action และคำนวณ target

```sh
../parking_qrl-env/bin/python -m unittest discover -s Tests -v
node Tests/preview.test.js
```

การเข้าถึงยังเป็น geometry/connectivity proxy ไม่ตรวจ swept path หรือรัศมีเลี้ยวจริง ไม่ควรเรียกช่องที่ reward ว่ารับรองการขับรถเข้าจอดได้จริง

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

หน้า **Model runs** ทดลอง Environment ด้วย Reset/Step ได้แล้ว แต่โฟลเดอร์โมเดลยังเป็น scaffold ไม่มี RL/QRL หรือการฝึกจริง ผลทดสอบ Environment อยู่ `Outputs/environment_*.json` ส่วน `Outputs/Model_RL` และ `Outputs/Model_QRL` เตรียมไว้สำหรับการฝึกในอนาคต การ preview รองรับ schema กลางโดยไม่ต้องรันโมเดล

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
Models/environment.py         Gymnasium reset/step/observation/action mask
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
