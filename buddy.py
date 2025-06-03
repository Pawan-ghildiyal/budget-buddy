import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3
import hashlib
from datetime import datetime
from tkcalendar import DateEntry

# ---------- UTILS ----------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    conn = sqlite3.connect('expense_tracker.db')
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

initialize_database()

# ---------- LOGIN WINDOW ----------

def register():
    username = entry_username.get()
    password = entry_password.get()

    if username == "" or password == "":
        messagebox.showerror("Error", "All fields are required!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        messagebox.showinfo("Success", "Registration Successful!")
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists!")
    finally:
        conn.close()

def login():
    global current_user_id, current_user
    username = entry_username.get()
    password = entry_password.get()

    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    result = cursor.fetchone()
    conn.close()

    if result:
        current_user_id = result[0]
        current_user = username
        messagebox.showinfo("Success", f"Welcome {username}!")
        login_window.destroy()
        open_expense_tracker()
    else:
        messagebox.showerror("Error", "Invalid username or password.")

# ---------- EXPENSE TRACKER ----------

current_user_id = None
current_user = ""

def open_expense_tracker():
    tracker = tk.Tk()
    tracker.title(f"{current_user}'s Expense Tracker")
    tracker.geometry("700x600")

    def load_transactions():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, category, description, amount FROM transactions WHERE user_id = ?", (current_user_id,))
        rows = cursor.fetchall()
        conn.close()

        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", tk.END, iid=row[0], values=row[1:])

        update_total_label()

    def add_transaction():
        add_win = tk.Toplevel(tracker)
        add_win.title("Add Transaction")
        add_win.geometry("300x300")

        tk.Label(add_win, text="Date:").pack(pady=5)
        cal = DateEntry(
            add_win,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            showothermonthdays=True,
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            date_pattern='yyyy-mm-dd'
        )
        cal.pack(pady=5)

        tk.Label(add_win, text="Category:").pack(pady=5)
        category_options = ["Dairy", "Household", "Grocery", "Transport", "Other"]
        combo_category = ttk.Combobox(add_win, values=category_options, state="readonly")
        combo_category.current(0)  # default to first category
        combo_category.pack(pady=5)

        tk.Label(add_win, text="Description:").pack(pady=5)
        entry_description = tk.Entry(add_win)
        entry_description.pack(pady=5)

        tk.Label(add_win, text="Amount:").pack(pady=5)
        entry_amount = tk.Entry(add_win)
        entry_amount.pack(pady=5)

        def submit():
            date = cal.get_date().strftime('%Y-%m-%d')
            category = combo_category.get()
            description = entry_description.get()
            amount_str = entry_amount.get()

            if not category or not description or not amount_str:
                messagebox.showerror("Error", "All fields are required.", parent=add_win)
                return

            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Error", "Amount must be a number.", parent=add_win)
                return

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transactions (user_id, date, category, description, amount) VALUES (?, ?, ?, ?, ?)",
                (current_user_id, date, category, description, amount)
            )
            conn.commit()
            conn.close()
            add_win.destroy()
            load_transactions()

        tk.Button(add_win, text="Add", command=submit).pack(pady=10)

    def delete_transaction():
        selected = tree.selection()
        if not selected:
            messagebox.showerror("Error", "No transaction selected.")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        for sel in selected:
            cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (sel, current_user_id))
        conn.commit()
        conn.close()
        load_transactions()

    def sort_transactions(criteria):
        order_by = {
            "date": "date",
            "amount": "amount",
            "category": "category"
        }.get(criteria, "date")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, date, category, description, amount FROM transactions WHERE user_id = ? ORDER BY {order_by}", (current_user_id,))
        rows = cursor.fetchall()
        conn.close()

        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", tk.END, iid=row[0], values=row[1:])
        update_total_label()

    def sort_and_update():
        sort_transactions(sort_criteria_var.get())

    def update_total_label():
        total = 0.0
        for child in tree.get_children():
            total += float(tree.item(child)["values"][3])  # amount is at index 3
        total_label.config(text=f"Total: {total:.2f}")

    # ---------- UI ----------

    frame = tk.Frame(tracker)
    frame.pack(pady=10)

    tk.Button(frame, text="Add Transaction", command=add_transaction).grid(row=0, column=0, padx=5)
    tk.Button(frame, text="Delete Selected", command=delete_transaction).grid(row=0, column=1, padx=5)

    tk.Label(frame, text="Sort by:").grid(row=0, column=2, padx=5)
    sort_criteria_var = tk.StringVar(value="date")
    tk.Radiobutton(frame, text="Date", variable=sort_criteria_var, value="date", command=sort_and_update).grid(row=0, column=3)
    tk.Radiobutton(frame, text="Amount", variable=sort_criteria_var, value="amount", command=sort_and_update).grid(row=0, column=4)
    tk.Radiobutton(frame, text="Category", variable=sort_criteria_var, value="category", command=sort_and_update).grid(row=0, column=5)

    columns = ("Date", "Category", "Description", "Amount")
    tree = ttk.Treeview(tracker, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=150)
    tree.pack(pady=20)

    total_label = tk.Label(tracker, text="Total: 0.00", font=("Arial", 12, "bold"))
    total_label.pack(pady=10)

    load_transactions()
    tracker.mainloop()

# ---------- MAIN LOGIN WINDOW ----------

login_window = tk.Tk()
login_window.title("Login Page")
login_window.geometry("300x250")

tk.Label(login_window, text="Username").pack(pady=5)
entry_username = tk.Entry(login_window)
entry_username.pack(pady=5)

tk.Label(login_window, text="Password").pack(pady=5)
entry_password = tk.Entry(login_window, show="*")
entry_password.pack(pady=5)

tk.Button(login_window, text="Login", command=login).pack(pady=10)
tk.Button(login_window, text="Register", command=register).pack(pady=5)

login_window.mainloop()
