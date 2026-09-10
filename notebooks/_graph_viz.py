"""用 PIL 把 compile() 後的圖畫出來，離線時自動退回文字版 mermaid。

`draw_mermaid_png()` 預設打 mermaid.ink 的線上 API，離線環境會噴例外——
所以這裡包一層 try/except，連得上網路就顯示圖片，連不上就印文字版 mermaid
（貼到 https://mermaid.live 一樣能看到圖）。
"""

import io

from IPython.display import display
from PIL import Image


def show_graph(graph, xray: bool = False) -> None:
    """xray=True 會把 subgraph 展開畫在同一張圖裡（見 16 章）。"""
    mermaid_graph = graph.get_graph(xray=xray)
    try:
        display(Image.open(io.BytesIO(mermaid_graph.draw_mermaid_png())))
    except Exception as exc:
        print(f"[離線或畫圖失敗，改印文字版 mermaid：{exc}]")
        print(mermaid_graph.draw_mermaid())
