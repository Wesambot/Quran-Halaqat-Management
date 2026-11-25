import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors, AppStyles
from utils.components import developer_footer

def groups_view(page: ft.Page, db: DBManager, on_back):
    page.clean()
    
    def group_form_dialog(e=None, existing_group=None):
        is_edit = existing_group is not None
        name_field = ft.TextField(label="اسم الحلقة", border_radius=10,
                                   value=existing_group['name'] if is_edit else "")
        type_dropdown = ft.Dropdown(
            label="نوع الحلقة",
            options=[
                ft.dropdown.Option("حفظ"),
                ft.dropdown.Option("مراجعة"),
                ft.dropdown.Option("تلقين"),
            ],
            border_radius=10,
            value=existing_group['type'] if is_edit else "حفظ"
        )

        days = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        existing_days = existing_group['study_days'].split(",") if is_edit else days
        day_checkboxes = [ft.Checkbox(label=day, value=(day in existing_days)) for day in days]

        error_text = ft.Text("", color="red", size=12)

        def save_group(e):
            selected_days = [cb.label for cb in day_checkboxes if cb.value]
            if not name_field.value or not name_field.value.strip():
                error_text.value = "الرجاء إدخال اسم الحلقة"
                error_text.update()
                return
            if not selected_days:
                error_text.value = "الرجاء اختيار يوم دراسة واحد على الأقل"
                error_text.update()
                return

            try:
                if is_edit:
                    db.update_group(existing_group['id'], name_field.value.strip(), type_dropdown.value, selected_days)
                else:
                    db.add_group(name_field.value.strip(), type_dropdown.value, selected_days)
            except Exception as ex:
                error_text.value = f"تعذر حفظ الحلقة: {ex}"
                error_text.update()
                return

            dialog.open = False
            msg = "تم تعديل" if is_edit else "تم حفظ"
            page.snack_bar = ft.SnackBar(ft.Text(f"{msg} حلقة \"{name_field.value.strip()}\" بنجاح ✅"), bgcolor=AppColors.PRIMARY)
            page.snack_bar.open = True
            groups_view(page, db, on_back)

        def cancel_group_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("تعديل الحلقة" if is_edit else "إضافة حلقة جديدة"),
            content=ft.Column([
                name_field,
                type_dropdown,
                ft.Text("أيام الدراسة:"),
                ft.Column(day_checkboxes, scroll=ft.ScrollMode.AUTO, height=150),
                error_text,
            ], tight=True, width=300),
            actions=[
                ft.TextButton("إلغاء", on_click=cancel_group_dialog),
                ft.ElevatedButton("حفظ", on_click=save_group, bgcolor=AppColors.PRIMARY, color="white"),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def delete_group(group_id, group_name):
        def cancel_delete_group(e):
            confirm_dialog.open = False
            page.update()

        def confirm_delete(e):
            confirm_dialog.open = False
            try:
                db.delete_group(group_id)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"تعذر حذف الحلقة: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            groups_view(page, db, on_back)

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("تأكيد الحذف"),
            content=ft.Text(f"هل أنت متأكد من حذف حلقة \"{group_name}\"؟ سيتم حذف كل طلابها وتقاريرها أيضًا."),
            actions=[
                ft.TextButton("إلغاء", on_click=cancel_delete_group),
                ft.ElevatedButton("حذف", on_click=confirm_delete, bgcolor="red", color="white"),
            ],
        )
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    groups = db.get_groups()
    
    groups_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    for g in groups:
        groups_list.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.PEOPLE, color=AppColors.PRIMARY),
                            title=ft.Text(g['name'], weight="bold"),
                            subtitle=ft.Text(f"النوع: {g['type']} | الطلاب: {g['student_count']}"),
                            trailing=ft.PopupMenuButton(
                                items=[
                                    ft.PopupMenuItem(text="تعديل", icon=ft.icons.EDIT,
                                                      on_click=lambda _, grp=g: group_form_dialog(existing_group=grp)),
                                    ft.PopupMenuItem(text="حذف", icon=ft.icons.DELETE, on_click=lambda _, gid=g['id'], gname=g['name']: delete_group(gid, gname)),
                                ]
                            ),
                            on_click=lambda _, gid=g['id']: show_students(gid)
                        ),
                    ]),
                    padding=10
                ),
                **AppStyles.CARD_STYLE
            )
        )

    def show_students(group_id):
        from views.students_view import students_view
        students_view(page, db, group_id, lambda: groups_view(page, db, on_back))

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("إدارة الحلقات"),
            bgcolor=AppColors.PRIMARY,
            color="white",
            center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("الحلقات المسجلة", size=20, weight="bold", color=AppColors.PRIMARY),
                groups_list,
                ft.FloatingActionButton(
                    icon=ft.icons.ADD,
                    bgcolor=AppColors.PRIMARY,
                    on_click=group_form_dialog,
                    tooltip="إضافة حلقة"
                ),
                developer_footer(),
            ], expand=True),
            padding=20,
            expand=True
        )
    )
    page.update()
