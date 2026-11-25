import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors
from utils.components import developer_footer, DEVELOPER_NAME

APP_VERSION = "1.1.0"


def about_view(page: ft.Page, db: DBManager, on_back):
    page.clean()
    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("حول التطبيق"),
            bgcolor=AppColors.PRIMARY,
            color="white",
            center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.MENU_BOOK_ROUNDED, size=70, color=AppColors.PRIMARY),
                ft.Text("نظام إدارة الحلقات القرآنية", size=20, weight="bold", color=AppColors.PRIMARY),
                ft.Text(f"الإصدار {APP_VERSION}", size=14, color=AppColors.TEXT_SECONDARY),
                ft.Divider(),
                ft.Text(
                    "تطبيق لإدارة حلقات تحفيظ القرآن الكريم: تسجيل الحضور والحفظ والمراجعة، "
                    "وإصدار تقارير يومية وأسبوعية وشهرية بصيغة PDF.",
                    text_align="center", size=13,
                ),
                ft.Divider(),
                ft.ListTile(leading=ft.Icon(ft.icons.PERSON), title=ft.Text("المطور"), subtitle=ft.Text(DEVELOPER_NAME)),
                ft.ListTile(leading=ft.Icon(ft.icons.COPYRIGHT), title=ft.Text(f"جميع الحقوق محفوظة © {2026}")),
                ft.Container(height=10),
                developer_footer(),
            ], horizontal_alignment="center", scroll=ft.ScrollMode.AUTO),
            padding=25,
        )
    )
    page.update()
