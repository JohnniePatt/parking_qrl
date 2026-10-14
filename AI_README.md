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

## ข้อตกลงกับผู้วิจัย

- ระบบวิจัยจัดผังจอดรถจาก boundary, columns, core, ramps และ gates; ระยะแรกใช้กรณีสี่เหลี่ยม 48 × 30 m พร้อมเสา/Core ตัวอย่างและสุ่มประตู ยังไม่มี CAD import หรือ ramp model สมบูรณ์
- `main.py` เป็น composition root และ API orchestration; `Arrange_tools/controller.py` แก้สถานะการวาง; `Arrange_tools/Policies/` แยกกฎจาก controller; `UI/` แสดงผลและเรียก API เท่านั้น ไม่คำนวณกฎจัดวางเอง
- ชื่อไฟล์ตัวเล็ก ยกเว้น AI_README.md และ LITERATURE.md ที่ผู้ใช้กำหนด; UI ใช้ชื่อนี้ตามผู้ใช้; Models และ Outputs แยก Model_RL / Model_QRL
- UI เป็นเว็บเต็มความกว้าง ฝั่งซ้าย 1/3 มี status ด้านบนและ action log ด้านล่าง ฝั่งขวา 2/3 เป็นพื้นที่ผังและเครื่องมือ มีหน้าเครื่องมือ / Model runs / Replay
- หน่วยเมตร ช่องทุกแบบ 5.5 × 2.5 m มี 90°, 45° และขนาน; grid 0.1 / 0.25 / 0.5 m ขนาดชิ้นงานจริงไม่ถูกขยายให้ลง cell
- ผู้ใช้เคยกำหนด 200 **actions ต่อการรัน** ไม่ใช่ 200 episodes; ล่าสุดอนุมัติข้อเสนอเริ่ม DQN ที่สูงสุด 50 actions ต่อ episode และ 100 episodes สำหรับ pilot จบก่อนได้ ไม่ต้องทำให้ครบ 50; manual tool budget ยังคง 200
- ผู้ใช้ต้องการทำงานต่อเนื่องโดยไม่ขออนุมัติซ้ำในงานที่อนุมัติแล้ว ไม่ commit/push หรือแก้ Git identity/history โดยไม่ได้รับคำขอ

## สภาพแวดล้อมและเครื่องมือปัจจุบัน

- ใช้ virtual environment `../parking_qrl-env`; มี NumPy, Gymnasium, Shapely และ PyTorch; requirements.txt และ requirements-lock.txt อยู่ root โปรเจกต์ PennyLane ยังไม่ติดตั้ง
- เปิดเว็บด้วย `../parking_qrl-env/bin/python main.py`; เปลี่ยน HTML/JS มีผลเมื่อ refresh แต่เปลี่ยน Python ต้อง restart server ก่อนเสมอ ตรวจ capabilities เพื่อกัน static UI ใหม่เรียก server เก่า
- ก่อน restart เว็บที่ผู้วิจัยใช้อยู่ ให้เรียก /api/save เก็บผัง แล้วเปิด `main.py --resume Outputs/<saved manual JSON>` เพื่อรักษา items/history/budget ตรวจว่า snapshot รับคืนได้ก่อนหยุด server
- /api/propose เป็น preview แบบ read-only ใช้ Controller._propose ชุดเดียวกับ commit; UI แสดงเงาเหลืองทันทีและเปลี่ยนเขียว/แดงจากผล backend ห้ามทำ snapping/collision policy ซ้ำใน JavaScript
- Drag จาก palette / คลิกวาง / ลากย้าย / R หมุน / Escape ยกเลิก / Delete ถอน; preview ยกเลิก stale responses และ latency ได้ มี regression JavaScript
- Snap เฉพาะจุดกึ่งกลาง; collision เป็น continuous rectangle SAT ห้ามพื้นที่ทับกันทุกกรณีรวม road-road แต่แตะขอบกันได้ ถนนต่อที่จุดมุมเดียวไม่นับเชื่อม
- `rows.py` ขยายแถว 90/45 เป็น rectangles จริง จัดเป็นหนึ่ง action ทั้งแถว หากช่องใดผิดกฎปฏิเสธทั้งแถว manual ยังย้าย/ถอนรายช่องได้ ยังไม่รองรับแก้ทั้งกลุ่มแถว
- ทุก action รวม rejected มี timestamp UTC, elapsed time, command, accepted/reason, before/after เก็บ JSON เพื่อ Replay โดยไม่รันซ้ำ

## การเข้าถึงและตรวจรถ

- **3.5 m = one way** ตาม rotation 0° → / 90° ↓ / 180° ← / 270° ↑; **6 m = two way** เป็นข้อกำหนดจากผู้วิจัย ห้ามเปลี่ยนกลับเป็นถนนไม่แยกทิศ
- `accesses.py` ตรวจ directed road graph + frontage probes; ถนนยังวางแยกส่วนได้ระหว่างสร้าง แต่ slot ต้องติดถนนที่ต่อถึง entry/exit ตามทิศ
- `vehicles.py` ใช้ low-speed rear-axle bicycle model รถ 4.5 × 1.8 m wheelbase 2.7 m steering 30°; รัศมีล้อหลังขั้นต่ำ ~4.68 m ไม่ใช่ curb-to-curb turning radius
- `turnings.py` ลอง analytic arc templates ก่อน แล้ว `paths.py` ทำ bounded hybrid A* สำหรับเครือข่ายถนนและทุก template; ตรวจ Shapely footprints และ conservative swept envelope ระหว่าง pose พร้อมบังคับทิศใน `traffics.py`
- อนุญาตถอยสวนลูกศรใกล้ช่องเฉพาะการจอดเมื่อหัวรถหันตามทิศจราจร ห้ามใช้ reverse เดินทางไกลสวนทาง
- พื้นที่เชื่อมปากช่องก้างปลาไปถนนต้องขยายตามแกนรถเฉียง ไม่ใช่ vertical projection; บั๊กเดิมทำให้ 45° ถูกปฏิเสธผิด แก้แล้วและมี regression ตำแหน่ง x44.75 y15 rotation0
- ช่องอื่นถือว่ามีรถจอดอยู่ หัก obstacles/ช่องอื่นออกจาก drivable region และ clip boundary เสมอ
- passed = พบ witness เข้าและออกจริง; failed = ขัดเงื่อนไขที่ชัดเจน; unknown = ตัวค้นหายังไม่พบ ไม่ใช่หลักฐานว่าใช้ไม่ได้ ไม่ให้ positive slot reward กับ unknown
- การวางและ Action Mask ตรวจ geometry/access; vehicle audit แยกตรวจภายหลังสำหรับ reward ไม่ทำ path search ทุก preview เพราะช้า ผลเชื่อม graph ไม่เท่ากับรถเลี้ยวผ่าน

## ข้อจำกัดและงานถัดไป

- Classical DQN ใช้งานได้แล้ว แต่ผลทดสอบระบบ/การฝึกสั้นไม่ใช่หลักฐาน convergence และยังไม่มีผลเปรียบเทียบ RL/QRL/GA
- Dataset ปัจจุบันมีเพียง rectangle family เดิม เปลี่ยนตำแหน่ง/บทบาทประตู ตรวจ geometry ซ้ำข้าม split ด้วย `Models/datasets.py` เพราะ seed ต่างกันสร้างผังซ้ำได้
- ชุดประเมินที่ใช้ติดตามทุก 50 episodes เป็น development evaluation; ต้องกัน final test cases แยกสำหรับงานวิจัยจริง
- Candidate actions ยังเป็นกริดตำแหน่งห่าง 6 m ไม่ใช่ทุกตำแหน่ง 0.5 m; ถนนเป็นแนวนอนเต็มผังเท่านั้น ยังไม่มี action ถนนแขนง/ช่องขนาน/ย้าย/ถอนใน DQN baseline
- รองรับผังเสา/core ตัวอย่าง แต่ยังไม่มี accessible parking, door clearance, slope/headroom/ramp dynamics, tandem, polygon boundary ทั่วไป หรือ certification
- Vehicle search จำกัดงบและ discretization อาจให้ unknown กับผังที่ใช้ได้จริง ต้องรายงานผลกระทบและเวลาในการฝึก
- เป้าหมายถัดไปคือ pilot 100 episodes วัดความเร็ว/learning curves ก่อนปรับ hyperparameters หรือขยาย action space จากนั้นทำ Quantum DQN ด้วย environment/reward/split เดียวกัน

## การยืนยันล่าสุด

- Unit/integration tests ครอบคลุม geometry, rows, Gymnasium contract, directed traffic, swept paths, rewards, snapshot restore, Bellman action masking, target sync, checkpoint loading, frozen test weights, background jobs, cancel และ dataset leakage
- Short run บน Environment จริง 4 episodes / เพดาน 4 actions สำหรับ smoke test มี 9 train transitions และ 8 optimizer updates พร้อม saved checkpoint และ evaluation 1 episode; ใช้ batch_size=2 เฉพาะ smoke test ไม่เปลี่ยน default batch_size=32 หรือ 100/50 ใน config
- ห้ามตีความผล smoke test ว่าโมเดลเรียนรู้ดีแล้ว หรือเป็นผลวิจัย; ให้ผู้วิจัยเริ่ม pilot ด้วยค่า default จากหน้า Model runs
