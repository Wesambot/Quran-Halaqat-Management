import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors, AppStyles
from utils.components import developer_footer
from services.statistics_engine import compute_student_period_stats


def student_profile_view(page: ft.Page, db: DBManager, student_id, on_back):
    page.clean()
    student = db.get_student_by_id(student_id)
    if not student:
        page.add(ft.Text("الطالب غير موجود."))
        page.add(ft.ElevatedButton("رجوع", on_click=lambda _: on_back()))
        page.update()
        return

    group = db.get_group_by_id(student['group_id']) if student['group_id'] else None
    history = db.get_student_full_history(student_id)
    stats = compute_student_period_stats(history)
    achievements = db.get_student_achievements(student_id)

    # آخر حفظ وآخر مراجعة فعليَّين (أحدث سجل يحتوي بيانات)
    last_hifz = next((h for h in reversed(history) if h.get("hifz_sura_name")), None)
    last_murajaa = next((h for h in reversed(history) if h.get("murajaa_sura_name")), None)

    # عدد مرات ختم القرآن تقديريًا (بناءً على إجمالي صفحات الحفظ، تقريبي)
    khatmat_hifz = stats["hifz_pages_total"] // 604 if stats["hifz_pages_total"] else 0
    khatmat_murajaa = stats["murajaa_pages_total"] // 604 if stats["murajaa_pages_total"] else 0

    def stat_tile(label, value):
        return ft.Container(
            content=ft.Column([
                ft.Text(str(value), size=20, weight="bold", color=AppColors.PRIMARY),
                ft.Text(label, size=11, color=AppColors.TEXT_SECONDARY),
            ], horizontal_alignment="center"),
            padding=10, width=100,
        )

    achievements_row = ft.Row(
        [ft.Chip(label=ft.Text(f"{a['type']} ({a['period_label'] or ''})")) for a in achievements],
        wrap=True,
    ) if achievements else ft.Text("لا توجد إنجازات مسجّلة بعد.", size=12, color=AppColors.TEXT_SECONDARY)

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("الملف الشخصي"),
            bgcolor=AppColors.PRIMARY, color="white", center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.PERSON, size=60, color=AppColors.PRIMARY),
                ft.Text(student['name'], size=22, weight="bold"),
                ft.Text(group['name'] if group else "بدون حلقة", size=14, color=AppColors.TEXT_SECONDARY),
                ft.Text(f"تاريخ الانضمام: {student.get('join_date') or '-'}", size=12, color=AppColors.TEXT_SECONDARY),
                ft.Divider(),

                ft.Text("إحصائيات الحضور", weight="bold"),
                ft.Row([
                    stat_tile("أيام مسجّلة", stats["total_days"]),
                    stat_tile("حاضر", stats["present"]),
                    stat_tile("غائب", stats["absent"]),
                    stat_tile("متأخر", stats["late"]),
                    stat_tile("مستأذن", stats["excused"]),
                    stat_tile("نسبة الحضور", f"{stats['attendance_rate']}%"),
                ], wrap=True, alignment="center"),
                ft.Divider(),

                ft.Text("إحصائيات الحفظ", weight="bold"),
                ft.Row([
                    stat_tile("إجمالي صفحات", stats["hifz_pages_total"]),
                    stat_tile("إجمالي آيات", stats["hifz_ayat_total"]),
                    stat_tile("متوسط يومي (صفحة)", stats["avg_daily_hifz_pages"]),
                    stat_tile("عدد الأجزاء تقريبًا", stats["hifz_juz_total"]),
                    stat_tile("مرات ختم تقريبًا", khatmat_hifz),
                ], wrap=True, alignment="center"),
                ft.Text(
                    f"آخر حفظ: {last_hifz['hifz_sura_name']} ({last_hifz['hifz_from_ayah']}-{last_hifz['hifz_to_ayah']}) بتاريخ {last_hifz['report_date']}"
                    if last_hifz else "لا يوجد حفظ مسجّل بعد.",
                    size=12,
                ),
                ft.Divider(),

                ft.Text("إحصائيات المراجعة", weight="bold"),
                ft.Row([
                    stat_tile("إجمالي صفحات", stats["murajaa_pages_total"]),
                    stat_tile("إجمالي آيات", stats["murajaa_ayat_total"]),
                    stat_tile("متوسط يومي (صفحة)", stats["avg_daily_murajaa_pages"]),
                    stat_tile("مرات ختم تقريبًا", khatmat_murajaa),
                ], wrap=True, alignment="center"),
                ft.Text(
                    f"آخر مراجعة: {last_murajaa['murajaa_sura_name']} ({last_murajaa['murajaa_from_ayah']}-{last_murajaa['murajaa_to_ayah']}) بتاريخ {last_murajaa['report_date']}"
                    if last_murajaa else "لا توجد مراجعة مسجّلة بعد.",
                    size=12,
                ),
                ft.Divider(),

                ft.Text("الإنجازات", weight="bold"),
                achievements_row,

                ft.Container(height=10),
                ft.Text(
                    "ملاحظة: عدد الصفحات مبني على ما أدخله المعلم يدويًا؛ وعدد مرات الختم تقديري.",
                    size=10, color=AppColors.TEXT_SECONDARY, text_align="center",
                ),
                ft.Container(height=10),
                developer_footer(),
            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment="center"),
            padding=20,
        )
    )
    page.update()
