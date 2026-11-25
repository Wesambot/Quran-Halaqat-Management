"""
خدمة تصدير التقارير إلى PDF
-----------------------------
تحتاج هذه الخدمة إلى:
  pip install fpdf2 arabic-reshaper python-bidi   (موجودة في requirements.txt)

وإلى خط عربي (ملف .ttf) موضوع في: assets/fonts/Amiri-Regular.ttf
لأن خطوط fpdf2 الأساسية (Helvetica/Times) لا تدعم الحروف العربية إطلاقًا.

خط "Amiri" مجاني ومفتوح المصدر، حمّله من الرابط التالي وضعه في المسار أعلاه:
https://fonts.google.com/specimen/Amiri  (زر Download family، ثم انسخ ملف Amiri-Regular.ttf)

إن لم يكن الخط موجودًا، تعرض الدالة رسالة خطأ عربية واضحة بدل الانهيار.
"""

from pathlib import Path
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF

from utils.app_paths import AppPaths


FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_PATH = FONT_DIR / "Amiri-Regular.ttf"
FONT_BOLD_PATH = FONT_DIR / "Amiri-Bold.ttf"


class PDFFontMissingError(Exception):
    pass


def _ar(text) -> str:
    """يهيئ أي نص عربي (يربط الحروف ويعكس الاتجاه) ليظهر صحيحًا داخل PDF."""
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


class ArabicPDF(FPDF):
    """صفحة PDF أساسية بخط عربي واتجاه RTL، مع رأس وتذييل موحّدين لكل التقارير."""

    def __init__(self, title_ar: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        if not FONT_PATH.exists():
            raise PDFFontMissingError(
                "لم يتم العثور على خط عربي لإنشاء ملف PDF.\n"
                f"يرجى تحميل خط Amiri المجاني من:\nhttps://fonts.google.com/specimen/Amiri\n"
                f"ووضع ملف Amiri-Regular.ttf في المسار:\n{FONT_PATH}"
            )
        self.add_font("Amiri", "", str(FONT_PATH))
        if FONT_BOLD_PATH.exists():
            self.add_font("Amiri", "B", str(FONT_BOLD_PATH))
        else:
            self.add_font("Amiri", "B", str(FONT_PATH))
        self.set_font("Amiri", "", 12)
        self.report_title = title_ar
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        self.set_font("Amiri", "B", 16)
        self.set_text_color(46, 125, 50)  # AppColors.PRIMARY
        self.cell(0, 12, _ar(self.report_title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(76, 175, 80)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Amiri", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, _ar("تم إنشاء هذا التقرير بواسطة نظام إدارة الحلقات القرآنية"), align="C")

    def section_line(self, label, value):
        self.set_font("Amiri", "", 11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, _ar(f"{label}: {value}"), align="R", new_x="LMARGIN", new_y="NEXT")

    def table_header(self, columns_widths):
        """columns_widths: قائمة من (نص_العمود, العرض_بالملم) بترتيب القراءة من اليمين لليسار."""
        self.set_font("Amiri", "B", 10)
        self.set_fill_color(46, 125, 50)
        self.set_text_color(255, 255, 255)
        # نعكس ترتيب الرسم لأن fpdf يرسم من اليسار لليمين، بينما نريد أول عمود بالقائمة
        # (وهو أول عمود منطقيًا من اليمين في القراءة العربية) أن يظهر أقصى اليمين فعليًا.
        for text, width in reversed(columns_widths):
            self.cell(width, 8, _ar(text), border=1, align="C", fill=True)
        self.ln()

    def table_row(self, values_widths, fill=False):
        self.set_font("Amiri", "", 9)
        self.set_text_color(20, 20, 20)
        if fill:
            self.set_fill_color(240, 247, 240)
        for text, width in reversed(values_widths):
            self.cell(width, 7, _ar(text), border=1, align="C", fill=fill)
        self.ln()


def _output_path(app_paths: AppPaths, filename: str) -> str:
    app_paths.pdf_dir.mkdir(parents=True, exist_ok=True)
    return str(app_paths.pdf_dir / filename)


# =============================================================================
# التقرير اليومي
# =============================================================================
def generate_daily_report_pdf(db, report_id: int) -> str:
    report = db.get_report_by_id(report_id)
    group = db.get_group_by_id(report["group_id"])
    settings = db.get_settings()
    records = db.get_report_records(report_id)  # مرتبة مسبقًا حسب الأقوى حفظًا

    pdf = ArabicPDF("نظام إدارة الحلقات القرآنية - التقرير اليومي")
    pdf.section_line("اسم الحلقة", group["name"])
    pdf.section_line("اسم الأستاذ", settings["teacher_name"])
    pdf.section_line("التاريخ", report["date"])
    pdf.ln(4)

    columns = [("الطالب", 45), ("الحالة", 22), ("الحفظ", 45), ("التقييم", 25), ("المراجعة", 43)]
    pdf.table_header(columns)

    total_hifz_pages = 0
    total_murajaa_pages = 0
    for i, r in enumerate(records):
        if r.get("hifz_sura_name"):
            if r.get("hifz_to_sura_name") and r["hifz_to_sura_name"] != r["hifz_sura_name"]:
                hifz_text = f"{r['hifz_sura_name']}:{r['hifz_from_ayah']} - {r['hifz_to_sura_name']}:{r['hifz_to_ayah']}"
            else:
                hifz_text = f"{r['hifz_sura_name']} ({r['hifz_from_ayah']}-{r['hifz_to_ayah']})"
        else:
            hifz_text = "-"
        if r.get("murajaa_sura_name"):
            if r.get("murajaa_to_sura_name") and r["murajaa_to_sura_name"] != r["murajaa_sura_name"]:
                murajaa_text = f"{r['murajaa_sura_name']}:{r['murajaa_from_ayah']} - {r['murajaa_to_sura_name']}:{r['murajaa_to_ayah']}"
            else:
                murajaa_text = f"{r['murajaa_sura_name']} ({r['murajaa_from_ayah']}-{r['murajaa_to_ayah']})"
        else:
            murajaa_text = "-"
        pdf.table_row([
            (r["student_name"], 45),
            (r["status"], 22),
            (hifz_text, 45),
            (r.get("hifz_rating") or "-", 25),
            (murajaa_text, 43),
        ], fill=(i % 2 == 0))
        total_hifz_pages += r.get("hifz_pages_count") or 0
        total_murajaa_pages += r.get("murajaa_pages_count") or 0

    pdf.ln(6)
    pdf.set_font("Amiri", "B", 12)
    pdf.section_line("ملخص التقرير", "")
    pdf.section_line("عدد الطلاب", len(records))
    pdf.section_line("إجمالي صفحات الحفظ", total_hifz_pages)
    pdf.section_line("إجمالي صفحات المراجعة", total_murajaa_pages)

    filename = f"تقرير_يومي_{report['date']}.pdf"
    path = _output_path(db.app_paths, filename)
    pdf.output(path)
    return path


# =============================================================================
# التقرير الأسبوعي / الشهري (نفس البنية، تختلف فقط الفترة الزمنية والعنوان)
# =============================================================================
def _generate_period_report_pdf(db, group_id, date_from, date_to, title, filename):
    group = db.get_group_by_id(group_id)
    settings = db.get_settings()
    summary = db.get_group_period_summary(group_id, date_from, date_to)

    pdf = ArabicPDF(f"نظام إدارة الحلقات القرآنية - {title}")
    pdf.section_line("اسم الحلقة", group["name"])
    pdf.section_line("اسم الأستاذ", settings["teacher_name"])
    pdf.section_line("الفترة", f"{date_from} إلى {date_to}")
    pdf.section_line("عدد الطلاب", summary["summary"]["students_count"])
    pdf.section_line("عدد أيام الدراسة المسجّلة", summary["summary"]["reports_count"])
    pdf.ln(4)

    columns = [
        ("الطالب", 30), ("حضور", 14), ("غياب", 14), ("تأخير", 14), ("استئذان", 16),
        ("مرات حفظ", 16), ("مرات مراجعة", 18), ("صفحات حفظ", 18), ("صفحات مراجعة", 20),
    ]
    pdf.table_header(columns)

    for i, s in enumerate(summary["students"]):
        pdf.table_row([
            (s["student_name"], 30),
            (s["present"], 14),
            (s["absent"], 14),
            (s["late"], 14),
            (s["excused"], 16),
            (s["hifz_sessions"], 16),
            (s["murajaa_sessions"], 18),
            (s["hifz_pages_total"], 18),
            (s["murajaa_pages_total"], 20),
        ], fill=(i % 2 == 0))

    pdf.ln(6)
    pdf.set_font("Amiri", "B", 12)
    pdf.section_line(f"ملخص {title}", "")
    pdf.section_line("عدد الحاضرين (إجمالي الأيام)", summary["summary"]["total_present"])
    pdf.section_line("عدد الغائبين (إجمالي الأيام)", summary["summary"]["total_absent"])
    pdf.section_line("إجمالي صفحات الحفظ", summary["summary"]["total_hifz_pages"])
    pdf.section_line("إجمالي صفحات المراجعة", summary["summary"]["total_murajaa_pages"])
    pdf.section_line("إجمالي الآيات", summary["summary"]["total_ayat"])

    path = _output_path(db.app_paths, filename)
    pdf.output(path)
    return path


def generate_weekly_report_pdf(db, group_id, week_start: str, week_end: str) -> str:
    filename = f"تقرير_أسبوعي_{week_start}_الى_{week_end}.pdf"
    return _generate_period_report_pdf(db, group_id, week_start, week_end, "التقرير الأسبوعي", filename)


def generate_yearly_report_pdf(db, group_id, year: int) -> str:
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    filename = f"تقرير_سنوي_{year}.pdf"
    return _generate_period_report_pdf(db, group_id, year_start, year_end, "التقرير السنوي", filename)


def generate_monthly_report_pdf(db, group_id, year: int, month: int) -> str:
    from calendar import monthrange
    month_start = f"{year}-{month:02d}-01"
    last_day = monthrange(year, month)[1]
    month_end = f"{year}-{month:02d}-{last_day:02d}"
    filename = f"تقرير_شهري_{year}-{month:02d}.pdf"
    return _generate_period_report_pdf(db, group_id, month_start, month_end, "التقرير الشهري", filename)
