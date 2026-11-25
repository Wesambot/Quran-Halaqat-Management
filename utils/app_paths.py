"""
وحدة إدارة مسارات التخزين الخاصة بالتطبيق.

الهدف: عدم تخزين أي بيانات (قاعدة بيانات، نسخ احتياطية، ملفات PDF، سجلات)
داخل مجلد المشروع نفسه، بل في مجلد بيانات التطبيق الرسمي الخاص بكل نظام تشغيل،
بحيث يعمل التطبيق مباشرة بعد تحويله إلى APK أو EXE دون أي تعديل يدوي.

أولوية تحديد المسار:
1) إن كان التطبيق يعمل عبر Flet (flet run / تطبيق مبني)، فإن Flet نفسه يوفر
   متغير البيئة FLET_APP_STORAGE_DATA ويشير مباشرة إلى مجلد بيانات صحيح
   ومُهيأ مسبقًا لكل منصة (Windows / Linux / macOS / Android). هذا هو
   الخيار المفضّل دائمًا لأنه الطريقة الرسمية الموصى بها من Flet.
2) إن لم يكن هذا المتغير موجودًا (مثلاً أثناء التطوير بتشغيل "python main.py"
   مباشرة خارج flet run)، يتم تحديد مسار مناسب يدويًا حسب نظام التشغيل:
   - Windows -> %LOCALAPPDATA%/QuranHalaqat
   - macOS   -> ~/Library/Application Support/QuranHalaqat
   - Linux   -> ~/.local/share/QuranHalaqat
"""

import os
import sys
import platform
from pathlib import Path


APP_FOLDER_NAME = "QuranHalaqat"


class StorageError(Exception):
    """يُرفع عند تعذر إنشاء أو الكتابة في مجلد بيانات التطبيق."""
    pass


class AppPaths:
    """
    توفر جميع المسارات التي يحتاجها التطبيق لتخزين بياناته،
    وتضمن إنشاء المجلدات المطلوبة تلقائيًا عند أول تشغيل.
    """

    def __init__(self):
        self.base_dir: Path = self._resolve_base_dir()
        self._ensure_directories()
        self._check_writable()

    # ---------------------------------------------------------------
    # تحديد المجلد الأساسي حسب المنصة
    # ---------------------------------------------------------------
    def _resolve_base_dir(self) -> Path:
        # 1) المسار الرسمي الذي يوفره Flet نفسه عند التشغيل الفعلي للتطبيق
        flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
        if flet_storage:
            return Path(flet_storage)

        # 2) fallback يدوي لبيئة التطوير (تشغيل مباشر بدون flet run)
        system = platform.system()

        if system == "Windows":
            base = os.getenv("LOCALAPPDATA") or str(Path.home())
            return Path(base) / APP_FOLDER_NAME

        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME

        # Linux وأي نظام آخر يشبه يونكس (وأندرويد عند التشغيل خارج flet)
        return Path.home() / ".local" / "share" / APP_FOLDER_NAME

    # ---------------------------------------------------------------
    # إنشاء بنية المجلدات المطلوبة
    # ---------------------------------------------------------------
    def _ensure_directories(self):
        try:
            for path in [
                self.base_dir,
                self.backup_dir,
                self.pdf_dir,
                self.logs_dir,
            ]:
                path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(
                f"تعذر إنشاء مجلدات بيانات التطبيق في المسار:\n{self.base_dir}\n\nالسبب: {e}"
            )

    # ---------------------------------------------------------------
    # التحقق من إمكانية الكتابة فعليًا قبل إنشاء قاعدة البيانات
    # ---------------------------------------------------------------
    def _check_writable(self):
        test_file = self.base_dir / ".write_test"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except OSError as e:
            raise StorageError(
                f"لا توجد صلاحية للكتابة في مجلد بيانات التطبيق:\n{self.base_dir}\n\nالسبب: {e}"
            )

    # ---------------------------------------------------------------
    # المسارات المتاحة للاستخدام في بقية التطبيق
    # ---------------------------------------------------------------
    @property
    def database_path(self) -> Path:
        return self.base_dir / "database.db"

    @property
    def backup_dir(self) -> Path:
        return self.base_dir / "backup"

    @property
    def pdf_dir(self) -> Path:
        return self.base_dir / "pdf"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def settings_file(self) -> Path:
        return self.base_dir / "settings.json"
