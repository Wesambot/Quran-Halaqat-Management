import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors
from utils.components import developer_footer
from services.date_service import DateService as DS


def _try_open_file(path):
    import os, platform
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


def reports_export_view(page: ft.Page, db: DBManager, on_back):
    """
    الصفحة المركزية "التقارير": اختيار نوع التقرير (يومي/أسبوعي/شهري/سنوي)،
    ثم أداة اختيار الفترة المناسبة، ثم بطاقة ملخص الفترة، ثم زر التنفيذ.
    - اليومي: يفتح تقرير اليوم المُختار (مع اكتشاف التكرار والتعديل).
    - الأسبوعي/الشهري/السنوي: يُصدر PDF مباشرة لنفس الفترة المعروضة بالضبط.
    """
    page.clean()
    groups = db.get_groups()

    if not groups:
        page.add(
            ft.AppBar(leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
                      title=ft.Text("التقارير"), bgcolor=AppColors.PRIMARY, color="white"),
            ft.Container(ft.Text("أضف حلقة أولاً لإصدار التقارير."), padding=20),
        )
        page.update()
        return

    state = {
        "mode": "يومي",
        "group_id": groups[0]['id'],
        "day": DS.today(),
        "week_anchor": DS.today(),
        "year": DS.today().year,
        "month": DS.today().month,
        "yearly_year": DS.today().year,
    }

    body_container = ft.Container(padding=20)

    def current_group():
        return db.get_group_by_id(state["group_id"])

    def build_period_range():
        """يرجع (start_date, end_date, عنوان نوع التقرير, نص الفترة بالعربية)."""
        if state["mode"] == "يومي":
            d = state["day"]
            return d, d, "تقرير يومي", DS.format_date_arabic(d)
        elif state["mode"] == "أسبوعي":
            d = state["week_anchor"]
            return DS.week_start(d), DS.week_end(d), "تقرير أسبوعي", DS.format_week_range_arabic(d)
        elif state["mode"] == "شهري":
            y, m = state["year"], state["month"]
            return DS.month_start(y, m), DS.month_end(y, m), "تقرير شهري", DS.format_month_arabic(y, m)
        else:
            y = state["yearly_year"]
            return DS.year_start(y), DS.year_end(y), "تقرير سنوي", DS.format_year(y)

    def render():
        body_container.content = build_body()
        page.update()

    def build_mode_switcher():
        def set_mode(m):
            state["mode"] = m
            render()

        def mode_button(label, key):
            selected = state["mode"] == key
            return ft.ElevatedButton(
                label,
                on_click=lambda e, k=key: set_mode(k),
                bgcolor=AppColors.PRIMARY if selected else "#E0E0E0",
                color="white" if selected else AppColors.TEXT,
            )

        return ft.Row(
            [mode_button("اليومي", "يومي"), mode_button("الأسبوعي", "أسبوعي"),
             mode_button("الشهري", "شهري"), mode_button("السنوي", "سنوي")],
            alignment=ft.MainAxisAlignment.CENTER, wrap=True,
        )

    def build_group_selector():
        dd = ft.Dropdown(
            label="الحلقة",
            options=[ft.dropdown.Option(key=str(g['id']), text=g['name']) for g in groups],
            value=str(state["group_id"]),
            width=float("inf"),
        )

        def on_change(e):
            state["group_id"] = int(dd.value)
            render()

        dd.on_change = on_change
        return dd

    # -------------------------------------------------------------------
    # أداة اختيار الفترة حسب النوع
    # -------------------------------------------------------------------
    def build_day_picker():
        date_field = ft.TextField(label="التاريخ (YYYY-MM-DD)", value=DS.to_db_format(state["day"]), width=200)

        def go(delta_days):
            from datetime import timedelta
            state["day"] = state["day"] + timedelta(days=delta_days)
            render()

        def go_today(e):
            state["day"] = DS.today()
            render()

        def apply_typed_date(e):
            try:
                state["day"] = DS.from_db_format(date_field.value.strip())
            except Exception:
                page.snack_bar = ft.SnackBar(ft.Text("صيغة التاريخ غير صحيحة، استخدم YYYY-MM-DD"), bgcolor="red")
                page.snack_bar.open = True
            render()

        return ft.Column([
            ft.Text(DS.format_date_arabic(state["day"]), size=18, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            ft.Row([
                ft.IconButton(ft.icons.ARROW_FORWARD_IOS, tooltip="اليوم السابق", on_click=lambda e: go(-1)),
                ft.TextButton("اليوم", on_click=go_today),
                ft.IconButton(ft.icons.ARROW_BACK_IOS, tooltip="اليوم التالي", on_click=lambda e: go(1)),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([date_field, ft.IconButton(ft.icons.CHECK, on_click=apply_typed_date, tooltip="تطبيق التاريخ")],
                   alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment="center")

    def build_week_picker():
        from services.date_service import ARABIC_DAY_NAMES

        def go(delta_weeks):
            from datetime import timedelta
            state["week_anchor"] = state["week_anchor"] + timedelta(weeks=delta_weeks)
            render()

        def go_this_week(e):
            state["week_anchor"] = DS.today()
            render()

        days = DS.week_days(state["week_anchor"])
        days_text = "  ".join(f"{ARABIC_DAY_NAMES[d.weekday()]} {d.day}" for d in days)

        return ft.Column([
            ft.Text(DS.format_week_range_arabic(state["week_anchor"]), size=18, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            ft.Row([
                ft.IconButton(ft.icons.ARROW_FORWARD_IOS, tooltip="الأسبوع السابق", on_click=lambda e: go(-1)),
                ft.TextButton("هذا الأسبوع", on_click=go_this_week),
                ft.IconButton(ft.icons.ARROW_BACK_IOS, tooltip="الأسبوع التالي", on_click=lambda e: go(1)),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Text(days_text, size=11, color=AppColors.TEXT_SECONDARY, text_align="center"),
        ], horizontal_alignment="center")

    def build_month_picker():
        from services.date_service import ARABIC_MONTH_NAMES
        year_field = ft.TextField(label="السنة", value=str(state["year"]), width=120, keyboard_type=ft.KeyboardType.NUMBER)
        month_dd = ft.Dropdown(
            label="الشهر", width=160,
            options=[ft.dropdown.Option(key=str(m), text=ARABIC_MONTH_NAMES[m]) for m in range(1, 13)],
            value=str(state["month"]),
        )

        def apply_change(e):
            try:
                state["year"] = int(year_field.value)
                state["month"] = int(month_dd.value)
            except (TypeError, ValueError):
                pass
            render()

        year_field.on_blur = apply_change
        month_dd.on_change = apply_change

        return ft.Column([
            ft.Text(DS.format_month_arabic(state["year"], state["month"]), size=18, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            ft.Row([year_field, month_dd], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment="center")

    def build_year_picker():
        year_field = ft.TextField(label="السنة", value=str(state["yearly_year"]), width=150, keyboard_type=ft.KeyboardType.NUMBER)

        def apply_change(e):
            try:
                state["yearly_year"] = int(year_field.value)
            except (TypeError, ValueError):
                pass
            render()

        year_field.on_blur = apply_change

        return ft.Column([
            ft.Text(DS.format_year(state["yearly_year"]), size=22, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            year_field,
        ], horizontal_alignment="center")

    # -------------------------------------------------------------------
    # بطاقة ملخص الفترة + زر التنفيذ
    # -------------------------------------------------------------------
    def build_summary_and_action():
        start, end, type_label, period_label = build_period_range()
        group = current_group()
        settings = db.get_settings()
        students = db.get_students_by_group(group['id'])
        study_days = group['study_days'].split(",") if group['study_days'] else []
        study_days_count = DS.count_study_days_in_range(study_days, start, end)

        summary_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"نوع التقرير: {type_label}", weight="bold"),
                    ft.Text(f"الفترة: {period_label}"),
                    ft.Text(f"الحلقة: {group['name']}"),
                    ft.Text(f"الأستاذ: {settings['teacher_name']}"),
                    ft.Text(f"عدد أيام الدراسة بالفترة: {study_days_count}"),
                    ft.Text(f"عدد الطلاب: {len(students)}"),
                ]),
                padding=15,
            ),
            elevation=2,
        )

        status_text = ft.Text("", size=12)

        if state["mode"] == "يومي":
            action_button = ft.ElevatedButton(
                "فتح / إنشاء تقرير هذا اليوم", icon=ft.icons.ASSIGNMENT,
                bgcolor=AppColors.PRIMARY, color="white", width=float("inf"),
                on_click=lambda e: handle_daily_action(start),
            )
        else:
            def export(e):
                try:
                    if state["mode"] == "أسبوعي":
                        from services.pdf_service import generate_weekly_report_pdf
                        path = generate_weekly_report_pdf(db, group['id'], DS.to_db_format(start), DS.to_db_format(end))
                    elif state["mode"] == "شهري":
                        from services.pdf_service import generate_monthly_report_pdf
                        path = generate_monthly_report_pdf(db, group['id'], state["year"], state["month"])
                    else:
                        from services.pdf_service import generate_yearly_report_pdf
                        path = generate_yearly_report_pdf(db, group['id'], state["yearly_year"])
                    status_text.value = f"تم إنشاء التقرير:\n{path}"
                    status_text.color = AppColors.PRIMARY
                    _try_open_file(path)
                except Exception as ex:
                    status_text.value = f"تعذر إنشاء التقرير: {ex}"
                    status_text.color = "red"
                page.update()

            action_button = ft.ElevatedButton(
                "إنشاء التقرير (PDF)", icon=ft.icons.PICTURE_AS_PDF,
                bgcolor=AppColors.PRIMARY, color="white", width=float("inf"),
                on_click=export,
            )

        return ft.Column([summary_card, ft.Container(height=10), action_button, status_text])

    def handle_daily_action(day):
        group_id = state["group_id"]
        date_str = DS.to_db_format(day)
        existing = db.get_report_by_group_and_date(group_id, date_str)

        if not existing:
            from views.report_view import report_view
            report_view(page, db, group_id, lambda: reports_export_view(page, db, on_back), report_date=date_str)
            return

        def open_readonly(e):
            close_dialog(e)
            records = db.get_report_records(existing['id'])
            text = "\n".join(f"{r['student_name']}: {r['status']}" for r in records)
            page.dialog = ft.AlertDialog(
                title=ft.Text(f"تقرير {date_str}"),
                content=ft.Text(text or "لا توجد سجلات"),
                actions=[ft.TextButton("إغلاق", on_click=close_dialog)],
            )
            page.dialog.open = True
            page.update()

        def edit_report(e):
            close_dialog(e)
            from views.report_view import report_view
            report_view(page, db, group_id, lambda: reports_export_view(page, db, on_back),
                        existing_report_id=existing['id'], report_date=date_str)

        def regenerate_pdf(e):
            close_dialog(e)
            try:
                from services.pdf_service import generate_daily_report_pdf
                path = generate_daily_report_pdf(db, existing['id'])
                page.snack_bar = ft.SnackBar(ft.Text(f"تم إنشاء PDF: {path}"), bgcolor=AppColors.PRIMARY)
                page.snack_bar.open = True
                _try_open_file(path)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"تعذر إنشاء PDF: {ex}"), bgcolor="red")
                page.snack_bar.open = True
            page.update()

        def close_dialog(e):
            page.dialog.open = False
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text("يوجد تقرير لهذا اليوم بالفعل"),
            content=ft.Text(f"تم تسجيل تقرير لهذه الحلقة بتاريخ {DS.format_date_short_arabic(day)} من قبل."),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.TextButton("فتح التقرير", on_click=open_readonly),
                ft.TextButton("إعادة إنشاء PDF", on_click=regenerate_pdf),
                ft.ElevatedButton("تعديل التقرير", on_click=edit_report, bgcolor=AppColors.PRIMARY, color="white"),
            ],
        )
        page.dialog.open = True
        page.update()

    def build_body():
        picker = {
            "يومي": build_day_picker,
            "أسبوعي": build_week_picker,
            "شهري": build_month_picker,
            "سنوي": build_year_picker,
        }[state["mode"]]()

        return ft.Column([
            build_mode_switcher(),
            ft.Divider(),
            build_group_selector(),
            ft.Container(height=10),
            picker,
            ft.Divider(),
            build_summary_and_action(),
            ft.Container(height=10),
            developer_footer(),
        ], scroll=ft.ScrollMode.AUTO)

    body_container.content = build_body()

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("التقارير"),
            bgcolor=AppColors.PRIMARY, color="white", center_title=True,
        ),
        body_container,
    )
    page.update()
