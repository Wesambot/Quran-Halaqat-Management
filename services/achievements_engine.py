"""
محرك الإنجازات (Achievements Engine)
--------------------------------------
يحسب شارات/إنجازات الطلاب تلقائيًا من ملخص فترة معينة (ناتج
DBManager.get_group_period_summary)، دون أي اتصال مباشر بقاعدة البيانات
أو بالواجهة - وحدة حسابية بحتة قابلة للاختبار بمعزل عنهما.
"""


def compute_achievements(students_summary: list) -> list:
    """
    يستقبل قائمة ملخصات طلاب (كل عنصر فيه: student_id, student_name,
    hifz_pages_total, murajaa_pages_total, attendance_rate, total_days)
    ويُرجع قائمة إنجازات: [{"type": "...", "student_id":, "student_name":}].
    لا يمنح أي إنجاز لطالب بدون نشاط حقيقي (قيمة صفر) لتفادي شارات فارغة.
    """
    if not students_summary:
        return []

    results = []

    top_hifz = max(students_summary, key=lambda s: s["hifz_pages_total"])
    if top_hifz["hifz_pages_total"] > 0:
        results.append({"type": "📖 أكثر حفظًا", "student_id": top_hifz["student_id"], "student_name": top_hifz["student_name"]})

    top_murajaa = max(students_summary, key=lambda s: s["murajaa_pages_total"])
    if top_murajaa["murajaa_pages_total"] > 0:
        results.append({"type": "🔁 أكثر مراجعة", "student_id": top_murajaa["student_id"], "student_name": top_murajaa["student_name"]})

    top_attendance = max(students_summary, key=lambda s: s["attendance_rate"])
    if top_attendance["attendance_rate"] > 0:
        results.append({"type": "🔥 أعلى نسبة حضور", "student_id": top_attendance["student_id"], "student_name": top_attendance["student_name"]})

    for s in students_summary:
        if s["total_days"] > 0 and s["attendance_rate"] == 100:
            results.append({"type": "📅 انتظام كامل خلال الفترة", "student_id": s["student_id"], "student_name": s["student_name"]})

    scored = sorted(students_summary, key=lambda s: s["hifz_pages_total"] + s["murajaa_pages_total"], reverse=True)

    if scored and (scored[0]["hifz_pages_total"] + scored[0]["murajaa_pages_total"]) > 0:
        results.append({"type": "⭐ نجم الحلقة", "student_id": scored[0]["student_id"], "student_name": scored[0]["student_name"]})

    medals = ["🥇 المركز الأول", "🥈 المركز الثاني", "🥉 المركز الثالث"]
    for i, medal in enumerate(medals):
        if i < len(scored) and (scored[i]["hifz_pages_total"] + scored[i]["murajaa_pages_total"]) > 0:
            results.append({"type": medal, "student_id": scored[i]["student_id"], "student_name": scored[i]["student_name"]})

    return results
