# Literature review และที่มาของการออกแบบ

สืบค้นวันที่ 14 ตุลาคม 2026 · เป็นการทบทวนเบื้องต้นแบบมีขอบเขต ไม่ใช่ systematic review

แยก **paper**, **คู่มือหน่วยงาน**, **ค่าที่ผู้ใช้กำหนด**, และ **ข้อเสนอของการพัฒนาระบบนี้** อย่างชัดเจน งานนี้ยังไม่ได้ทดลอง RL/QRL จึงยังสรุป quantum advantage ไม่ได้ แหล่งที่อ่านได้เพียง abstract/search extract ระบุไว้ด้านล่าง

## 1. งานจัดผังที่จอดรถโดยตรง

### [P1] Lan, D., Chen, K., & Xu, Z. (2023)

*Underground Parking Layout Generation Based on the WaveFunctionCollapse Algorithm.* Buildings, 13(11), 2898. DOI: [10.3390/buildings13112898](https://doi.org/10.3390/buildings13112898).

จากบทคัดย่อของผู้เผยแพร่ งานนี้ใช้ spatial modules และ adjacency rules ร่วมกับ WaveFunctionCollapse และ multi-objective optimization สำหรับสร้างผังจอดรถใต้ดิน **สิ่งที่นำมาใช้ในโปรเจกต์:** แนวคิดแยก templates ของช่องจอดออกจากกฎความสัมพันธ์กับทางรถใน `Slot_layouts` และ `Policies` เป็นการประยุกต์แนวคิด ไม่ใช่ implementation WFC และไม่ใช่ผลยืนยันว่า RL/QRL จะดีกว่า WFC

การเข้าถึง: อ่านบทคัดย่อ/metadata ที่ search index แสดงจากหน้า publisher; การเปิด full page ได้ HTTP 429 จึงยังไม่ได้ตรวจ implementation และตารางผลฉบับเต็ม

### [P2] Computational Approach towards Repetitive Design Tasks: The Case Study of Parking Lot Automated Design (2024)

Sustainability, 16(2), 592. DOI: [10.3390/su16020592](https://doi.org/10.3390/su16020592).

บทคัดย่ออธิบายการสร้างทางเลือกผังภายในขอบเขตพื้นที่ที่กำหนด เพื่อช่วยการตัดสินใจและใช้พื้นที่อย่างมีประสิทธิภาพ **ความเกี่ยวข้อง:** สนับสนุนการเก็บหลาย layout case และหลายผลลัพธ์ให้ตรวจย้อนหลัง แทนการประเมินเพียงผังเดียว โค้ดรอบนี้ไม่ได้ทำซ้ำอัลกอริทึมของ paper และยังไม่อ้างผลเชิงปริมาณของ paper

การเข้าถึง: อ่าน publisher abstract/search extract; full page ได้ HTTP 429 เช่นเดียวกับ P1 ยังไม่ได้ตรวจ full text

## 2. RL และการจัดวางเชิงพื้นที่

### [P3] Watkins, C. J. C. H., & Dayan, P. (1992)

*Q-learning.* Machine Learning, 8, 279–292. DOI: [10.1007/BF00992698](https://doi.org/10.1007/BF00992698). [ต้นฉบับจากเว็บไซต์ผู้เขียน](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf).

บทคัดย่อระบุการพิสูจน์ convergence ของ Q-learning **ความเกี่ยวข้อง:** เป็นพื้นฐานสำหรับการกำหนด state/action/reward และการเรียนรู้จากการกระทำ แต่ยังไม่ได้เลือก tabular Q-learning เป็นอัลกอริทึมของโปรเจกต์ และเงื่อนไขการพิสูจน์ไม่ใช่การรับประกันว่า 200 actions จะได้ผังที่ดีที่สุด

### [P4] Mirhoseini, A., et al. (2021)

*A graph placement methodology for fast chip design.* Nature, 594, 207–212. DOI: [10.1038/s41586-021-03544-w](https://doi.org/10.1038/s41586-021-03544-w). อ่านร่วมกับ [Addendum (2024)](https://doi.org/10.1038/s41586-024-08032-5).

หน้า publisher อธิบายการกำหนด chip floorplanning เป็นปัญหา RL โดยใช้ตัวแทนข้อมูล graph **สิ่งที่นำมาใช้:** เหตุผลในการเตรียม shared environment สำหรับปัญหาการวางวัตถุภายใต้ข้อจำกัด งานนี้คนละ domain กับที่จอดรถ จึงไม่สามารถใช้ผล chip design มายืนยัน performance ของ parking layout ได้ หน้า publisher มีประวัติ correction และ clarifying addendum จึงระบุลิงก์ประกอบไว้ ไม่ใช้ตัวเลข speedup ของงานนี้เป็นเป้าหมายรับรองของโปรเจกต์

## 3. QRL

### [P5] Skolik, A., Jerbi, S., & Dunjko, V. (2022)

*Quantum agents in the Gym: a variational quantum algorithm for deep Q-learning.* Quantum, 6, 720. DOI: [10.22331/q-2022-05-24-720](https://quantum-journal.org/papers/q-2022-05-24-720/).

งานศึกษาการใช้ parameterized quantum circuit แทนส่วนประมาณ Q-value และเปรียบเทียบกับ classical learner ใน benchmark ของตน รายงานความสำคัญของ architectural choices และ hyperparameters **สิ่งที่นำมาใช้:** แยก implementation กับ config ของ RL/QRL แต่ใช้ environment เดียวกัน หลักฐานนี้ไม่ได้แสดง quantum advantage สำหรับการจัดผังที่จอดรถ จึงยังไม่มีการเลือกรูปแบบวงจรหรือสร้าง QRL จำลองด้วย random policy ในรอบนี้

## 4. คู่มือมิติช่องจอด ทางวิ่ง และการเลี้ยว

### [G1] Singapore Land Transport Authority — 2019 Revised Edition

*Code of Practice on Vehicle Parking Provision in Development Proposals.* [เอกสารจาก LTA](https://www.lta.gov.sg/content/dam/ltagov/industry_innovations/industry_matters/development_construction_resources/vehicle_parking/pdf/cop_on_vehicle_parking_provision_in_development_proposals_2019_edition.pdf).

ตรวจตารางและข้อความใน PDF: §2.1.2 หน้า 19 แยกมุมจอด จำนวนฝั่งจอด และทิศทางเดินรถ ตัวอย่าง one-way/bays on one side: parallel 3.6 m, 45° 4.2 m, 90° 6.0 m; กรณี two-way 90° ใช้ 6.6 m จึงไม่ควรถือ 6 m เป็นมาตรฐานครบทุกกรณี §2.1.1 หน้า 16 กล่าวถึงช่องขนานที่ต้องยาวขึ้นตามสิ่งกีดขวางและลักษณะเข้าออก §2.1.3 หน้า 21 ให้ inside radius ของ curved accessway แต่ค่านี้ใช้แทน swept-path analysis ของรถทุกชนิดไม่ได้

**ผลต่อระบบ:** คงค่า 3.5/6 m และช่อง 5.5 × 2.5 m ตามโจทย์ใน experimental profile พร้อมแสดงข้อจำกัด แยกการตรวจการชนออกจาก access/turning และยังไม่อ้างว่าผ่านคู่มือนี้หรือกฎหมายไทย

## 5. ตารางเชื่อมแหล่งอ้างอิงกับไฟล์

| องค์ประกอบ | ที่มา | การใช้งานจริงใน Phase 1 |
|---|---|---|
| รูปแบบ 90°, 45°, parallel และขนาด 5.5 × 2.5 m | ผู้ใช้ | `Arrange_tools/Slot_layouts/slots.json` |
| ถนน 3.5/6 m | ผู้ใช้ | `Arrange_tools/policies.json`; ไม่อ้างว่าเป็นค่าจาก G1 |
| 90° ใช้ aisle 6 m; แบบอื่นยอม 3.5 m | การตัดสินใจ implementation สำหรับทดลอง | `Policies/accesses.py` + slot templates; ไม่ใช่ข้อสรุปมาตรฐาน |
| Template + adjacency rule separation | แนวคิดจาก P1 | template JSON แยกจาก policy Python |
| เก็บหลายผังและผลแต่ละ action | โจทย์ผู้ใช้; สอดคล้องกับการประเมินหลายทางเลือกใน P2 | `Layouts`, `Outputs`, replay UI |
| shared environment และ model config แยก | โจทย์ผู้ใช้ + แนวคิด P3/P5 | scaffolds ใน `Models` |
| Collision ด้วย separating axis test | เทคนิค geometry ที่พัฒนาในโปรเจกต์ | `Arrange_tools/geometries.py`; ไม่อ้างว่าได้จาก papers ด้านบน |
| sparse grid, frontage probes, undirected graph, tolerance หนึ่ง cell | สมมติฐานต้นแบบของโปรเจกต์ | `grid.py`, `Policies/accesses.py`; ต้องทดสอบกับ vehicle model ต่อไป |

## 6. ช่องว่างและแผนประเมินที่เสนอ

ส่วนนี้เป็น **ข้อเสนอของโปรเจกต์** ไม่ใช่ผลทดลองหรือคำกล่าวจาก paper ใดโดยตรง

- แยกจำนวน slot, slot-area/site-area, จำนวน action ที่ถูกปฏิเสธ, feasibility ที่ตรวจได้จริง และเวลา ไม่ใช้พื้นที่ช่องจอดอย่างเดียวแทนคุณภาพการเดินรถ
- 200 actions เป็น inference/search budget ต่อ run; ต้องรายงาน training budget แยกต่างหาก
- เทียบ RL/QRL ด้วย layout, seed, policy, action space, reward และงบค้นหาเดียวกัน พร้อมรายงาน wall-clock และต้นทุน quantum simulator/วงจร/shots
- เพิ่ม baseline ที่ไม่ใช้ learning เช่น rule-based placement, random search และวิธี optimization ที่เลือกภายหลัง ก่อนสรุปว่าการเรียนรู้คุ้มค่าหรือไม่
- ทดลองหลาย seed หลาย case แยก train/evaluation และรายงานความแปรปรวน ไม่เลือกเฉพาะ run ที่ดีที่สุด
- เปรียบเทียบ grid 0.1/0.25/0.5 m โดยยึด geometry จริง เพราะจำนวน candidate anchors และความคลาดเคลื่อนการ rasterize ต่างกัน
- ต้องเพิ่ม vehicle dimensions, steering model, swept path, directionality, clearance, accessible parking และข้อกำหนดท้องถิ่นที่เลือก ก่อนใช้ผลเป็นแบบก่อสร้าง
- ยังไม่พบหลักฐานที่ตรวจจากแหล่งข้างต้นว่ามี QRL เหนือ Classical RL สำหรับ parking layout ตาม action/policy ชุดนี้ ข้อนี้เป็นคำถามวิจัยที่ยังเปิดอยู่

## 7. ขอบเขตการสืบค้น

ใช้คำค้นเกี่ยวกับ parking layout automated design, WaveFunctionCollapse parking, reinforcement learning placement และ quantum deep Q-learning โดยเลือกหน้า publisher และหน่วยงานเป็นหลัก P1/P2 อ่านได้เฉพาะ abstract/search extract; P3 อ้าง metadata/abstract ของ publisher และลิงก์ผู้เขียน; P4/P5 อ่านหน้า publisher; G1 ตรวจ PDF ที่ระบุ ยังไม่ได้ทำ systematic comparison ของ full-text papers ทั้งหมด และยังไม่ได้ตรวจข้อบัญญัติไทยสำหรับประเภทอาคารเฉพาะ

## Implementation update: Parking Row and Gymnasium (2026-10-14)

[G2] Farama Foundation, Gymnasium official documentation: [Create a Custom Environment](https://gymnasium.farama.org/introduction/create_custom_env/) and [Env API](https://gymnasium.farama.org/api/env/), accessed 2026-10-14. This is software documentation, not a research paper. The environment follows reset returning observation/info and step returning observation/reward/terminated/truncated/info. The project distinguishes action-budget truncation from explicit finish termination and runs Gymnasium's environment checker.

New project assumptions, not conclusions of P1-P5: place_row expands 90/45-degree stall rectangles atomically; centres are snapped and row pitch is rounded upward to avoid collisions. Aisles are separate actions; every row must satisfy the same existing access policy. The initial finite action catalogue uses a coarse 6 m candidate stride, 10/15 m row-length choices, and horizontal full-width road actions on the 48 x 30 m example. It does not enumerate every 0.5 m grid anchor or every possible road network.

Initial reward is the increase in policy-valid stall count minus 1 for rejected actions and 0.01 per action. These coefficients are configurable experimental starting values, not literature-derived optima. NumPy/Gymnasium are implemented; DQN, quantum circuits, GA comparison and vehicle swept-path verification remain unimplemented. No measured quantum advantage or learning performance is claimed.

## Vehicle feasibility implementation (2026-10-14)

[P6: textbook, not a paper] Steven M. LaValle (2006), *Planning Algorithms*, Chapter 13, especially the simple-car model, equations 13.13-13.15. [Author-hosted chapter](https://msl.cs.uiuc.edu/~lavalle/planning/ch13.pdf). The project uses rear-axle poses and the low-speed bicycle curvature tan(steering)/wheelbase. A signed distance permits reversing. The vehicle dimensions, steering limit, clearance, radius candidates and stopping rules are project assumptions, not values supplied by this textbook.

[P7: related work, not reproduced] Dolgov, Thrun, Montemerlo and Diebel (2008), *Practical Search Techniques in Path Planning for Autonomous Driving*, STAIR-08. [Author's publication page](https://ai.stanford.edu/~ddolgov/dolgov08gppSTAIR.html), [paper](https://robotics.stanford.edu/~ddolgov/papers/dolgov_gpp_stair08.pdf). The abstract describes search in a 3D kinematic state space followed by optimization. This motivates a future broader planner. The current code does not implement its Hybrid A* search or optimization and makes no claim to reproduce its speed/performance.

The implemented checker enumerates a bounded straight-arc-straight library for forward and reverse parking. Each candidate must provide a complete entrance-to-stall path and a stall-to-exit path, with other stalls treated as occupied. A target-mouth apron connects the projected frontage to the actual angled rectangle and bridges the documented grid gap; that apron is an explicit experimental drivable-floor assumption. Collision checks use whole vehicle polygons and inflated convex envelopes between successive poses. Inflation includes a conservative arc sagitta bound in addition to clearance. Sampling is bounded at 0.25 m per segment, with numerical Shapely geometry operations.

A found witness is labelled passed under this model only; a hard precondition failure is failed; unsupported cases or exhausted template candidates are unknown, never a proof of infeasibility. The 90-degree example yields reverse-in witnesses. The default 45-degree example at (20,15) currently remains unknown, demonstrating the bounded library's incompleteness. Reward now uses changes in the number of witnessed slots, not every geometry-valid stall. Search completeness, steering-rate limits, gradients, dynamic traffic, road-direction rules and engineering/regulatory certification remain outside this implementation.

### การขยายตัวค้นหาเส้นทางและทางเดียว
ใช้แนวคิด hybrid A* (Dolgov et al., 2008, Practical Search Techniques in Path Planning for Autonomous Driving; ลิงก์อ้างอิงด้านบน) และ bicycle kinematics ของ LaValle ในตัวค้นหาที่เขียนสำหรับระบบนี้ ไม่ใช่การทำซ้ำอัลกอริทึมทั้งหมดหรือผลทดลองของเปเปอร์ การจำกัดงบ การปัด pose และค่า primitive เป็นการเลือก implementation ของงานนี้ ถนน 3.5 m ทางเดียว / 6 m สองทางเป็นข้อกำหนดจากผู้วิจัยโดยตรง

## Classical DQN implementation
- Mnih et al. (2015), *Human-level control through deep reinforcement learning*, Nature 518, 529–533. https://doi.org/10.1038/nature14236 — Q-network, experience replay and target network as the methodological basis. This implementation is a parking-specific CNN + budget MLP, not a reproduction of Atari results.
- PyTorch, *Reinforcement Learning (DQN) Tutorial*. https://docs.pytorch.org/tutorials/intermediate/reinforcement_q_learning.html — implementation reference for replay, target-network TD targets, Huber loss, epsilon-greedy exploration and gradient clipping. Our action mask applies to both action selection and the next-state Bellman maximum.
- The 100-episode pilot, 50-action horizon, learning rate, replay size, seed split and evaluation interval are initial engineering choices, not values established by these publications. Evaluate and tune them before reporting research results.
- Held-out seeds currently vary gates within the same rectangular layout family, with shared obstacle geometry. This does not establish generalization to new building geometries. A fixed held-out set used repeatedly is a development evaluation set; independent final test cases must be reserved for final RL/QRL/GA comparisons.
