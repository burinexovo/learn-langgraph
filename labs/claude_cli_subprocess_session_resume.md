# 實驗紀錄：`claude` CLI 能不能被當成 subprocess 驅動,接進 LangGraph node

## 背景

部門討論 `code_agent`（H/A 架構，見 `notebooks/arch/`）該怎麼實際接 Claude，原本假設走
Python Claude Agent SDK（`query()`），但查文件發現 SDK **強制要走 `ANTHROPIC_API_KEY`
分開計費**，不能沿用使用者自己的 Claude 訂閱登入。

同仁之前把 `claude` CLI 接到 Discord 上能跑起來，暗示 CLI 這條路可能不受一樣的限制。這份
紀錄是針對這個假設做的最小驗證實驗，**不是**正式實作，只回答「這個機制通不通」。

## 實驗設計邏輯：為什麼照這個順序測

三個測試故意設計成有依賴關係、一個接一個驗證，不是同時亂槍打鳥：

1. **先確認認證這個最大的未知數**——如果連不設 API key 都跑不動，後面兩個測試就沒有意義，
   整個「CLI 比 SDK 有優勢」的假設直接死掉，不需要再測下去。所以第一步只驗證「能不能跑」，
   刻意不碰 session resume。
2. **認證過了，才測 session resume 能不能跨 process**——這是 `code_agent` 要在 LangGraph
   裡被重複呼叫（每一輪 `review_gate` 打回來重做）的關鍵機制，如果 resume 只在同一個
   process 內有效（例如只是同一支程式裡的物件狀態），那對 LangGraph 這種「每次呼叫都是
   全新 Python function 呼叫」的場景就沒用。所以第二步刻意用**另一次獨立的 `claude` 呼叫**
   去 resume 第一步留下的 `session_id`，而不是在同一個 shell 管道裡串起來。
3. **最後才測「能不能自己指定 session_id」**——這是錦上添花的細節，不是核心可行性問題
   （就算不能自訂，靠 CLI 回傳的 `session_id` 一樣能用，只是要多一輪才拿得到 ID）。放在
   最後測是因為前兩步沒過的話，這一步問了也沒意義。

每一步都用不需要呼叫任何工具的純文字問答，是刻意排除「工具權限設定對不對」這個變因——
這次只想單獨驗證認證跟 session resume，不想讓另一個還沒測過的變數（工具權限）混進來，
搞不清楚失敗時到底是哪個環節出的問題。

## 實驗環境

- 執行時間：2026-09-11
- 執行位置：session 的 scratchpad 目錄（不是這個 repo 本身，避免任何副作用）
- 執行前確認：`ANTHROPIC_API_KEY` 環境變數**沒有設定**（`unset`/`-z` 檢查過）
- 每個測試用的 prompt 都刻意設計成不需要呼叫任何工具（純文字問答），排除掉「工具權限設定
  對不對」這個變因，只單純驗證認證 + session resume 這兩件事

## 測試 1：不設 API key，`-p --output-format json` 能不能跑

```bash
claude -p "Reply with exactly the single word: PONG" --output-format json
```

**結果：成功。** 回傳的 JSON 裡：

```json
{
  "result": "PONG",
  "session_id": "af985dea-3d1b-4f97-a199-fc1ab573876d",
  "total_cost_usd": 0.0566976,
  "is_error": false,
  "num_turns": 1,
  ...
}
```

**結論**：`claude --help` 裡 `--bare` 選項的說明暗示「不加 `--bare` 時會讀 OAuth/keychain」，
這次實驗直接證實了——沒有 API key，靠現有的訂閱登入狀態就能完成非互動式呼叫。`--output-format
json` 的輸出乾淨可解析，`result` 欄位就是純文字回應，`session_id` 直接可用。

## 測試 2：`--resume <session_id>` 能不能跨 process 記得上下文

用測試 1 拿到的 `session_id`，開一個全新的 `claude` process：

```bash
claude -p "What was the exact word I asked you to reply with in my previous message? Reply with only that word." \
  --output-format json --resume "af985dea-3d1b-4f97-a199-fc1ab573876d"
```

**結果：成功。** `result` 正確回傳 `"PONG"`，而且 `session_id` 在 resume 後**維持不變**
（不是每次都換一個新的）。

**結論**：跨 process 的 session resume 是真的，不是只在同一個 process 內有效；`session_id`
可以直接存進 LangGraph state（例如 `code_session_id` 欄位），下一輪要接續時原封不動拿出來用
即可，不用另外處理「resume 後 ID 變了」這種情況。

## 測試 3：能不能自己先指定 `session_id`（不用等回應才知道 ID）

```bash
MYID=$(python3 -c "import uuid; print(uuid.uuid4())")
claude -p "Remember this secret code: BLUE-42. Reply with exactly: STORED" \
  --output-format json --session-id "$MYID"
# → result: "STORED", session_id 跟 $MYID 一致

claude -p "What was the secret code? Reply with only the code." \
  --output-format json --resume "$MYID"
# → result: "BLUE-42"
```

**結果：成功。** 自己產生的 UUID 可以直接指定給 `--session-id`，回應裡的 `session_id` 跟
指定的一致；用同一個 ID 呼叫 `--resume` 也正確接續了上下文。

**結論**：LangGraph node 呼叫 CLI 前，可以先在 Python 端 `uuid.uuid4()` 產生 ID、寫進 state，
不用等 CLI 回應才知道要存什麼 ID——跟 `human_checkpoint`/`review_gate` 那種先寫 state 再往下
走的設計風格一致。

## 補充：登入流程長怎樣，跟「本機執行」vs「共用 server」的差異

實際跑過 `labs/claude_cli_langgraph_demo.ipynb` 之後確認：這台機器上 `claude login` 寫下的
OAuth 憑證存在 `~/.claude/.credentials.json`（權限 600，只有這個 OS 帳號能讀）。這次 demo
的程式碼完全沒碰過認證，`code_agent_real` 呼叫 `claude` CLI 能成功，純粹是因為這個檔案本來
就在——**任何在同一台機器、同一個 OS 帳號底下執行的 `claude` CLI 呼叫，都會自動讀這個檔案，
不需要在程式碼裡傳任何 token**。

這代表兩種部署方式的處境不一樣：

- **每個工程師在自己機器上跑 LangGraph（本機執行）**——完全沒問題，大家本來就因為日常用
  Claude Code 互動而 `claude login` 過，LangGraph 不用額外處理登入，直接沿用。這次實驗驗證
  的就是這個情境。
- **如果之後架成共用 server，大家透過一個服務去用**——這個憑證是**綁在那台 server 機器的
  OS 帳號上，不是綁在「使用這個服務的人」身上**。整個部門透過這個服務跑的所有工作，都會被
  算在「登入那台 server 的那一個人」的帳號底下：那個人的用量會被灌爆、帳號密碼一換/session
  過期整個服務就斷線、而且事後從 Anthropic 的用量紀錄上分不清楚是哪個工程師觸發的。這正是
  上面查到的 **Microsoft/Azure Foundry 認證路線在共用 server 情境下比個人 OAuth 更合理**的
  原因——Foundry 用的是組織級的 Azure 資源+憑證，天生不綁在某一個人的帳號上，適合「服務」
  這種用法。

**結論**：本機執行（這份實驗驗證的情境）不用擔心登入流程，直接沿用個人 `claude login` 即可；
但共用 server 這個部署方式，認證要提早決定是「每人各自跑一份」還是「切到 Foundry 走服務級
憑證」，不能把「個人登入」原封不動搬到共用服務上。

## 整體結論

三個測試全部通過，**CLI subprocess 驅動 `code_agent` 這條路技術上是通的**：

- 認證：確認不需要另外的 `ANTHROPIC_API_KEY`，靠現有訂閱登入就能跑（跟 Python Agent SDK
  的強制 API key 限制不一樣，是 CLI 路線目前看到最大的優勢）
- Session resume：跨 process 真的有效，`session_id` resume 後不變
- Session id 可控：可以自己預先指定，不用等回應

**還沒驗證、下一步該做的事**（這份實驗刻意留白，不假裝已經做完）：

- 這次測試的 prompt 都不需要呼叫工具——`--allowedTools`/`--disallowedTools`/`--restricted`
  這些權限範圍旗標，實際限制起來行不行、會不會誤擋正常操作，還沒測過。
- `--json-schema` 強制結構化輸出還沒測，這對 `synthesize_verdict` 這類需要乾淨欄位的節點
  很關鍵。
- **政策/合規問題還是沒解決**：這份實驗只證明「技術上能跑」，不代表「大規模自動化使用符合
  Anthropic 的使用條款」——這件事在上一輪討論已經標記過，正式導入部門基礎設施前，建議先跟
  管理 Claude 訂閱/企業合約的人確認清楚，不要只憑技術上跑得動就當作可以放心規模化。
- 這裡只測了單次一問一答；真正的 `code_agent` prompt 會複雜很多（要求它讀 codebase、改檔案），
  沒有在這次實驗裡測過真正的工具呼叫路徑。
