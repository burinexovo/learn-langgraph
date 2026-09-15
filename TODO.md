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

## 開發過程中遇到不明確的環境類問題，要有一個問題佇列丟給人回答（已定案，還沒接線）

構想：跑 `code_agent`/`blackboard_dispatch` 這類會真的動手做事的節點時，如果遇到不是「這段
程式邏輯該怎麼寫」這種可以自己判斷的問題，而是環境層級的不確定（例如缺哪個 `.env` 變數、
不確定要連測試環境還是正式環境的某個服務、密鑰放哪裡），不應該直接卡住整個流程等一個人來
`interrupt()`，而是丟進一個獨立的「問題佇列」，讓其他還能做的工作繼續跑，等人有空再回頭批次
回答佇列裡的問題。

原本三個沒想清楚的地方，這輪討論定案，答案都是「用已經驗證過的機制接上，不用新蓋一套」：

- **跟現有的 `human_checkpoint`/`interrupt()` 機制是什麼關係？**
  不是取代，是兩種不同層級的中斷，但底層機制是同一個 `interrupt()`。`human_checkpoint` 問的是
  「方向對不對」，一輪只問一次，會擋住整條線；環境類問題發生在單一 slice 裡，不該擋到其他
  slice。用 interrupt payload 裡的一個 `kind` 欄位分辨（`"direction"` vs `"env_question"`），
  不用蓋兩套機制，也不用改 LangGraph 的中斷/續跑流程。

- **佇列要放在哪裡？**
  不需要另外蓋一個佇列資料結構——LangGraph 每次 `invoke()`/`stream()` 回傳的
  `state["__interrupt__"]` 本身就是「目前卡住的問題列表」，而且已經實測過（見
  `notebooks/arch/A_full_custom_langgraph.ipynb`「驗證 `code_agent` 中途卡住問問題」那段）：
  多個平行 slice 同時卡住，每個都有自己獨立的 interrupt id，互不影響。真正缺的只是一層
  「把好幾波、好幾個 slice 累積下來的 `__interrupt__` 收集起來給人看」的外部小工具（可以只是
  一個 `{interrupt_id: 問題內容}` 的 dict），不需要動 graph 本身的 state schema。這層小工具也是
  「動態優先度」（例如卡越久的排前面）該放的地方——純粹是外部排序邏輯，不影響 graph 設計。

- **人回答之後，怎麼接回去？**
  已經驗證過：`Command(resume={interrupt_id: 答案})` 用同一個 `thread_id` 送回去，只會接續
  那一個卡住的 slice，其他已經做完的 slice 不會被動到。中間如果要來回討論，那個討論發生在
  graph 外面（人跟 agent 聊），只有討論完的「最終答案」才送進去 resume，graph 完全不需要知道
  中間討論過幾輪。

還沒做的事：A/A2 的 `code_agent`/`blackboard_dispatch` 目前 interrupt payload 只有
`{"slice_id": ..., "question": ...}`，還沒加上 `kind` 欄位；也還沒寫「收集多個 thread 的
`__interrupt__`」那層外部小工具（不屬於 graph 本身，屬於部署時的 harness）。
