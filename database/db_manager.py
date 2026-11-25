import sqlite3
import re
from datetime import datetime
from utils.app_paths import AppPaths, StorageError
from services.statistics_engine import (
    compute_ayah_span,
    sort_students_by_strength,
    compute_student_period_stats,
)


class DatabaseError(Exception):
    """يُرفع عند تعذر فتح أو تهيئة قاعدة البيانات، مع رسالة واضحة للمستخدم."""
    pass


class DBManager:
    """
    Version 1.1.1 - نظام قاعدة بيانات + Migration احترافي ودائم.
    ----------------------------------------------------------------
    الجداول: teachers, halaqat, students, attendance, memorization,
    revision, reports, achievements, settings, statistics_cache.
    اسم "الحلقة" في قاعدة البيانات هو halaqat حصرًا (لا يوجد أي مكان
    آخر بالمشروع يستخدم اسم groups كجدول فعلي).

    عند كل تشغيل، يقوم init_db بأربع خطوات بالترتيب:
    1) _create_tables      : إنشاء أي جدول ناقص بالكامل (IF NOT EXISTS).
    2) _migrate_legacy_data : نقل بيانات الجداول القديمة (قبل 1.1.0) - groups/
                              daily_reports/student_records/settings القديمة.
    3) _fix_stale_foreign_keys : يفحص كل جدول موجود، وإذا كان مفتاحه الخارجي
                              (FOREIGN KEY) في تعريفه الأصلي المخزّن لا يزال
                              يشير لجدول لم يعد موجودًا (كـ groups بعد حذفه)،
                              يعيد بناء الجدول بالكامل بمفتاح خارجي صحيح
                              يشير إلى الاسم الحالي (halaqat)، مع نقل كل
                              بياناته الموجودة دون أي فقدان.
    4) _ensure_columns     : يضيف أي عمود ناقص من الشكل الحالي المتوقع لكل
                              جدول، عبر ALTER TABLE، دون حذف أي بيانات.

    وفي النهاية يُسجَّل رقم إصدار قاعدة البيانات (PRAGMA user_version)
    ليُستخدم مستقبلاً لتفعيل أي Migration إضافي عند رفع رقم الإصدار.

    ملاحظة توافق: كل الدوال العامة (add_group, get_groups, add_student...)
    أُبقيت بنفس الاسم والمخرجات حتى تستمر شاشات الواجهة بالعمل دون تعديل.
    """

    CURRENT_SCHEMA_VERSION = 2

    # ترتيب الجداول مهم فقط عند الإنشاء الأول (لضمان وجود الجدول المرجعي
    # قبل الجدول الذي يشير إليه بمفتاح خارجي).
    TABLE_ORDER = [
        "teachers", "settings", "halaqat", "students", "reports",
        "attendance", "memorization", "revision", "achievements",
        "statistics_cache", "quran_ayat",
    ]

    def __init__(self, app_paths: AppPaths = None):
        try:
            self.app_paths = app_paths or AppPaths()
        except StorageError as e:
            raise DatabaseError(str(e))

        self.db_path = str(self.app_paths.database_path)
        self.init_db()

    def get_connection(self):
        """اتصال عادي للاستخدام أثناء تشغيل التطبيق (بعد اكتمال الترحيل)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            raise DatabaseError(
                f"تعذر فتح قاعدة البيانات في المسار:\n{self.db_path}\n\nالسبب: {e}"
            )

    def init_db(self):
        """
        يشغّل كل خطوات التهيئة/الترحيل على اتصال واحد مشترك، مع تعطيل فرض
        المفاتيح الخارجية مؤقتًا أثناء الترحيل فقط (لتفادي أخطاء وهمية
        كـ "no such table" في منتصف عملية إعادة بناء الجداول)، ثم يُعاد
        تفعيلها تلقائيًا في get_connection لعمليات التطبيق العادية بعد
        اكتمال الترحيل بالكامل ونجاحه.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = OFF")
            # حاسم: نمنع SQLite من "تحديث" مفاتيح خارجية بجداول أخرى تلقائيًا
            # عند إعادة تسمية جدول مؤقتًا أثناء إعادة البناء (RENAME TO)، وإلا
            # ستُفسَد إشارات جداول مثل attendance/memorization إلى students.
            conn.execute("PRAGMA legacy_alter_table = ON")
            try:
                self._create_tables(conn)
                self._migrate_legacy_data(conn)
                self._fix_stale_foreign_keys(conn)
                self._ensure_columns(conn)
                conn.execute(f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}")
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error as e:
            raise DatabaseError(
                f"تعذر تهيئة جداول قاعدة البيانات في المسار:\n{self.db_path}\n\nالسبب: {e}"
            )

    # =====================================================================
    # تعريف الشكل الصحيح الحالي لكل جدول (مصدر الحقيقة الوحيد)
    # =====================================================================
    def _table_ddl(self, table_name: str) -> str:
        """يرجع جملة CREATE TABLE الصحيحة والكاملة لاسم جدول معيّن (بدون IF NOT EXISTS)،
        تُستخدم عند الإنشاء الأول وعند إعادة بناء أي جدول تالف المفاتيح الخارجية."""
        ddls = {
            "teachers": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT DEFAULT 'المهندس وسام',
                phone_number TEXT DEFAULT ''
            )""",
            "settings": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY,
                is_first_run INTEGER DEFAULT 1,
                dark_mode INTEGER DEFAULT 0,
                app_version TEXT DEFAULT '1.1.0'
            )""",
            "halaqat": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                study_days TEXT NOT NULL,
                teacher_id INTEGER DEFAULT 1,
                FOREIGN KEY (teacher_id) REFERENCES teachers (id)
            )""",
            "students": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                name TEXT NOT NULL,
                age INTEGER,
                parent_phone TEXT,
                notes TEXT,
                image_path TEXT,
                join_date TEXT,
                FOREIGN KEY (group_id) REFERENCES halaqat (id) ON DELETE CASCADE
            )""",
            "reports": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                date TEXT NOT NULL,
                teacher_notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (group_id) REFERENCES halaqat (id) ON DELETE CASCADE
            )""",
            "attendance": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                student_id INTEGER,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )""",
            "memorization": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                student_id INTEGER,
                sura_number INTEGER,
                sura_name TEXT,
                from_ayah INTEGER,
                to_ayah INTEGER,
                to_sura_number INTEGER,
                to_sura_name TEXT,
                first_page INTEGER,
                last_page INTEGER,
                ayat_count INTEGER,
                pages_count INTEGER,
                manual_pages_count INTEGER,
                juz INTEGER,
                juz_end INTEGER,
                hizb INTEGER,
                hizb_end INTEGER,
                rating TEXT,
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )""",
            "revision": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                student_id INTEGER,
                sura_number INTEGER,
                sura_name TEXT,
                from_ayah INTEGER,
                to_ayah INTEGER,
                to_sura_number INTEGER,
                to_sura_name TEXT,
                first_page INTEGER,
                last_page INTEGER,
                ayat_count INTEGER,
                pages_count INTEGER,
                manual_pages_count INTEGER,
                juz INTEGER,
                juz_end INTEGER,
                hizb INTEGER,
                hizb_end INTEGER,
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )""",
            "achievements": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                type TEXT,
                period_label TEXT,
                date_awarded TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )""",
            "statistics_cache": f"""CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT,
                scope_id INTEGER,
                period TEXT,
                computed_json TEXT,
                updated_at TEXT
            )""",
            "quran_ayat": f"""CREATE TABLE {table_name} (
                sura_number INTEGER NOT NULL,
                sura_name TEXT,
                ayah_number INTEGER NOT NULL,
                page INTEGER,
                juz INTEGER,
                hizb INTEGER,
                quarter INTEGER,
                PRIMARY KEY (sura_number, ayah_number)
            )""",
        }
        return ddls[table_name]

    def _create_tables(self, conn):
        cursor = conn.cursor()
        for table_name in self.TABLE_ORDER:
            ddl = self._table_ddl(table_name).replace(
                "CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1
            )
            cursor.execute(ddl)

        cursor.execute('SELECT COUNT(*) FROM teachers')
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO teachers (id, name, phone_number) VALUES (1, ?, ?)',
                ('المهندس وسام', '')
            )

        cursor.execute('SELECT COUNT(*) FROM settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO settings (id, is_first_run, dark_mode) VALUES (1, 1, 0)')

        conn.commit()

    # =====================================================================
    # إصلاح المفاتيح الخارجية التالفة (تشير لجدول تم حذفه/إعادة تسميته)
    # =====================================================================
    def _rebuild_table_with_fresh_schema(self, conn, table_name):
        """يعيد بناء جدول بالكامل بالشكل الصحيح الحالي (مع مفاتيح خارجية سليمة)،
        وينقل كل بياناته الموجودة (الأعمدة المشتركة فقط) دون أي فقدان."""
        cursor = conn.cursor()
        backup_name = f"{table_name}__rebuild_backup"
        cursor.execute(f"ALTER TABLE {table_name} RENAME TO {backup_name}")
        cursor.execute(self._table_ddl(table_name))

        old_cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({backup_name})").fetchall()]
        new_cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]
        common_cols = [c for c in old_cols if c in new_cols]

        if common_cols:
            cols_sql = ", ".join(common_cols)
            cursor.execute(
                f"INSERT INTO {table_name} ({cols_sql}) SELECT {cols_sql} FROM {backup_name}"
            )

        cursor.execute(f"DROP TABLE {backup_name}")
        conn.commit()

    def _fix_stale_foreign_keys(self, conn):
        """
        يفحص التعريف الفعلي المخزّن (sqlite_master) لكل جدول من جداولنا،
        ويستخرج كل أسماء الجداول التي يشير إليها بمفتاح خارجي (REFERENCES).
        إن كان أي جدول مُشار إليه غير موجود فعليًا (مثل "groups" بعد حذفها
        في ترحيل قديم، بينما جدول "students" ما زال يحمل تعريفه القديم منذ
        إنشائه الأول)، تتم إعادة بناء الجدول المتضرر بمفتاح خارجي صحيح.
        """
        cursor = conn.cursor()

        for table_name in self.TABLE_ORDER:
            existing_tables = {
                row[0] for row in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if table_name not in existing_tables:
                continue

            row = cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
                (table_name,)
            ).fetchone()
            if not row or not row["sql"]:
                continue

            referenced_tables = re.findall(r"REFERENCES\s+([A-Za-z_][A-Za-z0-9_]*)", row["sql"])
            stale = [ref for ref in referenced_tables if ref not in existing_tables]

            if stale:
                self._rebuild_table_with_fresh_schema(conn, table_name)

    # =====================================================================
    # الشكل الكامل المتوقع لكل جدول (تُستخدم لإضافة أي عمود ناقص تلقائيًا)
    # =====================================================================
    EXPECTED_SCHEMA = {
        "teachers": {
            "name": "TEXT DEFAULT 'المهندس وسام'",
            "phone_number": "TEXT DEFAULT ''",
        },
        "settings": {
            "is_first_run": "INTEGER DEFAULT 1",
            "dark_mode": "INTEGER DEFAULT 0",
            "app_version": "TEXT DEFAULT '1.1.0'",
        },
        "halaqat": {
            "name": "TEXT",
            "type": "TEXT",
            "study_days": "TEXT",
            "teacher_id": "INTEGER DEFAULT 1",
        },
        "students": {
            "group_id": "INTEGER",
            "name": "TEXT",
            "age": "INTEGER",
            "parent_phone": "TEXT",
            "notes": "TEXT",
            "image_path": "TEXT",
            "join_date": "TEXT",
        },
        "reports": {
            "group_id": "INTEGER",
            "date": "TEXT",
            "teacher_notes": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
        "attendance": {
            "report_id": "INTEGER",
            "student_id": "INTEGER",
            "status": "TEXT",
            "notes": "TEXT",
        },
        "memorization": {
            "report_id": "INTEGER",
            "student_id": "INTEGER",
            "sura_number": "INTEGER",
            "sura_name": "TEXT",
            "from_ayah": "INTEGER",
            "to_ayah": "INTEGER",
            "to_sura_number": "INTEGER",
            "to_sura_name": "TEXT",
            "first_page": "INTEGER",
            "last_page": "INTEGER",
            "ayat_count": "INTEGER",
            "pages_count": "INTEGER",
            "manual_pages_count": "INTEGER",
            "juz": "INTEGER",
            "juz_end": "INTEGER",
            "hizb": "INTEGER",
            "hizb_end": "INTEGER",
            "rating": "TEXT",
        },
        "revision": {
            "report_id": "INTEGER",
            "student_id": "INTEGER",
            "sura_number": "INTEGER",
            "sura_name": "TEXT",
            "from_ayah": "INTEGER",
            "to_ayah": "INTEGER",
            "to_sura_number": "INTEGER",
            "to_sura_name": "TEXT",
            "first_page": "INTEGER",
            "last_page": "INTEGER",
            "ayat_count": "INTEGER",
            "pages_count": "INTEGER",
            "manual_pages_count": "INTEGER",
            "juz": "INTEGER",
            "juz_end": "INTEGER",
            "hizb": "INTEGER",
            "hizb_end": "INTEGER",
        },
        "achievements": {
            "student_id": "INTEGER",
            "type": "TEXT",
            "period_label": "TEXT",
            "date_awarded": "TEXT",
        },
        "statistics_cache": {
            "scope_type": "TEXT",
            "scope_id": "INTEGER",
            "period": "TEXT",
            "computed_json": "TEXT",
            "updated_at": "TEXT",
        },
        # جدول جاهز لاستقبال بيانات دقيقة 100% لكل آية (رقم الصفحة/الجزء/الحزب/الربع)
        # فور توفرها مستقبلاً، دون الحاجة لتغيير أي كود آخر بالمشروع - راجع
        # get_exact_ayah_data و bulk_import_quran_ayat أدناه.
        "quran_ayat": {
            "sura_number": "INTEGER",
            "sura_name": "TEXT",
            "ayah_number": "INTEGER",
            "page": "INTEGER",
            "juz": "INTEGER",
            "hizb": "INTEGER",
            "quarter": "INTEGER",
        },
    }

    def _ensure_columns(self, conn):
        """يفحص كل جدول من EXPECTED_SCHEMA، ويضيف أي عمود ناقص عبر ALTER TABLE
        دون حذف أو تعديل أي بيانات موجودة."""
        cursor = conn.cursor()
        existing_tables = {
            row[0] for row in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        for table, expected_columns in self.EXPECTED_SCHEMA.items():
            if table not in existing_tables:
                continue

            existing_columns = {
                row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
            }

            for column, definition in expected_columns.items():
                if column not in existing_columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

        conn.commit()

    # =====================================================================
    # ترحيل البيانات القديمة (من الإصدارات السابقة قبل 1.1.0)
    # =====================================================================
    def _migrate_legacy_data(self, conn):
        cursor = conn.cursor()
        existing_tables = {
            row[0] for row in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "settings" in existing_tables:
            cols = {row[1] for row in cursor.execute("PRAGMA table_info(settings)").fetchall()}
            if "teacher_name" in cols:
                old = cursor.execute(
                    "SELECT teacher_name, phone_number, is_first_run FROM settings WHERE id = 1"
                ).fetchone()
                if old:
                    cursor.execute(
                        "UPDATE teachers SET name = ?, phone_number = ? WHERE id = 1",
                        (old["teacher_name"], old["phone_number"])
                    )
                    cursor.execute("ALTER TABLE settings RENAME TO settings_old_backup")
                    cursor.execute(self._table_ddl("settings"))
                    cursor.execute(
                        "INSERT INTO settings (id, is_first_run, dark_mode) VALUES (1, ?, 0)",
                        (old["is_first_run"],)
                    )
                    cursor.execute("DROP TABLE settings_old_backup")

        if "groups" in existing_tables:
            old_groups = cursor.execute("SELECT * FROM groups").fetchall()
            for g in old_groups:
                cursor.execute(
                    "INSERT INTO halaqat (id, name, type, study_days) VALUES (?, ?, ?, ?)",
                    (g["id"], g["name"], g["type"], g["study_days"])
                )
            cursor.execute("DROP TABLE groups")

        if "daily_reports" in existing_tables:
            old_reports = cursor.execute("SELECT * FROM daily_reports").fetchall()
            for r in old_reports:
                cursor.execute(
                    "INSERT INTO reports (id, group_id, date, teacher_notes) VALUES (?, ?, ?, ?)",
                    (r["id"], r["group_id"], r["date"], r["teacher_notes"])
                )
            cursor.execute("DROP TABLE daily_reports")

        if "student_records" in existing_tables:
            old_records = cursor.execute("SELECT * FROM student_records").fetchall()
            for rec in old_records:
                cursor.execute(
                    "INSERT INTO attendance (report_id, student_id, status, notes) VALUES (?, ?, ?, ?)",
                    (rec["report_id"], rec["student_id"], rec["status"], rec["notes"])
                )
                if rec["hifz_from_page"]:
                    pages = max(1, (rec["hifz_to_page"] or rec["hifz_from_page"]) - rec["hifz_from_page"] + 1)
                    cursor.execute('''
                        INSERT INTO memorization (report_id, student_id, sura_name, pages_count, rating)
                        VALUES (?, ?, ?, ?, NULL)
                    ''', (rec["report_id"], rec["student_id"], rec["hifz_from_sura"], pages))
                if rec["murajaa_from_page"]:
                    pages = max(1, (rec["murajaa_to_page"] or rec["murajaa_from_page"]) - rec["murajaa_from_page"] + 1)
                    cursor.execute('''
                        INSERT INTO revision (report_id, student_id, sura_name, pages_count)
                        VALUES (?, ?, ?, ?)
                    ''', (rec["report_id"], rec["student_id"], rec["murajaa_from_sura"], pages))
            cursor.execute("DROP TABLE student_records")

        conn.commit()

    # =====================================================================
    # الإعدادات والمعلم
    # =====================================================================
    def get_settings(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            teacher = cursor.execute('SELECT * FROM teachers WHERE id = 1').fetchone()
            settings = cursor.execute('SELECT * FROM settings WHERE id = 1').fetchone()
            return {
                "id": 1,
                "teacher_name": teacher["name"],
                "phone_number": teacher["phone_number"],
                "is_first_run": settings["is_first_run"],
                "dark_mode": settings["dark_mode"],
            }

    def update_settings(self, teacher_name, phone_number, is_first_run=0):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE teachers SET name = ?, phone_number = ? WHERE id = 1',
                           (teacher_name, phone_number))
            cursor.execute('UPDATE settings SET is_first_run = ? WHERE id = 1', (is_first_run,))
            conn.commit()

    def set_dark_mode(self, enabled: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE settings SET dark_mode = ? WHERE id = 1', (1 if enabled else 0,))
            conn.commit()

    # =====================================================================
    # إدارة الحلقات (halaqat) - نفس أسماء الدوال القديمة
    # =====================================================================
    def add_group(self, name, group_type, study_days):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO halaqat (name, type, study_days) VALUES (?, ?, ?)',
                           (name, group_type, ",".join(study_days)))
            conn.commit()

    def get_groups(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.*, (SELECT COUNT(*) FROM students s WHERE s.group_id = h.id) as student_count
                FROM halaqat h
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def get_group_by_id(self, group_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM halaqat WHERE id = ?', (group_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_group(self, group_id, name, group_type, study_days):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE halaqat SET name = ?, type = ?, study_days = ? WHERE id = ?',
                (name, group_type, ",".join(study_days), group_id)
            )
            conn.commit()

    def delete_group(self, group_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM halaqat WHERE id = ?', (group_id,))
            conn.commit()

    # =====================================================================
    # إدارة الطلاب
    # =====================================================================
    def add_student(self, group_id, name, age=None, parent_phone=None, notes=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (group_id, name, age, parent_phone, notes, join_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (group_id, name, age, parent_phone, notes, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

    def get_students_by_group(self, group_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students WHERE group_id = ?', (group_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_student_by_id(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_student(self, student_id, name, age=None, parent_phone=None, notes=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE students SET name = ?, age = ?, parent_phone = ?, notes = ? WHERE id = ?',
                (name, age, parent_phone, notes, student_id)
            )
            conn.commit()

    def delete_student(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()

    def get_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM halaqat')
            groups_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM students')
            students_count = cursor.fetchone()[0]
            return {"groups": groups_count, "students": students_count}

    # =====================================================================
    # إدارة التقارير - إدخال بالسورة + من آية + إلى آية (بدون صفحات يدويًا)
    # =====================================================================
    def create_report(self, group_id, date, teacher_notes=""):
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO reports (group_id, date, teacher_notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (group_id, date, teacher_notes, now, now)
            )
            return cursor.lastrowid

    def get_report_by_group_and_date(self, group_id, date):
        """
        يبحث عن تقرير موجود مسبقًا لنفس الحلقة ونفس التاريخ (لمنع إنشاء
        تقرير مكرر). يُرجع التقرير كاملاً إن وُجد، أو None إن لم يوجد.
        """
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM reports WHERE group_id = ? AND date = ?',
                (group_id, date)
            ).fetchone()
            return dict(row) if row else None

    def update_report_records(self, report_id, records):
        """
        تحديث حقيقي لتقرير موجود مسبقًا: يحذف كل سجلات الحضور/الحفظ/المراجعة
        القديمة الخاصة بهذا التقرير فقط، ثم يعيد إدخال السجلات الجديدة لنفس
        report_id (بدون تغييره)، ويحدّث updated_at. هذا يضمن عدم إنشاء أي
        سجل مكرر لنفس الطالب ونفس اليوم، وأن كل الإحصائيات والتقارير
        المجمّعة (أسبوعي/شهري/سنوي) تعكس البيانات المحدّثة تلقائيًا في
        الاستدعاء التالي لها (لأنها تُحسب دائمًا من هذه الجداول الأصلية
        مباشرة، وليست نسخة مخزّنة منفصلة).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM attendance WHERE report_id = ?', (report_id,))
            cursor.execute('DELETE FROM memorization WHERE report_id = ?', (report_id,))
            cursor.execute('DELETE FROM revision WHERE report_id = ?', (report_id,))
            conn.commit()

        for r in records:
            r['report_id'] = report_id
            self.add_student_record(r)

        with self.get_connection() as conn:
            conn.execute(
                'UPDATE reports SET updated_at = ? WHERE id = ?',
                (datetime.now().isoformat(timespec="seconds"), report_id)
            )
            conn.commit()

    def get_exact_ayah_data(self, sura_number, ayah_number):
        """
        يبحث عن بيانات دقيقة 100% لآية معيّنة في جدول quran_ayat (إن وُجدت).
        يُرجع None إن لم تكن البيانات الدقيقة مُدخلة بعد لهذه الآية، وعندها
        يستمر التطبيق باستخدام الحساب التقريبي الحالي (statistics_engine)
        تلقائيًا دون أي تغيير في باقي الكود.
        """
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM quran_ayat WHERE sura_number = ? AND ayah_number = ?',
                (sura_number, ayah_number)
            ).fetchone()
            return dict(row) if row else None

    def bulk_import_quran_ayat(self, rows):
        """
        استيراد جماعي لبيانات دقيقة لكل آية دفعة واحدة، لاستخدامها فور توفر
        مصدر بيانات موثوق. كل عنصر في rows يجب أن يكون قاموسًا بالمفاتيح:
        sura_number, sura_name, ayah_number, page, juz, hizb, quarter.
        يستبدل أي بيانات سابقة لنفس الآية (INSERT OR REPLACE) دون التأثير
        على أي جدول آخر من جداول التطبيق.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for r in rows:
                cursor.execute('''
                    INSERT OR REPLACE INTO quran_ayat
                    (sura_number, sura_name, ayah_number, page, juz, hizb, quarter)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    r["sura_number"], r.get("sura_name"), r["ayah_number"],
                    r.get("page"), r.get("juz"), r.get("hizb"), r.get("quarter"),
                ))
            conn.commit()

    def _apply_exact_data_if_available(self, cursor, calc):
        """
        يفحص جدول quran_ayat (بنفس cursor الحالي، بدون فتح اتصال جديد
        لتفادي أي تعارض أثناء معاملة قيد التنفيذ) لآيتي البداية والنهاية،
        ويستبدل الصفحة/الجزء/الحزب التقريبية ببيانات دقيقة تمامًا إن توفرت.
        """
        start_exact = cursor.execute(
            'SELECT * FROM quran_ayat WHERE sura_number = ? AND ayah_number = ?',
            (calc["from_sura"], calc["from_ayah"])
        ).fetchone()
        end_exact = cursor.execute(
            'SELECT * FROM quran_ayat WHERE sura_number = ? AND ayah_number = ?',
            (calc["to_sura"], calc["to_ayah"])
        ).fetchone()

        if start_exact:
            calc["first_page"] = start_exact["page"] or calc["first_page"]
            calc["juz_start"] = start_exact["juz"] or calc["juz_start"]
            calc["hizb_start"] = start_exact["hizb"] or calc["hizb_start"]
        if end_exact:
            calc["last_page"] = end_exact["page"] or calc["last_page"]
            calc["juz_end"] = end_exact["juz"] or calc["juz_end"]
            calc["hizb_end"] = end_exact["hizb"] or calc["hizb_end"]
        if start_exact and end_exact and calc["first_page"] and calc["last_page"]:
            calc["pages_count"] = max(1, calc["last_page"] - calc["first_page"] + 1)

        return calc

    def add_student_record(self, record_data):
        """
        الحقول المتوقعة في record_data:
        report_id, student_id, status,
        hifz_from_sura / hifz_from_ayah / hifz_to_sura / hifz_to_ayah / hifz_rating (اختياري),
        murajaa_from_sura / murajaa_from_ayah / murajaa_to_sura / murajaa_to_ayah (اختياري),
        notes (اختياري)
        الحساب التلقائي لعدد الآيات/أول وآخر صفحة/الجزء/الحزب (بداية ونهاية) يتم
        داخليًا عبر statistics_engine.compute_ayah_span، ويدعم امتداد التسميع
        عبر أكثر من سورة. يرفع InvalidAyahRangeError لو كان الإدخال غير صحيح
        (نهاية قبل بداية، أو رقم آية غير موجود).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO attendance (report_id, student_id, status, notes) VALUES (?, ?, ?, ?)',
                (record_data['report_id'], record_data['student_id'], record_data['status'],
                 record_data.get('notes'))
            )

            if record_data.get('hifz_from_sura'):
                calc = compute_ayah_span(
                    record_data['hifz_from_sura'],
                    record_data.get('hifz_from_ayah', 1),
                    record_data.get('hifz_to_sura', record_data['hifz_from_sura']),
                    record_data.get('hifz_to_ayah', 1),
                )
                calc = self._apply_exact_data_if_available(cursor, calc)
                cursor.execute('''
                    INSERT INTO memorization
                    (report_id, student_id, sura_number, sura_name, from_ayah,
                     to_sura_number, to_sura_name, to_ayah,
                     first_page, last_page, ayat_count, pages_count, manual_pages_count,
                     juz, juz_end, hizb, hizb_end, rating)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record_data['report_id'], record_data['student_id'],
                    calc['from_sura'], calc['from_sura_name'], calc['from_ayah'],
                    calc['to_sura'], calc['to_sura_name'], calc['to_ayah'],
                    calc['first_page'], calc['last_page'], calc['ayat_count'], calc['pages_count'],
                    record_data.get('hifz_pages_manual'),
                    calc['juz_start'], calc['juz_end'], calc['hizb_start'], calc['hizb_end'],
                    record_data.get('hifz_rating')
                ))

            if record_data.get('murajaa_from_sura'):
                calc = compute_ayah_span(
                    record_data['murajaa_from_sura'],
                    record_data.get('murajaa_from_ayah', 1),
                    record_data.get('murajaa_to_sura', record_data['murajaa_from_sura']),
                    record_data.get('murajaa_to_ayah', 1),
                )
                calc = self._apply_exact_data_if_available(cursor, calc)
                cursor.execute('''
                    INSERT INTO revision
                    (report_id, student_id, sura_number, sura_name, from_ayah,
                     to_sura_number, to_sura_name, to_ayah,
                     first_page, last_page, ayat_count, pages_count, manual_pages_count,
                     juz, juz_end, hizb, hizb_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record_data['report_id'], record_data['student_id'],
                    calc['from_sura'], calc['from_sura_name'], calc['from_ayah'],
                    calc['to_sura'], calc['to_sura_name'], calc['to_ayah'],
                    calc['first_page'], calc['last_page'], calc['ayat_count'], calc['pages_count'],
                    record_data.get('murajaa_pages_manual'),
                    calc['juz_start'], calc['juz_end'], calc['hizb_start'], calc['hizb_end'],
                ))

            conn.commit()

    def get_report_records(self, report_id):
        """
        سجل كل طالب في تقرير معيّن (حضور + حفظ + مراجعة مدمجة في صف واحد)،
        مرتب تلقائيًا حسب الأقوى حفظًا (تقييم الحفظ ثم عدد الصفحات).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            attendance_rows = cursor.execute('''
                SELECT a.*, s.name as student_name
                FROM attendance a JOIN students s ON a.student_id = s.id
                WHERE a.report_id = ?
            ''', (report_id,)).fetchall()

            hifz_rows = cursor.execute('SELECT * FROM memorization WHERE report_id = ?', (report_id,)).fetchall()
            murajaa_rows = cursor.execute('SELECT * FROM revision WHERE report_id = ?', (report_id,)).fetchall()

            hifz_by_student = {r["student_id"]: dict(r) for r in hifz_rows}
            murajaa_by_student = {r["student_id"]: dict(r) for r in murajaa_rows}

            records = []
            for a in attendance_rows:
                row = dict(a)
                h = hifz_by_student.get(row["student_id"])
                m = murajaa_by_student.get(row["student_id"])
                row["hifz_sura_name"] = h["sura_name"] if h else None
                row["hifz_from_ayah"] = h["from_ayah"] if h else None
                row["hifz_to_sura_name"] = h["to_sura_name"] if h else None
                row["hifz_to_ayah"] = h["to_ayah"] if h else None
                row["hifz_ayat_count"] = h["ayat_count"] if h else 0
                row["hifz_pages_count"] = (h["manual_pages_count"] if h and h["manual_pages_count"] else (h["pages_count"] if h else 0))
                row["hifz_first_page"] = h["first_page"] if h else None
                row["hifz_last_page"] = h["last_page"] if h else None
                row["hifz_juz"] = h["juz"] if h else None
                row["hifz_juz_end"] = h["juz_end"] if h else None
                row["hifz_hizb"] = h["hizb"] if h else None
                row["hifz_hizb_end"] = h["hizb_end"] if h else None
                row["hifz_rating"] = h["rating"] if h else None
                row["murajaa_sura_name"] = m["sura_name"] if m else None
                row["murajaa_from_ayah"] = m["from_ayah"] if m else None
                row["murajaa_to_sura_name"] = m["to_sura_name"] if m else None
                row["murajaa_to_ayah"] = m["to_ayah"] if m else None
                row["murajaa_ayat_count"] = m["ayat_count"] if m else 0
                row["murajaa_pages_count"] = (m["manual_pages_count"] if m and m["manual_pages_count"] else (m["pages_count"] if m else 0))
                row["murajaa_first_page"] = m["first_page"] if m else None
                row["murajaa_last_page"] = m["last_page"] if m else None
                row["murajaa_juz"] = m["juz"] if m else None
                row["murajaa_juz_end"] = m["juz_end"] if m else None
                row["murajaa_hizb"] = m["hizb"] if m else None
                row["murajaa_hizb_end"] = m["hizb_end"] if m else None
                records.append(row)

            return sort_students_by_strength(records)

    def get_report_by_id(self, report_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
            return dict(row) if row else None

    # =====================================================================
    # تجميع بيانات لفترة زمنية (أسبوعي/شهري) - يُستخدم في تصدير PDF
    # =====================================================================
    def get_reports_in_range(self, group_id, date_from, date_to):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT * FROM reports
                WHERE group_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
            ''', (group_id, date_from, date_to)).fetchall()
            return [dict(r) for r in rows]

    def get_student_full_history(self, student_id):
        """
        يرجع السجل الكامل لطالب واحد عبر كل التقارير المسجّلة له على
        الإطلاق (تاريخ كل يوم + حالة الحضور + بيانات الحفظ/المراجعة إن
        وُجدت)، مرتبة تصاعديًا حسب التاريخ. تُستخدم لبناء صفحة الملف
        الشخصي للطالب (إحصائيات شاملة + آخر حفظ/مراجعة).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT a.*, r.date as report_date
                FROM attendance a
                JOIN reports r ON a.report_id = r.id
                WHERE a.student_id = ?
                ORDER BY r.date ASC
            ''', (student_id,)).fetchall()

            history = []
            for a in rows:
                h = cursor.execute(
                    'SELECT * FROM memorization WHERE report_id = ? AND student_id = ?',
                    (a["report_id"], student_id)
                ).fetchone()
                m = cursor.execute(
                    'SELECT * FROM revision WHERE report_id = ? AND student_id = ?',
                    (a["report_id"], student_id)
                ).fetchone()
                entry = dict(a)
                entry["hifz_sura_name"] = h["sura_name"] if h else None
                entry["hifz_to_sura_name"] = h["to_sura_name"] if h else None
                entry["hifz_from_ayah"] = h["from_ayah"] if h else None
                entry["hifz_to_ayah"] = h["to_ayah"] if h else None
                entry["hifz_rating"] = h["rating"] if h else None
                entry["hifz_pages_count"] = (h["manual_pages_count"] if h and h["manual_pages_count"] else (h["pages_count"] if h else 0))
                entry["hifz_ayat_count"] = h["ayat_count"] if h else 0
                entry["murajaa_sura_name"] = m["sura_name"] if m else None
                entry["murajaa_to_sura_name"] = m["to_sura_name"] if m else None
                entry["murajaa_from_ayah"] = m["from_ayah"] if m else None
                entry["murajaa_to_ayah"] = m["to_ayah"] if m else None
                entry["murajaa_pages_count"] = (m["manual_pages_count"] if m and m["manual_pages_count"] else (m["pages_count"] if m else 0))
                entry["murajaa_ayat_count"] = m["ayat_count"] if m else 0
                history.append(entry)

            return history

    def get_student_achievements(self, student_id):
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM achievements WHERE student_id = ? ORDER BY date_awarded DESC',
                (student_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def compute_and_store_achievements(self, group_id, date_from, date_to, period_label):
        """
        يحسب إنجازات حلقة لفترة معينة (عبر achievements_engine) ويخزّنها.
        إعادة الحساب لنفس period_label تحذف الإنجازات السابقة لنفس الفترة
        أولاً (لطلاب هذه الحلقة فقط) قبل إدراج الجديدة، فلا تتكرر الشارات
        عند تكرار الحساب. يُرجع قائمة الإنجازات الممنوحة.
        """
        from services.achievements_engine import compute_achievements
        from datetime import datetime

        summary = self.get_group_period_summary(group_id, date_from, date_to)
        awarded = compute_achievements(summary["students"])

        student_ids = [s["id"] for s in self.get_students_by_group(group_id)]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if student_ids:
                placeholders = ",".join("?" * len(student_ids))
                cursor.execute(
                    f'DELETE FROM achievements WHERE period_label = ? AND student_id IN ({placeholders})',
                    (period_label, *student_ids)
                )
            now = datetime.now().strftime("%Y-%m-%d")
            for a in awarded:
                cursor.execute(
                    'INSERT INTO achievements (student_id, type, period_label, date_awarded) VALUES (?, ?, ?, ?)',
                    (a["student_id"], a["type"], period_label, now)
                )
            conn.commit()

        return awarded

    def get_group_period_summary(self, group_id, date_from, date_to):
        reports = self.get_reports_in_range(group_id, date_from, date_to)
        report_ids = [r["id"] for r in reports]
        students = self.get_students_by_group(group_id)

        per_student = {s["id"]: {"student_name": s["name"], "records": []} for s in students}

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for rid in report_ids:
                att = cursor.execute('SELECT * FROM attendance WHERE report_id = ?', (rid,)).fetchall()
                hifz = {r["student_id"]: dict(r) for r in cursor.execute(
                    'SELECT * FROM memorization WHERE report_id = ?', (rid,)).fetchall()}
                muraj = {r["student_id"]: dict(r) for r in cursor.execute(
                    'SELECT * FROM revision WHERE report_id = ?', (rid,)).fetchall()}
                for a in att:
                    sid = a["student_id"]
                    if sid not in per_student:
                        continue
                    h = hifz.get(sid)
                    m = muraj.get(sid)
                    per_student[sid]["records"].append({
                        "status": a["status"],
                        "hifz_pages_count": (h.get("manual_pages_count") if h and h.get("manual_pages_count") else (h["pages_count"] if h else 0)),
                        "hifz_ayat_count": h["ayat_count"] if h else 0,
                        "murajaa_pages_count": (m.get("manual_pages_count") if m and m.get("manual_pages_count") else (m["pages_count"] if m else 0)),
                        "murajaa_ayat_count": m["ayat_count"] if m else 0,
                    })

        results = []
        for sid, data in per_student.items():
            stats = compute_student_period_stats(data["records"])
            stats["student_id"] = sid
            stats["student_name"] = data["student_name"]
            stats["hifz_sessions"] = sum(1 for r in data["records"] if (r.get("hifz_pages_count") or 0) > 0)
            stats["murajaa_sessions"] = sum(1 for r in data["records"] if (r.get("murajaa_pages_count") or 0) > 0)
            results.append(stats)

        results.sort(key=lambda r: r["hifz_pages_total"], reverse=True)

        group_summary = {
            "students_count": len(students),
            "reports_count": len(reports),
            "total_hifz_pages": sum(r["hifz_pages_total"] for r in results),
            "total_murajaa_pages": sum(r["murajaa_pages_total"] for r in results),
            "total_ayat": sum(r["hifz_ayat_total"] + r["murajaa_ayat_total"] for r in results),
            "total_present": sum(r["present"] for r in results),
            "total_absent": sum(r["absent"] for r in results),
        }

        return {"students": results, "summary": group_summary}
