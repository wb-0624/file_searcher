<p align="center">
  <h1 align="center">File Searcher</h1>
  <p align="center">本地文档全文搜索引擎</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
</p>

---

## Features

- **Multi-Archive** — 创建多个归档，每个归档对应一个本地目录，独立索引
- **Cross-Search** — 支持搜索单个归档，或跨所有归档全局搜索
- **Content + Filename** — 同时匹配文件内容和文件名，不区分大小写
- **Format Support** — `.docx` / `.xlsx` / `.md` 三种文件格式
- **Keyword Highlight** — 预览片段中精确标记每一次关键词出现
- **Match Count Badge** — 每个结果显示该关键词在全文中的命中次数
- **Card UI** — 现代化卡片式搜索结果，路径、时间、操作按钮一目了然
- **Quick Open** — 结果卡片上直接打开文件或所在文件夹；右键菜单
- **Incremental Sync** — 文件修改时间比对，仅更新变化的文件

## Screenshot

```
+-----------+------------------------------------------+
| Archive   | [All]  Search...                    [Go] |
| List      +------------------------------------------+
|   +       |                                          |
| +-------+ |  +------------------------------------+  |
| |* All  | |  | DOCX report.docx    [5 matches]   |  |
| |  428  | |  |   /home/docs/report.docx  [> Open]|  |
| +-------+ |  |   2024-03-15 14:30                  |  |
| |* Latex| |  | ----------------------------------- |  |
| |    3  | |  | ...keyword highlighted in preview.. |  |
| +-------+ |  +------------------------------------+  |
| |* Ob-  | |  +------------------------------------+  |
| |  sidi | |  | XLSX data.xlsx       [3 matches]   |  |
| |   um  | |  |   ...                              |  |
| |  351  | |  +------------------------------------+  |
| +-------+ |                                          |
+-----------+------------------------------------------+
| Found 27 results                                      |
+------------------------------------------------------+
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

1. Click **+** on the left sidebar to create a new archive — select a directory
2. Right-click an archive and choose **Update** to index all files within it
3. Select an archive (or **All**) in the sidebar, type a keyword, press Enter
4. Click **Open File** or **Open Folder** on any result card

## Configuration

Edit `config.py`:

```python
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data.db")
LOG_LEVEL = "INFO"          # DEBUG | INFO | WARNING | ERROR
```

## Project Structure

```
file_searcher/
├── main.py                  # Entry point
├── config.py                # DB path & logging
├── requirements.txt
├── database/
│   ├── __init__.py
│   ├── db_manager.py        # Connection, migration
│   ├── models.py            # Archive & Entry ORM
│   └── operations.py        # Archive CRUD, sync, search
├── file_handlers/
│   ├── __init__.py
│   ├── docx_handler.py      # .docx parser
│   ├── xlsx_handler.py      # .xlsx parser
│   └── md_handler.py        # .md parser
├── gui/
│   ├── __init__.py
│   └── app.py               # tkinter GUI
└── utils/
    ├── __init__.py
    └── helpers.py            # Context extractor
```

## Tech Stack

| Layer | Tech |
|-------|------|
| GUI | tkinter + ttk |
| DB | SQLite + SQLAlchemy ORM |
| Word | python-docx |
| Excel | openpyxl |
| Markdown | plain UTF-8 read |

## Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Search |
| `Escape` | Clear & go home |

## License

MIT
