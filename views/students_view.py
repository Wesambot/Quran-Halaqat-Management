import flet as ft
from database.db_manager import DBManager
from utils.styles import AppColors, AppStyles
from utils.components import developer_footer

def students_view(page: ft.Page, db: DBManager, group_id, on_back):
    page.clean()

    def open_student_profile(student_id):
        from views.student_profile_view import student_profile_view
        student_profile_view(page, db, student_id, lambda: students_view(page, db, group_id, on_back))

    def student_form_dialog(e=None, existing_student=None):
        is_edit = existing_student is not None
        name_field = ft.TextField(label="اسم الطالب", border_radius=10,
                                   value=existing_student['name'] if is_edit else "")
        age_field = ft.TextField(label="العمر", border_radius=10, keyboard_type=ft.KeyboardType.NUMBER,
                                  value=str(existing_student['age']) if is_edit and existing_student['age'] else "")
        phone_field = ft.TextField(label="رقم ولي الأمر", border_radius=10, keyboard_type=ft.KeyboardType.PHONE,
                                    value=existing_student['parent_phone'] if is_edit and existing_student['parent_phone'] else "")
        notes_field = ft.TextField(label="ملاحظات", border_radius=10, multiline=True,
                                    value=existing_student['notes'] if is_edit and existing_student['notes'] else "")

        def save_student(e):
            if not name_field.value or not name_field.value.strip():
                error_text.value = "الرجاء إدخال اسم الطالب"
                error_text.update()
                return

            age_value = None
            if age_field.value:
                try:
                    age_value = int(age_field.value)
                except ValueError:
                    error_text.value = "العمر يجب أن يكون رقمًا"
                    error_text.update()
                    return

            try:
                if is_edit:
                    db.update_student(existing_student['id'], name_field.value.strip(), age_value, phone_field.value, notes_field.value)
                else:
                    db.add_student(group_id, name_field.value.strip(), age_value, phone_field.value, notes_field.value)
            except Exception as ex:
                error_text.value = f"تعذر حفظ الطالب: {ex}"
                error_text.update()
                return

            dialog.open = False
            msg = "تم تعديل" if is_edit else "تم حفظ"
            page.snack_bar = ft.SnackBar(ft.Text(f"{msg} الطالب \"{name_field.value.strip()}\" بنجاح ✅"), bgcolor=AppColors.PRIMARY)
            page.snack_bar.open = True
            students_view(page, db, group_id, on_back)

        error_text = ft.Text("", color="red", size=12)

        def cancel_student_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("تعديل بيانات الطالب" if is_edit else "إضافة طالب جديد"),
            content=ft.Column([
                name_field,
                age_field,
                phone_field,
                notes_field,
                error_text,
            ], tight=True, width=300),
            actions=[
                ft.TextButton("إلغاء", on_click=cancel_student_dialog),
                ft.ElevatedButton("حفظ", on_click=save_student, bgcolor=AppColors.PRIMARY, color="white"),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def delete_student(student_id, student_name):
        def cancel_delete_student(e):
            confirm_dialog.open = False
            page.update()

        def confirm_delete(e):
            confirm_dialog.open = False
            try:
                db.delete_student(student_id)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"تعذر حذف الطالب: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            students_view(page, db, group_id, on_back)

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("تأكيد الحذف"),
            content=ft.Text(f"هل أنت متأكد من حذف الطالب \"{student_name}\"؟"),
            actions=[
                ft.TextButton("إلغاء", on_click=cancel_delete_student),
                ft.ElevatedButton("حذف", on_click=confirm_delete, bgcolor="red", color="white"),
            ],
        )
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    students = db.get_students_by_group(group_id)
    students_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    for s in students:
        students_list.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.ListTile(
                        leading=ft.CircleAvatar(content=ft.Text(s['name'][0])),
                        title=ft.Text(s['name'], weight="bold"),
                        subtitle=ft.Text(f"العمر: {s['age'] or '-'} | هاتف: {s['parent_phone'] or '-'}"),
                        on_click=lambda _, sid=s['id']: open_student_profile(sid),
                        trailing=ft.Row([
                            ft.IconButton(ft.icons.EDIT, icon_color=AppColors.PRIMARY, on_click=lambda _, st=s: student_form_dialog(existing_student=st)),
                            ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=lambda _, sid=s['id'], sname=s['name']: delete_student(sid, sname)),
                        ], tight=True),
                    ),
                    padding=5
                ),
                **AppStyles.CARD_STYLE
            )
        )

    page.add(
        ft.AppBar(
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: on_back()),
            title=ft.Text("طلاب الحلقة"),
            bgcolor=AppColors.PRIMARY,
            color="white",
            center_title=True,
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("قائمة الطلاب", size=20, weight="bold", color=AppColors.PRIMARY),
                students_list,
                ft.FloatingActionButton(
                    icon=ft.icons.PERSON_ADD,
                    bgcolor=AppColors.PRIMARY,
                    on_click=student_form_dialog,
                    tooltip="إضافة طالب"
                ),
                developer_footer(),
            ], expand=True),
            padding=20,
            expand=True
        )
    )
    page.update()
