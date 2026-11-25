"""
خدمة التاريخ والفترات الزمنية الموحدة (Date/Time Service)
-------------------------------------------------------------
مسؤولة عن كل حسابات التاريخ في التطبيق (اليوم، الأسبوع، الشهر، السنة)
في مكان واحد فقط، حتى لا تتكرر حسابات التاريخ داخل كل شاشة على حدة.

قواعد ثابتة يعتمد عليها كل التطبيق:
- الأسبوع يبدأ يوم السبت وينتهي يوم الجمعة.
- معرّف أي فترة (يوم/أسبوع/شهر/سنة) هو تاريخ البداية بصيغة قياسية
  ثابتة YYYY-MM-DD (وليس رقم أسبوع فقط، لتفادي التعارض بين السنوات).
- التاريخ يُخزَّن دائمًا بقاعدة البيانات بصيغة YYYY-MM-DD، ويُعرض
  للمستخدم بالعربية فقط عند الحاجة (format_* في هذا الملف).
- لا تُستخدم مكتبة Flet هنا إطلاقًا - هذه الخدمة مستقلة تمامًا وقابلة
  للاختبار بمعزل عن الواجهة.
"""

from datetime import date, timedelta
import calendar


ARABIC_DAY_NAMES = {
    0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
    4: "الجمعة", 5: "السبت", 6: "الأحد",
}

ARABIC_MONTH_NAMES = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}

DB_DATE_FORMAT = "%Y-%m-%d"


class DateService:
    """كل الدوال هنا static/module-level بالمعنى العملي: لا تحتاج حالة داخلية،
    تُستدعى مباشرة كـ DateService.today() إلخ."""

    # =====================================================================
    # القراءة الأساسية للتاريخ الحقيقي من نظام الجهاز
    # =====================================================================
    @staticmethod
    def today() -> date:
        return date.today()

    @staticmethod
    def yesterday_of(d: date) -> date:
        return d - timedelta(days=1)

    @staticmethod
    def tomorrow_of(d: date) -> date:
        return d + timedelta(days=1)

    # =====================================================================
    # تحويل صيغة التخزين القياسية (قاعدة البيانات) <-> كائن date
    # =====================================================================
    @staticmethod
    def to_db_format(d: date) -> str:
        return d.strftime(DB_DATE_FORMAT)

    @staticmethod
    def from_db_format(s: str) -> date:
        return date.fromisoformat(s)

    # =====================================================================
    # الأسبوع (يبدأ السبت وينتهي الجمعة)
    # =====================================================================
    @staticmethod
    def week_start(d: date) -> date:
        """يرجع تاريخ يوم السبت الذي يبدأ فيه أسبوع التاريخ d."""
        # Python: الاثنين=0 ... الأحد=6. نحوّلها بحيث السبت=0 ... الجمعة=6.
        days_since_saturday = (d.weekday() + 2) % 7
        return d - timedelta(days=days_since_saturday)

    @staticmethod
    def week_end(d: date) -> date:
        """يرجع تاريخ يوم الجمعة الذي ينتهي فيه أسبوع التاريخ d."""
        return DateService.week_start(d) + timedelta(days=6)

    @staticmethod
    def week_days(d: date) -> list:
        """يرجع الأيام السبعة لأسبوع التاريخ d، من السبت إلى الجمعة."""
        start = DateService.week_start(d)
        return [start + timedelta(days=i) for i in range(7)]

    @staticmethod
    def week_id(d: date) -> str:
        """معرّف فريد وآمن للأسبوع (تاريخ بداية الأسبوع بصيغة قياسية)،
        يُستخدم بدل رقم الأسبوع وحده لتفادي أي تعارض بين السنوات."""
        return DateService.to_db_format(DateService.week_start(d))

    @staticmethod
    def week_number_in_year(d: date) -> int:
        """رقم الأسبوع داخل سنته (للعرض فقط، وليس كمعرّف فترة)."""
        start = DateService.week_start(d)
        year_start_of_first_week = DateService.week_start(date(start.year, 1, 1))
        return ((start - year_start_of_first_week).days // 7) + 1

    @staticmethod
    def previous_week(d: date) -> date:
        return DateService.week_start(d) - timedelta(days=7)

    @staticmethod
    def next_week(d: date) -> date:
        return DateService.week_start(d) + timedelta(days=7)

    # =====================================================================
    # الشهر (مع مراعاة 28/29/30/31 يومًا والسنوات الكبيسة تلقائيًا)
    # =====================================================================
    @staticmethod
    def month_start(year: int, month: int) -> date:
        return date(year, month, 1)

    @staticmethod
    def month_end(year: int, month: int) -> date:
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)

    @staticmethod
    def days_in_month(year: int, month: int) -> int:
        return calendar.monthrange(year, month)[1]

    @staticmethod
    def is_leap_year(year: int) -> bool:
        return calendar.isleap(year)

    @staticmethod
    def previous_month(year: int, month: int) -> tuple:
        if month == 1:
            return year - 1, 12
        return year, month - 1

    @staticmethod
    def next_month(year: int, month: int) -> tuple:
        if month == 12:
            return year + 1, 1
        return year, month + 1

    # =====================================================================
    # السنة
    # =====================================================================
    @staticmethod
    def year_start(year: int) -> date:
        return date(year, 1, 1)

    @staticmethod
    def year_end(year: int) -> date:
        return date(year, 12, 31)

    # =====================================================================
    # التنسيق العربي للعرض (التخزين يبقى دائمًا YYYY-MM-DD عبر to_db_format)
    # =====================================================================
    @staticmethod
    def format_date_arabic(d: date) -> str:
        """مثال: الثلاثاء 11 أغسطس 2026"""
        day_name = ARABIC_DAY_NAMES[d.weekday()]
        month_name = ARABIC_MONTH_NAMES[d.month]
        return f"{day_name} {d.day} {month_name} {d.year}"

    @staticmethod
    def format_date_short_arabic(d: date) -> str:
        """مثال: 11 أغسطس 2026 (بدون اسم اليوم)"""
        month_name = ARABIC_MONTH_NAMES[d.month]
        return f"{d.day} {month_name} {d.year}"

    @staticmethod
    def format_month_arabic(year: int, month: int) -> str:
        """مثال: أغسطس 2026"""
        return f"{ARABIC_MONTH_NAMES[month]} {year}"

    @staticmethod
    def format_week_range_arabic(d: date) -> str:
        """مثال: 8 أغسطس 2026 → 14 أغسطس 2026"""
        start = DateService.week_start(d)
        end = DateService.week_end(d)
        return f"{DateService.format_date_short_arabic(start)} → {DateService.format_date_short_arabic(end)}"

    @staticmethod
    def format_year(year: int) -> str:
        return str(year)

    @staticmethod
    def count_study_days_in_range(study_days_list, start: date, end: date) -> int:
        """يحسب عدد أيام الدراسة (بأسماء الأيام العربية) الواقعة فعليًا
        بين تاريخين (شاملَين)."""
        count = 0
        current = start
        while current <= end:
            if ARABIC_DAY_NAMES[current.weekday()] in study_days_list:
                count += 1
            current += timedelta(days=1)
        return count
