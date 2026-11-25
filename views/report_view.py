import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors, AppStyles
from utils.quran_data import QURAN_SURAS, get_surah
from utils.components import developer_footer
from services.statistics_engine import RATING_ORDER, compute_ayah_span, InvalidAyahRangeError
from services.date_service import DateService


def _surah_options():
    return [ft.dropdown.Option(key=str(s['number']), text=f"{s['number']}. {s['name']}") for s in QURAN_SURAS]


def report_view(page: ft.Page, db: DBManager, group_id, on_back, existing_report_id=None, report_date=None):
    """
    existing_report_id: إن مُرِّر، فهذا تعديل لتقرير موجود مسبقًا (لن يُنشأ
    تقرير جديد، بل تُحدَّث بيانات نفس التقرير عبر update_report_records،
    مع تعبئة كل حقول كل طالب تلقائيًا ببياناته المُسجَّلة سابقًا).
    report_date: تاريخ التقرير بصيغة YYYY-MM-DD (افتراضيًا اليوم الحالي).
    """
    page.clean()
    group = db.get_group_by_id(group_id)
    students = db.get_students_by_group(group_id)
    is_edit_mode = existing_report_id is not None
    report_date = report_date or DateService.to_db_format(DateService.today())

    existing_by_student = {}
    if is_edit_mode:
        for r in db.get_report_records(existing_report_id):
            existing_by_student[r["student_id"]] = r

    if not students:
        page.add(ft.Text("لا يوجد طلاب في هذه الحلقة لإصدار تقرير."))
        page.add(ft.ElevatedButton("رجوع", on_click=lambda _: on_back()))
        return

    records = []

    def start_reporting():
        show_student_report(0)

    def show_student_report(index):
        page.clean()
        if index >= len(students):
            finish_report()
            return

        student = students[index]

        status_radio = ft.RadioGroup(content=ft.Row([
            ft.Radio(value="حاضر", label="حاضر"),
            ft.Radio(value="متأخر", label="متأخر"),
            ft.Radio(value="غائب", label="غائب"),
            ft.Radio(value="مستأذن", label="مستأذن"),
        ], alignment=ft.MainAxisAlignment.CENTER), value="حاضر")

        recited_checkbox = ft.Checkbox(label="هل سمع اليوم؟", value=True)
        recitation_type = ft.Dropdown(
            label="نوع التسميع",
            options=[
                ft.dropdown.Option("حفظ"),
                ft.dropdown.Option("مراجعة"),
                ft.dropdown.Option("حفظ + مراجعة"),
            ],
            value="حفظ",
            visible=True
        )

        # قسم الحفظ: من سورة+آية إلى سورة+آية (بدون أي إدخال للصفحات إطلاقًا)
        hifz_from_surah_dd = ft.Dropdown(label="من سورة", options=_surah_options(), width=170)
        hifz_from_ayah = ft.TextField(label="من آية", width=80, keyboard_type=ft.KeyboardType.NUMBER, value="1")
        hifz_to_surah_dd = ft.Dropdown(label="إلى سورة", options=_surah_options(), width=170)
        hifz_to_ayah = ft.TextField(label="إلى آية", width=80, keyboard_type=ft.KeyboardType.NUMBER, value="1")
        hifz_rating_dd = ft.Dropdown(
            label="تقييم الحفظ",
            options=[ft.dropdown.Option(r) for r in RATING_ORDER],
            value="جيد",
            width=380,
        )
        hifz_pages_field = ft.TextField(label="عدد صفحات الحفظ (يدخلها المعلم)", width=380, keyboard_type=ft.KeyboardType.NUMBER)
        hifz_section = ft.Column([
            ft.Text("الحفظ:", weight="bold"),
            ft.Row([hifz_from_surah_dd, hifz_from_ayah]),
            ft.Row([hifz_to_surah_dd, hifz_to_ayah]),
            hifz_rating_dd,
            hifz_pages_field,
        ], visible=True)

        # قسم المراجعة: من سورة+آية إلى سورة+آية (بدون صفحات أيضًا)
        murajaa_from_surah_dd = ft.Dropdown(label="من سورة", options=_surah_options(), width=170)
        murajaa_from_ayah = ft.TextField(label="من آية", width=80, keyboard_type=ft.KeyboardType.NUMBER, value="1")
        murajaa_to_surah_dd = ft.Dropdown(label="إلى سورة", options=_surah_options(), width=170)
        murajaa_to_ayah = ft.TextField(label="إلى آية", width=80, keyboard_type=ft.KeyboardType.NUMBER, value="1")
        murajaa_pages_field = ft.TextField(label="عدد صفحات المراجعة (يدخلها المعلم)", width=380, keyboard_type=ft.KeyboardType.NUMBER)
        murajaa_section = ft.Column([
            ft.Text("المراجعة:", weight="bold"),
            ft.Row([murajaa_from_surah_dd, murajaa_from_ayah]),
            ft.Row([murajaa_to_surah_dd, murajaa_to_ayah]),
            murajaa_pages_field,
        ], visible=False)

        error_text = ft.Text("", color="red", size=12)

        # في وضع التعديل: نعبئ كل الحقول ببيانات الطالب المسجلة سابقًا لهذا التقرير
        existing = existing_by_student.get(student['id']) if is_edit_mode else None
        if existing:
            status_radio.value = existing.get("status") or "حاضر"
            has_hifz = bool(existing.get("hifz_sura_name"))
            has_murajaa = bool(existing.get("murajaa_sura_name"))
            recited_checkbox.value = has_hifz or has_murajaa
            if has_hifz and has_murajaa:
                recitation_type.value = "حفظ + مراجعة"
            elif has_murajaa:
                recitation_type.value = "مراجعة"
            else:
                recitation_type.value = "حفظ"
            if has_hifz:
                for opt in _surah_options():
                    if opt.text.endswith(existing["hifz_sura_name"]):
                        hifz_from_surah_dd.value = opt.key
                    if opt.text.endswith(existing.get("hifz_to_sura_name") or existing["hifz_sura_name"]):
                        hifz_to_surah_dd.value = opt.key
                hifz_from_ayah.value = str(existing.get("hifz_from_ayah") or 1)
                hifz_to_ayah.value = str(existing.get("hifz_to_ayah") or 1)
                hifz_rating_dd.value = existing.get("hifz_rating") or "جيد"
                hifz_pages_field.value = str(existing.get("hifz_pages_count") or "")
            if has_murajaa:
                for opt in _surah_options():
                    if opt.text.endswith(existing["murajaa_sura_name"]):
                        murajaa_from_surah_dd.value = opt.key
                    if opt.text.endswith(existing.get("murajaa_to_sura_name") or existing["murajaa_sura_name"]):
                        murajaa_to_surah_dd.value = opt.key
                murajaa_from_ayah.value = str(existing.get("murajaa_from_ayah") or 1)
                murajaa_to_ayah.value = str(existing.get("murajaa_to_ayah") or 1)
                murajaa_pages_field.value = str(existing.get("murajaa_pages_count") or "")

            is_present = status_radio.value in ["حاضر", "متأخر"]
            recited_checkbox.visible = is_present
            recitation_type.visible = is_present and recited_checkbox.value
            hifz_section.visible = recitation_type.visible and "حفظ" in recitation_type.value
            murajaa_section.visible = recitation_type.visible and "مراجعة" in recitation_type.value

        def update_visibility(e):
            is_present = status_radio.value in ["حاضر", "متأخر"]
            is_recited = recited_checkbox.value

            recited_checkbox.visible = is_present
            recitation_type.visible = is_present and is_recited

            if is_present and is_recited:
                hifz_section.visible = "حفظ" in recitation_type.value
                murajaa_section.visible = "مراجعة" in recitation_type.value
            else:
                hifz_section.visible = False
                murajaa_section.visible = False

            page.update()

        status_radio.on_change = update_visibility
        recited_checkbox.on_change = update_visibility
        recitation_type.on_change = update_visibility

        def parse_ayah(value, default=1):
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                return default

        def parse_positive_pages(value, field_label):
            """
            يتحقق أن قيمة عدد الصفحات المُدخلة يدويًا رقم صحيح أكبر من صفر.
            يرفع ValueError برسالة عربية واضحة لو كانت القيمة فارغة، نصًا،
            صفرًا، أو رقمًا سالبًا.
            """
            text = (value or "").strip()
            if not text:
                raise ValueError(f"الرجاء إدخال {field_label}")
            try:
                num = int(text)
            except ValueError:
                raise ValueError(f"{field_label} يجب أن يكون رقمًا صحيحًا")
            if num <= 0:
                raise ValueError(f"{field_label} يجب أن يكون أكبر من صفر")
            return num

        def build_record_and_preview(e):
            record = {
                "student_id": student['id'],
                "student_name": student['name'],
                "status": status_radio.value,
                "notes": None,
            }
            summary_lines = []

            if hifz_section.visible and hifz_from_surah_dd.value and hifz_to_surah_dd.value:
                try:
                    calc = compute_ayah_span(
                        int(hifz_from_surah_dd.value), parse_ayah(hifz_from_ayah.value, 1),
                        int(hifz_to_surah_dd.value), parse_ayah(hifz_to_ayah.value, 1),
                    )
                except InvalidAyahRangeError as ex:
                    error_text.value = f"خطأ في الحفظ: {ex}"
                    page.update()
                    return
                record["hifz_from_sura"] = calc["from_sura"]
                record["hifz_from_ayah"] = calc["from_ayah"]
                record["hifz_to_sura"] = calc["to_sura"]
                record["hifz_to_ayah"] = calc["to_ayah"]
                record["hifz_rating"] = hifz_rating_dd.value

                try:
                    hifz_pages_manual = parse_positive_pages(hifz_pages_field.value, "عدد صفحات الحفظ")
                except ValueError as ex:
                    error_text.value = str(ex)
                    page.update()
                    return
                record["hifz_pages_manual"] = hifz_pages_manual

                summary_lines.append(ft.Text("الحفظ:", weight="bold", color=AppColors.PRIMARY))
                summary_lines.append(ft.Text(f"من: {calc['from_sura_name']} - آية {calc['from_ayah']}"))
                summary_lines.append(ft.Text(f"إلى: {calc['to_sura_name']} - آية {calc['to_ayah']}"))
                summary_lines.append(ft.Text(f"عدد الآيات: {calc['ayat_count']}   |   عدد الصفحات: {hifz_pages_manual}"))
                summary_lines.append(ft.Text(f"الجزء: {calc['juz_start']}" + (f" إلى {calc['juz_end']}" if calc['juz_end'] != calc['juz_start'] else "")))
                summary_lines.append(ft.Text(f"الحزب: {calc['hizb_start']}" + (f" إلى {calc['hizb_end']}" if calc['hizb_end'] != calc['hizb_start'] else "")))
                summary_lines.append(ft.Text(f"التقييم: {hifz_rating_dd.value}"))
                summary_lines.append(ft.Divider())

            if murajaa_section.visible and murajaa_from_surah_dd.value and murajaa_to_surah_dd.value:
                try:
                    calc = compute_ayah_span(
                        int(murajaa_from_surah_dd.value), parse_ayah(murajaa_from_ayah.value, 1),
                        int(murajaa_to_surah_dd.value), parse_ayah(murajaa_to_ayah.value, 1),
                    )
                except InvalidAyahRangeError as ex:
                    error_text.value = f"خطأ في المراجعة: {ex}"
                    page.update()
                    return
                record["murajaa_from_sura"] = calc["from_sura"]
                record["murajaa_from_ayah"] = calc["from_ayah"]
                record["murajaa_to_sura"] = calc["to_sura"]
                record["murajaa_to_ayah"] = calc["to_ayah"]

                try:
                    murajaa_pages_manual = parse_positive_pages(murajaa_pages_field.value, "عدد صفحات المراجعة")
                except ValueError as ex:
                    error_text.value = str(ex)
                    page.update()
                    return
                record["murajaa_pages_manual"] = murajaa_pages_manual

                summary_lines.append(ft.Text("المراجعة:", weight="bold", color=AppColors.PRIMARY))
                summary_lines.append(ft.Text(f"من: {calc['from_sura_name']} - آية {calc['from_ayah']}"))
                summary_lines.append(ft.Text(f"إلى: {calc['to_sura_name']} - آية {calc['to_ayah']}"))
                summary_lines.append(ft.Text(f"عدد الآيات: {calc['ayat_count']}   |   عدد الصفحات: {murajaa_pages_manual}"))
                summary_lines.append(ft.Text(f"الجزء: {calc['juz_start']}" + (f" إلى {calc['juz_end']}" if calc['juz_end'] != calc['juz_start'] else "")))
                summary_lines.append(ft.Text(f"الحزب: {calc['hizb_start']}" + (f" إلى {calc['hizb_end']}" if calc['hizb_end'] != calc['hizb_start'] else "")))

            error_text.value = ""

            if not summary_lines:
                # لا يوجد حفظ ولا مراجعة (غياب أو حضور بدون تسميع) - تابع مباشرة بدون ملخص
                records.append(record)
                show_student_report(index + 1)
                return

            def edit_again(ev):
                page.dialog.open = False
                page.update()

            def confirm_and_continue(ev):
                page.dialog.open = False
                records.append(record)
                show_student_report(index + 1)

            page.dialog = ft.AlertDialog(
                title=ft.Text(f"ملخص تسميع: {student['name']}"),
                content=ft.Column(summary_lines, tight=True, scroll=ft.ScrollMode.AUTO, width=320),
                actions=[
                    ft.TextButton("تعديل", on_click=edit_again),
                    ft.ElevatedButton("تأكيد ومتابعة", on_click=confirm_and_continue, bgcolor=AppColors.PRIMARY, color="white"),
                ],
            )
            page.dialog.open = True
            page.update()

        page.add(
            ft.AppBar(title=ft.Text(f"{'تعديل تقرير' if is_edit_mode else 'تقرير'}: {student['name']}"), bgcolor=AppColors.PRIMARY, color="white"),
            ft.Container(
                content=ft.Column([
                    ft.Text(f"الطالب {index + 1} من {len(students)}", size=14, color="grey"),
                    ft.Text(student['name'], size=22, weight="bold", color=AppColors.PRIMARY),
                    ft.Divider(),
                    ft.Text("الحالة:", weight="bold"),
                    status_radio,
                    recited_checkbox,
                    recitation_type,
                    hifz_section,
                    murajaa_section,
                    error_text,
                    ft.Container(height=20),
                    ft.ElevatedButton("معاينة والمتابعة", on_click=build_record_and_preview, bgcolor=AppColors.PRIMARY, color="white", width=float("inf")),
                    ft.Container(height=10),
                    developer_footer(),
                ], scroll=ft.ScrollMode.AUTO),
                padding=20
            )
        )
        page.update()

    def finish_report():
        if is_edit_mode:
            db.update_report_records(existing_report_id, records)
            report_id = existing_report_id
        else:
            report_id = db.create_report(group_id, report_date)
            for r in records:
                r['report_id'] = report_id
                db.add_student_record(r)

        # نعيد القراءة من قاعدة البيانات حتى نحصل على القيم المحسوبة تلقائيًا
        # (عدد الآيات، الصفحات التقريبية، الجزء، الحزب) والترتيب حسب الأقوى حفظًا
        computed_records = db.get_report_records(report_id)

        pdf_status = ft.Text("", size=12, color=AppColors.TEXT_SECONDARY)

        def export_pdf(e):
            try:
                from services.pdf_service import generate_daily_report_pdf
                path = generate_daily_report_pdf(db, report_id)
                pdf_status.value = f"تم الحفظ في: {path}"
                pdf_status.color = AppColors.PRIMARY
                _try_open_file(path)
            except Exception as ex:
                pdf_status.value = f"تعذر إنشاء PDF: {ex}"
                pdf_status.color = "red"
            page.update()

        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color="green", size=100),
                    ft.Text("تم تحديث التقرير بنجاح!" if is_edit_mode else "تم الانتهاء من التقرير بنجاح!", size=20, weight="bold"),
                    ft.ElevatedButton("تحديث PDF" if is_edit_mode else "تصدير PDF لهذا اليوم", on_click=export_pdf, bgcolor=AppColors.PRIMARY, color="white"),
                    pdf_status,
                    ft.ElevatedButton("عرض التقرير النصي", on_click=lambda _: show_text_report(computed_records)),
                    ft.ElevatedButton("العودة للرئيسية", on_click=lambda _: on_back()),
                    ft.Container(height=20),
                    developer_footer(),
                ], horizontal_alignment="center"),
                alignment=ft.alignment.center, padding=50
            )
        )
        page.update()

    def show_text_report(computed_records):
        text = f"تقرير حلقة: {group['name']}\nالتاريخ: {report_date}\n\n"
        for r in computed_records:
            text += f"- {r['student_name']}: {r['status']}"
            if r.get('hifz_sura_name'):
                hifz_to = f"{r['hifz_to_sura_name']} {r['hifz_to_ayah']}" if r.get('hifz_to_sura_name') != r.get('hifz_sura_name') else str(r['hifz_to_ayah'])
                text += f"\n  الحفظ: من {r['hifz_sura_name']} {r['hifz_from_ayah']} إلى {hifz_to} - {r.get('hifz_rating') or ''}"
            if r.get('murajaa_sura_name'):
                murajaa_to = f"{r['murajaa_to_sura_name']} {r['murajaa_to_ayah']}" if r.get('murajaa_to_sura_name') != r.get('murajaa_sura_name') else str(r['murajaa_to_ayah'])
                text += f"\n  المراجعة: من {r['murajaa_sura_name']} {r['murajaa_from_ayah']} إلى {murajaa_to}"
            text += "\n"

        def close_text_report(e):
            page.dialog.open = False
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("التقرير النصي (جاهز للنسخ إلى واتساب)"),
            content=ft.TextField(value=text, multiline=True, read_only=True, min_lines=10),
            actions=[ft.TextButton("إغلاق", on_click=close_text_report)]
        )
        page.dialog.open = True
        page.update()

    start_reporting()


def _try_open_file(path):
    """محاولة فتح الملف تلقائيًا بعد إنشائه (اختياري، لا تؤثر على باقي التطبيق إن فشلت)."""
    import os
    import platform
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass
