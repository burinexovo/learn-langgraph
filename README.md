# learn-langgraph

從 LangChain 到 LangGraph 的入門課程,以 Jupyter notebook 循序漸進。

## 環境需求

- Python 3.12(系統預設 3.14 因為第三方套件 wheel 支援度不足,不使用)
- [uv](https://docs.astral.sh/uv/)

## 建置環境

```bash
uv venv --python 3.12
uv sync
```

## LLM 設定(選用)

**沒有 API key 也能完整學習。** 每份 notebook 的主要教學路徑都用 `notebooks/_llm.py` 提供的
`scripted_model()`——一個可以事先寫好「第幾次呼叫要回什麼」的假模型(含 tool_calls 劇本),
讓整個 LCEL chain、agent 迴圈、記憶、human-in-the-loop、streaming、多 agent 協作都能離線、
確定性地完整執行,並產生真正跑出來的結果,而不是被跳過的空白 cell。notebook 裡已經預先執行
並存好輸出,直接讀就能學,不用先跑過一遍。

想接真模型看看實際模型的表現時,把 `.env.example` 複製成 `.env`、填入 `OPENAI_API_KEY`:

```bash
cp .env.example .env
```

每份 notebook 也保留了「如果你有 API key」的對照 cell,用 `get_llm()` 走一次一樣的流程。

## 執行 notebook

```bash
source .venv/bin/activate
jupyter lab
```

或在 VS Code 開啟 `.ipynb`,選擇 `.venv` 內的 kernel。

## 課程大綱

| # | Notebook | 主題 |
|---|----------|------|
| 00 | `00_setup_and_llm` | 環境驗證、共用 `get_llm()` / `scripted_model()` 介面 |
| 01 | `01_langchain_basics` | LCEL / Runnable / Chain |
| 02 | `02_three_agents_compare` | 三層次對比:手刻類 `AgentExecutor` 迴圈 vs `create_agent`(prebuilt)vs 手刻 `StateGraph` |
| 03 | `03_langgraph_core` | StateGraph / State / Node / Edge |
| 04 | `04_langgraph_control_flow` | 條件邊、迴圈、`Command` |
| 05 | `05_langgraph_tools_and_agent` | ToolNode、bind_tools、手刻 ReAct loop |
| 06 | `06_langgraph_memory_checkpoint` | Checkpointer、thread_id、對話記憶 |
| 07 | `07_langgraph_human_in_the_loop` | `interrupt()`、人工審核、resume |
| 08 | `08_langgraph_streaming` | `stream_mode` 種類與除錯 |
| 09 | `09_langgraph_multi_agent` | Supervisor pattern、subgraph |
| 10 | `10_langgraph_persistence_deploy` | SqliteSaver/PostgresSaver、部署概念 |
| 11 | `11_langsmith_observability` | LangSmith 追蹤與評估(選用,需要免費帳號才能看到 dashboard) |
| 12 | `12_mcp_tools` | MCP 概念、本機 stdio MCP server、把 MCP 工具接進 `ToolNode` |
| 13 | `13_provider_sdks` | 原生 OpenAI SDK / Anthropic (Claude) SDK 的工具呼叫格式對照 |
| 14 | `14_capstone_it_ticket_agent` | Capstone:IT 支援工單 agent,整合前 14 份幾乎所有技巧 |

`11` 是唯一一份沒辦法完全離線體驗核心價值的 notebook——LangSmith 的追蹤面板是雲端服務,
沒有本地等價物。程式碼一樣不需要 key 就能讀、能執行,只是看不到 trace 畫面。

`12`、`14` 會啟動一個本機 MCP server(`notebooks/_mcp_server.py`,用官方 `mcp` SDK 寫的,
透過 stdio 子行程溝通,不需要網路),示範怎麼把任何 MCP server 的工具接進 LangGraph 的
`ToolNode`。

## 版本資訊

本課程程式碼是針對以下已安裝版本撰寫並實際執行驗證過(見 `notebooks/00_setup_and_llm.ipynb`):

- `langchain` 1.4.0
- `langgraph` 1.2.11
- `langchain-openai` 1.6.1
- `langchain-core` 1.6.2
- `langsmith` 0.12.2
- `langchain-mcp-adapters` 0.3.2 / `mcp` 1.30.0
- `openai` 3.10.0 / `anthropic` 1.4.0 / `langchain-anthropic` 1.7.1

`langchain` 1.x 已經移除舊版 `AgentExecutor`,官方入口統一成 `langchain.agents.create_agent`
(底層就是編譯一個 LangGraph `StateGraph`)。API 表面跟 0.x 時期差異很大,規劃/撰寫每份
notebook 前都先用 `dir()` / `inspect.signature()` 對已安裝套件做過驗證,而不是憑訓練資料
的記憶寫。
