# 部門開發自動化 — 架構選項總覽

背景:部門在討論用 LangGraph(或相關工具)做一個「開發 agent」,目標是讓工程師不用再一直
用聊天的方式跟 Claude Code 來回對齊需求跟改 code——把人的介入壓縮成少數幾個明確的檢查點
(對齊需求一次、驗收一次),中間的多 agent 平行 coding、測試、review 全部自動跑完。

這個資料夾是針對這個目標,實際做過 GitHub 調查(兩輪:先廣泛掃五大類、再對 7 個 clone 下來的
repo 做程式碼層級的深讀)之後,整理出的架構選項——不是 10 個平均分數的選項,是研究之後**真正
還站得住腳的幾個**,加一份「評估後不採用」的比較表,把已經被排除的路線跟排除理由講清楚,
避免之後重複討論同樣的死路。

## 為什麼不是滿滿 10 個選項

原本想每個候選(LangGraph 手刻 / 委派 Claude Code / 官方 supervisor-py / swarm-py / 沿用既有
harness / spec-kit 風格 / 漸進 MVP …)都各出一份,但深讀 `langgraph-supervisor-py`、
`langgraph-swarm-py`、`spec-kit`、`BMAD-METHOD` 的原始碼之後發現:前兩者的抽象是「一群會話式
agent 互相 handoff」,跟我們用 `Send` 對結構化資料做平行分派的模式是不同典範,硬套只會多繞一層;
後兩者的核心設計目標根本是**強化多輪對話式的需求釐清**,跟部門要的「壓縮對話」方向正好相反。
把這幾個硬包成獨立架構頁面,只會製造「10 頁裡 4 頁沒用」的閱讀負擔,所以把它們收進下面的
「評估後不採用」比較表,只留下真正值得放在檯面上比較的選項。

## 每份架構頁面都有的固定欄位:人工介入次數(每個 change)

這是部門要解決的核心問題,所以每個選項都用同一個位置回答同一個數字。

## 選項列表

(這一段會在每個項目完成後更新——目前是研究進行中的即時狀態,不是最終報告)

| 選項 | 檔案 | 人工介入次數 | 一句話定位 | 狀態 |
|---|---|---|---|---|
| A — 完整自訂 LangGraph | `A_full_custom_langgraph.ipynb` | 2 | 平行 slice + 確定性合併判斷,全部邏輯自己控制、可觀測 | ✅ 完成 |
| H — 漸進式 MVP(不平行) | `H_incremental_mvp.ipynb` | 2 | 序列化單一 coding agent + `review_gate` 自動重試 + 進度通知,风险最低的起始版本 | ✅ 完成(2026-09-11 更新) |
| B — Claude Code 協調者黑箱 | `B_coordinator_blackbox.ipynb` | 2(但中途可見度低) | 平行/合併整包委派給 Claude Code 自己的 Task+worktree | ✅ 完成 |
| E — 沿用既有 harness | `E_reuse_harness_shell.html` | 2 | 不重刻 wave/merge,LangGraph 只做對齊+人工核准+長期記憶+服務化外殼 | ✅ 完成 |
| 評估後不採用 | `rejected_options.html` | — | 已排除路線的一句話結論跟理由 | ✅ 完成 |
| （選配）I — 服務化部署版 | `I_service_deployment.html` | 2 | 把架構 A 包成 API 服務 + 聊天前端 | ✅ 完成 |

**全部 6 份 2026-09-10 18:04 CST 前完成**(第一輪,約 15 分鐘內做完),每份都已離線執行/
驗證過(notebook 有跑出真的 mermaid 圖跟 demo log,不是空殼；HTML 都過 parser 檢查)。

**18:04–18:10 CST 做了第二輪:自我審查抓到兩個真實問題,已修好**:
1. **架構 A 有一個真的 bug**——`review_gate` 判斷沒過要重派時,忘記把 `current_wave` 重設
   回 0,導致重派永遠只重跑最後一波,被 review 點名的 slice 如果在更早的波次就完全沒被重做。
   這個 bug 光靠「notebook 有沒有跑出錯誤」是抓不到的,因為 demo 裡 `test_agent`/
   `review_agent` 永遠回報 PASS,根本不會走到這個分支——已修好(重派時重設
   `current_wave = 0`),並且加了一個直接呼叫 `review_gate()` 的驗證 cell 證明修好了,不是
   憑感覺說有修。
2. **架構 B 有一句話講過頭了**——原本寫「Task 工具 + `isolation: worktree` 從 SDK 驅動的
   headless session 內部生出平行 worktree subagent,這條路技術上確認可行」,但這句話裡只有
   「worktree 機制本身存在」是真的獨立核對過的(這次核對直接用了本機裝的 `claude --help`,
   看得到 `-w`/`--worktree`、`--tmux` 依賴 `--worktree`);「SDK headless session 的 Task
   工具也吃得到同一個參數」這個更具體的說法,其實一路溯源回一次背景調查 agent 的回報,那次
   回報裡混了幾個看起來像編造的細節,沒有另外找到獨立來源交叉驗證過。已經改寫成清楚區分
   「已核對」跟「還沒核對、先假設成立」兩件事,不再講成都確認過了。

這兩個問題都是研究過程中自己抓出來的(第二輪自我審查,不是等你發現才修),不是憑空編的——
細節見 `A_full_custom_langgraph.ipynb`/`B_coordinator_blackbox.ipynb` 各自的說明文字。

## 2026-09-11 討論後更新:H 加上 `review_gate` + 進度通知

隔天討論延伸出兩個問題,已經反映進 `H_incremental_mvp.ipynb`(A/B/E/I 這次沒動):

1. **`test_agent`/`review_agent` 後面要不要接一個決策關卡,評估要交給人還是回頭修正?**——
   答案是「這個角色本來就該有,而且架構 A 已經有了(`review_gate`),H 之前沒有」。已經把
   `review_gate` 加進 H:test/review 都過才交給人驗收,沒過就自動帶著意見重派、最多兩輪,
   兩輪都沒過才交人——**是純 Python 布林邏輯,不是另一個 agent 自己拿主意**,跟 A 用同一套
   收斂原則。這個改動也讓 H 不再是「每次失敗都要麻煩人」,人工介入次數 = 2 這個數字現在在
   H 身上更站得住腳。
2. **不管有沒有要交給人,每一輪做完要不要讓使用者知道進度?**——需要,但這是「通知」不是
   「介入」,不該用 `interrupt()`(那會卡住等人回應,違背「減少來回」的目標)。已加上
   `report_progress()`,在 `code_agent`/`review_gate` 完成時順手把訊息寫進 `store`,使用者
   隨時可以查詢,graph 本身不會因此停下來。

寫這次更新時也踩到一個真實的執行期錯誤,順便記錄下來:`report_progress()` 呼叫的
`get_store()` 只能在 LangGraph 真的在執行中(`invoke()`/`stream()`)才能用,原本想仿照架構
A 的做法直接呼叫 `review_gate(fake_state)` 這個 Python 函式來測試,會直接噴
`RuntimeError: Called get_config outside of a runnable context`。改成組一個包含
`review_gate` 的小型測試圖、真的 `invoke()` 它一次,才是正確驗證方式——細節跟完整 traceback
留在 notebook 裡自己的說明文字裡。

加了 `review_gate` 之後,H 跟 A 在「失敗要不要麻煩人」這件事上已經站在同一個起跑點,兩者現在
唯一的實質差異就是平不平行——這一點也更新進 `H_incremental_mvp.ipynb` 自己的比較表。

## 建議的決策順序(不是叫你選一個,是叫你按順序看)

1. **先看 `rejected_options.html`**——五分鐘讀完,確認「為什麼不是套用現成工具」這件事已經
   查過、查清楚了,不用再花時間重新評估 supervisor-py/swarm-py/spec-kit/BMAD/claude-squad/
   vibe-kanban 這幾條路。
2. **`H_incremental_mvp.ipynb` 是建議的起跑點**,不是妥協版——先用最少的複雜度驗證「壓縮成
   兩次人工介入」這個核心體驗工程師買不買單,平行化(架構 A)隨時可以之後加。
3. **`A_full_custom_langgraph.ipynb`** 是驗證過 H 的價值之後的下一步,也是目前研究下來
   最推薦的正式路線——收斂邏輯自己控制、可觀測、可排查,借用了 nimbalyst 唯一值得抄的
   合併檢查邏輯。
4. **`B_coordinator_blackbox.ipynb`** 讀完會發現它在「兩次人工介入」這個數字上跟 A 打平,
   但可觀測性明顯較差——除非團隊評估後真的能接受這個代價換取更低的 LangGraph 開發成本,
   否則不建議選它。
5. **`E_reuse_harness_shell.html`** 是唯一「不用重寫平行邏輯」的選項,但要注意頁面裡講的
   橋接層成本是真的成本,不是免費的重用。
6. **`I_service_deployment.html`** 是最後才需要想的問題(要不要讓多人共用),現在不用決定。

## 研究過程中的關鍵發現(細節見各頁面)

GitHub 上調查過的所有平行 worktree 工具(vibe-kanban、claude-squad、nimbalyst)都停在
「隔離執行 + 人工挑選/合併」,沒有一個做到自動合併驗證 + 衝突自動降級重試——這正是部門既有
harness 跟這裡在設計的 LangGraph 版本要解決、業界目前都還沒解決的部分,不是重複造輪子。唯一
值得直接借用的程式碼是 `nimbalyst` 的 `GitWorktreeService.mergeToMain()` 合併前安全檢查順序
(查 git 狀態乾淨→偵測未提交檔案與 worktree 分支重疊→必要時自動 stash→才合併),已經借用進
選項 A 的 `merge_wave` 節點設計。

沒有 commit/push 任何東西——全部變更都留在 working tree,由你決定要不要留、要不要 commit。
