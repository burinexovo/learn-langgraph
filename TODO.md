# TODO

## A / A2：`resolve_conflict` 的衝突處理還沒真的做

`notebooks/arch/A_full_custom_langgraph.ipynb`（`merge_wave`/`resolve_conflict`）跟
`notebooks/arch/A2_blackboard_dispatch.ipynb`（`merge_all`/`resolve_conflict`）目前這條路徑都是
示意用的空殼——`conflict` 寫死 `False`，`resolve_conflict` 只是 `Command(goto=...)`，沒有任何
`update=`，兩份 notebook 從沒真的跑過這條路徑。要接線前至少要想清楚：

- **重試前要不要 rebase 到最新主線**：現在是原地重做同一個 slice，base 是舊的。大部分被抓到的
  「衝突」可能只是 base 過期造成的假警報，rebase 後可能自然消失，不用動到 LLM。
- **真的撞到文字衝突時，要不要把 diff + 對方 patch 的上下文丟回黑板**：讓重做的 worker/CLI
  看得到「對方改了什麼」，才有機會產出真正相容的 patch，而不是盲目重做一份一樣的東西再賭一次。
  如果要做，context 應該存在黑板上該 task 自己的 record 裡（例如新增 `conflict_context` 欄位），
  不要塞進 `DevWorkflowState` 的全域欄位——理由是 A2 的設計精神就是 per-task 狀態該待在黑板上。
- **要不要分辨「範圍越界」跟「合法重疊」**：如果某個 worker 動到了宣告 `touches` 以外的檔案，
  這是它自己犯規（沙盒/範圍控制失敗），該算成任務失敗甚至異常標記，不該跟「兩個 slice 本來
  就都要合法碰到同一塊區域」用同一條路徑處理。
- **要不要設重試上限、超過交還人工**：`review_gate` 已經有 `MAX_REVIEW_ROUNDS = 2` 超過就交給
  `human_checkpoint`，但 `resolve_conflict` 目前完全沒有對應的上限，理論上會無限重試同一個衝突。
  這兩條重試迴圈的設計現在不一致，應該對齊。

參考業界作法：merge queue（rebase-and-retry 佇列，如 GitHub Merge Queue / Graphite / Mergify）、
optimistic concurrency control（重試前重讀最新狀態，不是拿舊狀態硬重做）、AI 輔助解衝突
（GitHub Copilot / aider 把雙方 diff 一起餵給 LLM 談判出相容版本）。

流程拓樸（merge → 偵測衝突 → resolve_conflict → 迴圈導回重新分派）本身沒問題，落差在節點
*裡面*要做的事，不是圖的形狀。

## 開發過程中遇到不明確的環境類問題，要有一個問題佇列丟給人回答（想法，還沒定案）

構想：跑 `code_agent`/`blackboard_dispatch` 這類會真的動手做事的節點時，如果遇到不是「這段
程式邏輯該怎麼寫」這種可以自己判斷的問題，而是環境層級的不確定（例如缺哪個 `.env` 變數、
不確定要連測試環境還是正式環境的某個服務、密鑰放哪裡），不應該直接卡住整個流程等一個人來
`interrupt()`，而是丟進一個獨立的「問題佇列」，讓其他還能做的工作繼續跑，等人有空再回頭批次
回答佇列裡的問題。

還沒想清楚的地方（回公司再想）：
- 這個佇列跟現有的 `human_checkpoint`/`interrupt()` 機制是什麼關係——是取代，還是分成兩種
  不同性質的中斷（「方向對不對」用 `human_checkpoint`，「環境參數是什麼」用問題佇列）？
- 佇列要放在哪裡（黑板 store？獨立的 state 欄位？）、怎麼跟卡住的那個 slice/worker 對應回去？
- 人回答之後，怎麼讓原本卡住的那個 worker/任務接著往下做，而不是要整批重來？
