import pytest

from services.statistics_engine import (
    InvalidAyahRangeError,
    compute_ayah_span,
    compute_period_summary,
    compute_student_period_stats,
    format_range_label,
    rating_score,
    sort_students_by_strength,
)
from utils.quran_data import get_surah, get_surah_by_name
from utils.hizb_boundaries import hizb_and_juz_for_ayah


def test_quran_has_114_surahs_and_valid_name_lookup():
    assert get_surah(1)["name"] == "الفاتحة"
    assert get_surah(114)["name"] == "الناس"
    assert get_surah_by_name("الفلق")["number"] == 113
    assert get_surah_by_name("الإخلاص")["number"] == 112
    assert get_surah_by_name("اسم غير موجود") is None


@pytest.mark.parametrize("number", [0, 115, -1, 1.5, "1", None, True])
def test_get_surah_rejects_invalid_numbers(number):
    assert get_surah(number) is None


def test_compute_ayah_span_inside_one_surah():
    result = compute_ayah_span(1, 1, 1, 7)
    assert result["ayat_count"] == 7
    assert result["from_sura_name"] == "الفاتحة"
    assert result["to_sura_name"] == "الفاتحة"
    assert result["pages_count"] == 1


def test_compute_ayah_span_across_surahs():
    result = compute_ayah_span(1, 7, 2, 2)
    assert result["ayat_count"] == 3
    assert result["from_sura_name"] == "الفاتحة"
    assert result["to_sura_name"] == "البقرة"


@pytest.mark.parametrize(
    "args",
    [
        (1, 0, 1, 2),
        (1, 1, 1, 8),
        (2, 1, 2, 287),
        (2, 10, 1, 7),
        (0, 1, 1, 1),
        (1, 1, 115, 1),
    ],
)
def test_compute_ayah_span_rejects_invalid_ranges(args):
    with pytest.raises(InvalidAyahRangeError):
        compute_ayah_span(*args)


def test_hizb_and_juz_boundaries():
    assert hizb_and_juz_for_ayah(1, 1) == (1, 1)
    assert hizb_and_juz_for_ayah(2, 75) == (1, 2)
    assert hizb_and_juz_for_ayah(87, 1) == (30, 60)


def test_rating_score_and_student_sorting():
    assert rating_score("ممتاز") > rating_score("جيد")
    assert rating_score("قيمة غير معروفة") == 0

    records = [
        {"name": "A", "hifz_rating": "جيد", "hifz_pages_count": 8},
        {"name": "B", "hifz_rating": "ممتاز", "hifz_pages_count": 2},
        {"name": "C", "hifz_rating": "جيد", "hifz_pages_count": 12},
    ]
    ordered = sort_students_by_strength(records)
    assert [item["name"] for item in ordered] == ["B", "C", "A"]


def test_compute_period_summary_totals():
    records = [
        {"status": "حاضر", "hifz_pages_count": 2, "murajaa_pages_count": 1,
         "hifz_ayat_count": 10, "murajaa_ayat_count": 5},
        {"status": "غائب"},
        {"status": "متأخر", "hifz_pages_count": 1},
        {"status": "مستأذن", "murajaa_pages_count": 2},
    ]
    result = compute_period_summary(records)
    assert result == {
        "students_count": 4,
        "present": 1,
        "absent": 1,
        "late": 1,
        "excused": 1,
        "attendance_rate": 25,
        "hifz_pages_total": 3,
        "murajaa_pages_total": 3,
        "hifz_ayat_total": 10,
        "murajaa_ayat_total": 5,
    }


def test_compute_period_summary_empty_records():
    result = compute_period_summary([])
    assert result["students_count"] == 0
    assert result["attendance_rate"] == 0


def test_compute_student_period_stats():
    records = [
        {"status": "حاضر", "hifz_pages_count": 2, "murajaa_pages_count": 1,
         "hifz_ayat_count": 12, "murajaa_ayat_count": 6},
        {"status": "غائب"},
        {"status": "حاضر", "hifz_pages_count": 1, "murajaa_pages_count": 3,
         "hifz_ayat_count": 8, "murajaa_ayat_count": 20},
        {"status": "متأخر"},
        {"status": "مستأذن"},
    ]
    result = compute_student_period_stats(records)
    assert result["total_days"] == 5
    assert result["present"] == 2
    assert result["absent"] == 1
    assert result["late"] == 1
    assert result["excused"] == 1
    assert result["attendance_rate"] == 40
    assert result["hifz_pages_total"] == 3
    assert result["murajaa_pages_total"] == 4
    assert result["hifz_ayat_total"] == 20
    assert result["murajaa_ayat_total"] == 26
    assert result["avg_daily_hifz_pages"] == 1.5
    assert result["avg_daily_murajaa_pages"] == 2


def test_compute_student_period_stats_empty_records():
    result = compute_student_period_stats([])
    assert result["total_days"] == 0
    assert result["attendance_rate"] == 0
    assert result["avg_daily_hifz_pages"] == 0
    assert result["avg_daily_murajaa_pages"] == 0


def test_format_range_label():
    assert format_range_label(3, 3) == "3"
    assert format_range_label(3, 5) == "3-5"
