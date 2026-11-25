import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors, AppStyles
from utils.components import developer_footer

def stats_view(page: ft.Page, db: DBManager, on_back):
    page.clean()
    
    # هذه الشاشة ستعرض إحصائيات عامة
    # للتبسيط، سنعرض إحصائيات الحضور والغياب الإجمالية
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) as count FROM attendance GROUP BY status')
        rows = cursor.fetchall()
        status_counts = {row['status']: row['count'] for row in rows}

    def create_stat_card(label, value, color):
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(label, size=16, weight="bold"),
                    ft.Text(str(value), size=30, color=color, weight="bold")
                ], horizontal_alignment="center"),
                padding=20, width=150
            ),
            **AppStyles.CARD_STYLE
        )

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("الإحصائيات العامة"),
            bgcolor=AppColors.PRIMARY,
            color="white",
            center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("ملخص الحضور والغياب", size=20, weight="bold"),
                ft.Row([
                    create_stat_card("حاضر", status_counts.get("حاضر", 0), "green"),
                    create_stat_card("غائب", status_counts.get("غائب", 0), "red"),
                ], alignment="center"),
                ft.Row([
                    create_stat_card("متأخر", status_counts.get("متأخر", 0), "orange"),
                    create_stat_card("مستأذن", status_counts.get("مستأذن", 0), "blue"),
                ], alignment="center"),
                ft.Divider(),
                ft.Text("الإحصائيات المتقدمة والرسوم البيانية قيد التطوير...", italic=True, color="grey"),
                ft.Container(height=10),
                developer_footer(),
            ], horizontal_alignment="center"),
            padding=20
        )
    )
    page.update()
