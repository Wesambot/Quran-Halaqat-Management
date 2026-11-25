import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors
from utils.components import developer_footer


def settings_view(page: ft.Page, db: DBManager, on_back):
    page.clean()
    settings = db.get_settings()

    name_field = ft.TextField(label="اسم الأستاذ", value=settings['teacher_name'], border_radius=10)
    phone_field = ft.TextField(label="رقم الهاتف", value=settings['phone_number'], border_radius=10)
    dark_mode_switch = ft.Switch(value=bool(settings['dark_mode']))

    def save_settings(e):
        db.update_settings(name_field.value, phone_field.value, 0)
        page.snack_bar = ft.SnackBar(ft.Text("تم حفظ الإعدادات بنجاح"))
        page.snack_bar.open = True
        page.update()

    def toggle_dark_mode(e):
        db.set_dark_mode(dark_mode_switch.value)
        page.theme_mode = ft.ThemeMode.DARK if dark_mode_switch.value else ft.ThemeMode.LIGHT
        page.bgcolor = None if dark_mode_switch.value else AppColors.BACKGROUND
        page.update()

    def open_about(e):
        from views.about_view import about_view
        about_view(page, db, lambda: settings_view(page, db, on_back))

    dark_mode_switch.on_change = toggle_dark_mode

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("الإعدادات"),
            bgcolor=AppColors.PRIMARY,
            color="white",
            center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("تعديل البيانات الأساسية", size=18, weight="bold"),
                name_field,
                phone_field,
                ft.ElevatedButton("حفظ التغييرات", on_click=save_settings, bgcolor=AppColors.PRIMARY, color="white", width=float("inf")),
                ft.Divider(),
                ft.Text("خيارات إضافية", size=18, weight="bold"),
                ft.ListTile(leading=ft.Icon(ft.icons.BACKUP), title=ft.Text("نسخة احتياطية (قريباً)")),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.BRIGHTNESS_4),
                    title=ft.Text("الوضع الليلي"),
                    trailing=dark_mode_switch,
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.INFO_OUTLINE),
                    title=ft.Text("حول التطبيق"),
                    on_click=open_about,
                ),
                ft.Container(height=10),
                developer_footer(),
            ]),
            padding=20
        )
    )
    page.update()
