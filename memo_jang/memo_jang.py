import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
from datetime import datetime
from pathlib import Path

APP_TITLE = "memo_jang"
DEFAULT_TAB = "기본"
PLACEHOLDER_TEXT = "여기에 메모를 입력하세요..."


def get_resource_path(relative_path: str) -> Path:
    """PyInstaller로 패키징된 exe 내부의 파일 경로 탐색"""
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


def get_data_file_path() -> Path:
    """Windows 배포(exe) 기준 사용자 데이터 경로 반환"""
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / "memo_jang"
    else:
        base = Path.home() / ".memo_jang"
    return base / "memos.json"


class MemoTabUI:
    """한 개의 메모 탭 UI/로직 (추가/수정 모드 지원)"""

    def __init__(self, parent, app, tab_name: str):
        self.app = app
        self.tab_name = tab_name
        self.frame = ttk.Frame(parent)
        self.editing_index = None

        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=6, pady=6)

        self.btn_save = ttk.Button(top, text="저장", command=self.save_memo)
        self.btn_save.pack(side="left")

        self.btn_cancel = ttk.Button(top, text="취소", command=self.reset_editor)

        ttk.Button(top, text="불러오기", command=self.load_selected_to_editor).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="삭제", command=self.delete_selected).pack(side="left", padx=(6, 0))

        self.editor = tk.Text(self.frame, wrap="word", height=14, foreground="gray")
        self.editor.pack(fill="x", padx=6)
        self.editor.insert("1.0", PLACEHOLDER_TEXT)

        self.editor.bind("<FocusIn>", self._on_focus_in)
        self.editor.bind("<FocusOut>", self._on_focus_out)

        blank = ttk.Frame(self.frame)
        blank.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(blank, text="해당 탭의 메모들").pack(anchor="w")

        mid = ttk.Frame(self.frame)
        mid.pack(fill="both", expand=True, padx=6, pady=6)

        self.listbox = tk.Listbox(mid, selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(mid, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        self.refresh()

    def _on_focus_in(self, _event):
        if self.editor.get("1.0", "end-1c") == PLACEHOLDER_TEXT:
            self.editor.delete("1.0", "end")
            self.editor.config(foreground="black")

    def _on_focus_out(self, _event):
        if not self.editor.get("1.0", "end-1c").strip():
            self.reset_editor()

    def memos(self):
        return self.app.data["tabs"][self.tab_name]

    def get_editor_text(self) -> str:
        text = self.editor.get("1.0", "end-1c").rstrip()
        if text == PLACEHOLDER_TEXT:
            return ""
        return text

    def reset_editor(self):
        self.editing_index = None
        self.btn_save.config(text="저장")
        self.btn_cancel.pack_forget()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", PLACEHOLDER_TEXT)
        self.editor.config(foreground="gray")

    def save_memo(self):
        text = self.get_editor_text()
        if not text.strip():
            messagebox.showinfo("안내", "저장할 내용이 비어있습니다.")
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.editing_index is not None and self.editing_index < len(self.memos()):
            self.memos().pop(self.editing_index)
            self.memos().insert(0, {"created_at": f"{now_str} (수정)", "text": text})
        else:
            self.memos().insert(0, {"created_at": now_str, "text": text})

        self.app.save_data()
        self.refresh()
        self.reset_editor()

    def load_selected_to_editor(self):
        indices = list(self.listbox.curselection())
        if not indices:
            messagebox.showinfo("안내", "불러올 항목을 선택하세요.")
            return

        idx = indices[0]
        self.editing_index = idx
        self.btn_save.config(text="수정 완료")
        self.btn_cancel.pack(side="left", padx=(6, 0))

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", self.memos()[idx]["text"])
        self.editor.config(foreground="black")

    def delete_selected(self):
        indices = list(self.listbox.curselection())
        if not indices:
            messagebox.showinfo("안내", "삭제할 항목을 선택하세요.")
            return

        if not messagebox.askyesno("삭제 확인", f"{len(indices)}개 메모를 삭제하시겠습니까?"):
            return

        for idx in sorted(indices, reverse=True):
            del self.memos()[idx]

        self.app.save_data()
        self.refresh()
        self.reset_editor()

    def refresh(self):
        self.listbox.delete(0, "end")
        for m in self.memos():
            first_line = (m["text"].splitlines()[0] if m["text"] else "").strip()
            if len(first_line) > 14:
                first_line = first_line[:14] + "…"
            title = f'{m["created_at"]} | {first_line}'
            self.listbox.insert("end", title)


class MemoJangApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.attributes("-topmost", True)
        self.root.title(APP_TITLE)
        self.root.geometry("320x800+820+100")
        self.root.resizable(True, True)

        # 아이콘 적용
        icon_path = get_resource_path("memo_jang.ico")
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

        self.save_file = get_data_file_path()
        self.data = self.load_data()

        if "tabs" not in self.data or not isinstance(self.data["tabs"], dict):
            self.data = {"tabs": {DEFAULT_TAB: []}}
        if DEFAULT_TAB not in self.data["tabs"]:
            self.data["tabs"][DEFAULT_TAB] = []

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)

        self.tab_uis = {}

        for tab_name in list(self.data["tabs"].keys()):
            self.create_memo_tab(tab_name)

        self.manage_tab = ttk.Frame(self.nb)
        self.nb.add(self.manage_tab, text="탭 관리")
        self.build_manage_tab()

        self.select_tab(DEFAULT_TAB)

    def create_memo_tab(self, tab_name: str):
        tab_name = tab_name.strip()
        if not tab_name or tab_name in self.tab_uis:
            return

        self.data["tabs"].setdefault(tab_name, [])

        ui = MemoTabUI(self.nb, self, tab_name)
        self.tab_uis[tab_name] = ui

        manage_index = None
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "탭 관리":
                manage_index = i
                break

        if manage_index is None:
            self.nb.add(ui.frame, text=tab_name)
        else:
            self.nb.insert(manage_index, ui.frame, text=tab_name)

        self.save_data()
        self.refresh_manage_list()

    def delete_memo_tab(self, tab_name: str):
        if tab_name == DEFAULT_TAB:
            messagebox.showinfo("안내", f"'{DEFAULT_TAB}' 탭은 삭제할 수 없습니다.")
            return
        if tab_name not in self.tab_uis:
            return

        memo_count = len(self.data["tabs"].get(tab_name, []))
        if not messagebox.askyesno("탭 삭제 확인", f"'{tab_name}' 탭을 삭제하시겠습니까?\n(포함된 메모 {memo_count}개도 함께 삭제됩니다)"):
            return

        frame = self.tab_uis[tab_name].frame
        self.nb.forget(frame)

        del self.tab_uis[tab_name]
        if tab_name in self.data["tabs"]:
            del self.data["tabs"][tab_name]

        self.save_data()
        self.refresh_manage_list()
        self.select_tab(DEFAULT_TAB)

    def select_tab(self, tab_name: str):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == tab_name:
                self.nb.select(i)
                return

    def build_manage_tab(self):
        top = ttk.Frame(self.manage_tab)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Label(top, text="새 탭 이름").pack(anchor="w")

        row = ttk.Frame(top)
        row.pack(fill="x", pady=(4, 0))

        self.new_tab_entry = ttk.Entry(row)
        self.new_tab_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text="추가", command=self.on_add_tab).pack(side="left", padx=(6, 0))

        mid = ttk.Frame(self.manage_tab)
        mid.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(mid, text="현재 탭 목록").pack(anchor="w")

        self.tabs_listbox = tk.Listbox(mid)
        self.tabs_listbox.pack(fill="both", expand=True, pady=(4, 6))

        ttk.Button(mid, text="선택 탭 삭제", command=self.on_delete_tab).pack(fill="x")

        path_info = ttk.Label(
            self.manage_tab,
            text=f"데이터 저장 위치:\n{self.save_file}",
            wraplength=280
        )
        path_info.pack(fill="x", padx=6, pady=(0, 0))

        self.refresh_manage_list()

    def refresh_manage_list(self):
        if not hasattr(self, "tabs_listbox"):
            return
        self.tabs_listbox.delete(0, "end")
        for name in self.get_tab_names():
            self.tabs_listbox.insert("end", name)

    def get_tab_names(self):
        names = list(self.data["tabs"].keys())
        names = sorted([n for n in names if n != DEFAULT_TAB])
        return [DEFAULT_TAB] + names

    def on_add_tab(self):
        name = self.new_tab_entry.get().strip()
        if not name:
            messagebox.showinfo("안내", "탭 이름을 입력하세요.")
            return
        if name in self.data["tabs"]:
            messagebox.showinfo("안내", "이미 존재하는 탭 이름입니다.")
            return
        if name == "탭 관리":
            messagebox.showinfo("안내", "'탭 관리'는 예약된 이름입니다.")
            return

        self.create_memo_tab(name)
        self.new_tab_entry.delete(0, "end")
        self.select_tab(name)

    def on_delete_tab(self):
        sel = self.tabs_listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "삭제할 탭을 선택하세요.")
            return
        name = self.tabs_listbox.get(sel[0])
        self.delete_memo_tab(name)

    def load_data(self):
        if not self.save_file.exists():
            return {"tabs": {DEFAULT_TAB: []}}
        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"tabs": {DEFAULT_TAB: []}}

    def save_data(self):
        try:
            self.save_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = MemoJangApp(root)
    root.mainloop()
