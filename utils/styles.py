import flet as ft

class AppColors:
    PRIMARY = "#2E7D32" # أخضر غامق
    SECONDARY = "#4CAF50" # أخضر فاتح
    BACKGROUND = "#F5F5F5" # رمادي فاتح جداً
    SURFACE = "#FFFFFF" # أبيض
    TEXT = "#212121" # أسود/رمادي غامق
    TEXT_SECONDARY = "#757575" # رمادي
    ERROR = "#D32F2F" # أحمر

class AppStyles:
    # ملاحظة: نسخ Flet الحديثة لم تعد تقبل border_radius مباشرة على Card،
    # بل تستخدم shape بدلاً منها. هذا هو مكان الإصلاح الوحيد اللازم لكل الشاشات.
    CARD_STYLE = {
        "elevation": 2,
        "shape": ft.RoundedRectangleBorder(radius=15),
        "color": AppColors.SURFACE,
    }
    
    TITLE_STYLE = ft.TextStyle(
        size=20,
        weight=ft.FontWeight.BOLD,
        color=AppColors.PRIMARY,
    )
    
    SUBTITLE_STYLE = ft.TextStyle(
        size=16,
        color=AppColors.TEXT_SECONDARY,
    )
