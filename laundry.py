import mysql.connector
from mysql.connector import errorcode
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import os


try:
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


DB_NAME = "database_laundry"
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",   
    "database": DB_NAME
}


DEFAULT_ADMIN = (
    "admin", 
    "admin123", 
    "Administrator Sistem"
)

DEFAULT_LAYANAN = [
    ("Cuci Kering", 4000),
    ("Setrika Saja", 3000),
    ("Cuci + Setrika", 6000)
]


def koneksi(with_db=True):
    cfg = DB_CONFIG.copy()
    if not with_db:
        cfg.pop("database", None)
    return mysql.connector.connect(**cfg)

def init_database_and_tables():
    
    try:
        cnx = koneksi(with_db=False)
        cur = cnx.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
        cnx.commit()
        cur.close()
        cnx.close()
    except Exception as e:
        messagebox.showerror("DB Init Error", f"Gagal membuat/akses database: {e}")
        raise

    
    try:
        db = koneksi(with_db=True)
        cur = db.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id_admin INT(11) AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            nama_lengkap VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan (
            id_pelanggan INT(11) AUTO_INCREMENT PRIMARY KEY,
            nama VARCHAR(100),
            no_hp VARCHAR(15) UNIQUE,
            alamat VARCHAR(150)
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS layanan (
            id_layanan INT(11) AUTO_INCREMENT PRIMARY KEY,
            nama_layanan VARCHAR(50),
            harga_per_kg INT(11)
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id_transaksi INT(11) AUTO_INCREMENT PRIMARY KEY,
            id_pelanggan INT(11),
            tanggal_masuk DATE,
            tanggal_selesai DATE,
            total_harga INT(11),
            status VARCHAR(20),
            FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan) ON DELETE SET NULL
        ) ENGINE=InnoDB;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS detail_transaksi (
            id_detail INT(11) AUTO_INCREMENT PRIMARY KEY,
            id_transaksi INT(11),
            id_layanan INT(11),
            berat_kg FLOAT(5),
            subtotal INT(11),
            FOREIGN KEY (id_transaksi) REFERENCES transaksi(id_transaksi) ON DELETE CASCADE,
            FOREIGN KEY (id_layanan) REFERENCES layanan(id_layanan) ON DELETE SET NULL
        ) ENGINE=InnoDB;
        """)

        db.commit()

        
        cur.execute("SELECT COUNT(*) FROM admin")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO admin (username, password, nama_lengkap) VALUES (%s,%s,%s)", DEFAULT_ADMIN)
            db.commit()

    
        cur.execute("SELECT COUNT(*) FROM layanan")
        if cur.fetchone()[0] == 0:
            cur.executemany("INSERT INTO layanan (nama_layanan, harga_per_kg) VALUES (%s,%s)", DEFAULT_LAYANAN)
            db.commit()

        cur.close()
        db.close()

    except Exception as e:
        messagebox.showerror("DB Init Error", f"Gagal inisialisasi tabel: {e}")
        raise


def cek_login_db(username, password):
    try:
        db = koneksi()
        cur = db.cursor()
        cur.execute("SELECT id_admin, username, nama_lengkap FROM admin WHERE username=%s AND password=%s", (username, password))
        row = cur.fetchone()
        cur.close()
        db.close()
        return row
    except Exception as e:
        messagebox.showerror("DB Error", f"cek_login_db: {e}")
        return None

def fetch_pelanggan():
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("SELECT id_pelanggan, nama, no_hp, alamat FROM pelanggan ORDER BY id_pelanggan")
        rows = cur.fetchall()
        cur.close(); db.close()
        return rows
    except Exception as e:
        messagebox.showerror("DB Error", f"fetch_pelanggan: {e}"); return []

def insert_pelanggan(nama, no_hp, alamat):
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("INSERT INTO pelanggan (nama, no_hp, alamat) VALUES (%s,%s,%s)", (nama, no_hp, alamat))
        db.commit()
        cur.close(); db.close()
        return True
    except mysql.connector.IntegrityError as ie:
        messagebox.showerror("DB Error", f"Data duplikat/no_hp sudah ada: {ie}")
        return False
    except Exception as e:
        messagebox.showerror("DB Error", f"insert_pelanggan: {e}"); return False

def delete_pelanggan(id_p):
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("DELETE FROM pelanggan WHERE id_pelanggan=%s", (id_p,))
        db.commit()
        cur.close(); db.close()
        return True
    except Exception as e:
        messagebox.showerror("DB Error", f"delete_pelanggan: {e}"); return False

def fetch_layanan():
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("SELECT id_layanan, nama_layanan, harga_per_kg FROM layanan ORDER BY id_layanan")
        rows = cur.fetchall()
        cur.close(); db.close()
        return rows
    except Exception as e:
        messagebox.showerror("DB Error", f"fetch_layanan: {e}"); return []

def insert_layanan(nama, harga):
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("INSERT INTO layanan (nama_layanan, harga_per_kg) VALUES (%s,%s)", (nama, harga))
        db.commit()
        cur.close(); db.close()
        return True
    except Exception as e:
        messagebox.showerror("DB Error", f"insert_layanan: {e}"); return False

def delete_layanan(id_l):
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("DELETE FROM layanan WHERE id_layanan=%s", (id_l,))
        db.commit()
        cur.close(); db.close()
        return True
    except Exception as e:
        messagebox.showerror("DB Error", f"delete_layanan: {e}"); return False

def create_transaksi(id_pelanggan, items, status="Diterima"):

    try:
        db = koneksi(); cur = db.cursor()
        tgl = date.today()
        cur.execute("INSERT INTO transaksi (id_pelanggan, tanggal_masuk, total_harga, status) VALUES (%s,%s,%s,%s)",
                    (id_pelanggan, tgl, 0, status))
        id_trans = cur.lastrowid
        total = 0
        for it in items:
            subtotal = int(it['subtotal'])
            total += subtotal
            cur.execute("INSERT INTO detail_transaksi (id_transaksi, id_layanan, berat_kg, subtotal) VALUES (%s,%s,%s,%s)",
                        (id_trans, it['id_layanan'], it['berat'], subtotal))
        cur.execute("UPDATE transaksi SET total_harga=%s WHERE id_transaksi=%s", (total, id_trans))
        db.commit(); cur.close(); db.close()
        return id_trans
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        messagebox.showerror("DB Error", f"create_transaksi: {e}")
        return None

def get_transaksi_all():
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("""
            SELECT t.id_transaksi, p.nama, t.tanggal_masuk, t.total_harga, t.status
            FROM transaksi t LEFT JOIN pelanggan p ON p.id_pelanggan = t.id_pelanggan
            ORDER BY t.id_transaksi DESC
        """)
        rows = cur.fetchall(); cur.close(); db.close()
        return rows
    except Exception as e:
        messagebox.showerror("DB Error", f"get_transaksi_all: {e}"); return []

def get_detail_by_trans(id_transaksi):
    try:
        db = koneksi(); cur = db.cursor()
        cur.execute("""
            SELECT dt.id_detail, l.nama_layanan, dt.berat_kg, dt.subtotal
            FROM detail_transaksi dt
            LEFT JOIN layanan l ON l.id_layanan = dt.id_layanan
            WHERE dt.id_transaksi=%s
        """, (id_transaksi,))
        rows = cur.fetchall(); cur.close(); db.close()
        return rows
    except Exception as e:
        messagebox.showerror("DB Error", f"get_detail_by_trans: {e}"); return []

def update_status_transaksi(id_transaksi, status):
    try:
        db = koneksi(); cur = db.cursor()
        if status == "Selesai":

            today = date.today()
            cur.execute("UPDATE transaksi SET status=%s, tanggal_selesai=%s WHERE id_transaksi=%s", (status, today, id_transaksi))
        else:
            cur.execute("UPDATE transaksi SET status=%s WHERE id_transaksi=%s", (status, id_transaksi))
        db.commit(); cur.close(); db.close()
        return True
    except Exception as e:
        messagebox.showerror("DB Error", f"update_status_transaksi: {e}"); return False

def map_status_to_category(status):
    if status == "Diterima":
        return "Diterima"
    elif status in ["Dicuci", "Dikeringkan", "Disetrika"]:
        return "Di Proses"
    elif status in ["Selesai", "Diambil"]:
        return "Selesai"
    else:
        return status

def update_status_to_category(id_transaksi, category):
    if category == "Diterima":
        status = "Diterima"
    elif category == "Di Proses":
        status = "Dicuci"
    elif category == "Selesai":
        status = "Selesai"
    else:
        return False
    return update_status_transaksi(id_transaksi, status)


def export_transaksi_to_pdf(id_transaksi, folder=None):
    if not REPORTLAB_AVAILABLE:
        messagebox.showwarning("PDF", "ReportLab tidak terpasang. Install `reportlab` untuk export PDF.")
        return None
    try:
        trans = None
        for r in get_transaksi_all():
            if r[0] == id_transaksi:
                trans = r
                break
        if not trans:
            messagebox.showerror("PDF", "Transaksi tidak ditemukan.")
            return None
        details = get_detail_by_trans(id_transaksi)
        if folder is None:
            folder = os.getcwd()
        filename = os.path.join(folder, f"nota_{id_transaksi}.pdf")
        c = canvas.Canvas(filename, pagesize=A5)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 480, "NOTA LAUNDRY")
        c.setFont("Helvetica", 10)
        c.drawString(30, 460, f"ID: {trans[0]}")
        c.drawString(30, 445, f"Pelanggan: {trans[1]}")
        if isinstance(trans[2], datetime):
            tanggal = trans[2].strftime("%Y-%m-%d")
        else:
            tanggal = str(trans[2])
        c.drawString(30, 430, f"Tanggal: {tanggal}")
        c.drawString(30, 415, f"Status: {trans[4]}")
        c.drawString(30, 400, "-"*40)
        y = 385
        for d in details:
            line = f"{d[1]} - {d[2]} kg"
            c.drawString(30, y, line)
            c.drawString(30, y-30, f"terima kasih sudah order".replace(",", "."))
            y -= 14
        c.drawString(30, y-6, "-"*40)
        c.drawString(30, y-26, f"Total: Rp {int(trans[3]):,}".replace(",", "."))
        c.save()
        return filename
    except Exception as e:
        messagebox.showerror("PDF Error", f"export_transaksi_to_pdf: {e}")
        return None


class LaundryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistem Laundry - Full")
        self.geometry("1000x650")
        self.resizable(False, False)

        
        init_database_and_tables()

        
        self.frame_login = tk.Frame(self)
        self.frame_main = tk.Frame(self, bg="#f5f7fb")
        self.sidebar = tk.Frame(self.frame_main, bg="#375a7f", width=220)
        self.content = tk.Frame(self.frame_main, bg="#ffffff")

        
        self.page_dashboard = tk.Frame(self.content, bg="#ffffff")
        self.page_pelanggan = tk.Frame(self.content, bg="#ffffff")
        self.page_layanan = tk.Frame(self.content, bg="#ffffff")
        self.page_transaksi = tk.Frame(self.content, bg="#ffffff")
        self.page_riwayat = tk.Frame(self.content, bg="#ffffff")

        self.cart_items = []
        self.current_user = None

        self._build_login()
        self._build_main_layout()

        self.frame_login.pack(fill="both", expand=True)

    
    def _build_login(self):
        f = self.frame_login
        f.place(x=0, y=0, relwidth=1, relheight=1)
        box = tk.Frame(f, bg="#ffffff", bd=1, relief="solid")
        box.place(relx=0.5, rely=0.5, anchor="center", width=420, height=300)
        tk.Label(box, text="LOGIN ADMIN", font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=12)
        tk.Label(box, text="Username", bg="#ffffff").pack(anchor="w", padx=16)
        self.ent_user = tk.Entry(box); self.ent_user.pack(fill="x", padx=16, pady=6)
        tk.Label(box, text="Password", bg="#ffffff").pack(anchor="w", padx=16)
        self.ent_pass = tk.Entry(box, show="*"); self.ent_pass.pack(fill="x", padx=16, pady=6)
        btn = tk.Button(box, text="LOGIN", bg="#375a7f", fg="white", command=self.action_login)
        btn.pack(pady=12)

    def action_login(self):
        user = self.ent_user.get().strip()
        pw = self.ent_pass.get().strip()
        if not user or not pw:
            messagebox.showwarning("Peringatan", "Isi username & password")
            return
        row = cek_login_db(user, pw)
        if row:
            self.current_user = {"id": row[0], "username": row[1], "nama": row[2]}
            messagebox.showinfo("Sukses", f"Login berhasil. Selamat, {row[2]}!")
            self.frame_login.pack_forget()
            self.frame_main.pack(fill="both", expand=True)
            self.sidebar.pack(side="left", fill="y")
            self.content.pack(side="left", fill="both", expand=True)
            for p in (self.page_dashboard, self.page_pelanggan, self.page_layanan, self.page_transaksi, self.page_riwayat):
                p.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.show_page("dashboard")
        else:
            messagebox.showerror("Gagal", "Username atau password salah")

    
    def _build_main_layout(self):
        
        tk.Label(self.sidebar, text="LAUNDRY SYSTEM", bg="#375a7f", fg="white", font=("Arial", 12, "bold")).pack(pady=18)
        btns = [
            ("Dashboard", lambda: self.show_page("dashboard")),
            ("Data Pelanggan", lambda: self.show_page("pelanggan")),
            ("Data Layanan", lambda: self.show_page("layanan")),
            ("Transaksi", lambda: self.show_page("transaksi")),
            ("Riwayat", lambda: self.show_page("riwayat")),
            ("Logout", self.logout)
        ]
        for t, cmd in btns:
            b = tk.Button(self.sidebar, text=t, bg="#375a7f", fg="white", bd=0, command=cmd)
            b.pack(fill="x", pady=6, padx=8)

        self._build_page_dashboard()
        self._build_page_pelanggan()
        self._build_page_layanan()
        self._build_page_transaksi()
        self._build_page_riwayat()

    def _build_page_dashboard(self):
        p = self.page_dashboard
        tk.Label(p, text="Dashboard", font=("Arial", 16, "bold"), bg="#ffffff").pack(anchor="w", padx=16, pady=12)
        stat_frame = tk.Frame(p, bg="#ffffff"); stat_frame.pack(anchor="nw", padx=16)
        tk.Label(stat_frame, text="Pelanggan: ", bg="#ffffff").grid(row=0, column=0, sticky="w")
        self.lbl_count_pelanggan = tk.Label(stat_frame, text="0", bg="#ffffff", font=("Arial", 12, "bold")); self.lbl_count_pelanggan.grid(row=0, column=1, padx=8)
        tk.Label(stat_frame, text="Layanan: ", bg="#ffffff").grid(row=1, column=0, sticky="w")
        self.lbl_count_layanan = tk.Label(stat_frame, text="0", bg="#ffffff", font=("Arial", 12, "bold")); self.lbl_count_layanan.grid(row=1, column=1, padx=8)
        tk.Button(p, text="Refresh Statistik", command=self.refresh_stats).pack(anchor="w", padx=16, pady=10)

    def refresh_stats(self):
        self.lbl_count_pelanggan.config(text=str(len(fetch_pelanggan())))
        self.lbl_count_layanan.config(text=str(len(fetch_layanan())))

    
    def _build_page_pelanggan(self):
        p = self.page_pelanggan
        header = tk.Frame(p, bg="#ffffff"); header.pack(fill="x", padx=12, pady=8)
        tk.Label(header, text="Data Pelanggan", font=("Arial", 14, "bold"), bg="#ffffff").pack(side="left")
        tk.Button(header, text="Tambah", command=self.popup_add_pelanggan).pack(side="right", padx=6)
        tk.Button(header, text="Hapus", command=self.hapus_selected_pelanggan).pack(side="right", padx=6)
        tk.Button(header, text="Refresh", command=self.refresh_pelanggan_table).pack(side="right")
        cols = ("id","nama","no_hp","alamat")
        self.tree_pelanggan = ttk.Treeview(p, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree_pelanggan.heading(c, text=c.capitalize())
        self.tree_pelanggan.column("id", width=80); self.tree_pelanggan.column("nama", width=220)
        self.tree_pelanggan.column("no_hp", width=140); self.tree_pelanggan.column("alamat", width=300)
        self.tree_pelanggan.pack(padx=12, pady=6)
        self.refresh_pelanggan_table()

    def refresh_pelanggan_table(self):
        for it in self.tree_pelanggan.get_children(): self.tree_pelanggan.delete(it)
        for r in fetch_pelanggan(): self.tree_pelanggan.insert("", "end", values=r)
        self.refresh_stats()

    def popup_add_pelanggan(self):
        win = tk.Toplevel(self); win.title("Tambah Pelanggan"); win.geometry("380x220")
        tk.Label(win, text="Nama").pack(anchor="w", padx=12); e_n = tk.Entry(win); e_n.pack(fill="x", padx=12, pady=6)
        tk.Label(win, text="No HP").pack(anchor="w", padx=12); e_hp = tk.Entry(win); e_hp.pack(fill="x", padx=12, pady=6)
        tk.Label(win, text="Alamat").pack(anchor="w", padx=12); e_al = tk.Entry(win); e_al.pack(fill="x", padx=12, pady=6)
        def simpan():
            nama = e_n.get().strip(); hp = e_hp.get().strip(); al = e_al.get().strip()
            if not nama:
                messagebox.showwarning("Peringatan", "Nama tidak boleh kosong"); return
            if insert_pelanggan(nama, hp, al):
                messagebox.showinfo("Sukses", "Pelanggan ditambahkan"); win.destroy(); self.refresh_pelanggan_table()
        tk.Button(win, text="Simpan", command=simpan).pack(pady=10)

    def hapus_selected_pelanggan(self):
        sel = self.tree_pelanggan.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih pelanggan terlebih dahulu"); return
        item = self.tree_pelanggan.item(sel[0])["values"]; id_p = item[0]
        if messagebox.askyesno("Konfirmasi", f"Hapus pelanggan ID {id_p}?"):
            if delete_pelanggan(id_p): messagebox.showinfo("Sukses", "Pelanggan dihapus"); self.refresh_pelanggan_table()

    
    def _build_page_layanan(self):
        p = self.page_layanan
        header = tk.Frame(p, bg="#ffffff"); header.pack(fill="x", padx=12, pady=8)
        tk.Label(header, text="Data Layanan", font=("Arial", 14, "bold"), bg="#ffffff").pack(side="left")
        tk.Button(header, text="Tambah", command=self.popup_add_layanan).pack(side="right", padx=6)
        tk.Button(header, text="Refresh", command=self.refresh_layanan_table).pack(side="right")
        cols = ("id","nama","harga")
        self.tree_layanan = ttk.Treeview(p, columns=cols, show="headings", height=18)
        self.tree_layanan.heading("id", text="ID"); self.tree_layanan.heading("nama", text="Nama Layanan"); self.tree_layanan.heading("harga", text="Harga (per kg)")
        self.tree_layanan.column("nama", width=420); self.tree_layanan.column("harga", width=160)
        self.tree_layanan.pack(padx=12, pady=6)
        self.refresh_layanan_table()

    def refresh_layanan_table(self):
        for it in self.tree_layanan.get_children(): self.tree_layanan.delete(it)
        for row in fetch_layanan(): self.tree_layanan.insert("", "end", values=(row[0], row[1], f"Rp {int(row[2]):,}".replace(",", ".")))
        self.refresh_stats()

    def popup_add_layanan(self):
        win = tk.Toplevel(self); win.title("Tambah Layanan"); win.geometry("380x180")
        tk.Label(win, text="Nama Layanan").pack(anchor="w", padx=12, pady=(12,0)); e_n = tk.Entry(win); e_n.pack(fill="x", padx=12, pady=6)
        tk.Label(win, text="Harga per KG (angka)").pack(anchor="w", padx=12); e_h = tk.Entry(win); e_h.pack(fill="x", padx=12, pady=6)
        def simpan():
            nama = e_n.get().strip(); h = e_h.get().strip()
            if not nama or not h: messagebox.showwarning("Peringatan", "Isi semua kolom"); return
            try: harga = int(h)
            except: messagebox.showwarning("Peringatan", "Harga harus angka"); return
            if insert_layanan(nama, harga): messagebox.showinfo("Sukses", "Layanan ditambahkan"); win.destroy(); self.refresh_layanan_table()
        tk.Button(win, text="Simpan", command=simpan).pack(pady=10)

    def hapus_selected_layanan(self):
        sel = self.tree_layanan.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih layanan terlebih dahulu"); return
        item = self.tree_layanan.item(sel[0])["values"]; id_l = item[0]
        if messagebox.askyesno("Konfirmasi", f"Hapus layanan ID {id_l}?"): 
            if delete_layanan(id_l): messagebox.showinfo("Sukses", "Layanan dihapus"); self.refresh_layanan_table()

    
    def _build_page_transaksi(self):
        p = self.page_transaksi
        header = tk.Frame(p, bg="#ffffff"); header.pack(fill="x", padx=12, pady=8)
        tk.Label(header, text="Transaksi", font=("Arial", 14, "bold"), bg="#ffffff").pack(side="left")
        tk.Button(header, text="Refresh Data", command=self.refresh_comboboxes).pack(side="right", padx=6)

        body = tk.Frame(p, bg="#ffffff"); body.pack(fill="both", expand=True, padx=12, pady=6)
        left = tk.Frame(body, bg="#ffffff"); left.pack(side="left", fill="y", padx=6, pady=6)
        right = tk.Frame(body, bg="#ffffff"); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        tk.Label(left, text="Pilih Pelanggan").pack(anchor="w")
        self.cmb_pelanggan = ttk.Combobox(left, state="readonly", width=30); self.cmb_pelanggan.pack(pady=4)
        tk.Label(left, text="Pilih Layanan").pack(anchor="w", pady=(8,0))
        self.cmb_layanan_trans = ttk.Combobox(left, state="readonly", width=30); self.cmb_layanan_trans.pack(pady=4)
        tk.Label(left, text="Berat (kg)").pack(anchor="w", pady=(8,0)); self.ent_berat_trans = tk.Entry(left, width=12); self.ent_berat_trans.pack(pady=4)
        tk.Button(left, text="Tambah ke Cart", command=self.add_to_cart).pack(pady=6)
        tk.Button(left, text="Simpan Transaksi (Checkout)", command=self.save_transaction).pack(pady=6)
        tk.Label(left, text="Cart (Detail)").pack(anchor="w", pady=(12,4))
        self.tree_cart = ttk.Treeview(left, columns=("layanan","berat","subtotal"), show="headings", height=8)
        self.tree_cart.heading("layanan", text="Layanan"); self.tree_cart.heading("berat", text="Berat"); self.tree_cart.heading("subtotal", text="Subtotal")
        self.tree_cart.pack()
        tk.Button(left, text="Hapus Item Terpilih", command=self.remove_cart_item).pack(pady=6)
        self.lbl_total_trans = tk.Label(left, text="Total: Rp 0", font=("Arial", 12, "bold")); self.lbl_total_trans.pack(pady=6)

        search_frame = tk.Frame(right, bg="#ffffff"); search_frame.pack(fill="x", padx=6, pady=(6,0))
        tk.Label(search_frame, text="Cari Nota (ID atau Nama):", bg="#ffffff").pack(side="left", padx=(0,6))
        self.ent_search_trans = tk.Entry(search_frame, width=20); self.ent_search_trans.pack(side="left", padx=(0,6))
        tk.Button(search_frame, text="Cari", command=self.search_transaksi).pack(side="left", padx=(0,6))
        tk.Button(search_frame, text="Reset", command=self.reset_search_transaksi).pack(side="left")

        cols = ("id","nama","tanggal","total","status")
        self.tree_transaksi = ttk.Treeview(right, columns=cols, show="headings", height=12)
        for c in cols: self.tree_transaksi.heading(c, text=c.capitalize())
        self.tree_transaksi.column("id", width=70); self.tree_transaksi.column("nama", width=180)
        self.tree_transaksi.column("tanggal", width=100); self.tree_transaksi.column("total", width=120); self.tree_transaksi.column("status", width=120)
        self.tree_transaksi.pack(padx=6, pady=6)
        self.tree_transaksi.bind("<<TreeviewSelect>>", self.on_trans_selected)

        fr_act = tk.Frame(right, bg="#ffffff"); fr_act.pack(fill="x", padx=6)
        tk.Button(fr_act, text="Refresh Daftar", command=self.refresh_transaction_table).pack(side="left", padx=6)
        tk.Button(fr_act, text="Export Nota PDF", command=self.export_selected_trans).pack(side="right", padx=6)
        self.cmb_status_update = ttk.Combobox(fr_act, state="readonly", values=["Diterima","Dicuci","Dikeringkan","Disetrika","Selesai","Diambil"], width=14)
        self.cmb_status_update.pack(side="right", padx=6)
        tk.Button(fr_act, text="Update", command=self.update_status_selected).pack(side="right", padx=6)
        tk.Button(fr_act, text="Advance Status", command=self.advance_status_selected).pack(side="right", padx=6)
        tk.Button(fr_act, text="Set Diterima", command=lambda: self.update_status_category_selected("Diterima")).pack(side="right", padx=6)
        tk.Button(fr_act, text="Set Di Proses", command=lambda: self.update_status_category_selected("Di Proses")).pack(side="right", padx=6)
        tk.Button(fr_act, text="Set Selesai", command=lambda: self.update_status_category_selected("Selesai")).pack(side="right", padx=6)

        tk.Label(right, text="Detail Transaksi:", bg="#ffffff").pack(anchor="w", padx=6, pady=(6,0))
        self.tree_detail = ttk.Treeview(right, columns=("layanan","berat","subtotal"), show="headings", height=6)
        self.tree_detail.heading("layanan", text="Layanan"); self.tree_detail.heading("berat", text="Berat"); self.tree_detail.heading("subtotal", text="Subtotal")
        self.tree_detail.pack(padx=6, pady=6, fill="x")

        self.refresh_comboboxes(); self.refresh_transaction_table()

    def refresh_comboboxes(self):
        pel = fetch_pelanggan(); lay = fetch_layanan()
        self.cmb_pelanggan['values'] = [f"{r[0]} - {r[1]}" for r in pel]
        self.cmb_layanan_trans['values'] = [f"{r[0]} - {r[1]} (Rp {int(r[2]):,})".replace(",", ".") for r in lay]

    def add_to_cart(self):
        sel_l = self.cmb_layanan_trans.get(); sel_p = self.cmb_pelanggan.get(); berat_raw = self.ent_berat_trans.get().strip()
        if sel_p == "" or sel_l == "" or berat_raw == "":
            messagebox.showwarning("Peringatan", "Pilih pelanggan, layanan, dan masukkan berat"); return
        try:
            berat = float(berat_raw); 
            if berat <= 0: raise ValueError
        except:
            messagebox.showwarning("Peringatan", "Berat harus angka > 0"); return
        id_l = int(sel_l.split(" - ")[0])
        harga = None; nama_l = ""
        for r in fetch_layanan():
            if r[0] == id_l:
                harga = r[2]; nama_l = r[1]; break
        if harga is None:
            messagebox.showerror("Error", "Layanan tidak ditemukan"); return
        subtotal = int(harga * berat)
        item = {"id_layanan": id_l, "nama_layanan": nama_l, "berat": berat, "harga": harga, "subtotal": subtotal}
        self.cart_items.append(item); self.refresh_cart_view(); self.ent_berat_trans.delete(0, tk.END)

    def refresh_cart_view(self):
        for it in self.tree_cart.get_children(): self.tree_cart.delete(it)
        total = 0
        for it in self.cart_items:
            self.tree_cart.insert("", "end", values=(it['nama_layanan'], it['berat'], f"Rp {int(it['subtotal']):,}".replace(",", ".")))
            total += it['subtotal']
        self.lbl_total_trans.config(text=f"Total: Rp {int(total):,}".replace(",", "."))

    def remove_cart_item(self):
        sel = self.tree_cart.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih item cart terlebih dahulu"); return
        idx = self.tree_cart.index(sel[0]); del self.cart_items[idx]; self.refresh_cart_view()
    

    def save_transaction(self):
        sel_p = self.cmb_pelanggan.get()
        if not sel_p: messagebox.showwarning("Peringatan", "Pilih pelanggan"); return
        if not self.cart_items: messagebox.showwarning("Peringatan", "Cart kosong"); return
        id_p = int(sel_p.split(" - ")[0])
        new_id = create_transaksi(id_p, self.cart_items)
        if new_id:
            messagebox.showinfo("Sukses", f"Transaksi tersimpan. ID: {new_id}")
            self.cart_items = []; self.refresh_cart_view(); self.refresh_transaction_table()
        else:
            messagebox.showerror("Gagal", "Gagal menyimpan transaksi")

    def refresh_transaction_table(self, filter_text=""):
        for it in self.tree_transaksi.get_children(): self.tree_transaksi.delete(it)
        all_trans = get_transaksi_all()
        if filter_text:
            filtered = []
            for r in all_trans:
                if str(r[0]).startswith(filter_text) or (r[1] and filter_text.lower() in r[1].lower()):
                    filtered.append(r)
            all_trans = filtered
        for r in all_trans:
            tanggal = r[2].strftime("%Y-%m-%d") if isinstance(r[2], (date, datetime)) else str(r[2])
            total_fmt = f"Rp {int(r[3]):,}".replace(",", ".")
            self.tree_transaksi.insert("", "end", values=(r[0], r[1] or "-", tanggal, total_fmt, r[4] or "-"))
        for it in self.tree_detail.get_children(): self.tree_detail.delete(it)

    def refresh_riwayat_table(self):
        for it in self.tree_riwayat.get_children(): self.tree_riwayat.delete(it)
        for r in get_transaksi_all():
            tanggal = r[2].strftime("%Y-%m-%d") if isinstance(r[2], (date, datetime)) else str(r[2])
            total_fmt = f"Rp {int(r[3]):,}".replace(",", ".")
            self.tree_riwayat.insert("", "end", values=(r[0], r[1] or "-", tanggal, total_fmt, r[4] or "-"))

    def on_trans_selected(self, event):
        sel = self.tree_transaksi.selection()
        if not sel: return
        idt = self.tree_transaksi.item(sel[0])["values"][0]
        for it in self.tree_detail.get_children(): self.tree_detail.delete(it)
        details = get_detail_by_trans(idt)
        for d in details:
            self.tree_detail.insert("", "end", values=(d[1] or "-", d[2], f"Rp {int(d[3]):,}".replace(",", ".")))

    def update_status_selected(self):
        sel = self.tree_transaksi.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih transaksi terlebih dahulu"); return
        idt = self.tree_transaksi.item(sel[0])["values"][0]; status = self.cmb_status_update.get()
        if not status: messagebox.showwarning("Peringatan", "Pilih status baru"); return
        if update_status_transaksi(idt, status): messagebox.showinfo("Sukses", "Status diperbarui"); self.refresh_transaction_table()

    def update_status_category_selected(self, category):
        sel = self.tree_transaksi.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih transaksi terlebih dahulu"); return
        idt = self.tree_transaksi.item(sel[0])["values"][0]
        if update_status_to_category(idt, category): messagebox.showinfo("Sukses", f"Status diperbarui ke {category}"); self.refresh_transaction_table()

    def advance_status_selected(self):
        sel = self.tree_transaksi.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih transaksi terlebih dahulu"); return
        idt = self.tree_transaksi.item(sel[0])["values"][0]
        
        current_status = None
        for r in get_transaksi_all():
            if r[0] == idt:
                current_status = r[4]
                break
        if not current_status:
            messagebox.showerror("Error", "Status tidak ditemukan"); return
        
        next_status = None
        if current_status == "Diterima":
            next_status = "Dicuci"
        elif current_status == "Dicuci":
            next_status = "Dikeringkan"
        elif current_status == "Dikeringkan":
            next_status = "Disetrika"
        elif current_status == "Disetrika":
            next_status = "Selesai"
        elif current_status == "Selesai":
            next_status = "Diambil"
        elif current_status == "Diambil":
            messagebox.showinfo("Info", "Status sudah selesai"); return
        else:
            messagebox.showerror("Error", "Status tidak valid"); return
        if update_status_transaksi(idt, next_status): messagebox.showinfo("Sukses", f"Status dimajukan ke {next_status}"); self.refresh_transaction_table()

    def search_transaksi(self):
        query = self.ent_search_trans.get().strip()
        self.refresh_transaction_table(filter_text=query)

    def reset_search_transaksi(self):
        self.ent_search_trans.delete(0, tk.END)
        self.refresh_transaction_table()

    def export_selected_trans(self):
        sel = self.tree_transaksi.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih transaksi untuk export"); return
        idt = self.tree_transaksi.item(sel[0])["values"][0]
        fn = export_transaksi_to_pdf(idt)
        if fn: messagebox.showinfo("Sukses", f"Nota berhasil dibuat:\n{fn}")


    def _build_page_riwayat(self):
        p = self.page_riwayat
        header = tk.Frame(p, bg="#ffffff"); header.pack(fill="x", padx=12, pady=8)
        tk.Label(header, text="Riwayat Transaksi", font=("Arial", 14, "bold"), bg="#ffffff").pack(side="left")
        tk.Button(header, text="Refresh", command=self.refresh_riwayat_table).pack(side="right", padx=6)
        cols = ("id","nama","tanggal","total","status")
        self.tree_riwayat = ttk.Treeview(p, columns=cols, show="headings", height=20)
        for c in cols: self.tree_riwayat.heading(c, text=c.capitalize())
        self.tree_riwayat.pack(padx=12, pady=12, fill="both")
        tk.Button(p, text="Lihat Detail Terpilih", command=self.riwayat_show_detail).pack(padx=12, anchor="w")
        self.refresh_riwayat_table()

    def riwayat_show_detail(self):
        sel = self.tree_riwayat.selection()
        if not sel: messagebox.showwarning("Peringatan", "Pilih transaksi pada riwayat"); return
        idt = self.tree_riwayat.item(sel[0])["values"][0]; details = get_detail_by_trans(idt)
        s = "Detail:\n"
        for d in details:
            s += f"- {d[1]} : {d[2]} kg -> Rp {int(d[3]):,}\n".replace(",", ".")
        messagebox.showinfo("Detail Transaksi", s)

    
    def show_page(self, key):
        pages = {"dashboard": self.page_dashboard, "pelanggan": self.page_pelanggan, "layanan": self.page_layanan, "transaksi": self.page_transaksi, "riwayat": self.page_riwayat}
        p = pages.get(key, self.page_dashboard); p.tkraise()
        if key == "dashboard": self.refresh_stats()
        if key == "pelanggan": self.refresh_pelanggan_table()
        if key == "layanan": self.refresh_layanan_table()
        if key in ("transaksi","riwayat"): self.refresh_comboboxes(); self.refresh_transaction_table()

    def logout(self):
        if messagebox.askyesno("Logout", "Yakin ingin logout?"):
            self.current_user = None
            self.frame_main.pack_forget()
            self.frame_login.pack(fill="both", expand=True)
            self.ent_user.delete(0, tk.END); self.ent_pass.delete(0, tk.END)


if __name__ == "__main__":
    try:
        app = LaundryApp()
        app.mainloop()
    except Exception as e:
        print("Fatal error:", e)
