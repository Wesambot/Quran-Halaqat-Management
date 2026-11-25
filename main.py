import flet as ft
from database.db_manager import DBManager, DatabaseError
from views.welcome_view import welcome_view
from views.groups_view import groups_view
from views.report_view import report_view
from views.stats_view import stats_view
from views.settings_view import settings_view
from utils.styles import AppColors, AppStyles
from utils.components import developer_footer


def show_fatal_error(page: ft.Page, message: str):
    """تعرض شاشة خطأ واضحة داخل التطبيق بدل انهيار البرنامج بالكامل."""
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.ERROR_OUTLINE, color="red", size=80),
                    ft.Text("حدث خطأ في تشغيل التطبيق", size=20, weight="bold", color="red"),
                    ft.Text(message, size=14, color="#555555", selectable=True, text_align="center"),
                ],
                horizontal_alignment="center",
                spacing=15,
            ),
            alignment=ft.alignment.center,
            padding=30,
            expand=True,
        )
    )
    page.update()


def main(page: ft.Page):
    page.title = "نظام إدارة الحلقات القرآنية"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.rtl = True
    page.window.width = 450
    page.window.height = 850
    page.bgcolor = AppColors.BACKGROUND

    # تهيئة قاعدة البيانات (مع مسار تخزين صحيح لكل نظام تشغيل)
    try:
        db = DBManager()
    except DatabaseError as e:
        show_fatal_error(page, str(e))
        return

    # تطبيق الوضع الليلي المحفوظ من التشغيل السابق
    saved_settings = db.get_settings()
    if saved_settings.get('dark_mode'):
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = None

    def check_daily_reminders():
        """
        يفحص عند كل فتح للتطبيق: هل يوجد حلقات "اليوم" (حسب أيام دراستها)
        لم يُسجَّل لها تقرير بعد؟ هذا تذكير عند فتح التطبيق فقط (وليس
        إشعار نظام حقيقي في الخلفية، لأن Flet Desktop لا يوفر ذلك بسهولة
        عبر كل الأنظمة)، لكنه يذكّر المعلم فورًا في كل مرة يفتح البرنامج.
        """
        from services.date_service import DateService as DS, ARABIC_DAY_NAMES
        today = DS.today()
        today_name = ARABIC_DAY_NAMES[today.weekday()]
        today_str = DS.to_db_format(today)
        missing = []
        for g in db.get_groups():
            study_days = g['study_days'].split(",") if g['study_days'] else []
            if today_name in study_days and not db.get_report_by_group_and_date(g['id'], today_str):
                missing.append(g['name'])
        return missing

    def show_main_dashboard():
        page.clean()
        settings = db.get_settings()
        stats = db.get_stats()
        reminder_groups = check_daily_reminders()
        
        def navigate_to_groups(e):
            groups_view(page, db, show_main_dashboard)

        def navigate_to_stats(e):
            stats_view(page, db, show_main_dashboard)

        def navigate_to_settings(e):
            settings_view(page, db, show_main_dashboard)

        def navigate_to_reports_export(e):
            from views.reports_export_view import reports_export_view
            reports_export_view(page, db, show_main_dashboard)

        def navigate_to_achievements(e):
            from views.achievements_view import achievements_view
            achievements_view(page, db, show_main_dashboard)

        def start_daily_report(e):
            from views.reports_export_view import reports_export_view
            reports_export_view(page, db, show_main_dashboard)

        page.add(
            ft.AppBar(
                title=ft.Text("نظام إدارة الحلقات", color="white", weight="bold"),
                bgcolor=AppColors.PRIMARY,
                center_title=True,
                actions=[
                    ft.IconButton(ft.icons.SETTINGS, icon_color="white", on_click=navigate_to_settings)
                ]
            ),
            ft.Container(
                content=ft.Column([
                    # تذكير يومي: حلقات اليوم التي لم يُسجَّل لها تقرير بعد
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.NOTIFICATIONS_ACTIVE, color="white"),
                            ft.Text(
                                "تذكير: لم يُسجَّل تقرير اليوم للحلقات: " + "، ".join(reminder_groups),
                                color="white", size=13, expand=True,
                            ),
                        ]),
                        bgcolor="#F57C00", padding=12, border_radius=8,
                        visible=bool(reminder_groups),
                    ),
                    ft.Container(height=10 if reminder_groups else 0),
                    # كرت الترحيب
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.ListTile(
                                    leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE, size=40, color=AppColors.PRIMARY),
                                    title=ft.Text(f"الأستاذ: {settings['teacher_name']}", size=18, weight="bold"),
                                    subtitle=ft.Text(f"رقم الهاتف: {settings['phone_number']}"),
                                ),
                            ]),
                            padding=10
                        ),
                        **AppStyles.CARD_STYLE
                    ),
                    
                    ft.Row([
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text("الحلقات", weight="bold"),
                                    ft.Text(str(stats['groups']), size=25, color=AppColors.PRIMARY, weight="bold")
                                ], horizontal_alignment="center"),
                                padding=20, width=150,
                                ink=True,
                                on_click=navigate_to_groups
                            ),
                            **AppStyles.CARD_STYLE,
                        ),
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text("الطلاب", weight="bold"),
                                    ft.Text(str(stats['students']), size=25, color=AppColors.PRIMARY, weight="bold")
                                ], horizontal_alignment="center"),
                                padding=20, width=150,
                                ink=True,
                                on_click=navigate_to_groups
                            ),
                            **AppStyles.CARD_STYLE,
                        ),
                    ], alignment="center"),
                    
                    ft.Container(height=20),
                    
                    ft.ElevatedButton(
                        "إدارة الحلقات والطلاب",
                        icon=ft.icons.PEOPLE,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor=AppColors.PRIMARY,
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=navigate_to_groups,
                        width=float("inf")
                    ),
                    
                    ft.Container(height=10),
                    
                    ft.ElevatedButton(
                        "بدء التقرير اليومي",
                        icon=ft.icons.ASSIGNMENT,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor=AppColors.SECONDARY,
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=start_daily_report,
                        width=float("inf")
                    ),

                    ft.Container(height=10),
                    
                    ft.ElevatedButton(
                        "الإحصائيات العامة",
                        icon=ft.icons.BAR_CHART,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor=ft.colors.BLUE_GREY_700,
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=navigate_to_stats,
                        width=float("inf")
                    ),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "تصدير تقارير أسبوعية / شهرية PDF",
                        icon=ft.icons.PICTURE_AS_PDF,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor=AppColors.PRIMARY,
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=navigate_to_reports_export,
                        width=float("inf")
                    ),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "الإنجازات",
                        icon=ft.icons.EMOJI_EVENTS,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor="#F9A825",
                            padding=20,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=navigate_to_achievements,
                        width=float("inf")
                    ),
                    ft.Container(height=10),
                    developer_footer(),
                ]),
                padding=20
            )
        )
        page.update()

    # التحقق من التشغيل الأول
    settings = db.get_settings()
    if settings['is_first_run'] == 1:
        welcome_view(page, db, show_main_dashboard)
    else:
        show_main_dashboard()

if __name__ == "__main__":
    ft.app(target=main)
