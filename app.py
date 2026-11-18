# -*- coding: utf-8 -*-
# نقش — أداة سطح مكتب حديثة لتكتب Arabic/Native على الصور
# واجهة CustomTkinter داكنة + تحكم مباشر على اللوحة (مقابض، عجلة، اختصارات).
# كل النصوص الأصلية UTF-8 (بايثون 3) — التشكيل/Bidi بيحصل قبل الرسم مباشرة.

import math
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageGrab
import arabic_reshaper
from bidi.algorithm import get_display

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    HAS_DND = False

APP_NAME = "نقش"
SS = 2  # supersampling لتنعيم الحروف

# ---------------------------------------------------------------------------
# الخطوط واللغات
# ---------------------------------------------------------------------------
FONT_PATHS = {
    "Arial": (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    "Tahoma": (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf"),
    "Traditional Arabic": (r"C:\Windows\Fonts\trado.ttf", r"C:\Windows\Fonts\tradbdo.ttf"),
    "Segoe UI": (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    "Calibri": (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
    "Georgia": (r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\georgiab.ttf"),
    "Verdana": (r"C:\Windows\Fonts\verdana.ttf", r"C:\Windows\Fonts\verdanab.ttf"),
    "Candara": (r"C:\Windows\Fonts\Candara.ttf", r"C:\Windows\Fonts\Candarab.ttf"),
    "Microsoft YaHei": (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"),
    "Baloo Bhaijaan 2": ("BalooBhaijaan2.ttf", "BalooBhaijaan2.ttf"),  # متغير: Bold جوّه الملف
    "Cairo": ("Cairo.ttf", "Cairo.ttf"),
    "Tajawal": ("Tajawal-Regular.ttf", "Tajawal-Bold.ttf"),
    "Amiri": ("Amiri-Regular.ttf", "Amiri-Bold.ttf"),
    "Noto Sans Arabic": ("NotoSansArabic.ttf", "NotoSansArabic.ttf"),
    "Noto Naskh Arabic": ("NotoNaskhArabic.ttf", "NotoNaskhArabic.ttf"),
    "Almarai": ("Almarai-Regular.ttf", "Almarai-Bold.ttf"),
    "IBM Plex Sans Arabic": ("IBMPlexSansArabic-Regular.ttf", "IBMPlexSansArabic-Bold.ttf"),
}
LATIN_FONTS = ["Segoe UI", "Arial", "Calibri", "Georgia", "Verdana", "Candara"]
ARABIC_FONTS = ["Baloo Bhaijaan 2", "Cairo", "Tajawal", "Amiri", "Noto Sans Arabic",
                "Noto Naskh Arabic", "Almarai", "IBM Plex Sans Arabic",
                "Arial", "Tahoma", "Traditional Arabic"]
LANGS = {
    "العربية": {"rtl": True, "shape": True, "fonts": ARABIC_FONTS, "default": "Baloo Bhaijaan 2"},
    "English": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Segoe UI"},
    "Français": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Segoe UI"},
    "Español": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Segoe UI"},
    "Deutsch": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Segoe UI"},
    "Português": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Segoe UI"},
    "Italiano": {"rtl": False, "shape": False, "fonts": LATIN_FONTS, "default": "Georgia"},
    "Русский": {"rtl": False, "shape": False, "fonts": ["Arial", "Tahoma", "Verdana"], "default": "Arial"},
    "中文": {"rtl": False, "shape": False, "fonts": ["Microsoft YaHei", "Arial"], "default": "Microsoft YaHei"},
}

# ---------------------------------------------------------------------------
# الثيمات
# ---------------------------------------------------------------------------
DARK = {
    "bg": "#121212", "sidebar": "#1E1E1E", "card": "#232323",
    "field": "#2A2A2A", "border": "#3A3A3A", "text": "#FFFFFF",
    "muted": "#9CA3AF", "accent": "#2563EB", "accent_hover": "#1D4ED8",
    "canvas": "#121212", "handle": "#60A5FA", "crop": "#FBBF24",
}
LIGHT = {
    "bg": "#F3F4F6", "sidebar": "#FFFFFF", "card": "#FFFFFF",
    "field": "#FFFFFF", "border": "#D1D5DB", "text": "#111827",
    "muted": "#6B7280", "accent": "#2563EB", "accent_hover": "#1D4ED8",
    "canvas": "#E5E7EB", "handle": "#2563EB", "crop": "#F59E0B",
}

try:
    RESHAPER = arabic_reshaper.ArabicReshaper(
        configuration={"delete_harakat": False, "support_ligatures": True})
except Exception:
    RESHAPER = None


def res_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def rgb_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


def is_light(color):
    h = color.lstrip("#")
    if len(h) != 6:
        return True
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return True
    return (r * 299 + g * 587 + b * 114) / 1000 > 140


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME + " — حط الكلام على الصورة")
        root.geometry("1500x920")
        root.minsize(1150, 700)
        try:
            root.iconbitmap(res_path("logo.ico"))
        except Exception:
            pass

        self.s = {
            "lang": "العربية", "text": "أهلاً بك في نقش\nاكتب كلامك هنا وحرّكه زي ما تحب",
            "font": "Baloo Bhaijaan 2", "size": 44, "bold": False,
            "color": "#FFFFFF", "outline": "#101010", "outline_w": 3,
            "bg": True, "opacity": 40, "width_pct": 90,
            "x": 50, "y": 50, "pos": None,
        }
        self.image = self.default_image()
        self.overlay = None
        self.clean = None
        self.text_box = (0, 0, 0, 0)
        self.scale = 1.0
        self.zoom = 1.0
        self.offset = (0, 0)
        self.drag = None
        self.resize = None
        self.dark = True
        self.p = DARK
        self.base_item = self.text_item = self.guide_item = None
        self.base_photo = self.text_photo = None
        self.handle_items = {}
        self.handle_pts = {}
        self.crop_mode = False
        self.crop_start = None
        self.crop_anchor = None
        self.crop_rect = None
        self.crop_shades = []
        self.crop_win = None
        self.crop_frame = None

        self.build_ui()
        self.apply_theme(True)
        self.bind_keys()
        self.setup_dnd()
        self.rebuild_overlay()
        self.rebuild_base()
        self.rebuild_text_item()
        self.position_overlay()

    # ------------------------------------------------------------------ صورة افتراضية
    @staticmethod
    def default_image():
        w, h = 1200, 675
        img = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)], fill=(round(20 + 26 * t), round(22 + 30 * t), round(28 + 38 * t), 255))
        for i in range(24):
            x, y = (i * 173) % w, (i * 97) % h
            r = 36 + (i % 5) * 20
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 10))
        return img

    # ------------------------------------------------------------------ الواجهة
    def build_ui(self):
        root = self.root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # شريط أدوات علوي
        self.toolbar = ctk.CTkFrame(root, height=62, corner_radius=0, fg_color=self.p["sidebar"])
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.toolbar.grid_propagate(False)
        self.toolbar.columnconfigure(20, weight=1)
        tb = self.toolbar

        self.open_btn = self.tool_btn("📁  افتح صورة", self.open_image)
        self.paste_btn = self.tool_btn("📋  الصق", self.paste_clipboard)
        self.save_btn = self.tool_btn("💾  احفظ PNG", self.save, primary=True)
        self.save_desktop_btn = self.tool_btn("Save", self.save_to_desktop,
                                              primary=True, width=84)
        self.crop_btn = self.tool_btn("✂️  قص الصورة", self.start_crop)
        self.reset_btn = self.tool_btn("↺  رجّع الافتراضي", self.reset)
        self.help_btn = self.tool_btn("❔  اختصارات", self.show_help)
        self.theme_btn = self.tool_btn("◐  نهاري", self.toggle_theme)
        self.zoom_out = self.tool_btn("−", lambda: self.change_zoom(1 / 1.25), small=True)
        self.zoom_in = self.tool_btn("+", lambda: self.change_zoom(1.25), small=True)
        self.zoom_fit = self.tool_btn("ملاءمة", self.fit_zoom, small=True)

        # منطقة العمل
        work = ctk.CTkFrame(root, fg_color=self.p["bg"], corner_radius=0)
        work.grid(row=1, column=0, sticky="nsew")
        work.grid_columnconfigure(0, weight=1)
        work.grid_rowconfigure(0, weight=1)

        holder = ctk.CTkFrame(work, fg_color=self.p["bg"], corner_radius=0)
        holder.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=10)
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(holder, bg=self.p["canvas"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # اللوحة اليمنى
        self.sidebar = ctk.CTkScrollableFrame(work, width=386, corner_radius=0,
                                              fg_color=self.p["sidebar"])
        self.sidebar.grid(row=0, column=1, sticky="ns", padx=(4, 10), pady=10)

        self.build_text_card()
        self.build_font_card()
        self.build_position_card()
        self.build_advanced_card()

        # شريط الحالة
        self.status_bar = ctk.CTkFrame(root, height=32, corner_radius=0, fg_color=self.p["sidebar"])
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.lbl_status = ctk.CTkLabel(self.status_bar, text="جاهز", anchor="w",
                                       font=("Segoe UI", 11), text_color=self.p["muted"])
        self.lbl_status.pack(side="left", padx=12)
        self.lbl_lang = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11))
        self.lbl_image = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11))
        self.lbl_zoom = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11))
        self.lbl_pos = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11))
        for w in (self.lbl_pos, self.lbl_zoom, self.lbl_image, self.lbl_lang):
            w.pack(side="right", padx=10)

    def tool_btn(self, text, cmd, primary=False, small=False, width=None):
        b = ctk.CTkButton(
            self.toolbar, text=text, command=cmd,
            width=width or (44 if small else 132), height=34, corner_radius=8,
            font=("Segoe UI", 12, "bold" if primary else "normal"),
            fg_color=self.p["accent"] if primary else self.p["field"],
            hover_color=self.p["accent_hover"] if primary else self.p["border"],
            text_color="#FFFFFF", border_width=0 if primary else 1,
            border_color=self.p["border"])
        b.pack(side="left", padx=(4, 3), pady=12)
        return b

    def card(self, title):
        c = ctk.CTkFrame(self.sidebar, corner_radius=8, fg_color=self.p["card"],
                         border_width=1, border_color=self.p["border"])
        c.pack(fill="x", padx=6, pady=(6, 4))
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(head, text=title, font=("Segoe UI", 13, "bold"),
                     text_color=self.p["text"], anchor="w").pack(side="left")
        body = ctk.CTkFrame(c, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(2, 14))
        return c, body

    def field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11),
                     text_color=self.p["muted"], anchor="w").pack(fill="x", pady=(6, 2))

    def build_text_card(self):
        _, body = self.card("الكلام واللغة")
        self.field_label(body, "لغة الكلام")
        self.lang_var = ctk.StringVar(value=self.s["lang"])
        self.cmb_lang = ctk.CTkComboBox(
            body, values=list(LANGS), variable=self.lang_var, height=34, corner_radius=8,
            fg_color=self.p["field"], border_color=self.p["border"], border_width=1,
            button_color=self.p["border"], button_hover_color=self.p["accent"],
            dropdown_fg_color=self.p["field"], dropdown_text_color=self.p["text"],
            dropdown_hover_color=self.p["border"], text_color=self.p["text"],
            font=("Segoe UI", 12))
        self.cmb_lang.pack(fill="x")
        self.lang_var.trace_add("write", lambda *a: self.on_language())

        self.field_label(body, "اكتب كلامك هنا")
        self.txt = ctk.CTkTextbox(
            body, height=104, corner_radius=8, fg_color=self.p["field"],
            border_color=self.p["border"], border_width=1, text_color=self.p["text"],
            font=("Arial", 14), scrollbar_button_color=self.p["border"])
        self.txt.pack(fill="x")
        self.txt.insert("1.0", self.s["text"])
        try:
            self.txt._textbox.configure(justify="right")
        except Exception:
            pass
        self.txt.bind("<KeyRelease>", lambda e: self.full_render())
        # ربط صريح على الـ Text الحقيقي جوّه CTkTextbox
        self.setup_textbox_shortcuts()

    def build_font_card(self):
        _, body = self.card("الخط والمقاس")
        self.field_label(body, "الخط")
        self.font_var = ctk.StringVar(value=self.s["font"])
        self.cmb_font = ctk.CTkComboBox(
            body, values=ARABIC_FONTS, variable=self.font_var, height=34, corner_radius=8,
            fg_color=self.p["field"], border_color=self.p["border"], border_width=1,
            button_color=self.p["border"], button_hover_color=self.p["accent"],
            dropdown_fg_color=self.p["field"], dropdown_text_color=self.p["text"],
            dropdown_hover_color=self.p["border"], text_color=self.p["text"],
            font=("Segoe UI", 12))
        self.cmb_font.pack(fill="x")
        self.font_var.trace_add("write", lambda *a: self.on_font_change())
        # تنقّل بالأسهم مع معاينة حيّة لكل خط
        self.cmb_font._entry.bind("<Up>", lambda e: self.font_arrow(-1))
        self.cmb_font._entry.bind("<Down>", lambda e: self.font_arrow(1))

        self.field_label(body, "مقاس الكلام")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        self.size_var = ctk.IntVar(value=self.s["size"])
        self.size_slider = ctk.CTkSlider(
            row, from_=12, to=160, variable=self.size_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.set_size(round(float(v)), sync_slider=False))
        self.size_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.size_entry_var = ctk.StringVar(value=str(self.s["size"]))
        self.size_entry = ctk.CTkEntry(
            row, width=54, height=30, textvariable=self.size_entry_var, corner_radius=6,
            fg_color=self.p["field"], border_color=self.p["border"], border_width=1,
            text_color=self.p["text"], justify="center", font=("Segoe UI", 12))
        self.size_entry.pack(side="right")
        for seq in ("<Return>", "<FocusOut>"):
            self.size_entry.bind(seq, lambda e: self.commit_size_entry())
        self.size_entry.bind("<Up>", lambda e: self.set_size(self.s["size"] + 2))
        self.size_entry.bind("<Down>", lambda e: self.set_size(self.s["size"] - 2))

        self.field_label(body, "لون الكلام")
        self.color_btn = ctk.CTkButton(
            body, text="       ", width=54, height=28, corner_radius=6,
            fg_color=self.s["color"], hover_color=self.s["color"],
            border_width=1, border_color=self.p["border"],
            command=lambda: self.pick_color("color", self.color_btn))
        self.color_btn.pack(anchor="w")

        self.bold_chk = ctk.CTkCheckBox(
            body, text="عريض", font=("Segoe UI", 12), corner_radius=6,
            fg_color=self.p["accent"], hover_color=self.p["accent_hover"],
            border_color=self.p["border"], text_color=self.p["text"],
            command=self.full_render)
        self.bold_chk.pack(anchor="w", pady=(10, 2))

        self.field_label(body, "عرض الكلام")
        self.width_var = ctk.IntVar(value=self.s["width_pct"])
        self.width_slider = ctk.CTkSlider(
            body, from_=30, to=100, variable=self.width_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.on_scale("width_pct", v))
        self.width_slider.pack(fill="x")

    def build_position_card(self):
        _, body = self.card("المكان والتحريك")
        self.field_label(body, "أفقي")
        self.x_var = ctk.IntVar(value=self.s["x"])
        self.x_slider = ctk.CTkSlider(
            body, from_=0, to=100, variable=self.x_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.on_scale("x", v))
        self.x_slider.pack(fill="x")
        self.field_label(body, "رأسي")
        self.y_var = ctk.IntVar(value=self.s["y"])
        self.y_slider = ctk.CTkSlider(
            body, from_=0, to=100, variable=self.y_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.on_scale("y", v))
        self.y_slider.pack(fill="x")
        ctk.CTkButton(
            body, text="◎  وسّط الكلام   (Home)", height=32, corner_radius=8,
            fg_color=self.p["field"], hover_color=self.p["border"],
            border_width=1, border_color=self.p["border"], text_color=self.p["text"],
            font=("Segoe UI", 12), command=self.center_text).pack(fill="x", pady=(12, 4))
        ctk.CTkLabel(
            body, text="اسحب الكلام أو المقابض على الصورة • Ctrl + عجلة تغيّر المقاس",
            font=("Segoe UI", 10), text_color=self.p["muted"],
            wraplength=320, justify="right").pack(anchor="w", pady=(6, 0))

    def build_advanced_card(self):
        card, body = self.card("إعدادات زيادة")
        self.card_adv = card
        self.field_label(body, "لون الحافة")
        self.outline_btn = ctk.CTkButton(
            body, text="       ", width=54, height=28, corner_radius=6,
            fg_color=self.s["outline"], hover_color=self.s["outline"],
            border_width=1, border_color=self.p["border"],
            command=lambda: self.pick_color("outline", self.outline_btn))
        self.outline_btn.pack(anchor="w")
        self.field_label(body, "سماكة الحافة")
        self.outline_var = ctk.IntVar(value=self.s["outline_w"])
        ctk.CTkSlider(
            body, from_=0, to=12, variable=self.outline_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.on_scale("outline_w", v)).pack(fill="x")
        self.bg_chk = ctk.CTkCheckBox(
            body, text="خلفية خفيفة ورا الكلام", font=("Segoe UI", 12), corner_radius=6,
            fg_color=self.p["accent"], hover_color=self.p["accent_hover"],
            border_color=self.p["border"], text_color=self.p["text"],
            command=self.full_render)
        self.bg_chk.set(True)
        self.bg_chk.pack(anchor="w", pady=(10, 2))
        self.field_label(body, "شفافية الخلفية")
        self.opacity_var = ctk.IntVar(value=self.s["opacity"])
        ctk.CTkSlider(
            body, from_=5, to=95, variable=self.opacity_var, height=18, corner_radius=8,
            fg_color=self.p["border"], progress_color=self.p["accent"],
            button_color=self.p["accent"], button_hover_color=self.p["accent_hover"],
            command=lambda v: self.on_scale("opacity", v)).pack(fill="x")

    # ------------------------------------------------------------------ الثيم
    def apply_theme(self, dark):
        self.dark = dark
        self.p = DARK if dark else LIGHT
        p = self.p
        ctk.set_appearance_mode("dark" if dark else "light")

        for w in (self.root, self.toolbar, self.status_bar):
            w.configure(fg_color=p["sidebar"])
        self.sidebar.configure(fg_color=p["sidebar"])
        self.canvas.configure(bg=p["canvas"])
        for c in (self.card_adv,):
            c.configure(fg_color=p["card"], border_color=p["border"])

        for b in (self.open_btn, self.paste_btn, self.reset_btn, self.crop_btn,
                  self.help_btn, self.theme_btn, self.zoom_out, self.zoom_in, self.zoom_fit):
            b.configure(fg_color=p["field"], hover_color=p["border"],
                        border_color=p["border"], text_color=p["text"])
        for b in (self.save_btn, self.save_desktop_btn):
            b.configure(fg_color=p["accent"], hover_color=p["accent_hover"],
                        text_color="#FFFFFF")
        self.theme_btn.configure(text=("◐  نهاري" if dark else "◐  ليلي"))

        for cmb in (self.cmb_lang, self.cmb_font):
            cmb.configure(fg_color=p["field"], border_color=p["border"],
                          button_color=p["border"], button_hover_color=p["accent"],
                          dropdown_fg_color=p["field"], dropdown_text_color=p["text"],
                          dropdown_hover_color=p["border"], text_color=p["text"])
        for e in (self.size_entry,):
            e.configure(fg_color=p["field"], border_color=p["border"], text_color=p["text"])
        for s in (self.size_slider, self.width_slider, self.x_slider, self.y_slider):
            s.configure(fg_color=p["border"], progress_color=p["accent"],
                        button_color=p["accent"], button_hover_color=p["accent_hover"])
        self.txt.configure(fg_color=p["field"], border_color=p["border"], text_color=p["text"],
                           scrollbar_button_color=p["border"])
        self.color_btn.configure(border_color=p["border"])
        self.outline_btn.configure(border_color=p["border"])
        for chk in (self.bold_chk, self.bg_chk):
            chk.configure(fg_color=p["accent"], hover_color=p["accent_hover"],
                          border_color=p["border"], text_color=p["text"])
        for lab in (self.lbl_status, self.lbl_lang, self.lbl_image, self.lbl_zoom, self.lbl_pos):
            lab.configure(text_color=p["muted"])
        if self.guide_item:
            self.canvas.itemconfig(self.guide_item, outline=p["accent"])
        self.full_render()

    def toggle_theme(self):
        self.apply_theme(not self.dark)

    # ------------------------------------------------------------------ الأحداث
    def bind_keys(self):
        r = self.root
        r.bind("<Control-o>", lambda e: self.open_image())
        r.bind("<Control-s>", lambda e: self.save())
        r.bind("<Control-a>", lambda e: self.select_all_in_textbox())
        r.bind("<Control-A>", lambda e: self.select_all_in_textbox())
        r.bind("<Control-v>", self.on_global_ctrl_v)
        r.bind("<Control-V>", self.on_global_ctrl_v)
        r.bind("<Control-plus>", lambda e: self.change_size(+4))
        r.bind("<Control-equal>", lambda e: self.change_size(+4))
        r.bind("<Control-minus>", lambda e: self.change_size(-4))
        r.bind("<Control-0>", lambda e: self.fit_zoom())
        r.bind("<Home>", lambda e: self.center_text())
        r.bind("<Return>", lambda e: self.confirm_crop() if self.crop_mode else None)
        r.bind("<Escape>", lambda e: self.cancel_crop() if self.crop_mode else None)

        # اللوحة: سحب + مقابض + عجلة
        self.canvas.bind("<Configure>", lambda e: self.on_resize())
        self.canvas.bind("<ButtonPress-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_wheel)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-3>", lambda e: self.show_help())

    def setup_dnd(self):
        if not HAS_DND:
            return
        try:
            TkinterDnD._require(self.root)
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind("<<Drop>>", lambda e: self.load_image(e.data.strip("{}")))
        except Exception:
            pass

    def show_help(self):
        messagebox.showinfo(
            "الاختصارات",
            "Ctrl+O افتح • Ctrl+V الصق (صورة أو كلام) • Ctrl+S احفظ\n"
            "Ctrl+A تحديد كل الكلام • Ctrl++ / Ctrl+- مقاس الكلام\n"
            "Home وسّط • الأسهم حرّك • Ctrl+0 ملاءمة\n"
            "Ctrl + عجلة الفارة على اللوحة: تكبير/تصغير الكلام\n"
            "اسحب المقابض حوالين الكلام لتغيير المقاس • Enter تأكيد القص، Esc إلغاء")

    def on_language(self):
        self.s["lang"] = self.lang_var.get()
        info = LANGS[self.s["lang"]]
        self.cmb_font.configure(values=info["fonts"])
        if self.s["font"] not in info["fonts"]:
            self.s["font"] = info["default"]
            self.font_var.set(self.s["font"])
        try:
            self.txt._textbox.configure(justify="right" if info["rtl"] else "left")
            self.txt.configure(font=("Arial" if info["rtl"] else "Segoe UI", 14))
        except Exception:
            pass
        self.full_render()
        self.set_status("لغة الكلام: " + self.s["lang"])

    def on_font_change(self):
        name = self.font_var.get()
        if not name:
            return
        self.s["font"] = name
        self.full_render()
        self.set_status("الخط: " + name)

    def font_arrow(self, delta):
        values = list(self.cmb_font.cget("values") or [])
        if not values:
            return "break"
        current = self.font_var.get()
        try:
            i = values.index(current)
        except ValueError:
            i = 0
        i = max(0, min(len(values) - 1, i + delta))
        self.font_var.set(values[i])
        return "break"

    # ---------------------------------------------------------- مربع النص: اختصارات
    def text_widget(self):
        """الـ Text الحقيقي اللي CTkTextbox بيغلّفه — نربط عليه مباشرة."""
        return getattr(self.txt, "_textbox", self.txt)

    def focus_in_textbox(self):
        try:
            return self.root.focus_get() in (self.txt, self.text_widget())
        except Exception:
            return False

    def setup_textbox_shortcuts(self):
        box = self.text_widget()

        # قائمة بالزر الأيمن جوّه مربع النص
        self.text_menu = tk.Menu(self.root, tearoff=0)
        self.text_menu.add_command(label="قص", command=self.cut_from_textbox)
        self.text_menu.add_command(label="نسخ", command=self.copy_from_textbox)
        self.text_menu.add_command(label="لصق", command=self.paste_into_textbox)
        self.text_menu.add_separator()
        self.text_menu.add_command(label="تحديد الكل", command=self.select_all_in_textbox)

        # أحداث حقيقية + أحداث افتراضية (بعض لوحات المفاتيح العربية بتبعت <<Paste>>)
        for seq in ("<Control-a>", "<Control-A>", "<<SelectAll>>"):
            box.bind(seq, self.select_all_in_textbox)
        for seq in ("<Control-v>", "<Control-V>", "<<Paste>>", "<Shift-Insert>"):
            box.bind(seq, self.paste_into_textbox)
        box.bind("<Button-3>", self.show_text_menu)

    def show_text_menu(self, event):
        try:
            self.text_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.text_menu.grab_release()
        return "break"

    def select_all_in_textbox(self, event=None):
        box = self.text_widget()
        try:
            box.focus_set()
            box.tag_remove("sel", "1.0", "end")
            box.tag_add("sel", "1.0", "end")
            box.mark_set("insert", "end")
            box.see("end")
            self.set_status("اتحدد كل الكلام — اكتب أو احذف وانت طالع.")
        except Exception as e:
            self.set_status("التحديد فشل: " + str(e))
        return "break"

    def paste_into_textbox(self, event=None):
        """لصق نص فقط جوّه الصندوق — من غير ما يروح للحافظة الخاصة بالصور."""
        now = time.monotonic()
        if now - getattr(self, "_last_text_paste", 0) < 0.08:  # حماية من تكرار الحدث
            return "break"
        self._last_text_paste = now

        data = ""
        for getter in (lambda: self.text_widget().clipboard_get(),
                       lambda: self.root.clipboard_get()):
            try:
                data = getter()
                if data:
                    break
            except Exception:
                continue
        if not data:
            self.set_status("مفيش كلام في الحافظة.")
            return "break"

        box = self.text_widget()
        try:
            box.focus_set()
            if box.tag_ranges("sel"):
                box.delete("sel.first", "sel.last")
            box.insert("insert", data)
            box.see("insert")
            self.full_render()
            self.set_status("اتلصق الكلام جوّه مربع النص.")
        except Exception as e:
            self.set_status("ماقدرتش ألصق الكلام: " + str(e))
        return "break"

    def copy_from_textbox(self, event=None):
        box = self.text_widget()
        try:
            if box.tag_ranges("sel"):
                data = box.get("sel.first", "sel.last")
                self.root.clipboard_clear()
                self.root.clipboard_append(data)
                self.set_status("اتنسخ الكلام المحدد.")
        except Exception:
            pass
        return "break"

    def cut_from_textbox(self, event=None):
        box = self.text_widget()
        try:
            if box.tag_ranges("sel"):
                data = box.get("sel.first", "sel.last")
                self.root.clipboard_clear()
                self.root.clipboard_append(data)
                box.delete("sel.first", "sel.last")
                self.full_render()
                self.set_status("اتقطع الكلام المحدد.")
        except Exception:
            pass
        return "break"

    def on_global_ctrl_v(self, event=None):
        if self.focus_in_textbox():
            return self.paste_into_textbox()
        return self.paste_clipboard()

    def on_scale(self, key, value):
        self.s[key] = int(float(value))
        if key in ("x", "y"):
            self.s["pos"] = None
            self.position_overlay()
        else:
            self.rebuild_overlay()
            self.rebuild_text_item()
            self.position_overlay()

    def set_size(self, value, sync_slider=True, sync_entry=True):
        v = max(12, min(160, int(value)))
        self.s["size"] = v
        if sync_slider:
            self.size_var.set(v)
        if sync_entry:
            self.size_entry_var.set(str(v))
        self.rebuild_overlay()
        self.rebuild_text_item()
        self.position_overlay()

    def commit_size_entry(self):
        try:
            self.set_size(int(self.size_entry_var.get()))
        except ValueError:
            self.size_entry_var.set(str(self.s["size"]))

    def change_size(self, delta):
        self.set_size(self.s["size"] + delta)

    def change_zoom(self, factor):
        if self.crop_mode:
            self.exit_crop()
        self.zoom = max(0.25, min(4.0, self.zoom * factor))
        self.rebuild_base()
        self.rebuild_text_item()
        self.position_overlay()

    def fit_zoom(self):
        self.zoom = 1.0
        self.change_zoom(1.0)

    def on_ctrl_wheel(self, event):
        self.change_size(3 if event.delta > 0 else -3)
        return "break"

    def on_wheel(self, event):
        if event.state & 0x4:  # Ctrl متضغط — اتعامل معاه في on_ctrl_wheel
            return None
        x, y = self.pointer(event)
        bx, by, bw, bh = self.text_box
        if bx <= x <= bx + bw and by <= y <= by + bh:
            self.change_size(3 if event.delta > 0 else -3)
        else:
            self.change_zoom(1.1 if event.delta > 0 else 1 / 1.1)
        return "break"

    def nudge(self, dx, dy):
        x, y, _, _ = self.text_box
        if self.s.get("pos") is None:
            x, y = self.center_positions()
        self.s["pos"] = (x + dx, y + dy)
        self.position_overlay()

    def center_text(self):
        self.s["x"], self.s["y"] = 50, 50
        self.x_var.set(50)
        self.y_var.set(50)
        self.s["pos"] = None
        self.position_overlay()
        self.set_status("وسّطت الكلام.")

    def reset(self):
        if self.crop_mode:
            self.exit_crop()
        self.s.update({"lang": "العربية", "font": "Baloo Bhaijaan 2", "size": 44, "bold": False,
                       "color": "#FFFFFF", "outline": "#101010", "outline_w": 3,
                       "bg": True, "opacity": 40, "width_pct": 90,
                       "x": 50, "y": 50, "pos": None})
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "أهلاً بك في نقش\nاكتب كلامك هنا وحرّكه زي ما تحب")
        try:
            self.txt._textbox.configure(justify="right")
        except Exception:
            pass
        self.lang_var.set("العربية")
        self.font_var.set("Baloo Bhaijaan 2")
        self.cmb_font.configure(values=ARABIC_FONTS)
        self.size_var.set(44); self.size_entry_var.set("44")
        self.width_var.set(90); self.x_var.set(50); self.y_var.set(78)
        self.outline_var.set(3); self.opacity_var.set(40)
        self.bold_chk.set(False); self.bg_chk.set(True)
        self.color_btn.configure(fg_color=self.s["color"], hover_color=self.s["color"])
        self.outline_btn.configure(fg_color=self.s["outline"], hover_color=self.s["outline"])
        self.zoom = 1.0
        self.full_render()
        self.set_status("رجّعت كل حاجة لالأصل.")

    def set_status(self, text):
        self.lbl_status.configure(text=text)

    # ------------------------------------------------------------------ ملفات/حافظة
    def open_image(self):
        p = filedialog.askopenfilename(
            filetypes=[("صور", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"), ("كل الملفات", "*.*")])
        if p:
            self.load_image(p)

    def load_image(self, path):
        if self.crop_mode:
            self.exit_crop()
        try:
            im = Image.open(path).convert("RGBA")
            self.image = im
            self.s["pos"] = None
            self.zoom = 1.0
            self.full_render()
            self.set_status("تحمّلت: " + os.path.basename(path))
        except Exception as e:
            messagebox.showerror("خطأ", "ماقدرتش أفتح الصورة:\n" + str(e))

    def paste_clipboard(self):
        """Ctrl+V عالمي: صورة أولاً، ولو مفيش كلام يتلصق في مربع النص."""
        if self.crop_mode:
            self.exit_crop()
        try:
            im = ImageGrab.grabclipboard()
        except Exception:
            im = None
        if isinstance(im, Image.Image):
            self.image = im.convert("RGBA")
            self.s["pos"] = None
            self.zoom = 1.0
            self.full_render()
            self.set_status("لصقت الصورة من الحافظة.")
            return
        try:
            data = self.root.clipboard_get()
        except Exception:
            data = ""
        if data:
            box = self.text_widget()
            if box.tag_ranges("sel"):
                box.delete("sel.first", "sel.last")
            box.insert("insert", data)
            box.focus_set()
            self.full_render()
            self.set_status("اتلصق الكلام من الحافظة.")
        else:
            self.set_status("مفيش صورة ولا كلام في الحافظة.")

    def paste_text(self):
        return self.paste_into_textbox()

    def save(self):
        if self.overlay is None:
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG", "*.png")],
            initialfile="نقش-بالكلام.png")
        if not p:
            return
        try:
            clean = self.image.copy()
            px, py = self.s["pos"] or self.center_positions()
            clean.alpha_composite(self.overlay, (round(px), round(py)))
            clean.convert("RGB").save(p, "PNG")
            self.set_status("اتحفظت: " + os.path.basename(p))
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
            self.set_status("الحفظ فشل.")

    @staticmethod
    def desktop_path():
        """مسار سطح المكتب (يتعامل مع OneDrive لو موجود)."""
        home = os.path.expanduser("~")
        candidates = []
        one = os.environ.get("OneDrive")
        if one:
            candidates.append(os.path.join(one, "Desktop"))
        candidates.append(os.path.join(home, "Desktop"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return home

    def save_to_desktop(self):
        """زر Save: يحفظ PNG جاهز على سطح المكتب من غير نافذة اختيار مكان."""
        if self.overlay is None:
            return
        folder = self.desktop_path()
        name = "نقش-" + time.strftime("%Y%m%d-%H%M%S") + ".png"
        p = os.path.join(folder, name)
        try:
            clean = self.image.copy()
            px, py = self.s["pos"] or self.center_positions()
            clean.alpha_composite(self.overlay, (round(px), round(py)))
            clean.convert("RGB").save(p, "PNG")
            self.set_status("اتحفظت على سطح المكتب: " + name)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
            self.set_status("الحفظ على سطح المكتب فشل.")

    def pick_color(self, key, btn):
        ans = colorchooser.askcolor(initialcolor=self.s[key], title="اختار اللون")
        if ans and ans[0]:
            self.s[key] = rgb_hex(ans[0])
            btn.configure(fg_color=self.s[key], hover_color=self.s[key])
            self.rebuild_overlay()
            self.rebuild_text_item()
            self.position_overlay()

    # ------------------------------------------------------------------ النص/الرسم
    def shape_text(self, text):
        """المعالجة الوحيدة لكل نص عربي قبل الرسم/الحفظ:
        raw UTF-8 → arabic_reshaper (ربط وتشكيل الحروف) → get_display (اتجاه RTL).
        """
        if not text:
            return ""
        if not LANGS[self.s["lang"]]["shape"]:
            return text
        try:
            shaped = RESHAPER.reshape(text) if RESHAPER else arabic_reshaper.reshape(text)
            return get_display(shaped)
        except Exception:
            try:
                return get_display(arabic_reshaper.reshape(text))
            except Exception:
                return text

    _font_ok_cache = {}

    @classmethod
    def _font_supports_presentation(cls, path, font):
        """هل الخط فيه Arabic Presentation Forms (U+FE70–U+FEFF)؟

        arabic_reshaper بيطلع صيغ U+FE70–U+FEFF. لو الخط مفيهوش النماذج دي،
        FreeType بيرسم مربع فاضي (tofu). بنكتشف ده بمقارنة bbox بحرف غير موجود
        — من غير أي مكتبة إضافية — ونستبدل الخط تلقائياً ببديل عربي كامل.
        """
        if path in cls._font_ok_cache:
            return cls._font_ok_cache[path]
        try:
            missing = font.getbbox("\U0010FFFF")
            ok = font.getbbox("\uFE8D") != missing  # ALEF ISOLATED FORM
        except Exception:
            ok = True
        cls._font_ok_cache[path] = ok
        return ok

    def font(self, size):
        regular, bold = FONT_PATHS.get(self.s["font"], FONT_PATHS["Arial"])
        path = bold if self.s["bold"] else regular
        full = path if os.path.isabs(path) else res_path(os.path.join("fonts", path))
        try:
            f = ImageFont.truetype(full, max(1, size))
            if LANGS[self.s["lang"]]["shape"] and not self._font_supports_presentation(full, f):
                full = res_path(os.path.join("fonts", "NotoSansArabic.ttf"))
                f = ImageFont.truetype(full, max(1, size))
            if self.s["bold"] and hasattr(f, "set_variation_by_name"):
                try:
                    f.set_variation_by_name("Bold")
                except Exception:
                    pass
            return f
        except Exception:
            return ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", max(1, size))

    def wrap(self, text, max_w, font):
        out = []
        for para in text.replace("\r", "").split("\n"):
            if not para.strip():
                out.append("")
                continue
            line = ""
            for word in para.split():
                test = (line + " " + word).strip()
                if not line or font.getlength(self.shape_text(test)) <= max_w:
                    line = test
                else:
                    out.append(line)
                    line = word
            out.append(line)
        return out

    def center_positions(self):
        w, h = self.image.size
        bw, bh = self.overlay.size if self.overlay else (1, 1)
        return (round(w * self.s["x"] / 100 - bw / 2),
                round(h * self.s["y"] / 100 - bh / 2))

    def rebuild_overlay(self):
        s = self.s
        s["text"] = self.txt.get("1.0", "end").rstrip("\n")
        s["font"] = self.font_var.get()
        s["bold"] = self.bold_chk.get()
        s["bg"] = self.bg_chk.get()

        # خزّن مركز الصندوق القديم قبل ما مقاسه يتغيّر — عشان الكتابة/المقاس
        # ما تعملش انزياح للنص (الـ pos كان بيفضل ثابت بينما الصندوق بيكبر).
        old_overlay, old_pos = self.overlay, s.get("pos")

        font = self.font(s["size"] * SS)
        max_w = max(60, round(self.image.width * s["width_pct"] / 100))
        lines = self.wrap(s["text"], max_w * SS, font)
        if not any(l.strip() for l in lines):
            blank = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            self._reanchor(old_overlay, old_pos, blank.size)
            self.overlay = blank
            self.text_box = (0, 0, 1, 1)
            return

        pad = max(6, round(s["size"] * 0.35))
        line_h = round(s["size"] * 1.45)
        ow = s["outline_w"]
        shaped_lines = [self.shape_text(l) for l in lines]  # UTF-8 → reshaper → bidi
        measure = max(font.getlength(l) for l in shaped_lines)
        text_w = min(max_w, measure / SS + ow * 2)
        box_w, box_h = max(1, int(text_w + pad * 2)), max(1, int(len(lines) * line_h + pad * 2))
        big = Image.new("RGBA", (box_w * SS, box_h * SS), (0, 0, 0, 0))
        o = ImageDraw.Draw(big, "RGBA")

        if s["bg"]:
            c = (14, 18, 26) if is_light(s["color"]) else (250, 250, 248)
            o.rounded_rectangle((0, 0, big.width - 1, big.height - 1),
                                radius=min(18, pad) * SS,
                                fill=(c[0], c[1], c[2], round(s["opacity"] * 255 / 100)))

        # توسيط كل السطور داخل مربع التحديد:
        # align="center"  → كل سطر متوسط بالنسبة لأطول سطر
        # anchor="mm"     → نقطة الرسم هي مركز الصندوق مش الزاوية
        # spacing يحافظ على نفس مسافة السطور اللي اتحسبت في box_h.
        line_spacing = max(0, round(line_h * SS - font.getbbox("A")[3] - ow * SS))
        o.multiline_text(
            (big.width / 2, big.height / 2), "\n".join(shaped_lines),
            font=font, fill=s["color"],
            align="center", anchor="mm", spacing=line_spacing,
            stroke_width=ow * SS, stroke_fill=s["outline"])

        new_overlay = big.resize((box_w, box_h), Image.Resampling.LANCZOS)
        self._reanchor(old_overlay, old_pos, new_overlay.size)
        self.overlay = new_overlay
        self.text_box = (0, 0, box_w, box_h)

    def _reanchor(self, old_overlay, old_pos, new_size):
        """ثبّت مركز الصندوق لما مقاسه (العرض/الارتفاع) يتغيّر."""
        if old_overlay is None or old_pos is None:
            self.s["pos"] = None
            return
        cx = old_pos[0] + old_overlay.width / 2
        cy = old_pos[1] + old_overlay.height / 2
        self.s["pos"] = (round(cx - new_size[0] / 2), round(cy - new_size[1] / 2))

    def rebuild_base(self):
        cw, ch = max(120, self.canvas.winfo_width()), max(120, self.canvas.winfo_height())
        fit = min(cw / self.image.width, ch / self.image.height)
        self.scale = fit * self.zoom
        dw, dh = max(1, int(self.image.width * self.scale)), max(1, int(self.image.height * self.scale))
        self.offset = ((cw - dw) // 2, (ch - dh) // 2)
        self.base_photo = ImageTk.PhotoImage(
            self.image.convert("RGB").resize((dw, dh), Image.Resampling.BILINEAR))
        if self.base_item is None:
            self.base_item = self.canvas.create_image(*self.offset, anchor="nw", image=self.base_photo)
        else:
            self.canvas.itemconfig(self.base_item, image=self.base_photo)
            self.canvas.coords(self.base_item, *self.offset)

    def full_render(self):
        self.rebuild_overlay()
        self.rebuild_base()
        self.rebuild_text_item()
        self.position_overlay()

    def rebuild_text_item(self):
        if self.overlay is None:
            return
        w, h = self.overlay.size
        sw, sh = max(1, int(w * self.scale)), max(1, int(h * self.scale))
        self.text_photo = ImageTk.PhotoImage(
            self.overlay.resize((sw, sh), Image.Resampling.BILINEAR))
        if self.text_item is None:
            self.text_item = self.canvas.create_image(0, 0, anchor="nw", image=self.text_photo)
            self.guide_item = self.canvas.create_rectangle(0, 0, 0, 0, outline=self.p["accent"],
                                                           dash=(5, 4), width=1)
        else:
            self.canvas.itemconfig(self.text_item, image=self.text_photo)

    def draw_handles(self):
        p = self.p
        for it in self.handle_items.values():
            self.canvas.delete(it)
        self.handle_items.clear()
        self.handle_pts.clear()
        if self.overlay is None:
            return
        px, py = self.s["pos"] or self.center_positions()
        bw, bh = self.overlay.size
        x = self.offset[0] + px * self.scale
        y = self.offset[1] + py * self.scale
        w, h = bw * self.scale, bh * self.scale
        pts = {
            "nw": (x, y), "n": (x + w / 2, y), "ne": (x + w, y),
            "e": (x + w, y + h / 2), "se": (x + w, y + h), "s": (x + w / 2, y + h),
            "sw": (x, y + h), "w": (x, y + h / 2),
        }
        state = "hidden" if self.crop_mode else "normal"
        for role, (hx, hy) in pts.items():
            r = 5
            item = self.canvas.create_rectangle(
                hx - r, hy - r, hx + r, hy + r,
                fill=p["handle"], outline="#FFFFFF", width=1,
                tags=("handle", role), state=state)
            self.handle_items[role] = item
            self.handle_pts[role] = (hx, hy)

    def position_overlay(self):
        s = self.s
        if self.overlay is None:
            return
        bw, bh = self.overlay.size
        if s.get("pos") is None:
            px, py = self.center_positions()
        else:
            px, py = s["pos"]
        keep_x, keep_y = min(40, bw / 2), min(30, bh / 2)
        px = max(-bw + keep_x, min(self.image.width - keep_x, px))
        py = max(-bh + keep_y, min(self.image.height - keep_y, py))
        s["pos"] = (round(px), round(py))
        self.text_box = (round(px), round(py), bw, bh)

        if self.text_item is not None:
            x = self.offset[0] + px * self.scale
            y = self.offset[1] + py * self.scale
            self.canvas.coords(self.text_item, x, y)
            self.canvas.coords(self.guide_item, x, y, x + bw * self.scale, y + bh * self.scale)
            self.canvas.itemconfig(self.guide_item, state=("hidden" if self.crop_mode else "normal"))
        self.draw_handles()

        cx = (px + bw / 2) / self.image.width * 100
        cy = (py + bh / 2) / self.image.height * 100
        s["x"], s["y"] = round(max(0, min(100, cx))), round(max(0, min(100, cy)))
        self.x_var.set(s["x"]); self.y_var.set(s["y"])
        self.lbl_lang.configure(text="اللغة: " + s["lang"])
        self.lbl_image.configure(text="الصورة: %d × %d" % self.image.size)
        self.lbl_zoom.configure(text="المعاينة: %d%%" % round(self.scale * 100))
        self.lbl_pos.configure(text="المكان: %d%% , %d%%" % (s["x"], s["y"]))

    # ------------------------------------------------------------------ اللوحة: سحب/مقابض/قص
    def pointer(self, e):
        dw, dh = self.image.width * self.scale, self.image.height * self.scale
        ox, oy = self.offset
        return ((e.x - ox) / self.scale, (e.y - oy) / self.scale)

    def on_down(self, e):
        self.canvas.focus_set()
        if self.crop_mode:
            ix, iy = self.pointer(e)
            ix = max(0, min(self.image.width, ix))
            iy = max(0, min(self.image.height, iy))
            self.crop_anchor = (ix, iy)
            self.crop_start = [ix, iy, ix, iy]
            self.draw_crop(ix, iy, ix, iy)
            return

        if self.resize is None:
            for role, (hx, hy) in self.handle_pts.items():
                if abs(e.x - hx) <= 8 and abs(e.y - hy) <= 8:
                    fx, fy = {
                        "nw": (1, 1), "n": (0.5, 1), "ne": (0, 1),
                        "e": (0, 0.5), "se": (0, 0), "s": (0.5, 0),
                        "sw": (1, 0), "w": (1, 0.5),
                    }[role]
                    px, py = self.s["pos"] or self.center_positions()
                    bw, bh = self.overlay.size
                    ax, ay = px + fx * bw, py + fy * bh
                    ix, iy = self.pointer(e)
                    if role in ("e", "w"):
                        d0 = max(1.0, abs(ix - ax))
                    elif role in ("n", "s"):
                        d0 = max(1.0, abs(iy - ay))
                    else:
                        d0 = max(1.0, math.hypot(ix - ax, iy - ay))
                    self.resize = {"role": role, "f": (fx, fy), "anchor": (ax, ay),
                                   "start_size": self.s["size"], "d0": d0}
                    return

        px, py = self.pointer(e)
        x, y, w, h = self.text_box
        pad = 12
        if x - pad <= px <= x + w + pad and y - pad <= py <= y + h + pad:
            self.drag = (px - x, py - y)
        else:
            self.drag = (w / 2, h / 2)
            self.s["pos"] = (round(px - w / 2), round(py - h / 2))
            self.position_overlay()
        self.canvas.config(cursor="fleur")

    def on_move(self, e):
        if self.crop_mode:
            if self.crop_anchor is None:
                return
            ix, iy = self.pointer(e)
            ix = max(0, min(self.image.width, ix))
            iy = max(0, min(self.image.height, iy))
            ax, ay = self.crop_anchor
            self.crop_start = [min(ax, ix), min(ay, iy), max(ax, ix), max(ay, iy)]
            self.draw_crop(*self.crop_start)
            return

        if self.resize:
            ix, iy = self.pointer(e)
            role = self.resize["role"]
            ax, ay = self.resize["anchor"]
            if role in ("e", "w"):
                d1 = abs(ix - ax)
            elif role in ("n", "s"):
                d1 = abs(iy - ay)
            else:
                d1 = math.hypot(ix - ax, iy - ay)
            new_size = max(12, min(160, round(self.resize["start_size"] * d1 / self.resize["d0"])))
            self.s["size"] = new_size
            self.size_var.set(new_size)
            self.size_entry_var.set(str(new_size))
            self.rebuild_overlay()
            bw, bh = self.overlay.size
            fx, fy = self.resize["f"]
            self.s["pos"] = (round(ax - fx * bw), round(ay - fy * bh))
            self.rebuild_text_item()
            self.position_overlay()
            return

        if self.drag is None:
            return
        px, py = self.pointer(e)
        self.s["pos"] = (round(px - self.drag[0]), round(py - self.drag[1]))
        self.position_overlay()

    def on_up(self, _=None):
        if self.crop_mode:
            return
        self.resize = None
        if self.drag is not None:
            self.drag = None
            self.canvas.config(cursor="arrow")

    def on_resize(self):
        self.rebuild_base()
        self.rebuild_text_item()
        self.position_overlay()

    # ------------------------------------------------------------------ القص
    def start_crop(self):
        if self.crop_mode:
            return
        self.crop_mode = True
        self.drag = None
        self.resize = None
        self.crop_start = None
        self.crop_anchor = None
        self.canvas.config(cursor="crosshair")
        self.draw_handles()
        self.set_status("قص: اسحب على الصورة تحدد الجزء — Enter تأكيد، Esc إلغاء")

    def exit_crop(self):
        self.crop_mode = False
        self.crop_start = None
        self.crop_anchor = None
        for it in [self.crop_rect] + self.crop_shades:
            if it:
                self.canvas.delete(it)
        self.crop_rect = None
        self.crop_shades = []
        if self.crop_win:
            self.canvas.delete(self.crop_win)
            self.crop_win = None
        if self.crop_frame:
            self.crop_frame.destroy()
            self.crop_frame = None
        self.canvas.config(cursor="arrow")
        self.draw_handles()

    def cancel_crop(self):
        if self.crop_mode:
            self.exit_crop()
            self.set_status("القص اتلغى.")

    def confirm_crop(self):
        if not self.crop_mode or self.crop_start is None:
            return
        x0, y0, x1, y1 = self.crop_start
        x0 = max(0, min(self.image.width - 1, round(x0)))
        y0 = max(0, min(self.image.height - 1, round(y0)))
        x1 = max(x0 + 10, min(self.image.width, round(x1)))
        y1 = max(y0 + 10, min(self.image.height, round(y1)))
        self.exit_crop()
        self.image = self.image.crop((x0, y0, x1, y1))
        self.s["pos"] = None
        self.zoom = 1.0
        self.full_render()
        self.set_status("اتقصّت الصورة: %d × %d" % self.image.size)

    def draw_crop(self, x0, y0, x1, y1):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        sx0 = self.offset[0] + x0 * self.scale
        sy0 = self.offset[1] + y0 * self.scale
        sx1 = self.offset[0] + x1 * self.scale
        sy1 = self.offset[1] + y1 * self.scale
        if self.crop_rect is None:
            self.crop_rect = self.canvas.create_rectangle(
                sx0, sy0, sx1, sy1, outline=self.p["crop"], width=2, dash=(6, 4), tags=("crop",))
        else:
            self.canvas.coords(self.crop_rect, sx0, sy0, sx1, sy1)

        regions = [(0, 0, cw, max(0, sy0)), (0, sy1, cw, ch),
                   (0, sy0, max(0, sx0), sy1), (sx1, sy0, cw, sy1)]
        if not self.crop_shades:
            for reg in regions:
                self.crop_shades.append(self.canvas.create_rectangle(
                    *reg, fill="#000000", stipple="gray50", outline="", tags=("crop",)))
        else:
            for it, reg in zip(self.crop_shades, regions):
                self.canvas.coords(it, *reg)

        cx = (sx0 + sx1) / 2
        cy = min(ch - 22, sy1 + 26)
        if self.crop_win is None:
            frame = ctk.CTkFrame(self.canvas)
            ctk.CTkButton(frame, text="تم", width=64, height=28, corner_radius=6,
                          fg_color=self.p["accent"], hover_color=self.p["accent_hover"],
                          command=self.confirm_crop).pack(side="left", padx=3, pady=3)
            ctk.CTkButton(frame, text="إلغاء", width=64, height=28, corner_radius=6,
                          fg_color=self.p["field"], hover_color=self.p["border"],
                          command=self.cancel_crop).pack(side="left", padx=3, pady=3)
            self.crop_frame = frame
            self.crop_win = self.canvas.create_window(cx, cy, window=frame, anchor="center", tags=("crop",))
        else:
            self.canvas.coords(self.crop_win, cx, cy)


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
