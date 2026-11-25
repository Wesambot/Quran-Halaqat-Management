import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors
from utils.components import developer_footer
from services.date_service import DateService as DS


BADGE_COLORS = {
    "📖": "#1976D2", "🔁": "#00897B", "🔥": "#E64A19", "📅": "#7B1FA2",
    "⭐": "#F9A825", "🥇": "#FFD700", "🥈": "#C0C0C0", "🥉": "#CD7F32",
}


def _badge_color(achievement_type: str) -> str:
    for emoji, color in BADGE_COLORS.items():
        if achievement_type.startswith(emoji):
            return color
    return AppColors.PRIMARY


def achievements_view(page: ft.Page, db: DBManager, on_back):
    page.clean()
    groups = db.get_groups()

    if not groups:
        page.add(
            ft.AppBar(leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
                      title=ft.Text("الإنجازات"), bgcolor=AppColors.PRIMARY, color="white"),
            ft.Container(ft.Text("أضف حلقة أولاً."), padding=20),
        )
        page.update()
        return

    state = {"group_id": groups[0]['id'], "week_anchor": DS.today()}
    body = ft.Container(padding=20)

    def render():
        body.content = build_body()
        page.update()

    def build_body():
        group_dd = ft.Dropdown(
            label="الحلقة",
            options=[ft.dropdown.Option(key=str(g['id']), text=g['name']) for g in groups],
            value=str(state["group_id"]), width=float("inf"),
        )

        def on_group_change(e):
            state["group_id"] = int(group_dd.value)
            render()
        group_dd.on_change = on_group_change

        def go_week(delta):
            from datetime import timedelta
            state["week_anchor"] = state["week_anchor"] + timedelta(weeks=delta)
            render()

        week_start = DS.week_start(state["week_anchor"])
        week_end = DS.week_end(state["week_anchor"])
        period_label = f"أسبوع {DS.to_db_format(week_start)}"

        week_picker = ft.Column([
            ft.Text(DS.format_week_range_arabic(state["week_anchor"]), size=16, weight="bold", color=AppColors.PRIMARY, text_align="center"),
            ft.Row([
                ft.IconButton(ft.icons.ARROW_FORWARD_IOS, on_click=lambda e: go_week(-1)),
                ft.TextButton("هذا الأسبوع", on_click=lambda e: (state.__setitem__("week_anchor", DS.today()), render())),
                ft.IconButton(ft.icons.ARROW_BACK_IOS, on_click=lambda e: go_week(1)),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment="center")

        def compute(e):
            db.compute_and_store_achievements(
                state["group_id"], DS.to_db_format(week_start), DS.to_db_format(week_end), period_label
            )
            render()

        # عرض الإنجازات الحالية لكل طلاب هذه الحلقة لهذه الفترة تحديدًا
        students = db.get_students_by_group(state["group_id"])
        cards = []
        for s in students:
            student_achievements = [
                a for a in db.get_student_achievements(s['id']) if a['period_label'] == period_label
            ]
            if not student_achievements:
                continue
            cards.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(s['name'], weight="bold", size=16),
                            ft.Row(
                                [ft.Container(
                                    content=ft.Text(a['type'], color="white", size=12),
                                    bgcolor=_badge_color(a['type']),
                                    padding=8, border_radius=20,
                                 ) for a in student_achievements],
                                wrap=True,
                            ),
                        ]),
                        padding=15,
                    ),
                    elevation=2,
                )
            )

        results_section = ft.Column(cards) if cards else ft.Text(
            "لا توجد إنجازات محسوبة لهذا الأسبوع بعد - اضغط \"احسب إنجازات الأسبوع\".",
            size=12, color=AppColors.TEXT_SECONDARY, text_align="center",
        )

        return ft.Column([
            group_dd,
            ft.Container(height=10),
            week_picker,
            ft.Container(height=10),
            ft.ElevatedButton(
                "احسب إنجازات هذا الأسبوع", icon=ft.icons.EMOJI_EVENTS,
                bgcolor=AppColors.PRIMARY, color="white", width=float("inf"),
                on_click=compute,
            ),
            ft.Divider(),
            results_section,
            ft.Container(height=10),
            developer_footer(),
        ], scroll=ft.ScrollMode.AUTO)

    body.content = build_body()
    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("الإنجازات"),
            bgcolor=AppColors.PRIMARY, color="white", center_title=True,
        ),
        body,
    )
    page.update()
