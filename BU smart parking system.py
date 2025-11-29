import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime, timedelta
import re
import math

# --- Configuration & Assets ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Color Palette (Bennett University Theme)
COLORS = {
    "brand": "#001233",       # Deepest Blue
    "brand_light": "#002147", # Bennett Blue
    "gold": "#FFD700",        # Accent
    "white": "#FFFFFF",
    "red": "#FF3B30",         # Alerts/Fine
    "green": "#34C759",       # Success
    "orange": "#FF9500",      # Warning
    "card_bg": "#1C1C1E"
}

# Pricing Logic
FINE_THRESHOLD_MINUTES = 45
FINE_AMOUNT = 500.0
PRICING = {"Student": 20.0, "Faculty": 0.0, "Guest": 50.0, "Bike": 10.0}

# --- Database Manager ---
class Database:
    DB_NAME = "bennett_smart_parking.db"

    @staticmethod
    def get_connection():
        return sqlite3.connect(Database.DB_NAME)

    @staticmethod
    def initialize():
        with Database.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users Table (Added Email)
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE, password TEXT, full_name TEXT, 
                email TEXT, phone TEXT, role TEXT, is_member INTEGER DEFAULT 0)""")
            
            # Slots Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS parking_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT, block TEXT, 
                slot_number INTEGER, type TEXT, status TEXT DEFAULT 'available', 
                UNIQUE(block, slot_number))""")
            
            # Reservations Table (Added Payment Info)
            cursor.execute("""CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, slot_id INTEGER, 
                vehicle_number TEXT, start_time TIMESTAMP, duration REAL, 
                fare REAL, fine_amount REAL DEFAULT 0, 
                payment_method TEXT, payment_status TEXT DEFAULT 'Unpaid',
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (slot_id) REFERENCES parking_slots (id))""")

            # Initialize Slots (30 Cars, 50 Bikes)
            cursor.execute("SELECT count(*) FROM parking_slots")
            if cursor.fetchone()[0] == 0:
                # Cars: A (1-15), B (1-15)
                for i in range(1, 16): cursor.execute("INSERT INTO parking_slots (block, slot_number, type) VALUES (?, ?, 'Car')", ('A', i))
                for i in range(1, 16): cursor.execute("INSERT INTO parking_slots (block, slot_number, type) VALUES (?, ?, 'Car')", ('B', i))
                # Bikes: C (1-25), D (1-25)
                for i in range(1, 26): cursor.execute("INSERT INTO parking_slots (block, slot_number, type) VALUES (?, ?, 'Bike')", ('C', i))
                for i in range(1, 26): cursor.execute("INSERT INTO parking_slots (block, slot_number, type) VALUES (?, ?, 'Bike')", ('D', i))
            conn.commit()

# =========================================
# --- SPLASH SCREEN (Animation) ---
# =========================================
class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        w, h = 700, 400
        x = (self.winfo_screenwidth()/2) - (w/2)
        y = (self.winfo_screenheight()/2) - (h/2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        self.configure(fg_color=COLORS["brand"])

        self.title_lbl = ctk.CTkLabel(self, text="BENNETT UNIVERSITY", font=("Montserrat", 36, "bold"), text_color="white")
        self.sub_lbl = ctk.CTkLabel(self, text="SMART CAMPUS AUTHORITY", font=("Roboto", 14), text_color=COLORS["gold"])
        
        self.canvas = tk.Canvas(self, width=700, height=150, bg=COLORS["brand"], highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.6, anchor="center")
        self.car_parts = []
        self.after(500, self.animate_intro)

    def draw_car(self, x, y):
        w1 = self.canvas.create_oval(x+25, y+40, x+55, y+70, fill="#111")
        w2 = self.canvas.create_oval(x+145, y+40, x+175, y+70, fill="#111")
        body = self.canvas.create_polygon([x, y+40, x+200, y+40, x+210, y+25, x+205, y+10, x+180, y+10, x+140, y-20, x+60, y-20, x+10, y+15], fill="#007AFF", outline="#0056b3")
        return [w1, w2, body]

    def animate_intro(self):
        self.title_lbl.place(relx=0.5, rely=0.3, anchor="center")
        self.car_parts = self.draw_car(-250, 70)
        self.animate_move()

    def animate_move(self):
        coords = self.canvas.coords(self.car_parts[2])
        if coords[0] < 250:
            for part in self.car_parts: self.canvas.move(part, 12, 0)
            self.after(20, self.animate_move)
        else:
            self.sub_lbl.place(relx=0.5, rely=0.8, anchor="center")
            self.after(2000, lambda: [self.destroy(), AuthWindow().mainloop()])

# =========================================
# --- AUTHENTICATION ---
# =========================================
class AuthWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bennett Portal - Login")
        self.geometry("900x650")
        self.resizable(False, False)
        self.eval('tk::PlaceWindow . center')
        
        left = ctk.CTkFrame(self, width=400, corner_radius=0, fg_color=COLORS["brand_light"])
        left.pack(side="left", fill="both")
        ctk.CTkLabel(left, text="BENNETT\nUNIVERSITY", font=("Montserrat", 36, "bold"), text_color="white").place(relx=0.5, rely=0.4, anchor="center")
        
        self.right = ctk.CTkFrame(self, fg_color="transparent")
        self.right.pack(side="right", fill="both", expand=True, padx=40, pady=40)
        self.show_login()

    def clear(self):
        for w in self.right.winfo_children(): w.destroy()

    def show_login(self):
        self.clear()
        ctk.CTkLabel(self.right, text="Secure Login", font=("Roboto", 32, "bold")).pack(pady=30)
        self.u_ent = ctk.CTkEntry(self.right, placeholder_text="Username", width=300, height=45)
        self.u_ent.pack(pady=10)
        self.p_ent = ctk.CTkEntry(self.right, placeholder_text="Password", show="•", width=300, height=45)
        self.p_ent.pack(pady=10)
        ctk.CTkButton(self.right, text="LOGIN", command=self.do_login, width=300, height=45, fg_color=COLORS["brand_light"]).pack(pady=20)
        ctk.CTkButton(self.right, text="Create Account", fg_color="transparent", text_color="gray", command=self.show_reg).pack()

    def show_reg(self):
        self.clear()
        ctk.CTkLabel(self.right, text="New Registration", font=("Roboto", 32, "bold")).pack(pady=20)
        self.entries = {}
        for f in ["Username", "Password", "Full Name", "Email", "Phone"]:
            e = ctk.CTkEntry(self.right, placeholder_text=f, width=300, height=40, show="•" if f=="Password" else "")
            e.pack(pady=5)
            self.entries[f] = e
        
        self.role_var = ctk.StringVar(value="Student")
        ctk.CTkSegmentedButton(self.right, values=["Student", "Faculty", "Staff"], variable=self.role_var).pack(pady=10)
        ctk.CTkLabel(self.right, text="*Staff Registration requires @bennett.edu.in email", font=("Arial", 10), text_color="orange").pack()
        
        ctk.CTkButton(self.right, text="REGISTER", command=self.do_reg, width=300, height=45, fg_color=COLORS["gold"], text_color="black").pack(pady=10)
        ctk.CTkButton(self.right, text="Back", fg_color="transparent", text_color="gray", command=self.show_login).pack()

    def do_login(self):
        u, p = self.u_ent.get(), self.p_ent.get()
        with Database.get_connection() as conn:
            user = conn.execute("SELECT id, username, role, full_name, is_member FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            if user:
                self.destroy()
                Dashboard(user).mainloop()
            else: messagebox.showerror("Error", "Invalid Credentials")

    def do_reg(self):
        d = {k: v.get() for k, v in self.entries.items()}
        role = self.role_var.get()
        if not all(d.values()): return messagebox.showerror("Error", "All fields required")
        
        # Staff Validation Logic
        if role == "Staff":
            if not re.search(r"@bennett\.edu\.in$", d["Email"]):
                return messagebox.showerror("Security Alert", "Staff Authority denied.\nEmail must end with @bennett.edu.in")

        try:
            with Database.get_connection() as conn:
                conn.execute("INSERT INTO users (username, password, full_name, email, phone, role) VALUES (?, ?, ?, ?, ?, ?)", 
                             (d["Username"], d["Password"], d["Full Name"], d["Email"], d["Phone"], role))
                conn.commit()
            messagebox.showinfo("Success", "Account created!")
            self.show_login()
        except sqlite3.IntegrityError: messagebox.showerror("Error", "Username or Email already exists")

# =========================================
# --- MAIN DASHBOARD ---
# =========================================
class Dashboard(ctk.CTk):
    def __init__(self, user_data):
        super().__init__()
        self.uid, self.uname, self.role, self.fname, self.ismem = user_data
        self.title("Bennett Parking System")
        self.geometry("1200x800")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        side = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLORS["brand_light"])
        side.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(side, text=f"{self.fname.split()[0]}", font=("Roboto", 24, "bold")).pack(pady=(40, 5))
        ctk.CTkLabel(side, text=self.role.upper(), font=("Roboto", 12), text_color=COLORS["gold"]).pack(pady=(0, 30))

        # --- DYNAMIC MENU BASED ON ROLE ---
        if self.role == "Staff":
            # Staff sees ONLY management tools
            self.create_btn(side, "👮  Patrol / Fines", self.show_admin_patrol, color=COLORS["brand"])
            self.create_btn(side, "🚧  Gate Control", self.show_admin_gate, color=COLORS["brand"])
            self.default_view = self.show_admin_patrol
        else:
            # Students/Faculty see Booking tools
            self.create_btn(side, "🚘  Car Parking", lambda: self.show_booking("Car"))
            self.create_btn(side, "🛵  Bike Parking", lambda: self.show_booking("Bike"))
            self.create_btn(side, "📄  My Bookings", self.show_history)
            self.create_btn(side, "⭐  Membership", self.show_membership)
            self.default_view = lambda: self.show_booking("Car")

        ctk.CTkButton(side, text="Logout", fg_color=COLORS["red"], command=self.logout).pack(side="bottom", fill="x", padx=20, pady=30)

        self.main = ctk.CTkFrame(self, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.default_view()

    def create_btn(self, parent, text, cmd, color="transparent"):
        ctk.CTkButton(parent, text=text, height=50, fg_color=color, anchor="w", font=("Roboto", 14), command=cmd).pack(fill="x", padx=10, pady=5)

    def logout(self):
        self.destroy()
        AuthWindow().mainloop()

    def clear(self):
        for w in self.main.winfo_children(): w.destroy()

    # ==========================
    # STUDENT/FACULTY VIEWS
    # ==========================
    def show_booking(self, v_type):
        self.clear()
        self.selected_slot = None
        self.curr_v_type = v_type
        
        ctk.CTkLabel(self.main, text=f"{v_type} Parking Zone", font=("Montserrat", 26, "bold")).pack(pady=10, anchor="w")
        
        # Legend
        leg = ctk.CTkFrame(self.main, fg_color="transparent")
        leg.pack(pady=5, anchor="w")
        for c, t in [(COLORS["green"], "Available"), (COLORS["red"], "Occupied"), (COLORS["gold"], "Your Slot")]:
            ctk.CTkLabel(leg, text="●", text_color=c, font=("Arial", 20)).pack(side="left")
            ctk.CTkLabel(leg, text=t, font=("Roboto", 12)).pack(side="left", padx=(2, 15))

        grid = ctk.CTkScrollableFrame(self.main, height=450)
        grid.pack(fill="x", expand=True, pady=10)
        
        blocks = ['A', 'B'] if v_type == 'Car' else ['C', 'D']
        for block in blocks:
            bf = ctk.CTkFrame(grid)
            bf.pack(fill="x", pady=5)
            ctk.CTkLabel(bf, text=f"Block {block}", font=("Roboto", 16, "bold")).pack(anchor="w", padx=10)
            row_f = ctk.CTkFrame(bf, fg_color="transparent")
            row_f.pack(fill="x")
            
            with Database.get_connection() as conn:
                slots = conn.execute("""SELECT ps.id, ps.slot_number, ps.status, r.user_id 
                                        FROM parking_slots ps LEFT JOIN reservations r ON ps.id=r.slot_id AND r.status='active'
                                        WHERE ps.block=?""", (block,)).fetchall()
            
            for sid, num, status, uid in slots:
                color, state = COLORS["green"], "normal"
                if status == "occupied":
                    state = "disabled"
                    color = COLORS["red"]
                    if uid == self.uid: color, state = COLORS["gold"], "normal"
                
                ctk.CTkButton(row_f, text=str(num), width=50, height=40, fg_color=color, state=state,
                              command=lambda s=sid, b=block, n=num: self.select(s, b, n)).pack(side="left", padx=5, pady=5)

        # Booking Action
        form = ctk.CTkFrame(self.main, fg_color=COLORS["card_bg"])
        form.pack(fill="x", pady=10)
        self.lbl_sel = ctk.CTkLabel(form, text="Select a slot", font=("Roboto", 14, "bold"))
        self.lbl_sel.pack(pady=5)
        
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(pady=10)
        self.ent_veh = ctk.CTkEntry(row, placeholder_text="Vehicle Number", width=180)
        self.ent_veh.pack(side="left", padx=10)
        self.ent_dur = ctk.CTkEntry(row, placeholder_text="Hours", width=80)
        self.ent_dur.insert(0, "1")
        self.ent_dur.pack(side="left", padx=10)
        
        rate = PRICING["Bike"] if v_type == "Bike" else PRICING.get(self.role, 20)
        if self.ismem: rate *= 0.5
        
        ctk.CTkButton(row, text=f"Book Now (@ ₹{rate}/hr)", fg_color=COLORS["green"], command=lambda: self.book(rate)).pack(side="left", padx=10)

    def select(self, s, b, n):
        self.selected_slot = s
        self.lbl_sel.configure(text=f"Selected: {b}-{n}", text_color=COLORS["green"])

    def book(self, rate):
        if not self.selected_slot or not self.ent_veh.get(): return messagebox.showwarning("!", "Fill details")
        try:
            hrs = float(self.ent_dur.get())
            fare = hrs * rate
            if messagebox.askyesno("Confirm", f"Estimated Fare: ₹{fare}\nProceed?"):
                with Database.get_connection() as conn:
                    conn.execute("UPDATE parking_slots SET status='occupied' WHERE id=?", (self.selected_slot,))
                    conn.execute("INSERT INTO reservations (user_id, slot_id, vehicle_number, start_time, duration, fare) VALUES (?, ?, ?, datetime('now', 'localtime'), ?, ?)", 
                                 (self.uid, self.selected_slot, self.ent_veh.get(), hrs, fare))
                    conn.commit()
                self.show_booking(self.curr_v_type)
        except: messagebox.showerror("Error", "Invalid Duration")

    def show_history(self):
        self.clear()
        ctk.CTkLabel(self.main, text="My Parking Activity", font=("Montserrat", 26, "bold")).pack(pady=10, anchor="w")
        scroll = ctk.CTkScrollableFrame(self.main)
        scroll.pack(fill="both", expand=True)

        with Database.get_connection() as conn:
            rows = conn.execute("""
                SELECT r.id, r.vehicle_number, ps.block, ps.slot_number, r.start_time, r.duration, r.fare, r.status, r.payment_status
                FROM reservations r JOIN parking_slots ps ON r.slot_id = ps.id
                WHERE r.user_id=? ORDER BY r.start_time DESC""", (self.uid,)).fetchall()

        for rid, veh, b, s, start, dur, fare, status, pay_stat in rows:
            f = ctk.CTkFrame(scroll, fg_color=COLORS["card_bg"])
            f.pack(fill="x", pady=5, padx=5)
            
            end_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=dur)
            is_late = datetime.now() > end_dt + timedelta(minutes=FINE_THRESHOLD_MINUTES)
            fine_txt = f" + ₹{FINE_AMOUNT} FINE" if is_late and status=='active' else ""
            
            info = f"{veh} | {b}-{s} | Ends: {end_dt.strftime('%H:%M')} | ₹{fare:.0f}{fine_txt}"
            ctk.CTkLabel(f, text=info, font=("Roboto", 14)).pack(side="left", padx=15, pady=15)
            
            if status == 'active':
                if pay_stat == "Cash_Pending":
                    ctk.CTkLabel(f, text="WAITING FOR STAFF AT GATE", text_color="orange", font=("bold", 12)).pack(side="right", padx=15)
                else:
                    ctk.CTkButton(f, text="EXIT / PAY", fg_color=COLORS["red"], width=100, 
                                  command=lambda r=rid, s=s: self.initiate_checkout(r)).pack(side="right", padx=10)
            else:
                ctk.CTkLabel(f, text="COMPLETED", text_color="gray").pack(side="right", padx=15)

    def initiate_checkout(self, rid):
        # Calculate Final Bill
        with Database.get_connection() as conn:
            res = conn.execute("SELECT start_time, duration, fare FROM reservations WHERE id=?", (rid,)).fetchone()
        
        end_dt = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=res[1])
        is_late = datetime.now() > end_dt + timedelta(minutes=FINE_THRESHOLD_MINUTES)
        
        total = res[2]
        if is_late: total += FINE_AMOUNT
        
        # Payment Modal
        top = ctk.CTkToplevel(self)
        top.title("Payment Gateway")
        top.geometry("400x300")
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text=f"Total Amount: ₹{total}", font=("Montserrat", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(top, text="Select Payment Method:", font=("Roboto", 14)).pack(pady=10)
        
        # UPI Logic
        def pay_upi():
            with Database.get_connection() as conn:
                conn.execute("UPDATE reservations SET status='completed', payment_method='UPI', payment_status='Paid', fare=?, fine_amount=? WHERE id=?", 
                             (total, FINE_AMOUNT if is_late else 0, rid))
                # Free the slot
                slot_id = conn.execute("SELECT slot_id FROM reservations WHERE id=?", (rid,)).fetchone()[0]
                conn.execute("UPDATE parking_slots SET status='available' WHERE id=?", (slot_id,))
                conn.commit()
            messagebox.showinfo("UPI Success", "Payment Verified. Gate Opening...")
            top.destroy()
            self.show_history()

        # Cash Logic
        def pay_cash():
            with Database.get_connection() as conn:
                conn.execute("UPDATE reservations SET payment_method='Cash', payment_status='Cash_Pending', fare=?, fine_amount=? WHERE id=?", 
                             (total, FINE_AMOUNT if is_late else 0, rid))
                conn.commit()
            messagebox.showinfo("Cash Request", "Please drive to the Exit Gate.\nStaff will collect cash and open the barrier.")
            top.destroy()
            self.show_history()

        ctk.CTkButton(top, text="📱 UPI / QR Code", fg_color=COLORS["brand"], command=pay_upi).pack(pady=10, fill="x", padx=40)
        ctk.CTkButton(top, text="💵 Cash at Gate", fg_color=COLORS["green"], command=pay_cash).pack(pady=10, fill="x", padx=40)

    def show_membership(self):
        self.clear()
        # (Same logic as previous version, just ensuring it's available for Student/Faculty only)
        ctk.CTkLabel(self.main, text="Membership", font=("Montserrat", 26, "bold")).pack(pady=20)
        card = ctk.CTkFrame(self.main, fg_color=COLORS["brand_light"], border_color=COLORS["gold"], border_width=2)
        card.pack(pady=20, padx=50, fill="x")
        ctk.CTkLabel(card, text="👑 GOLD PLAN", font=("Montserrat", 30, "bold"), text_color=COLORS["gold"]).pack(pady=20)
        ctk.CTkButton(card, text="Buy (₹500)", fg_color=COLORS["gold"], text_color="black", command=self.buy_mem).pack(pady=20)
    
    def buy_mem(self):
        with Database.get_connection() as conn:
            conn.execute("UPDATE users SET is_member=1 WHERE id=?", (self.uid,))
            conn.commit()
        self.ismem = 1
        messagebox.showinfo("Success", "Upgraded to Gold!")

    # ==========================
    # STAFF VIEWS (Admin)
    # ==========================
    def show_admin_patrol(self):
        self.clear()
        ctk.CTkLabel(self.main, text="👮 Staff Patrol Dashboard", font=("Montserrat", 26, "bold"), text_color=COLORS["red"]).pack(pady=10, anchor="w")
        ctk.CTkLabel(self.main, text="Active Vehicles & Contact Details", font=("Roboto", 12)).pack(anchor="w", padx=5)

        scroll = ctk.CTkScrollableFrame(self.main)
        scroll.pack(fill="both", expand=True, pady=10)
        
        head = ctk.CTkFrame(scroll, fg_color="#333")
        head.pack(fill="x")
        for c, w in [("Vehicle", 100), ("Slot", 80), ("Owner", 150), ("PHONE", 120), ("Status", 150)]:
            ctk.CTkLabel(head, text=c, width=w, font=("bold", 12)).pack(side="left", padx=5)

        with Database.get_connection() as conn:
            rows = conn.execute("""
                SELECT r.vehicle_number, ps.block, ps.slot_number, u.full_name, u.phone, r.start_time, r.duration
                FROM reservations r JOIN users u ON r.user_id=u.id JOIN parking_slots ps ON r.slot_id=ps.id
                WHERE r.status='active'""").fetchall()

        if not rows: ctk.CTkLabel(scroll, text="Premises Empty").pack(pady=20)

        for veh, b, s, name, phone, start, dur in rows:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=2)
            
            end_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=dur)
            mins_left = (end_dt - datetime.now()).total_seconds() / 60
            
            stat = f"{int(mins_left)}m left"
            clr = "white"
            if mins_left < 0: stat, clr = f"LATE ({int(abs(mins_left))}m)", "orange"
            if mins_left < -FINE_THRESHOLD_MINUTES: stat, clr = "FINE APPLICABLE", COLORS["red"]

            for d, w, c in [(veh, 100, "white"), (f"{b}-{s}", 80, "white"), (name, 150, "white"), (phone, 120, "white"), (stat, 150, clr)]:
                ctk.CTkLabel(row, text=d, width=w, text_color=c).pack(side="left", padx=5)
            
            ctk.CTkButton(row, text="📞", width=40, fg_color=COLORS["brand_light"], 
                          command=lambda p=phone: messagebox.showinfo("Call", f"Calling {p}...")).pack(side="left")

    def show_admin_gate(self):
        self.clear()
        ctk.CTkLabel(self.main, text="🚧 Gate Control (Cash Payments)", font=("Montserrat", 26, "bold"), text_color=COLORS["orange"]).pack(pady=10, anchor="w")
        
        scroll = ctk.CTkScrollableFrame(self.main)
        scroll.pack(fill="both", expand=True)

        # Poll Database for Cash Pending status
        with Database.get_connection() as conn:
            rows = conn.execute("""
                SELECT r.id, r.vehicle_number, r.fare, r.fine_amount, u.full_name
                FROM reservations r JOIN users u ON r.user_id=u.id
                WHERE r.payment_status='Cash_Pending'""").fetchall()

        if not rows: ctk.CTkLabel(scroll, text="No vehicles waiting at gate.").pack(pady=20)

        for rid, veh, fare, fine, name in rows:
            f = ctk.CTkFrame(scroll, fg_color=COLORS["card_bg"])
            f.pack(fill="x", pady=10)
            
            total = fare + fine
            info = f"GATE WAIT: {veh} ({name})\nCollet: ₹{total} (Inc. Fine: ₹{fine})"
            ctk.CTkLabel(f, text=info, font=("Roboto", 16, "bold"), text_color="white").pack(side="left", padx=20, pady=20)
            
            ctk.CTkButton(f, text="CONFIRM RECEIPT & OPEN GATE", fg_color=COLORS["green"], 
                          command=lambda r=rid: self.staff_collect_cash(r)).pack(side="right", padx=20)

        # Auto-refresh every 5 seconds
        self.after(5000, lambda: self.show_admin_gate() if hasattr(self, 'main') and self.main.winfo_exists() else None)

    def staff_collect_cash(self, rid):
        with Database.get_connection() as conn:
            # Mark Paid
            conn.execute("UPDATE reservations SET status='completed', payment_status='Paid' WHERE id=?", (rid,))
            # Free Slot
            sid = conn.execute("SELECT slot_id FROM reservations WHERE id=?", (rid,)).fetchone()[0]
            conn.execute("UPDATE parking_slots SET status='available' WHERE id=?", (sid,))
            conn.commit()
        messagebox.showinfo("Success", "Payment Recorded. Barrier Opened.")
        self.show_admin_gate()

if __name__ == "__main__":
    Database.initialize()
    app = SplashScreen()
    app.mainloop()