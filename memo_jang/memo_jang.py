import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime

APP_TITLE = "memo_jang"
SAVE_FILE = "memos.json"
DEFAULT_TAB = "기본"


class MemoTabUI:
    """한 개의 메모 탭 UI/로직(스택 + 목록 + 미리보기)"""
    def __init__(self, parent, app, tab_name: str):
        self.app = app
        self.tab_name = tab_name

        self.frame = ttk.Frame(parent)

        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Button(top, text="저장", command=self.push_memo).pack(side="left")
        ttk.Button(top, text="불러오기", command=self.load_selected_to_editor).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="삭제", command=self.delete_selected).pack(side="left", padx=(6, 0))

        # 작성 Text (placeholder 포함)
        self.editor = tk.Text(
        self.frame,
        wrap="word",
        height=14,
        foreground="gray"
        )
        self.editor.pack(fill="x", padx=6)

        PLACEHOLDER_TEXT = "여기에 메모를 입력하세요..."

        # 초기 placeholder
        self.editor.insert("1.0", PLACEHOLDER_TEXT)

        def on_focus_in(event):
            if self.editor.get("1.0", "end-1c") == PLACEHOLDER_TEXT:
                self.editor.delete("1.0", "end")
            self.editor.config(foreground="black")


        def on_focus_out(event):
            if not self.editor.get("1.0", "end-1c").strip():
                self.editor.insert("1.0", PLACEHOLDER_TEXT)
            self.editor.config(foreground="gray")

        self.editor.bind("<FocusIn>", on_focus_in)
        self.editor.bind("<FocusOut>", on_focus_out)

        # 목록 + 스크롤
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

        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        self.refresh()

    def memos(self):
        return self.app.data["tabs"][self.tab_name]

    def get_editor_text(self) -> str:
        return self.editor.get("1.0", "end-1c").rstrip()

    def push_memo(self):
        text = self.get_editor_text()
        if not text:
            messagebox.showinfo("안내", "저장할 내용이 비어있습니다.")
            return

        item = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": text
        }

        self.memos().insert(0, item)

        self.app.save_data()
        self.refresh()

    def get_selected_index(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return int(sel[0])

    def delete_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("안내", "삭제할 항목을 선택하세요.")
            return
        del self.memos()[idx]
        self.app.save_data()
        self.refresh()
        self.set_preview_text("")

    def load_selected_to_editor(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showinfo("안내", "불러올 항목을 선택하세요.")
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", self.memos()[idx]["text"])

    def on_select(self, _event=None):
        idx = self.get_selected_index()
        if idx is None:
            self.set_preview_text("")
            return
        self.set_preview_text(self.memos()[idx]["text"])

    def set_preview_text(self, text: str):
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.config(state="disabled")

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

        self.data = self.load_data()  # {"tabs": {"기본":[...], "extab":[...]}}
        if "tabs" not in self.data or not isinstance(self.data["tabs"], dict):
            self.data = {"tabs": {DEFAULT_TAB: []}}
        if DEFAULT_TAB not in self.data["tabs"]:
            self.data["tabs"][DEFAULT_TAB] = []

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)

        self.tab_uis = {}  # tab_name -> MemoTabUI

        for tab_name in list(self.data["tabs"].keys()):
            self.create_memo_tab(tab_name)

        self.manage_tab = ttk.Frame(self.nb)
        self.nb.add(self.manage_tab, text="탭 관리")
        self.build_manage_tab()

        # 첫 탭 선택
        self.select_tab(DEFAULT_TAB)

    # -------------------------
    # 탭 생성/삭제
    # -------------------------
    def create_memo_tab(self, tab_name: str):
        tab_name = tab_name.strip()
        if not tab_name:
            return
        if tab_name in self.tab_uis:
            return

        # 데이터 준비
        self.data["tabs"].setdefault(tab_name, [])

        ui = MemoTabUI(self.nb, self, tab_name)
        self.tab_uis[tab_name] = ui

        # "탭 관리" 탭 앞에 삽입하고 싶으니: 관리 탭이 이미 있으면 그 index 앞에 넣기
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

        # Notebook에서 해당 프레임 제거
        frame = self.tab_uis[tab_name].frame
        self.nb.forget(frame)

        # 메모리/데이터에서 제거
        del self.tab_uis[tab_name]
        if tab_name in self.data["tabs"]:
            del self.data["tabs"][tab_name]

        self.save_data()
        self.refresh_manage_list()
        self.select_tab(DEFAULT_TAB)

    def select_tab(self, tab_name: str):
        # 탭 텍스트로 찾아 선택
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == tab_name:
                self.nb.select(i)
                return

    # 탭 관리UI
    def build_manage_tab(self):
        top = ttk.Frame(self.manage_tab)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Label(top, text="새 탭 이름").pack(anchor="w")

        row = ttk.Frame(top)
        row.pack(fill="x", pady=(4, 0))

        self.new_tab_entry = ttk.Entry(row)
        self.new_tab_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text="추가", command=self.on_add_tab).pack(side="left", padx=(6, 0))

        # 탭 목록 + 삭제
        mid = ttk.Frame(self.manage_tab)
        mid.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(mid, text="현재 탭 목록").pack(anchor="w")

        self.tabs_listbox = tk.Listbox(mid)
        self.tabs_listbox.pack(fill="both", expand=True, pady=(4, 6))

        ttk.Button(mid, text="선택 탭 삭제", command=self.on_delete_tab).pack(fill="x")

        self.refresh_manage_list()

    def refresh_manage_list(self):
        if not hasattr(self, "tabs_listbox"):
            return
        self.tabs_listbox.delete(0, "end")
        for name in self.get_tab_names():
            self.tabs_listbox.insert("end", name)

    def get_tab_names(self):
        # data 기준(저장 기준)으로 정렬: 기본 먼저, 나머지 알파벳/가나다 순
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

    # -------------------------
    # 저장/로드
    # -------------------------
    def load_data(self):
        if not os.path.exists(SAVE_FILE):
            return {"tabs": {DEFAULT_TAB: []}}
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"tabs": {DEFAULT_TAB: []}}

    def save_data(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = MemoJangApp(root)
    root.mainloop()