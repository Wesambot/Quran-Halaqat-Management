import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors
from utils.components import developer_footer

def welcome_view(page: ft.Page, db: DBManager, on_complete):
    page.clean()
    page.rtl = True
    page.bgcolor = AppColors.BACKGROUND

    teacher_name_field = ft.TextField(
        label="اسم الأستاذ",
        value="المهندس وسام",
        border_radius=10,
        focused_border_color=AppColors.PRIMARY,
        prefix_icon=ft.icons.PERSON,
    )

    phone_field = ft.TextField(
        label="رقم الهاتف",
        value="",
        border_radius=10,
        focused_border_color=AppColors.PRIMARY,
        prefix_icon=ft.icons.PHONE,
        keyboard_type=ft.KeyboardType.PHONE,
    )

    def save_and_continue(e):
        if not teacher_name_field.value or not phone_field.value:
            page.snack_bar = ft.SnackBar(ft.Text("يرجى ملء جميع الحقول"))
            page.snack_bar.open = True
            page.update()
            return
        
        db.update_settings(teacher_name_field.value, phone_field.value, 0)
        on_complete()

    content = ft.Column(
        [
            ft.Container(height=50),
            ft.Icon(ft.icons.MENU_BOOK_ROUNDED, size=100, color=AppColors.PRIMARY),
            ft.Text("مرحباً بك في نظام إدارة الحلقات", size=24, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            ft.Text("يرجى إعداد بياناتك الأساسية للبدء", size=16, color="#666666", text_align="center"),
            ft.Container(height=20),
            teacher_name_field,
            ft.Container(height=10),
            phone_field,
            ft.Container(height=30),
            ft.ElevatedButton(
                "ابدأ الآن",
                icon=ft.icons.ARROW_FORWARD,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=AppColors.PRIMARY,
                    padding=20,
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                on_click=save_and_continue,
                width=200,
            ),
            ft.Container(height=30),
            developer_footer(),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.add(
        ft.Container(
            content=content,
            alignment=ft.alignment.center,
            padding=20,
        )
    )
    page.update()
