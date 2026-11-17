"""MadePharmEasy - Pharmacy Management System - Python + Tkinter + MySQL."""
import csv
import hashlib
import os
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

import mysql.connector

# ---------- Database ----------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "pharmacy_db"),
}

COLUMNS = ("ref_no", "name", "company", "type", "batch_no",
           "mfg_date", "exp_date", "price", "quantity", "notes")
MED_TYPES = ["Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Drops"]
LOW_STOCK = 10


def init_db():
    """First run: if the database doesn't exist yet, create it from schema.sql."""
    server = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**server)
    try:
        cur = conn.cursor()
        cur.execute("SHOW DATABASES LIKE %s", (DB_CONFIG["database"],))
        if cur.fetchone():
            return  # already set up, keep existing data
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"), encoding="utf-8") as f:
            for statement in f.read().split(";"):
                if statement.strip():
                    cur.execute(statement)
        conn.commit()
    finally:
        conn.close()


def run(sql, params=(), fetch=False):
    """Execute one query. Returns rows when fetch=True."""
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
    finally:
        conn.close()


# ---------- Styling ----------
GREEN, LIGHT, BG = "#2e7d32", "#a5d6a7", "#e8f5e9"


def setup_styles(root):
    s = ttk.Style(root)
    s.theme_use("clam")  # clam lets us colour buttons on every OS
    s.configure("TFrame", background=BG)
    s.configure("TLabel", background=BG, font=("Arial", 11))
    s.configure("Header.TLabel", background=GREEN, foreground="white", font=("Arial", 20, "bold"))
    s.configure("Stat.TLabel", background=LIGHT, font=("Arial", 12, "bold"), padding=8)
    s.configure("TLabelframe", background=BG)
    s.configure("TLabelframe.Label", background=BG, font=("Arial", 12, "bold"), foreground=GREEN)
    s.configure("TRadiobutton", background=BG)
    s.configure("TCheckbutton", background=BG)
    s.configure("Treeview.Heading", font=("Arial", 10, "bold"), background=LIGHT)
    s.configure("Treeview", rowheight=24)
    for name, color in [("Green", "#43a047"), ("Orange", "#fb8c00"),
                        ("Red", "#e53935"), ("Blue", "#1e88e5"), ("Grey", "#757575")]:
        s.configure(f"{name}.TButton", background=color, foreground="white",
                    font=("Arial", 11, "bold"), padding=6)
        s.map(f"{name}.TButton", background=[("active", color)])


# ---------- Login screen ----------
class LoginFrame(ttk.Frame):
    def __init__(self, root, on_success):
        super().__init__(root, padding=30)
        self.on_success = on_success
        ttk.Label(self, text="💊 MadePharmEasy Login", style="Header.TLabel",
                  anchor="center").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20), ipady=8)

        ttk.Label(self, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        self.user = ttk.Entry(self, width=25)
        self.user.grid(row=1, column=1, pady=5)

        ttk.Label(self, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        self.pwd = ttk.Entry(self, width=25, show="*")
        self.pwd.grid(row=2, column=1, pady=5)

        self.show = tk.BooleanVar()
        ttk.Checkbutton(self, text="Show password", variable=self.show,
                        command=lambda: self.pwd.config(show="" if self.show.get() else "*")
                        ).grid(row=3, column=1, sticky="w")

        ttk.Button(self, text="Login", style="Green.TButton", command=self.login
                   ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=15)
        ttk.Label(self, text="Default: admin / admin123", foreground="grey").grid(row=5, column=0, columnspan=2)

        self.user.focus()
        root.bind("<Return>", lambda e: self.login())

    def login(self):
        hashed = hashlib.sha256(self.pwd.get().encode()).hexdigest()
        try:
            rows = run("SELECT id FROM users WHERE username=%s AND password=%s",
                       (self.user.get(), hashed), fetch=True)
        except mysql.connector.Error as e:
            return messagebox.showerror("Database Error", str(e))
        if rows:
            self.master.unbind("<Return>")
            self.on_success(self.user.get())
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")


# ---------- Main application ----------
class PharmacyApp(ttk.Frame):
    def __init__(self, root, username, on_logout):
        super().__init__(root)
        self.on_logout = on_logout
        self.vars = {c: tk.StringVar() for c in COLUMNS if c != "notes"}
        self.build_menu(root)
        self.build_header(username)
        self.build_form()
        self.build_table()
        self.status = ttk.Label(self, text="Ready", relief="sunken", anchor="w")
        self.status.pack(side="bottom", fill="x")
        self.refresh()

    # --- UI builders ---
    def build_menu(self, root):
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Refresh", command=self.refresh)
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Logout", command=self.on_logout)
        file_menu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", "MadePharmEasy\nPharmacy Management System\nPython | Tkinter | MySQL"))
        menubar.add_cascade(label="Help", menu=help_menu)
        root.config(menu=menubar)

    def build_header(self, username):
        ttk.Label(self, text="💊 MadePharmEasy", style="Header.TLabel",
                  anchor="center").pack(fill="x", ipady=10)
        stats = ttk.Frame(self, padding=(10, 8))
        stats.pack(fill="x")
        self.stat_total = ttk.Label(stats, style="Stat.TLabel")
        self.stat_low = ttk.Label(stats, style="Stat.TLabel", foreground="#e65100")
        self.stat_exp = ttk.Label(stats, style="Stat.TLabel", foreground="#c62828")
        for lbl in (self.stat_total, self.stat_low, self.stat_exp):
            lbl.pack(side="left", padx=5)
        ttk.Label(stats, text=f"👤 {username}").pack(side="right")

    def build_form(self):
        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)
        self.body = body

        form = ttk.LabelFrame(body, text="➕ Medicine Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))

        fields = [("Ref No", "ref_no"), ("Name", "name"), ("Company", "company"),
                  ("Type", "type"), ("Batch No", "batch_no"),
                  ("Mfg Date", "mfg_date"), ("Exp Date", "exp_date"),
                  ("Price (₹)", "price"), ("Quantity", "quantity")]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=4)
            if key == "type":
                w = ttk.Combobox(form, textvariable=self.vars[key], values=MED_TYPES, state="readonly")
            elif key == "quantity":
                w = ttk.Spinbox(form, textvariable=self.vars[key], from_=0, to=10000)
            else:
                w = ttk.Entry(form, textvariable=self.vars[key])
            w.grid(row=i, column=1, pady=4, sticky="ew")
        ttk.Label(form, text="(dates: YYYY-MM-DD)", foreground="grey").grid(row=len(fields), column=1, sticky="w")

        ttk.Label(form, text="Notes").grid(row=10, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(form, width=22, height=4, font=("Arial", 11),
                             bg="white", fg="black", insertbackground="black")
        self.notes.grid(row=10, column=1, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=11, column=0, columnspan=2, pady=10, sticky="ew")
        for i, (text, style, cmd) in enumerate([
                ("Add", "Green", self.add), ("Update", "Orange", self.update),
                ("Delete", "Red", self.delete), ("Clear", "Grey", self.clear)]):
            ttk.Button(btns, text=text, style=f"{style}.TButton", command=cmd
                       ).grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
        btns.columnconfigure((0, 1), weight=1)

    def build_table(self):
        right = ttk.Frame(self.body)
        right.pack(side="left", fill="both", expand=True)

        # Search bar
        search = ttk.LabelFrame(right, text="🔍 Search", padding=8)
        search.pack(fill="x")
        self.search_by = tk.StringVar(value="name")
        ttk.Radiobutton(search, text="Name", variable=self.search_by, value="name").pack(side="left")
        ttk.Radiobutton(search, text="Ref No", variable=self.search_by, value="ref_no").pack(side="left", padx=8)
        self.search_text = tk.StringVar()
        ttk.Entry(search, textvariable=self.search_text, width=25).pack(side="left", padx=5)
        ttk.Button(search, text="Search", style="Blue.TButton", command=self.search).pack(side="left", padx=3)
        ttk.Button(search, text="Show All", style="Grey.TButton", command=self.refresh).pack(side="left", padx=3)

        # Table with scrollbars
        table_frame = ttk.Frame(right)
        table_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings")
        widths = [60, 150, 110, 80, 80, 90, 90, 70, 70, 160]
        for col, w in zip(COLUMNS, widths):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=w, anchor="center")
        ys = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("low", background="#ffe0b2")
        self.tree.tag_configure("expired", background="#ffcdd2")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        ttk.Label(right, text="🟧 Low stock (< 10)    🟥 Expired", foreground="grey").pack(anchor="w", pady=4)

    # --- Helpers ---
    def form_values(self):
        values = [self.vars[c].get().strip() for c in COLUMNS[:-1]]
        values.append(self.notes.get("1.0", "end").strip())
        return [v or None for v in values]

    def load_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        today = date.today()
        for r in rows:
            tag = "expired" if r[6] and r[6] < today else "low" if r[8] < LOW_STOCK else ""
            self.tree.insert("", "end", values=[("" if v is None else v) for v in r], tags=(tag,))
        self.status.config(text=f"{len(rows)} record(s) shown")

    def update_stats(self):
        total, low, expired = run(
            "SELECT COUNT(*), SUM(quantity < %s), SUM(exp_date < CURDATE()) FROM medicines",
            (LOW_STOCK,), fetch=True)[0]
        self.stat_total.config(text=f"📦 Total Medicines: {total}")
        self.stat_low.config(text=f"⚠️ Low Stock: {low or 0}")
        self.stat_exp.config(text=f"⛔ Expired: {expired or 0}")

    def safe(self, action, success_msg=None):
        """Run a DB action, show errors nicely, then refresh."""
        try:
            action()
            if success_msg:
                messagebox.showinfo("Success", success_msg)
            self.refresh()
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    # --- CRUD ---
    def add(self):
        v = self.form_values()
        if not v[0] or not v[1]:
            return messagebox.showwarning("Missing", "Ref No and Name are required")
        self.safe(lambda: run(f"INSERT INTO medicines VALUES ({', '.join(['%s'] * 10)})", v),
                  "Medicine added")
        self.clear()

    def update(self):
        v = self.form_values()
        if not v[0]:
            return messagebox.showwarning("Select", "Select a medicine to update")
        sets = ", ".join(f"{c}=%s" for c in COLUMNS[1:])
        self.safe(lambda: run(f"UPDATE medicines SET {sets} WHERE ref_no=%s", v[1:] + [v[0]]),
                  "Medicine updated")

    def delete(self):
        ref = self.vars["ref_no"].get()
        if not ref:
            return messagebox.showwarning("Select", "Select a medicine to delete")
        if messagebox.askyesno("Confirm", f"Delete medicine {ref}?"):
            self.safe(lambda: run("DELETE FROM medicines WHERE ref_no=%s", (ref,)), "Medicine deleted")
            self.clear()

    def search(self):
        col = self.search_by.get()  # only "name" or "ref_no" from the radio buttons
        try:
            self.load_rows(run(f"SELECT * FROM medicines WHERE {col} LIKE %s",
                               (f"%{self.search_text.get()}%",), fetch=True))
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    def refresh(self):
        try:
            self.load_rows(run("SELECT * FROM medicines ORDER BY ref_no", fetch=True))
            self.update_stats()
        except mysql.connector.Error as e:
            messagebox.showerror("Database Error", str(e))

    def clear(self):
        for var in self.vars.values():
            var.set("")
        self.notes.delete("1.0", "end")
        self.tree.selection_remove(self.tree.selection())

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        for col, val in zip(COLUMNS, values):
            if col == "notes":
                self.notes.delete("1.0", "end")
                self.notes.insert("1.0", val)
            else:
                self.vars[col].set(val)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(COLUMNS)
                for item in self.tree.get_children():
                    w.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Exported", f"Saved to {path}")


# ---------- Entry point ----------
def main():
    root = tk.Tk()
    root.title("MadePharmEasy - Pharmacy Management System")
    root.configure(bg=BG)
    setup_styles(root)
    try:
        init_db()
    except mysql.connector.Error as e:
        messagebox.showerror("Database Error", f"Is MySQL running?\n\n{e}")
        return root.destroy()

    def show_login():
        for w in root.winfo_children():
            w.destroy()
        root.config(menu="")
        root.geometry("400x330")
        LoginFrame(root, show_app).pack(expand=True)

    def show_app(username):
        for w in root.winfo_children():
            w.destroy()
        root.geometry("1250x680")
        PharmacyApp(root, username, show_login).pack(fill="both", expand=True)

    show_login()
    root.mainloop()


if __name__ == "__main__":
    main()
