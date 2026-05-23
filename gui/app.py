# -*- coding: utf-8 -*-
"""
主窗口 GUI — 三栏布局：侧栏归档列表 | 搜索 + 结果卡片
"""
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk
import logging
import os
import subprocess
import platform
import config
from database.db_manager import ensure_database, get_session, init_db
from database.operations import (
    create_archive, delete_archive, list_archives,
    rebuild_archive, search, update_archive_name,
)

logger = logging.getLogger(__name__)

# ==========================================
#  设计常量
# ==========================================
COLORS = {
    'bg':            '#F5F5F5',
    'surface':       '#FFFFFF',
    'sidebar_bg':    '#F0F0F0',
    'primary':       '#0078D4',
    'primary_dark':  '#106EBE',
    'primary_light': '#E8F4FD',
    'text':          '#1A1A1A',
    'text_secondary':'#605E5C',
    'text_muted':    '#8A8886',
    'border':        '#E1DFDD',
    'success':       '#107C10',
    'error':         '#D13438',
    'highlight_bg':  '#FFF4CE',
    'highlight_fg':  '#A80000',
    'active_item':   '#D0E4F7',
}

FONTS = {
    'title':      ('Microsoft YaHei UI', 16, 'bold'),
    'body':       ('Microsoft YaHei UI', 10),
    'small':      ('Microsoft YaHei UI', 9),
    'mono':       ('Consolas', 9),
    'card_title': ('Microsoft YaHei UI', 11, 'bold'),
    'search':     ('Microsoft YaHei UI', 11),
    'sidebar':    ('Microsoft YaHei UI', 10),
    'sidebar_bold':('Microsoft YaHei UI', 10, 'bold'),
}

FILE_ICONS = {'.docx': 'DOCX', '.xlsx': 'XLSX', '.md': 'MD'}
DEFAULT_FILE_ICON = 'FILE'

SIDEBAR_WIDTH = 220


# ==========================================
#  结果卡片
# ==========================================
class ResultCard(ttk.Frame):
    def __init__(self, parent, result, keyword,
                 on_open_file, on_open_folder):
        super().__init__(parent, style='Card.TFrame')
        self.result = result
        self.keyword = keyword
        self.on_open_file = on_open_file
        self.on_open_folder = on_open_folder
        self._build()

    def _build(self):
        res = self.result
        is_file = res['source_type'] == 'file'
        path = res.get('source_path', '')
        ext = os.path.splitext(path)[1].lower() if path else ''
        icon = FILE_ICONS.get(ext, DEFAULT_FILE_ICON) if is_file else 'TXT'

        self.configure(padding=0)
        inner = ttk.Frame(self, style='CardInner.TFrame')
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ---- 顶行 ----
        top_row = ttk.Frame(inner, style='CardInner.TFrame')
        top_row.pack(fill=tk.X, padx=14, pady=(12, 0))

        tk.Label(top_row, text=icon,
                 font=('Microsoft YaHei UI', 10, 'bold'),
                 bg=COLORS['surface'],
                 fg=COLORS['primary_dark']).pack(side=tk.LEFT, ipadx=2)

        name_text = res['source_name'] or '(无名称)'
        tk.Label(top_row, text=name_text, font=FONTS['card_title'],
                 bg=COLORS['surface'], fg=COLORS['text'],
                 anchor='w').pack(side=tk.LEFT, padx=(8, 0))

        count = res.get('match_count', 0)
        if count > 0:
            badge = tk.Label(top_row,
                             text=f'  {count} 处匹配  ',
                             font=FONTS['small'],
                             bg=COLORS['primary_light'],
                             fg=COLORS['primary_dark'])
            badge.pack(side=tk.LEFT, padx=(8, 0))

        if is_file and path and os.path.exists(path):
            btn_frame = ttk.Frame(top_row, style='CardInner.TFrame')
            btn_frame.pack(side=tk.RIGHT)
            for text, cmd in [('> 打开文件夹', self.on_open_folder),
                              ('> 打开文件',   self.on_open_file)]:
                btn = tk.Label(btn_frame, text=text, font=FONTS['small'],
                               bg=COLORS['surface'], fg=COLORS['primary'],
                               cursor='hand2')
                btn.pack(side=tk.RIGHT, padx=(8, 0))
                btn.bind('<Button-1>',
                         lambda e, p=path, c=cmd: c(p))
                btn.bind('<Enter>', lambda e, b=btn:
                         b.configure(fg=COLORS['primary_dark']))
                btn.bind('<Leave>', lambda e, b=btn:
                         b.configure(fg=COLORS['primary']))

        # ---- 路径 ----
        if path:
            pr = ttk.Frame(inner, style='CardInner.TFrame')
            pr.pack(fill=tk.X, padx=14, pady=(2, 0))
            tk.Label(pr, text=path, font=FONTS['small'],
                     bg=COLORS['surface'], fg=COLORS['text_secondary'],
                     anchor='w').pack(side=tk.LEFT)

        # ---- 时间 ----
        tr = ttk.Frame(inner, style='CardInner.TFrame')
        tr.pack(fill=tk.X, padx=14, pady=(2, 0))
        tk.Label(tr, text='\u231A ' + res['updated_at'],
                 font=FONTS['small'], bg=COLORS['surface'],
                 fg=COLORS['text_muted'],
                 anchor='w').pack(side=tk.LEFT)

        ttk.Separator(inner, orient='horizontal').pack(
            fill=tk.X, padx=14, pady=(8, 0))

        # ---- 预览 ----
        pf = ttk.Frame(inner, style='CardInner.TFrame')
        pf.pack(fill=tk.X, padx=14, pady=(6, 14))

        preview = tk.Text(pf, font=FONTS['mono'], wrap=tk.WORD,
                          height=3, borderwidth=0,
                          bg=COLORS['primary_light'],
                          fg=COLORS['text'], padx=8, pady=6,
                          relief='flat', cursor='arrow')
        preview.insert('1.0', res['highlight'])
        preview.configure(state='disabled')
        preview.pack(fill=tk.X, expand=True)
        preview.tag_configure('hl', background=COLORS['highlight_bg'],
                              foreground=COLORS['highlight_fg'])
        self._apply_highlights(preview)

        # 预览区独立滚动（不触发外层 Canvas 滚动）
        preview.bind('<MouseWheel>',
                     lambda e: self._preview_wheel(e, preview))
        preview.bind('<Button-4>',
                     lambda e: preview.yview_scroll(-1, 'units'))
        preview.bind('<Button-5>',
                     lambda e: preview.yview_scroll(1, 'units'))

        if is_file and path:
            for w in (inner, top_row, preview):
                w.bind('<Button-3>',
                       lambda e, p=path: self._context_menu(e, p))

    def _apply_highlights(self, text_widget):
        if not self.keyword:
            return
        kw = self.keyword
        start = '1.0'
        while True:
            pos = text_widget.search(kw, start, stopindex='end',
                                     nocase=True)
            if not pos:
                break
            end_pos = f'{pos} + {len(kw)} chars'
            text_widget.tag_add('hl', pos, end_pos)
            start = end_pos

    @staticmethod
    def _preview_wheel(event, text_widget):
        """预览区滚轮：滚动自身内容，阻止外层 Canvas 滚动"""
        text_widget.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        return 'break'

    def _context_menu(self, event, file_path):
        if not os.path.exists(file_path):
            messagebox.showinfo('提示', '文件已不存在')
            return
        menu = tk.Menu(self, tearoff=0, font=FONTS['body'],
                       bg=COLORS['surface'], fg=COLORS['text'],
                       activebackground=COLORS['primary_light'],
                       activeforeground=COLORS['primary_dark'])
        menu.add_command(label='打开文件',
                         command=lambda: self.on_open_file(file_path))
        menu.add_command(label='打开文件夹',
                         command=lambda: self.on_open_folder(file_path))
        menu.post(event.x_root, event.y_root)


# ==========================================
#  主窗口
# ==========================================
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('觅文')
        self.geometry('1060x700')
        self.minsize(850, 520)
        self.configure(bg=COLORS['bg'])

        self.engine = None
        self.session = None
        self.current_archive_id = None  # None = 全部
        self._results_shown = False

        self._setup_styles()
        self._create_header()
        self._create_body()
        self._create_status_bar()
        self._bind_events()
        self._init_db()

        logger.info('主窗口启动完成')

    # ======================================
    #  样式
    # ======================================
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=FONTS['body'], background=COLORS['bg'])
        style.configure('TFrame', background=COLORS['bg'])
        style.configure('Header.TFrame', background=COLORS['surface'])
        style.configure('Sidebar.TFrame', background=COLORS['sidebar_bg'])
        style.configure('Content.TFrame', background=COLORS['bg'])
        style.configure('Card.TFrame', background=COLORS['border'],
                        relief='flat')
        style.configure('CardInner.TFrame', background=COLORS['surface'])
        style.configure('TLabel', background=COLORS['bg'],
                        foreground=COLORS['text'])
        style.configure('HeaderTitle.TLabel', font=FONTS['title'],
                        background=COLORS['surface'],
                        foreground=COLORS['text'])
        style.configure('HeaderBtn.TButton', font=FONTS['small'],
                        background=COLORS['surface'],
                        foreground=COLORS['text_secondary'],
                        borderwidth=0, relief='flat', padding=(10, 4))
        style.map('HeaderBtn.TButton',
                  background=[('active', COLORS['primary_light']),
                              ('!active', COLORS['surface'])],
                  foreground=[('active', COLORS['primary'])])
        style.configure('TSeparator', background=COLORS['border'])

    # ======================================
    #  顶部导航栏
    # ======================================
    def _create_header(self):
        header = ttk.Frame(self, style='Header.TFrame')
        header.pack(fill=tk.X)
        left = ttk.Frame(header, style='Header.TFrame')
        left.pack(side=tk.LEFT, padx=20, pady=10)
        ttk.Label(left, text='觅文',
                  style='HeaderTitle.TLabel').pack(side=tk.LEFT)
        right = ttk.Frame(header, style='Header.TFrame')
        right.pack(side=tk.RIGHT, padx=12, pady=10)
        menu_btn = ttk.Button(right, text='...', style='HeaderBtn.TButton',
                              width=3)
        menu_btn.pack(side=tk.RIGHT, padx=(4, 0))
        menu_btn.bind('<Button-1>', self._show_more_menu)
        tk.Frame(self, height=1, bg=COLORS['border']).pack(fill=tk.X)

    def _show_more_menu(self, event):
        menu = tk.Menu(self, tearoff=0, font=FONTS['body'],
                       bg=COLORS['surface'], fg=COLORS['text'],
                       activebackground=COLORS['primary_light'],
                       activeforeground=COLORS['primary_dark'])
        menu.add_command(label='初始化数据库', command=self.reinit_db)
        menu.add_separator()
        menu.add_command(label='退出', command=self._on_close)
        menu.post(event.x_root, event.y_root)

    # ======================================
    #  主体：侧栏 + 主区域
    # ======================================
    def _create_body(self):
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                    bg=COLORS['border'], sashwidth=1)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # ---- 侧栏 ----
        self.sidebar = tk.Frame(self.paned, bg=COLORS['sidebar_bg'],
                                width=SIDEBAR_WIDTH)
        self.paned.add(self.sidebar, minsize=160)

        self._build_sidebar()

        # ---- 主区域 ----
        self.main_area = tk.Frame(self.paned, bg=COLORS['bg'])
        self.paned.add(self.main_area)
        self._build_main_area()

    # ======================================
    #  侧栏构建
    # ======================================
    def _build_sidebar(self):
        # 标题行
        top = tk.Frame(self.sidebar, bg=COLORS['sidebar_bg'])
        top.pack(fill=tk.X, padx=12, pady=(12, 6))

        tk.Label(top, text='归档列表', font=FONTS['sidebar_bold'],
                 bg=COLORS['sidebar_bg'],
                 fg=COLORS['text']).pack(side=tk.LEFT)

        add_btn = tk.Label(top, text='+', font=('Microsoft YaHei UI', 14),
                           bg=COLORS['sidebar_bg'], fg=COLORS['primary'],
                           cursor='hand2')
        add_btn.pack(side=tk.RIGHT)
        add_btn.bind('<Button-1>', lambda e: self._add_archive())

        tk.Frame(self.sidebar, height=1,
                 bg=COLORS['border']).pack(fill=tk.X, padx=8)

        # 列表（Canvas 滚动）
        self.sidebar_canvas = tk.Canvas(
            self.sidebar, bg=COLORS['sidebar_bg'],
            highlightthickness=0, bd=0)
        sb_scroll = ttk.Scrollbar(self.sidebar, orient='vertical',
                                  command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=sb_scroll.set)

        self.sidebar_list = tk.Frame(self.sidebar_canvas,
                                     bg=COLORS['sidebar_bg'])
        self._sw = self.sidebar_canvas.create_window(
            (0, 0), window=self.sidebar_list, anchor='nw')

        self.sidebar_list.bind('<Configure>',
                               lambda e: self._update_sidebar_scroll())
        self.sidebar_canvas.bind('<Configure>',
                                 lambda e: self.sidebar_canvas.itemconfig(
                                     self._sw, width=e.width))
        # 鼠标滚轮
        self.sidebar_canvas.bind('<Enter>', self._bind_sidebar_wheel)
        self.sidebar_canvas.bind('<Leave>', self._unbind_sidebar_wheel)

        sb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- 右键菜单 ----
        self.sidebar_menu = tk.Menu(self, tearoff=0, font=FONTS['body'],
                                    bg=COLORS['surface'],
                                    fg=COLORS['text'],
                                    activebackground=COLORS['primary_light'],
                                    activeforeground=COLORS['primary_dark'])

    def _bind_sidebar_wheel(self, event):
        if platform.system() == 'Windows':
            self.sidebar_canvas.bind_all('<MouseWheel>',
                                         self._sb_mousewheel)
        else:
            self.sidebar_canvas.bind_all('<Button-4>',
                                         self._sb_mw_up)
            self.sidebar_canvas.bind_all('<Button-5>',
                                         self._sb_mw_down)

    def _unbind_sidebar_wheel(self, event):
        if platform.system() == 'Windows':
            self.sidebar_canvas.unbind_all('<MouseWheel>')
        else:
            self.sidebar_canvas.unbind_all('<Button-4>')
            self.sidebar_canvas.unbind_all('<Button-5>')

    def _sb_mousewheel(self, event):
        self.sidebar_canvas.yview_scroll(
            int(-1 * (event.delta / 120)), 'units')

    def _sb_mw_up(self, event):
        self.sidebar_canvas.yview_scroll(-1, 'units')

    def _sb_mw_down(self, event):
        self.sidebar_canvas.yview_scroll(1, 'units')

    def _update_sidebar_scroll(self):
        """更新侧栏 Canvas 滚动区域以匹配内容高度"""
        self.sidebar_canvas.update_idletasks()
        bbox = self.sidebar_canvas.bbox('all')
        if bbox:
            self.sidebar_canvas.configure(scrollregion=bbox)

    def _refresh_sidebar(self):
        """刷新侧栏归档列表"""
        for w in self.sidebar_list.winfo_children():
            w.destroy()

        if not self.session:
            return

        try:
            archives, total = list_archives(self.session)
        except Exception:
            return

        row_bg = COLORS['sidebar_bg']

        # ---- 全部 ----
        self._add_sidebar_item(
            '全部', total,
            is_all=True,
            active=(self.current_archive_id is None),
        )

        # 分隔
        tk.Frame(self.sidebar_list, height=1,
                 bg=COLORS['border']).pack(fill=tk.X, padx=8, pady=2)

        # ---- 各归档 ----
        for a in archives:
            self._add_sidebar_item(
                a['name'], a['entry_count'],
                archive_id=a['id'],
                active=(self.current_archive_id == a['id']),
            )
        self._update_sidebar_scroll()

    def _add_sidebar_item(self, name, count, is_all=False,
                          archive_id=None, active=False):
        bg = COLORS['active_item'] if active else COLORS['sidebar_bg']
        item = tk.Frame(self.sidebar_list, bg=bg, cursor='hand2',
                        height=36)
        item.pack(fill=tk.X, padx=4, pady=1)
        item.pack_propagate(False)

        icon_text = '\u2605 ' if is_all else '\u25CF '
        icon_color = COLORS['primary'] if is_all else COLORS['text_muted']

        tk.Label(item, text=icon_text, font=FONTS['sidebar'],
                 bg=bg, fg=icon_color).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(item, text=name, font=FONTS['sidebar'],
                 bg=bg, fg=COLORS['text'],
                 anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(item, text=str(count), font=FONTS['small'],
                 bg=bg,
                 fg=COLORS['text_secondary']).pack(side=tk.RIGHT, padx=8)

        # 点击事件
        for w in item.winfo_children():
            w.bind('<Button-1>',
                   lambda e, aid=archive_id: self._select_archive(aid))
        item.bind('<Button-1>',
                  lambda e, aid=archive_id: self._select_archive(aid))

        # 悬停
        def on_enter(e, it=item):
            if it['bg'] != COLORS['active_item']:
                self._set_item_bg(it, COLORS['primary_light'])

        def on_leave(e, it=item, a=active):
            if not a:
                self._set_item_bg(it, COLORS['sidebar_bg'])

        item.bind('<Enter>', on_enter)
        item.bind('<Leave>', on_leave)
        for w in item.winfo_children():
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)

        # 右键菜单（仅归档项）
        if not is_all and archive_id is not None:
            item.bind('<Button-3>',
                      lambda e, aid=archive_id: self._archive_context(e, aid))
            for w in item.winfo_children():
                w.bind('<Button-3>',
                       lambda e, aid=archive_id:
                       self._archive_context(e, aid))

    def _set_item_bg(self, item, color):
        item.configure(bg=color)
        for w in item.winfo_children():
            w.configure(bg=color)

    def _select_archive(self, archive_id):
        self.current_archive_id = archive_id
        self._refresh_sidebar()
        self._go_home()

    def _archive_context(self, event, archive_id):
        menu = tk.Menu(self, tearoff=0, font=FONTS['body'],
                       bg=COLORS['surface'], fg=COLORS['text'],
                       activebackground=COLORS['primary_light'],
                       activeforeground=COLORS['primary_dark'])
        menu.add_command(label='更新归档',
                         command=lambda: self._rebuild_archive(archive_id))
        menu.add_command(label='重命名',
                         command=lambda: self._rename_archive(archive_id))
        menu.add_separator()
        menu.add_command(label='删除归档',
                         command=lambda: self._delete_archive(archive_id))
        menu.post(event.x_root, event.y_root)

    # ======================================
    #  主区域构建
    # ======================================
    def _build_main_area(self):
        # 搜索栏
        self._create_search_bar()

        # 内容区
        self.content_frame = tk.Frame(self.main_area, bg=COLORS['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # 欢迎页
        self.welcome_frame = tk.Frame(self.content_frame, bg=COLORS['bg'])

        # 结果区
        self.result_container = tk.Frame(self.content_frame,
                                         bg=COLORS['bg'])
        self.result_canvas = tk.Canvas(
            self.result_container, bg=COLORS['bg'],
            highlightthickness=0, bd=0)
        self.result_scrollbar = ttk.Scrollbar(
            self.result_container, orient='vertical',
            command=self.result_canvas.yview)
        self.result_canvas.configure(
            yscrollcommand=self.result_scrollbar.set)

        self.result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.cards_frame = tk.Frame(self.result_canvas, bg=COLORS['bg'])
        self._cw = self.result_canvas.create_window(
            (0, 0), window=self.cards_frame, anchor='nw')

        self.cards_frame.bind('<Configure>',
                              lambda e: self.result_canvas.configure(
                                  scrollregion=self.result_canvas.bbox(
                                      'all')))
        self.result_canvas.bind('<Configure>',
                                lambda e: self.result_canvas.itemconfig(
                                    self._cw, width=e.width))
        self.result_canvas.bind('<Enter>', self._bind_mw)
        self.result_canvas.bind('<Leave>', self._unbind_mw)

        self._show_welcome()

    def _create_search_bar(self):
        self.search_bar_frame = tk.Frame(self.main_area,
                                         bg=COLORS['surface'], height=52)
        self.search_bar_frame.pack(fill=tk.X)
        self.search_bar_frame.pack_propagate(False)

        inner = tk.Frame(self.search_bar_frame, bg=COLORS['surface'])
        inner.pack(expand=True, pady=6)

        # 归档上下文标签
        self.scope_label = tk.Label(
            inner, text='全部归档', font=FONTS['small'],
            bg=COLORS['primary_light'],
            fg=COLORS['primary_dark'], padx=6)
        self.scope_label.pack(side=tk.LEFT, padx=(12, 8))

        # 搜索输入框
        entry_frame = tk.Frame(inner, bg=COLORS['surface'],
                               highlightbackground=COLORS['border'],
                               highlightthickness=1, bd=0)
        entry_frame.pack(side=tk.LEFT)

        self.keyword_var = tk.StringVar()
        self.keyword_var.trace_add('write', self._on_keyword_change)
        self.keyword_entry = tk.Entry(
            entry_frame, textvariable=self.keyword_var,
            font=FONTS['search'], width=36,
            bg=COLORS['surface'], fg=COLORS['text'],
            bd=0, relief='flat', insertbackground=COLORS['primary'])
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X,
                                padx=(10, 8), pady=6)
        self.keyword_entry.bind('<Return>', lambda e: self.do_search())

        self.clear_btn = tk.Label(entry_frame, text='\u2715',
                                  font=FONTS['body'],
                                  bg=COLORS['surface'],
                                  fg=COLORS['text_muted'],
                                  cursor='hand2')
        self.clear_btn.bind('<Button-1>', lambda e: self._clear_search())

        self.search_btn = tk.Button(
            inner, text='搜索', font=FONTS['body'],
            bg=COLORS['primary'], fg='white',
            activebackground=COLORS['primary_dark'],
            activeforeground='white',
            bd=0, relief='flat', padx=20, pady=8,
            cursor='hand2', command=self.do_search)
        self.search_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 焦点效果
        self.keyword_entry.bind(
            '<FocusIn>', lambda e: entry_frame.configure(
                highlightbackground=COLORS['primary']))
        self.keyword_entry.bind(
            '<FocusOut>', lambda e: entry_frame.configure(
                highlightbackground=COLORS['border']))

        tk.Frame(self.search_bar_frame, height=1,
                 bg=COLORS['border']).pack(fill=tk.X, side=tk.BOTTOM)

    def _on_keyword_change(self, *args):
        if self.keyword_var.get().strip():
            self.clear_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=6)
        else:
            self.clear_btn.pack_forget()

    def _clear_search(self):
        self.keyword_var.set('')
        self.keyword_entry.focus_set()
        self._go_home()

    def _update_scope_label(self):
        if self.current_archive_id is None:
            self.scope_label.configure(text='全部归档')
        else:
            try:
                from database.models import Archive
                a = self.session.query(Archive).get(
                    self.current_archive_id)
                name = a.name if a else '???'
                self.scope_label.configure(text=f'归档: {name}')
            except Exception:
                self.scope_label.configure(text='全部归档')

    # ======================================
    #  欢迎页 / 结果区切换
    # ======================================
    def _show_welcome(self):
        self._hide_results()
        self._results_shown = False
        self.welcome_stats_lbl = None  # 清除旧引用，防止 _update 操作已销毁控件
        for w in self.welcome_frame.winfo_children():
            w.destroy()

        self.welcome_frame.place(relx=0.5, rely=0.45, anchor='center')

        tk.Label(self.welcome_frame, text='\u2726',
                 font=('Microsoft YaHei UI', 36),
                 bg=COLORS['bg'],
                 fg=COLORS['primary']).pack(pady=(0, 8))

        tk.Label(self.welcome_frame, text='觅文',
                 font=('Microsoft YaHei UI', 28, 'bold'),
                 bg=COLORS['bg'],
                 fg=COLORS['text']).pack()

        tk.Label(self.welcome_frame,
                 text='文档搜索，一觅即中',
                 font=FONTS['body'], bg=COLORS['bg'],
                 fg=COLORS['text_secondary']).pack(pady=(4, 0))

        self._update_welcome_stats()

    def _update_welcome_stats(self):
        label = getattr(self, 'welcome_stats_lbl', None)
        if label is None:
            self.welcome_stats_lbl = tk.Label(
                self.welcome_frame, text='', font=FONTS['small'],
                bg=COLORS['bg'], fg=COLORS['text_muted'])
            self.welcome_stats_lbl.pack(pady=(16, 0))
            label = self.welcome_stats_lbl
        try:
            if self.session:
                from database.models import Entry, Archive
                total = self.session.query(Entry).count()
                arch_count = self.session.query(Archive).count()
                label.configure(
                    text=f'已索引 {total} 条记录（{arch_count} 个归档）')
            else:
                label.configure(text='正在连接数据库...')
        except Exception:
            try:
                label.configure(text='')
            except Exception:
                pass

    def _hide_results(self):
        self.result_container.pack_forget()

    def _show_results(self):
        self.welcome_frame.place_forget()
        self.result_container.pack(fill=tk.BOTH, expand=True)
        self._results_shown = True

    def _go_home(self):
        self._hide_results()
        self._results_shown = False
        self._show_welcome()

    # ======================================
    #  鼠标滚轮（结果区）
    # ======================================
    def _bind_mw(self, event):
        if platform.system() == 'Windows':
            self.result_canvas.bind_all('<MouseWheel>', self._on_mw)
        else:
            self.result_canvas.bind_all('<Button-4>', self._on_mw_up)
            self.result_canvas.bind_all('<Button-5>', self._on_mw_down)

    def _unbind_mw(self, event):
        if platform.system() == 'Windows':
            self.result_canvas.unbind_all('<MouseWheel>')
        else:
            self.result_canvas.unbind_all('<Button-4>')
            self.result_canvas.unbind_all('<Button-5>')

    def _on_mw(self, event):
        if isinstance(event.widget, tk.Text):
            return
        self.result_canvas.yview_scroll(
            int(-1 * (event.delta / 120)), 'units')

    def _on_mw_up(self, event):
        if isinstance(event.widget, tk.Text):
            return
        self.result_canvas.yview_scroll(-1, 'units')

    def _on_mw_down(self, event):
        if isinstance(event.widget, tk.Text):
            return
        self.result_canvas.yview_scroll(1, 'units')

    # ======================================
    #  状态栏
    # ======================================
    def _create_status_bar(self):
        sf = tk.Frame(self, bg=COLORS['surface'], height=28)
        sf.pack(side=tk.BOTTOM, fill=tk.X)
        sf.pack_propagate(False)
        tk.Frame(sf, height=1, bg=COLORS['border']).pack(fill=tk.X)
        self.status_bar = tk.Label(
            sf, text='就绪', font=FONTS['small'],
            bg=COLORS['surface'], fg=COLORS['text_secondary'],
            anchor='w', padx=16)
        self.status_bar.pack(fill=tk.X, expand=True)

    # ======================================
    #  全局事件
    # ======================================
    def _bind_events(self):
        self.bind('<Escape>', lambda e: self._clear_search())
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _on_close(self):
        logger.info('用户关闭窗口')
        self.destroy()

    # ======================================
    #  数据库初始化
    # ======================================
    def _init_db(self):
        logger.info('初始化数据库连接')
        try:
            self.engine = ensure_database()
            self.session = get_session(self.engine)
            self.status_bar.configure(text='数据库已连接')
            self._refresh_sidebar()
            self._update_welcome_stats()
            logger.info('数据库连接成功')
        except Exception as e:
            logger.exception('数据库连接失败')
            messagebox.showerror('错误', f'数据库连接失败: {e}')
            self.status_bar.configure(text='数据库连接失败')

    # ======================================
    #  数据库操作
    # ======================================
    def reinit_db(self):
        logger.info('用户请求重新初始化数据库')
        if not messagebox.askyesno('确认',
                                   '此操作将删除所有现有数据，确定吗？'):
            return
        try:
            self.engine = init_db()
            self.session = get_session(self.engine)
            self.current_archive_id = None
            self.status_bar.configure(text='数据库已重新初始化')
            self._refresh_sidebar()
            self._update_welcome_stats()
            self._go_home()
            logger.info('数据库重新初始化成功')
        except Exception as e:
            logger.exception('数据库重新初始化失败')
            messagebox.showerror('错误', f'初始化失败: {e}')

    # ---- 归档操作 ----
    def _add_archive(self):
        if not self.session:
            return
        root_dir = filedialog.askdirectory(
            title='选择归档目录',
            parent=self)
        if not root_dir:
            return
        name = simpledialog.askstring(
            '归档名称', '请输入归档名称:',
            initialvalue=os.path.basename(root_dir),
            parent=self)
        if not name:
            return
        try:
            create_archive(self.session, name, root_dir)
            self._refresh_sidebar()
            self._update_welcome_stats()
            self.status_bar.configure(text=f'归档 [{name}] 已创建')
        except Exception as e:
            logger.exception('创建归档失败')
            messagebox.showerror('错误', f'创建归档失败: {e}')

    def _rebuild_archive(self, archive_id):
        if not self.session:
            return
        try:
            self.status_bar.configure(text='正在更新归档...')
            self.update()
            rebuild_archive(self.session, archive_id)
            self._refresh_sidebar()
            self._update_welcome_stats()
            self.status_bar.configure(text='归档更新完成')
        except Exception as e:
            logger.exception('更新归档失败')
            messagebox.showerror('错误', f'更新归档失败: {e}')
            self.status_bar.configure(text='更新归档失败')

    def _rename_archive(self, archive_id):
        if not self.session:
            return
        new_name = simpledialog.askstring(
            '重命名', '请输入新名称:', parent=self)
        if not new_name:
            return
        try:
            update_archive_name(self.session, archive_id, new_name)
            self._refresh_sidebar()
            self._update_scope_label()
            self.status_bar.configure(text='归档已重命名')
        except Exception as e:
            logger.exception('重命名归档失败')
            messagebox.showerror('错误', f'重命名失败: {e}')

    def _delete_archive(self, archive_id):
        if not self.session:
            return
        if not messagebox.askyesno('确认',
                                   '确定要删除此归档及其中所有文件记录吗？'):
            return
        try:
            delete_archive(self.session, archive_id)
            if self.current_archive_id == archive_id:
                self.current_archive_id = None
            self._refresh_sidebar()
            self._update_welcome_stats()
            self._go_home()
            self.status_bar.configure(text='归档已删除')
        except Exception as e:
            logger.exception('删除归档失败')
            messagebox.showerror('错误', f'删除归档失败: {e}')

    # ======================================
    #  搜索 & 结果展示
    # ======================================
    def do_search(self):
        keyword = self.keyword_var.get().strip()
        if not keyword:
            return
        logger.info(f'执行搜索 [{self.current_archive_id}]: {keyword}')
        self._update_scope_label()
        self.status_bar.configure(text=f'正在搜索: {keyword}...')
        self.update()

        try:
            results = search(self.session, keyword, self.current_archive_id)
        except Exception as e:
            logger.exception('搜索失败')
            messagebox.showerror('错误', f'搜索失败: {e}')
            self.status_bar.configure(text='搜索失败')
            return

        self._clear_results()
        self._show_results()

        if not results:
            self._show_empty_result(keyword)
            scope = '当前归档' if self.current_archive_id else '所有归档'
            self.status_bar.configure(
                text=f'在{scope}中未找到 "{keyword}"')
            return

        self._render_results(results, keyword)
        self.status_bar.configure(text=f'找到 {len(results)} 条结果')
        self.result_canvas.yview_moveto(0)

    def _clear_results(self):
        self._pending_cards = []
        for child in self.cards_frame.winfo_children():
            child.destroy()

    def _show_empty_result(self, keyword):
        ef = tk.Frame(self.cards_frame, bg=COLORS['bg'])
        ef.pack(pady=60)
        tk.Label(ef, text='\u2726',
                 font=('Microsoft YaHei UI', 36),
                 bg=COLORS['bg']).pack()
        tk.Label(ef, text='未找到匹配内容',
                 font=FONTS['card_title'], bg=COLORS['bg'],
                 fg=COLORS['text']).pack(pady=(8, 4))
        tk.Label(ef,
                 text=f'没有找到包含 "{keyword}" 的文档',
                 font=FONTS['body'], bg=COLORS['bg'],
                 fg=COLORS['text_secondary']).pack()
        tk.Label(ef,
                 text='试试其他关键词或更新归档',
                 font=FONTS['small'], bg=COLORS['bg'],
                 fg=COLORS['text_muted']).pack(pady=(8, 0))

    def _render_results(self, results, keyword):
        """分批渐进渲染，避免一次性创建大量控件卡顿 UI"""
        self._pending_cards = list(results)
        self._card_keyword = keyword
        self._card_idx = 0
        self._render_batch()

    def _render_batch(self):
        batch_size = 8
        for _ in range(batch_size):
            if self._card_idx >= len(self._pending_cards):
                return
            res = self._pending_cards[self._card_idx]
            card = ResultCard(self.cards_frame, res, self._card_keyword,
                              on_open_file=self.open_file,
                              on_open_folder=self.open_folder)
            card.pack(fill=tk.X, padx=16, pady=(0, 10))
            self._card_idx += 1
        # 下一批
        self.after(1, self._render_batch)

    # ======================================
    #  文件操作
    # ======================================
    def open_file(self, file_path):
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            else:
                subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            logger.exception('打开文件失败')
            messagebox.showerror('错误', f'打开文件失败: {e}')

    def open_folder(self, file_path):
        folder = os.path.dirname(file_path)
        if not os.path.exists(folder):
            messagebox.showerror('错误', '文件夹不存在')
            return
        try:
            if platform.system() == 'Windows':
                os.startfile(folder)
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            logger.exception('打开文件夹失败')
            messagebox.showerror('错误', f'打开文件夹失败: {e}')
