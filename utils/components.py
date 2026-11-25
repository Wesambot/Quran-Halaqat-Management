import flet as ft
from utils.styles import AppColors

# بيانات المبرمج الثابتة (غير قابلة للتعديل من داخل التطبيق، بخلاف
# اسم/رقم "الأستاذ" في الإعدادات وهي بيانات مستخدم التطبيق نفسه).
DEVELOPER_NAME = "المهندس وسام"


def developer_footer() -> ft.Container:
    """
    فوتر ثابت يظهر أسفل كل شاشة في التطبيق ويعرض اسم المبرمج دون بيانات اتصال شخصية.
    أضِفه كآخر عنصر في أي Column يتم عرضه في الصفحة.
    """
    return ft.Container(
        content=ft.Text(
            f"تطوير: {DEVELOPER_NAME}",
            size=11,
            color=AppColors.TEXT_SECONDARY,
            text_align="center",
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=8, bottom=4),
    )
