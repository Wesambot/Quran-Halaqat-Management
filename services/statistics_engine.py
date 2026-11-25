"""
محرك الإحصائيات (Statistics Engine)
------------------------------------
وحدة حسابية مستقلة تمامًا عن الواجهة (لا تستورد Flet إطلاقًا)، مسؤولة عن:
- حساب عدد الآيات/الصفحات التقريبية/الجزء/الحزب لأي مقطع (سورة، من آية، إلى آية).
- حساب تقييم الحفظ (ممتاز/جيد جدًا/جيد/مقبول/ضعيف) من عدد الصفحات.
- تجميع إحصائيات الحضور والحفظ والمراجعة لفترة زمنية معينة.

هذه الوحدة لا تتصل بقاعدة البيانات مباشرة؛ تستقبل بيانات خام (قوائم/قواميس)
من DBManager وتُرجع نتائج محسوبة، حتى يسهل اختبارها وتطويرها مستقبلاً.
"""

from utils.quran_data import get_surah
from utils.hizb_boundaries import hizb_and_juz_for_ayah


# ترتيب تقييمات الحفظ من الأعلى للأقل، وتُستخدم أيضًا لترتيب الطلاب حسب الأقوى حفظًا
RATING_ORDER = ["ممتاز", "جيد جدًا", "جيد", "مقبول", "ضعيف"]
RATING_SCORE = {name: (len(RATING_ORDER) - i) for i, name in enumerate(RATING_ORDER)}


class InvalidAyahRangeError(ValueError):
    """تُرفع عند إدخال نطاق تسميع غير صحيح (نهاية قبل بداية، أو رقم آية غير موجود)."""
    pass


def _estimate_page(surah: dict, ayah: int) -> int:
    """
    يقدّر رقم صفحة آية معيّنة داخل صفحات سورتها عبر الاستيفاء الخطي
    (الآية الأولى = أول صفحة للسورة بالضبط، الآية الأخيرة = آخر صفحة بالضبط).
    ملاحظة: هذا تقدير (approximation) للصفحة تحديدًا، بخلاف الجزء/الحزب
    اللذين يُحسبان بدقة تامة من جدول حدود الأحزاب الحقيقي.
    """
    total_ayat = surah["ayats"]
    total_pages = surah["end_page"] - surah["start_page"] + 1
    if total_ayat <= 1 or total_pages <= 1:
        return surah["start_page"]
    offset = round((ayah - 1) * (total_pages - 1) / (total_ayat - 1))
    return surah["start_page"] + offset


def compute_ayah_span(from_sura: int, from_ayah: int, to_sura: int, to_ayah: int) -> dict:
    """
    يحسب بيانات مقطع تسميع كامل قد يمتد عبر أكثر من سورة:
    من سورة+آية إلى سورة+آية أخرى. يُرجع عدد الآيات الحقيقي (بجمع آيات
    أي سور كاملة بينهما)، أول/آخر صفحة وعددها، وبداية/نهاية الجزء والحزب
    (بدقة تامة على مستوى الآية). يرفع InvalidAyahRangeError لو كانت
    النهاية تسبق البداية أو كان رقم السورة غير صحيح.
    """
    from_surah = get_surah(from_sura)
    to_surah = get_surah(to_sura)
    if from_surah is None:
        raise InvalidAyahRangeError(f"رقم سورة البداية غير صحيح: {from_sura}")
    if to_surah is None:
        raise InvalidAyahRangeError(f"رقم سورة النهاية غير صحيح: {to_sura}")

    if from_ayah < 1 or from_ayah > from_surah["ayats"]:
        raise InvalidAyahRangeError(
            f"سورة {from_surah['name']} تحتوي {from_surah['ayats']} آية فقط - تحقق من آية البداية ({from_ayah})"
        )
    if to_ayah < 1 or to_ayah > to_surah["ayats"]:
        raise InvalidAyahRangeError(
            f"سورة {to_surah['name']} تحتوي {to_surah['ayats']} آية فقط - تحقق من آية النهاية ({to_ayah})"
        )

    if (to_sura, to_ayah) < (from_sura, from_ayah):
        raise InvalidAyahRangeError(
            f"نهاية التسميع ({to_surah['name']}: آية {to_ayah}) تسبق بدايته "
            f"({from_surah['name']}: آية {from_ayah}) - تحقق من الترتيب"
        )

    if from_sura == to_sura:
        ayat_count = to_ayah - from_ayah + 1
    else:
        ayat_count = (from_surah["ayats"] - from_ayah + 1)
        for s_num in range(from_sura + 1, to_sura):
            ayat_count += get_surah(s_num)["ayats"]
        ayat_count += to_ayah

    first_page = _estimate_page(from_surah, from_ayah)
    last_page = _estimate_page(to_surah, to_ayah)
    pages_count = max(1, last_page - first_page + 1)

    juz_start, hizb_start = hizb_and_juz_for_ayah(from_sura, from_ayah)
    juz_end, hizb_end = hizb_and_juz_for_ayah(to_sura, to_ayah)

    return {
        "from_sura": from_sura, "from_sura_name": from_surah["name"], "from_ayah": from_ayah,
        "to_sura": to_sura, "to_sura_name": to_surah["name"], "to_ayah": to_ayah,
        "ayat_count": ayat_count,
        "first_page": first_page, "last_page": last_page, "pages_count": pages_count,
        "juz_start": juz_start, "juz_end": juz_end,
        "hizb_start": hizb_start, "hizb_end": hizb_end,
    }


def format_range_label(value_start, value_end) -> str:
    """يُنسّق مجالاً (جزء أو حزب) كنص: رقم واحد إن كانت البداية والنهاية متطابقتين، وإلا 'من-إلى'."""
    return str(value_start) if value_start == value_end else f"{value_start}-{value_end}"


def rating_score(rating: str) -> int:
    """يحوّل تقييم الحفظ النصي إلى رقم لأغراض الترتيب (الأعلى = الأقوى حفظًا)."""
    return RATING_SCORE.get(rating, 0)


def sort_students_by_strength(records: list) -> list:
    """
    يرتب قائمة سجلات الطلاب حسب الأقوى حفظًا:
    الأولوية لتقييم الحفظ (ممتاز -> ضعيف)، ثم لعدد صفحات الحفظ المسجلة.
    """
    return sorted(
        records,
        key=lambda r: (
            rating_score(r.get("hifz_rating")),
            r.get("hifz_pages_count") or 0,
        ),
        reverse=True,
    )


def compute_period_summary(records: list) -> dict:
    """
    يحسب ملخصًا لمجموعة من سجلات التقارير (يوم واحد أو عدة أيام):
    عدد الحاضرين/الغائبين/المتأخرين/المستأذنين، إجمالي صفحات الحفظ والمراجعة، وإجمالي الآيات.
    """
    total_present = sum(1 for r in records if r.get("status") == "حاضر")
    total_absent = sum(1 for r in records if r.get("status") == "غائب")
    total_late = sum(1 for r in records if r.get("status") == "متأخر")
    total_excused = sum(1 for r in records if r.get("status") == "مستأذن")

    total_hifz_pages = sum(r.get("hifz_pages_count") or 0 for r in records)
    total_murajaa_pages = sum(r.get("murajaa_pages_count") or 0 for r in records)
    total_hifz_ayat = sum(r.get("hifz_ayat_count") or 0 for r in records)
    total_murajaa_ayat = sum(r.get("murajaa_ayat_count") or 0 for r in records)

    return {
        "students_count": len(records),
        "present": total_present,
        "absent": total_absent,
        "late": total_late,
        "excused": total_excused,
        "attendance_rate": round((total_present / len(records)) * 100) if records else 0,
        "hifz_pages_total": total_hifz_pages,
        "murajaa_pages_total": total_murajaa_pages,
        "hifz_ayat_total": total_hifz_ayat,
        "murajaa_ayat_total": total_murajaa_ayat,
    }


def compute_student_period_stats(student_records: list) -> dict:
    """
    يحسب إحصائيات طالب واحد عبر عدة تقارير (أسبوع/شهر/سنة):
    حضور/غياب/تأخير/استئذان، إجمالي الحفظ والمراجعة، ومتوسط الحفظ اليومي.
    """
    days_recited = [r for r in student_records if r.get("status") == "حاضر"]
    total_hifz_pages = sum(r.get("hifz_pages_count") or 0 for r in student_records)
    total_murajaa_pages = sum(r.get("murajaa_pages_count") or 0 for r in student_records)
    total_hifz_ayat = sum(r.get("hifz_ayat_count") or 0 for r in student_records)
    total_murajaa_ayat = sum(r.get("murajaa_ayat_count") or 0 for r in student_records)

    hifz_days = [r for r in student_records if (r.get("hifz_pages_count") or 0) > 0]
    murajaa_days = [r for r in student_records if (r.get("murajaa_pages_count") or 0) > 0]

    total = len(student_records)
    present = sum(1 for r in student_records if r.get("status") == "حاضر")
    absent = sum(1 for r in student_records if r.get("status") == "غائب")
    late = sum(1 for r in student_records if r.get("status") == "متأخر")
    excused = sum(1 for r in student_records if r.get("status") == "مستأذن")

    return {
        "total_days": total,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_rate": round((present / total) * 100) if total else 0,
        "hifz_pages_total": total_hifz_pages,
        "murajaa_pages_total": total_murajaa_pages,
        "hifz_ayat_total": total_hifz_ayat,
        "murajaa_ayat_total": total_murajaa_ayat,
        "hifz_juz_total": round(total_hifz_pages / 20, 2) if total_hifz_pages else 0,
        "avg_daily_hifz_pages": round(total_hifz_pages / len(hifz_days), 2) if hifz_days else 0,
        "avg_daily_murajaa_pages": round(total_murajaa_pages / len(murajaa_days), 2) if murajaa_days else 0,
    }
