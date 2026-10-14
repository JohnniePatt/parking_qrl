# บริบทและข้อตกลงของ Parking QRL

อัปเดต: 14 ตุลาคม 2026 · Phase 1: โครงระบบและเครื่องมือ ยังไม่ฝึกโมเดล

## เป้าหมายงานวิจัย

สร้างผังจอดรถจากพื้นที่อาคาร เสา Core ทางลาด และทางเข้า–ออก แล้วเปรียบเทียบ Classical RL กับ QRL บน environment และ policy เดียวกัน เป้าหมายคือจำนวนช่องจอด การใช้พื้นที่ การละเมิดข้อกำหนด และเวลาค้นหาคำตอบ ยังไม่มีหลักฐานจากโปรเจกต์นี้ว่า QRL ดีกว่า RL

## ข้อตกลงที่ผู้ใช้ยืนยัน

- ไฟล์โค้ด/JSON ใช้ตัวเล็ก โฟลเดอร์เริ่มตัวใหญ่และลงท้าย s ยกเว้นชื่อที่ผู้ใช้ระบุ ได้แก่ `Arrange_tools`, `UI`, `Model_RL`, `Model_QRL` และเอกสาร `AI_README.md`, `LITERATURE.md`
- ใช้ `main.py` เป็น composition root และ orchestration กลาง
- `Arrange_tools/controller.py` ทำเฉพาะการเปลี่ยนสถานะการวาง กฎต้องอยู่แยกใน `Policies`
- UI เป็นเว็บเต็มความกว้าง หน้าจอ desktop แบ่งซ้าย 1/3 ขวา 2/3 ฝั่งซ้ายครึ่งบนเป็นสถานะ ครึ่งล่างเป็น action log ทางขวาเป็นผังและเครื่องมือ หน้าจอแคบเรียงแนวตั้ง
- UI มีหน้าทดสอบเครื่องมือ หน้ารันโมเดล และหน้า preview/replay; UI มี event bindings และการวาดภาพเท่านั้น ห้ามมีกฎหรือตัวเปลี่ยนสถานะผังใน JavaScript
- 200 หมายถึง **200 actions ต่อ session/run** ไม่ใช่ 200 episodes ปรับได้ และนับคำสั่งที่ถูกปฏิเสธด้วย
- Models แยก `Model_RL`, `Model_QRL` แต่ละตัวมี `model.py`, `adapter.py`, `config.json`
- Outputs เตรียม `Model_RL`, `Model_QRL`; ผลทดสอบมือบันทึก `Outputs/manual_*.json` โดยไม่อ้างว่าเป็นผลโมเดล
- Layouts เก็บ JSON อ่านง่าย เริ่มด้วยสี่เหลี่ยมผืนผ้าและสุ่มทางเข้า–ออก
- ช่องจอด 90°, 45°, ขนานข้าง ยาว 5.5 × กว้าง 2.5 เมตรทุกแบบ; ทางรถกว้าง 3.5 หรือ 6 เมตร
- Templates อยู่ใน `Arrange_tools/Slot_layouts/slots.json`
- Grid เลือก 0.1, 0.25, 0.50 เมตร ค่าเริ่มต้น 0.25 เมตร
- รอบแรกทำโครงระบบและเครื่องมือก่อน มีเอกสารบริบทและ literature review อยู่ข้าง `main.py`

## การไหลของคำสั่งและเหตุผล

```text
UI event → UI/server.py → main.Application → Arrange_tools.Controller
                                               ↓ Validator ที่ main ประกอบให้
                                          Policies แยกตามหน้าที่

main → Model adapter → Model → shared Environment → Controller (Phase 2)
main → Outputs.Repository → JSON → UI replay
```

`main.py` ประกอบ dependency และจัด session/load/save ส่วนการตรวจทุกรูปแบบอยู่ที่ขอบเขต Controller เพื่อไม่ให้ UI หรือโมเดลข้าม policy ได้โดยเผลอ UI ไม่เรียก controller โดยตรงผ่านภาษา Python แต่เรียก HTTP route ที่ main รับผิดชอบ `adapter.py` คือไฟล์กลางที่ผู้ใช้ขอ ไม่ใช่โมเดลหรือกฎชุดใหม่

## สิ่งที่ทำแล้ว

- เพิ่มตามคำขอผู้ใช้: เมนู BUILD MENU ลากช่องจอด/ถนนลงผังแบบเกม เลือกการ์ดแล้วคลิกวางซ้ำได้ และโหมดเลือกลากย้ายของเดิม มีเงาระหว่างลาก หมุน R ยกเลิก Esc ถอน Delete เมนู sticky ขณะเลื่อนหน้า
- `UI/interactions.js` รับ pointer/keyboard และวาดเงาเหลืองตาม pointer ทันทีระหว่างรอ `/api/propose` ผลจาก backend จึงเปลี่ยนเป็นเงา snap สีเขียว/แดง ไม่แก้ `live.items` ไม่ตรวจ policy หรือ snap ซ้ำใน browser ปล่อยวางแล้วเรียก `/api/action` ผ่าน main/controller เดิมหนึ่งครั้งต่อ action; ปล่อยนอกผังหรือยกเลิกไม่เพิ่ม action และไม่อนุญาตแก้ผังระหว่าง Replay/Model runs

- เว็บ Python standard library + HTML/CSS/JavaScript ไม่ต้องติดตั้ง package ภายนอก
- วาง ย้าย หมุนครั้งละ 90° ถอน reset ผ่าน controller และ validation ชุดกลาง
- ตรวจรูปทรงสี่เหลี่ยมหมุนจริงด้วย separating axis test: ไม่ออกนอกพื้นที่ ไม่ชนเสา/Core ไม่ทับ slot/road และไม่ปิด reserve ทางเข้า–ออก
- ถนนต่อชนขอบกันได้แต่ห้ามทับกัน รวม road-road ตามข้อกำหนดล่าสุด (policy version 2) แยกการตรวจเชื่อมต่อออกจากการชน
- ทุก slot ต้องมีถนนขนานกับแนวแถวติด projected frontage และอยู่ใน component ที่เชื่อมทั้ง entry และ exit
- ถนนยังสร้างเป็นส่วนที่ไม่ต่อกันได้ระหว่างจัดผัง แต่ยังใช้รองรับ slot ไม่ได้จนกว่าจะเชื่อม entry/exit
- ตรวจผลกระทบทั้งผังทุกครั้ง การย้าย/ถอนถนนที่ทำให้ slot เดิมผิด policy จะถูกปฏิเสธและคงสถานะเดิม
- เก็บ before/after ของทุก action, timestamp UTC, elapsed time, คำสั่งที่ร้องขอ, accepted/reason และสถานะหลัง snap
- JSON ผลลัพธ์ฝัง layout, policy, templates, grid, budget, metrics และประวัติ จึง replay ได้โดยไม่พึ่งการฝึกซ้ำหรือไฟล์ config ปัจจุบัน
- ผังเริ่มต้น 48 × 30 เมตร มี Core/เสาตัวอย่าง seed สุ่มตำแหน่ง Y ของประตูบนฝั่งตะวันตก–ตะวันออกและสลับบทบาท entry/exit ถนนเริ่มต้นถูกบันทึกเป็น **Action 1**
- การสร้าง session ใหม่เริ่ม budget และ log ใหม่ ส่วน reset เป็น action ที่ล้างอุปกรณ์ใน session เดิม
- โครงสร้างโมเดลและ shared environment พร้อม interface แต่ `act()` จะยก NotImplementedError; ปุ่ม run ถูกปิดไว้

## ข้อจำกัดที่ต้องรักษาความชัดเจน

1. ค่าช่องจอดและถนนเป็น **experimental profile จากผู้ใช้** ไม่ใช่ค่ามาตรฐานไทยหรือการรับรองกฎหมาย ผล literature review ห้ามนำมาทับค่าที่ผู้ใช้ระบุโดยไม่ตกลง
2. Collision ใช้ continuous geometry หน่วยเมตร Grid snap เฉพาะจุดกึ่งกลาง ไม่ย่อ/ขยายช่องจอดให้หารลงตัวกับ cell โดยเฉพาะ 0.50 เมตร
3. Grid occupancy แบบ sparse แยก obstacle/road/slot: cell ที่มีเนื้อที่ตัดกับรูปทรงถูกนับ occupied ดังนั้นรูปทรงสองชิ้นที่ไม่ชนกันอาจมี cell ร่วมกันได้ ข้อมูลนี้ยังไม่ใช่ observation encoding ของโมเดล
4. Frontage ใช้ 5 probes ตลอดความกว้าง projected envelope ยอมระยะถึงหนึ่ง grid cell + 0.01 เมตร เพื่อรองรับการปัดตำแหน่งออกจากถนนของรูปทรง 45° เป็น geometric proxy ไม่ใช่เส้นทางรถจริง
5. Graph ถนนเป็น undirected ไม่มีการบังคับเลนเดินรถทางเดียว ลูกศร/ตัวเลขในภาพใช้สื่อความหมายผังเท่านั้น ห้ามอ้างว่าผ่านการตรวจ traffic flow
6. ถนนต่อกันที่มุมจุดเดียวไม่นับเชื่อมต่อ แต่การต่อที่มีความกว้างเป็นบวกยังไม่ได้รับรองว่ารถเลี้ยวผ่านได้
7. 90° ต้องติดถนน 6 เมตร; 45°/parallel ยอม 3.5 หรือ 6 เมตร เป็น implementation decision สำหรับ profile ทดลอง ยังไม่ใช่ผลวิเคราะห์ swept path
8. ยังไม่มี turning radius, swept path, ที่จอดผู้พิการ, ความชัน/ความสูงทางลาด, clearance เปิดประตู, tandem/double parking, CAD import หรือขอบเขต polygon ไม่สม่ำเสมอ
9. ยังไม่มี reward function, algorithm RL/QRL, training loop, checkpoint หรือผลเปรียบเทียบจริง ต้องกำหนด observation/action encoding และ reward ร่วมกันใน Phase 2
10. local server เป็น single shared research session และผูก loopback ใช้ทดลองบนเครื่อง ไม่ใช่ระบบหลายผู้ใช้
11. `config.json` ของโมเดลเป็น scaffold; UI session limit ยังไม่ใช่ hyperparameter ที่โหลดจากโมเดล เพราะยังไม่มีการรันโมเดล

## แนวทางงานรอบถัดไป

เริ่มจากยืนยัน policy profile และเพิ่ม vehicle model/swept-path validation ก่อนอ้าง feasibility ทางสถาปัตยกรรม เลือก RL baseline และ QRL circuit/backend ให้ชัด กำหนด reward, observation และ action space ชุดเดียวกัน วัดทั้ง 200-action budget และ wall-clock budget หลาย seed หลายผัง พร้อม conventional baseline แยก train/evaluation layouts และรายงานต้นทุน simulator/quantum shots อย่างเปิดเผย

เอกสารอ้างอิงและเหตุผลเชิงวิจัยอยู่ใน `LITERATURE.md` วิธีเปิดโปรแกรมและคำสั่งทดสอบอยู่ใน `readme.md`

## Latest user decision: shared snap and no-overlap policies

Policy version 2 moves snapping into `Policies/snapping.py`, called by `Validator.prepare()`, with an additional off-grid check in `validate()`. Controller shares `_propose()` between preview and commit. Moving excludes only the original object itself from collision tests. The previous road-road overlap exemption has been removed: all positive-area overlap is rejected, while edge contact remains allowed.

`POST /api/propose` has no effect on state/history/action budget. It returns snapped geometry plus accepted/reason. UI uses those results for green/red ghosts, throttles preview requests and discards cancelled/stale gesture responses. Dropping calls `/api/action` and validates again against current state. Saved old outputs are not rewritten and can still be replayed as historical records.
