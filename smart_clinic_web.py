"""Local-only Flask prototype for non-diagnostic triage and appointment scheduling."""

from __future__ import annotations

import hmac
import math
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template_string, request, session, url_for
from markupsafe import Markup


SPECIALTIES = (
    "طب الأسرة",
    "الباطنية",
    "الأطفال",
    "الجلدية",
    "العيون",
    "الأنف والأذن والحنجرة",
    "العظام",
    "النسائية والتوليد",
    "الأسنان",
)
SLOT_START = time(8, 0)
SLOT_END = time(17, 0)
SLOT_STEP_MINUTES = 15
DEFAULT_DURATION_MINUTES = 30
MAX_BOOKING_DAYS = 30
EMERGENCY_ANSWERS = (
    ("breathing_difficulty", "صعوبة شديدة في التنفس"),
    ("unconscious", "فقدان الوعي أو صعوبة الإيقاظ"),
    ("uncontrolled_bleeding", "نزيف شديد لا يتوقف"),
    ("stroke_signs", "ضعف مفاجئ في الوجه أو الذراع أو صعوبة الكلام"),
    ("severe_chest_pain", "ألم شديد في الصدر"),
)
SYMPTOM_SPECIALTIES = {
    "fever": "طب الأسرة",
    "cough": "طب الأسرة",
    "stomach": "الباطنية",
    "skin": "الجلدية",
    "eye": "العيون",
    "ear_nose_throat": "الأنف والأذن والحنجرة",
    "bone_joint": "العظام",
    "pregnancy": "النسائية والتوليد",
    "tooth": "الأسنان",
}

BASE_TEMPLATE = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} — Smart Clinic</title>
  <style>
    :root {
      color-scheme: light;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: #f3f7fa;
      color: #183044;
      font-synthesis: none;
      text-rendering: optimizeLegibility;
      --ink: #183044;
      --muted: #64788a;
      --line: #e1eaf0;
      --primary: #087f8c;
      --primary-dark: #066875;
      --surface: #fff;
    }
    * { box-sizing: border-box; }
    body { min-width: 320px; min-height: 100vh; margin: 0; display: flex; flex-direction: column; }
    .site-header { color: white; background: linear-gradient(115deg, #075e70, #087f8c 58%, #1196a0); box-shadow: 0 5px 20px #164e6330; }
    .header-inner { max-width: 1160px; margin: 0 auto; padding: 1rem 1.25rem .85rem; }
    .brand { display: flex; align-items: center; gap: .8rem; margin-bottom: 1rem; }
    .brand-mark { width: 2.5rem; height: 2.5rem; display: grid; place-items: center; border: 1px solid #ffffff70; border-radius: 12px; background: #ffffff20; font-size: 1.7rem; font-weight: 400; line-height: 1; }
    .brand h1 { margin: 0; font-size: 1.15rem; letter-spacing: -.02em; }
    .brand p { margin: .2rem 0 0; color: #d3f0f1; font-size: .82rem; }
    nav { display: flex; flex-wrap: wrap; gap: .4rem; }
    nav a { padding: .55rem .85rem; border: 1px solid transparent; border-radius: 8px; color: #e9fbfb; font-size: .92rem; text-decoration: none; transition: background .18s ease, border-color .18s ease; }
    nav a:hover, nav a[aria-current="page"] { border-color: #ffffff38; background: #ffffff20; color: white; }
    main { width: min(1160px, 100%); flex: 1; margin: 0 auto; padding: 1.7rem 1.25rem 2.5rem; }
    section, .card { margin: 0 0 1.25rem; padding: clamp(1.1rem, 2.5vw, 1.65rem); border: 1px solid var(--line); border-radius: 16px; background: var(--surface); box-shadow: 0 6px 22px #18304408; }
    h2 { margin: 0 0 1rem; color: var(--ink); font-size: clamp(1.25rem, 2vw, 1.55rem); letter-spacing: -.025em; }
    h3 { margin: 1.5rem 0 .65rem; color: var(--ink); font-size: 1.05rem; }
    p { line-height: 1.75; }
    label { display: block; margin: 1rem 0 .4rem; color: #304b5e; font-weight: 650; }
    input, select { max-width: 100%; min-height: 2.8rem; padding: .65rem .8rem; border: 1px solid #cbd9e2; border-radius: 9px; background: white; color: var(--ink); font: inherit; transition: border-color .18s ease, box-shadow .18s ease; }
    input[type=text], input[type=date], input[type=number], select { width: min(100%, 32rem); }
    input:focus, select:focus, button:focus-visible, a:focus-visible { outline: 3px solid #20a4aa55; outline-offset: 2px; border-color: var(--primary); }
    input[type=checkbox] { width: 1.1rem; min-height: 1.1rem; margin: 0; accent-color: var(--primary); }
    .check { display: flex; align-items: center; gap: .65rem; margin: .5rem 0; padding: .7rem .8rem; border: 1px solid #e7eef2; border-radius: 10px; background: #fbfdfe; color: #304b5e; font-weight: 450; cursor: pointer; transition: border-color .18s ease, background .18s ease; }
    .check:hover { border-color: #a9d8db; background: #f2fbfb; }
    button, .button { display: inline-flex; align-items: center; justify-content: center; min-height: 2.75rem; margin-top: .8rem; padding: .65rem 1rem; border: 1px solid var(--primary); border-radius: 9px; background: var(--primary); color: white; font: inherit; font-weight: 650; text-decoration: none; cursor: pointer; transition: background .18s ease, transform .18s ease, box-shadow .18s ease; }
    button:hover, .button:hover { transform: translateY(-1px); border-color: var(--primary-dark); background: var(--primary-dark); box-shadow: 0 5px 13px #087f8c2b; }
    .notice { padding: .9rem 1rem; border: 1px solid #f2d594; border-right: 4px solid #d97706; border-radius: 10px; background: #fff9e9; color: #624719; }
    .danger { border-color: #f2c5c5; border-right-color: #c24141; background: #fff3f2; color: #762f2f; }
    .success { border-color: #b8e4d1; border-right-color: #198754; background: #effaf4; color: #20593d; }
    .muted { color: var(--muted); }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .9rem; margin: 1.2rem 0; }
    .metric { min-height: 105px; padding: 1rem; border: 1px solid #e1eef0; border-radius: 12px; background: linear-gradient(145deg, #f8fcfc, #f1f8f9); color: #4a6374; }
    .metric strong { display: block; margin-bottom: .25rem; color: var(--primary-dark); font-size: 1.8rem; line-height: 1.2; }
    table { width: 100%; margin-top: 1rem; border-collapse: separate; border-spacing: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 11px; }
    th, td { padding: .8rem .75rem; border-bottom: 1px solid var(--line); text-align: right; vertical-align: middle; }
    th { background: #f5f9fa; color: #4b6373; font-size: .88rem; font-weight: 700; white-space: nowrap; }
    tbody tr:last-child td { border-bottom: 0; }
    tbody tr:hover { background: #f8fbfc; }
    td form { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; }
    td form select { width: auto; min-height: 2.45rem; }
    td form button { min-height: 2.45rem; margin: 0; padding: .45rem .7rem; font-size: .88rem; }
    .messages { padding: 0; list-style: none; }
    .messages li { margin: 0 0 .65rem; padding: .8rem 1rem; border: 1px solid #c9e2f5; border-right: 4px solid #2680b9; border-radius: 9px; background: #f0f8fd; color: #294d64; }
    footer { padding: 1.1rem 1rem; border-top: 1px solid var(--line); background: #fff; color: var(--muted); font-size: .88rem; text-align: center; }
    @media (max-width: 650px) {
      .header-inner { padding: .9rem 1rem .75rem; }
      nav { gap: .3rem; }
      nav a { padding: .5rem .65rem; font-size: .87rem; }
      main { padding: 1rem .85rem 2rem; }
      section, .card { border-radius: 13px; }
      table { display: block; overflow-x: auto; white-space: nowrap; }
      .metrics { grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
    }
  </style>
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">+</span>
        <div><h1>Smart Clinic</h1><p>نموذج محلي تجريبي لإدارة العيادة</p></div>
      </div>
      <nav aria-label="التنقل الرئيسي">
        <a href="{{ url_for('dashboard') }}" {% if request.endpoint == 'dashboard' %}aria-current="page"{% endif %}>الرئيسية</a>
        <a href="{{ url_for('triage') }}" {% if request.endpoint == 'triage' %}aria-current="page"{% endif %}>توجيه أولي للأعراض</a>
        <a href="{{ url_for('book') }}" {% if request.endpoint == 'book' %}aria-current="page"{% endif %}>حجز موعد</a>
        <a href="{{ url_for('analytics') }}" {% if request.endpoint == 'analytics' %}aria-current="page"{% endif %}>تحليل الحضور</a>
      </nav>
    </div>
  </header>
  <main id="main-content">
    {% with messages = get_flashed_messages() %}
      {% if messages %}<ul class="messages">{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
    {% endwith %}
    {{ content }}
  </main>
  <footer>نموذج تجريبي محلي فقط — لا تستخدمه لتشخيص الحالات أو تخزين بيانات مرضى حقيقية.</footer>
</body>
</html>"""


def _render(title: str, template: str, **context):
    content = render_template_string(template, **context)
    return render_template_string(BASE_TEMPLATE, title=title, content=Markup(content))


def _get_connection(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _connection(path: str):
    connection = _get_connection(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with _connection(path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_code TEXT NOT NULL UNIQUE,
                specialty TEXT NOT NULL,
                scheduled_for TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
                urgency TEXT NOT NULL CHECK(urgency IN ('routine', 'same_day')),
                status TEXT NOT NULL CHECK(status IN ('scheduled', 'attended', 'no_show', 'cancelled')),
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_appointments_schedule ON appointments(specialty, scheduled_for, status)"
        )


def _new_csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def _validate_csrf() -> None:
    expected = session.get("_csrf_token", "")
    submitted = request.form.get("_csrf_token", "")
    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        abort(400, description="رمز حماية النموذج غير صالح. أعد تحميل الصفحة وحاول مجدداً.")


def classify_symptoms(form) -> dict[str, str | bool]:
    emergency = any(form.get(key) == "yes" for key, _ in EMERGENCY_ANSWERS)
    selected = [key for key in SYMPTOM_SPECIALTIES if form.get(key) == "yes"]
    selected_specialties = {SYMPTOM_SPECIALTIES[key] for key in selected}
    specialty = next(iter(selected_specialties)) if len(selected_specialties) == 1 else "طب الأسرة"
    high_fever = False
    temperature = form.get("temperature", "").strip()
    if temperature:
        try:
            temperature_value = float(temperature)
        except ValueError as exc:
            raise ValueError("أدخل درجة حرارة صحيحة أو اترك الحقل فارغاً.") from exc
        if not math.isfinite(temperature_value) or not 30 <= temperature_value <= 45:
            raise ValueError("درجة الحرارة يجب أن تكون بين 30 و45 مئوية.")
        high_fever = temperature_value >= 39
    severe_pain = form.get("severe_pain") == "yes"
    if emergency:
        urgency = "emergency"
        message = "قد تكون هناك علامة خطر. لا تنتظر موعداً عبر النظام؛ توجّه فوراً إلى الطوارئ أو اتصل برقم الطوارئ المحلي."
    elif high_fever or severe_pain:
        urgency = "same_day"
        message = "يُفضّل التواصل مع مقدم رعاية صحية اليوم لتحديد الخطوة المناسبة."
    else:
        urgency = "routine"
        message = "يمكنك طلب موعد اعتيادي مع التخصص المقترح أو استشارة مقدم رعاية صحية."
    return {
        "emergency": emergency,
        "specialty": specialty,
        "urgency": urgency,
        "message": message,
    }


def _find_slot(connection: sqlite3.Connection, specialty: str, earliest_date: date, urgency: str):
    duration = DEFAULT_DURATION_MINUTES
    horizon = 1 if urgency == "same_day" else MAX_BOOKING_DAYS
    for day_offset in range(horizon):
        slot_date = earliest_date + timedelta(days=day_offset)
        candidate = datetime.combine(slot_date, SLOT_START)
        close = datetime.combine(slot_date, SLOT_END)
        rows = connection.execute(
            """SELECT scheduled_for, duration_minutes
               FROM appointments
               WHERE specialty = ? AND status = 'scheduled'
                 AND scheduled_for >= ? AND scheduled_for < ?""",
            (specialty, candidate.isoformat(timespec="minutes"), close.isoformat(timespec="minutes")),
        ).fetchall()
        occupied = []
        for row in rows:
            start = datetime.fromisoformat(row["scheduled_for"])
            occupied.append((start, start + timedelta(minutes=row["duration_minutes"])))
        while candidate + timedelta(minutes=duration) <= close:
            end = candidate + timedelta(minutes=duration)
            if not any(candidate < occupied_end and occupied_start < end for occupied_start, occupied_end in occupied):
                return candidate, duration
            candidate += timedelta(minutes=SLOT_STEP_MINUTES)
    return None, duration


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SMART_CLINIC_SECRET") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    db_path = database_path or os.environ.get(
        "SMART_CLINIC_DB",
        str(Path.home() / ".hospital_manager" / "smart_clinic_web.sqlite"),
    )
    app.config["DATABASE"] = str(Path(db_path).expanduser())
    init_db(app.config["DATABASE"])

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": _new_csrf_token}

    @app.get("/")
    def dashboard():
        with _connection(app.config["DATABASE"]) as connection:
            metrics = {
                "scheduled": connection.execute(
                    "SELECT COUNT(*) FROM appointments WHERE status='scheduled'"
                ).fetchone()[0],
                "today": connection.execute(
                    "SELECT COUNT(*) FROM appointments WHERE status='scheduled' AND date(scheduled_for)=date('now','localtime')"
                ).fetchone()[0],
                "specialties": len(SPECIALTIES),
            }
            recent = connection.execute(
                """SELECT id, visit_code, specialty, scheduled_for, urgency, status
                   FROM appointments ORDER BY scheduled_for DESC LIMIT 10"""
            ).fetchall()
        return _render(
            "الرئيسية",
            """<section>
              <h2>لوحة العيادة</h2>
              <p class="notice">هذا النموذج لا يستخدم الذكاء الاصطناعي ولا يشخّص الأمراض. توجيه الأعراض قواعد إدارية أولية فقط.</p>
              <div class="metrics">
                <div class="metric"><strong>{{ metrics.scheduled }}</strong>مواعيد قائمة</div>
                <div class="metric"><strong>{{ metrics.today }}</strong>مواعيد اليوم</div>
                <div class="metric"><strong>{{ metrics.specialties }}</strong>تخصصاً متاحاً للحجز</div>
              </div>
              <p><a class="button" href="{{ url_for('triage') }}">ابدأ التوجيه الأولي</a>
                 <a class="button" href="{{ url_for('book') }}">احجز موعداً</a></p>
            </section>
            <section><h2>أحدث المواعيد</h2>
              {% if recent %}<table><thead><tr><th>رمز الزيارة</th><th>التخصص</th><th>الموعد</th><th>الحالة</th><th>تحديث الحضور التجريبي</th></tr></thead><tbody>
              {% for row in recent %}<tr><td>{{ row.visit_code }}</td><td>{{ row.specialty }}</td><td>{{ row.scheduled_for }}</td><td>{{ status_labels[row.status] }}</td><td>
                {% if row.status == 'scheduled' %}
                  <form method="post" action="{{ url_for('update_status', appointment_id=row.id) }}">
                    <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
                    <select name="status"><option value="attended">حضر</option><option value="no_show">لم يحضر</option><option value="cancelled">أُلغي</option></select>
                    <button type="submit">حفظ الحالة</button>
                  </form>
                {% else %}—{% endif %}
              </td></tr>{% endfor %}
              </tbody></table>{% else %}<p class="muted">لا توجد مواعيد محفوظة بعد.</p>{% endif %}
            </section>""",
            metrics=metrics,
            recent=recent,
            status_labels={"scheduled": "مجدول", "attended": "حضر", "no_show": "لم يحضر", "cancelled": "ملغي"},
        )

    @app.route("/triage", methods=["GET", "POST"])
    def triage():
        result = None
        if request.method == "POST":
            _validate_csrf()
            session.pop("suggested_specialty", None)
            session.pop("suggested_urgency", None)
            try:
                result = classify_symptoms(request.form)
            except ValueError as exc:
                flash(str(exc))
            else:
                if not result["emergency"]:
                    session["suggested_specialty"] = result["specialty"]
                    session["suggested_urgency"] = result["urgency"]
        return _render(
            "توجيه أولي",
            """<section>
              <h2>توجيه إداري أولي للأعراض</h2>
              <p class="notice danger"><strong>ليس تشخيصاً طبياً أو بديلاً عن الطبيب.</strong> لا تدخل اسماً أو بيانات تعريفية. إذا كانت الحالة طارئة فاتصل بالطوارئ المحلية.</p>
              <form method="post">
                <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
                <h3>هل توجد أي من علامات الخطر التالية الآن؟</h3>
                {% for key, label in emergency_answers %}
                  <label class="check"><input type="checkbox" name="{{ key }}" value="yes"> {{ label }}</label>
                {% endfor %}
                <label for="temperature">درجة الحرارة إن كانت مقاسة (°م، اختياري)</label>
                <input id="temperature" name="temperature" type="number" min="30" max="45" step="0.1">
                <label class="check"><input type="checkbox" name="severe_pain" value="yes"> ألم شديد أو متفاقم</label>
                <h3>اختر الأعراض لتوجيهك إلى تخصص عام</h3>
                {% for key, label, _specialty in symptom_options %}
                  <label class="check"><input type="checkbox" name="{{ key }}" value="yes"> {{ label }}</label>
                {% endfor %}
                <button type="submit">عرض التوجيه الأولي</button>
              </form>
            </section>
            {% if result %}
              <section class="notice {{ 'danger' if result.emergency else 'success' }}">
                <h2>التوجيه المقترح: {{ urgency_labels[result.urgency] }}</h2>
                <p>{{ result.message }}</p>
                {% if not result.emergency %}
                  <p>التخصص العام المقترح: <strong>{{ result.specialty }}</strong></p>
                  <a class="button" href="{{ url_for('book', specialty=result.specialty) }}">عرض المواعيد المتاحة</a>
                {% endif %}
                <p class="muted">النتيجة لا تحدد المرض ولا تقدّر احتمال الإصابة. اعتمد على مختص صحي.</p>
              </section>
            {% endif %}""",
            result=result,
            emergency_answers=EMERGENCY_ANSWERS,
            symptom_options=[
                (key, label, SYMPTOM_SPECIALTIES[key])
                for key, label in (
                    ("fever", "حمّى أو أعراض عامة"),
                    ("cough", "سعال أو أعراض تنفسية غير شديدة"),
                    ("stomach", "أعراض هضمية"),
                    ("skin", "مشكلة جلدية"),
                    ("eye", "مشكلة في العين"),
                    ("ear_nose_throat", "أعراض الأذن أو الأنف أو الحلق"),
                    ("bone_joint", "ألم بالعظام أو المفاصل"),
                    ("pregnancy", "استفسار متعلق بالحمل"),
                    ("tooth", "ألم أو مشكلة بالأسنان"),
                )
            ],
            urgency_labels={"emergency": "طوارئ", "same_day": "تواصل اليوم", "routine": "موعد اعتيادي"},
        )

    @app.route("/book", methods=["GET", "POST"])
    def book():
        result = None
        selected_specialty = request.args.get("specialty", "")
        today = date.today()
        if request.method == "POST":
            _validate_csrf()
            selected_specialty = request.form.get("specialty", "")
            requested_date = request.form.get("requested_date", "")
            urgency = request.form.get("urgency", "routine")
            if selected_specialty not in SPECIALTIES:
                flash("اختر تخصصاً من القائمة.")
            elif urgency not in ("routine", "same_day"):
                flash("مستوى الحجز غير صالح.")
            else:
                try:
                    start_date = date.fromisoformat(requested_date)
                    if start_date < today or start_date > today + timedelta(days=MAX_BOOKING_DAYS):
                        raise ValueError
                except ValueError:
                    flash(f"اختر تاريخاً بين {today.isoformat()} و{(today + timedelta(days=MAX_BOOKING_DAYS)).isoformat()}.")
                else:
                    if urgency == "same_day" and start_date != today:
                        flash("للحاجة إلى مراجعة اليوم اختر تاريخ اليوم، أو تواصل مع العيادة مباشرة.")
                    else:
                        connection = _get_connection(app.config["DATABASE"])
                        try:
                            connection.execute("BEGIN IMMEDIATE")
                            slot, duration = _find_slot(connection, selected_specialty, start_date, urgency)
                            if slot is None:
                                connection.rollback()
                                flash("لا توجد فترة متاحة ضمن المدة المحددة؛ تواصل مع العيادة.")
                            else:
                                visit_code = secrets.token_hex(4).upper()
                                cursor = connection.execute(
                                    """INSERT INTO appointments
                                       (visit_code, specialty, scheduled_for, duration_minutes, urgency, status, created_at)
                                       VALUES (?, ?, ?, ?, ?, 'scheduled', ?)""",
                                    (
                                        visit_code,
                                        selected_specialty,
                                        slot.isoformat(timespec="minutes"),
                                        duration,
                                        urgency,
                                        datetime.now().astimezone().isoformat(timespec="seconds"),
                                    ),
                                )
                                connection.commit()
                                result = {
                                    "id": cursor.lastrowid,
                                    "visit_code": visit_code,
                                    "specialty": selected_specialty,
                                    "scheduled_for": slot.strftime("%Y-%m-%d %H:%M"),
                                }
                                session.pop("suggested_specialty", None)
                                session.pop("suggested_urgency", None)
                        except sqlite3.Error:
                            connection.rollback()
                            app.logger.exception("Appointment booking failed")
                            abort(500, description="تعذر حفظ الموعد. حاول لاحقاً.")
                        finally:
                            connection.close()
        if selected_specialty not in SPECIALTIES:
            selected_specialty = session.get("suggested_specialty", SPECIALTIES[0])
        selected_urgency = session.pop("suggested_urgency", "routine")
        return _render(
            "حجز موعد",
            """<section>
              <h2>حجز موعد تجريبي</h2>
              <p class="notice">لا ندخل اسماً أو هاتفاً في هذا النموذج. احتفظ برمز الزيارة الظاهر بعد الحجز. هذا النموذج محلي وليس قناة حجز فعلية للمشفى.</p>
              <form method="post">
                <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
                <label for="specialty">التخصص</label>
                <select id="specialty" name="specialty" required>
                  {% for specialty in specialties %}<option value="{{ specialty }}" {% if specialty == selected_specialty %}selected{% endif %}>{{ specialty }}</option>{% endfor %}
                </select>
                <label for="requested_date">ابدأ البحث من تاريخ</label>
                <input id="requested_date" name="requested_date" type="date" min="{{ today }}" max="{{ latest }}" value="{{ today }}" required>
                <label for="urgency">نوع الموعد</label>
                <select id="urgency" name="urgency">
                  <option value="routine" {% if selected_urgency == 'routine' %}selected{% endif %}>اعتيادي</option>
                  <option value="same_day" {% if selected_urgency == 'same_day' %}selected{% endif %}>تواصل اليوم (ليس للطوارئ)</option>
                </select>
                <button type="submit">ابحث واحجز أقرب فترة متاحة</button>
              </form>
            </section>
            {% if result %}<section class="notice success"><h2>تم حجز فترة تجريبية</h2>
              <p>رمز الزيارة: <strong>{{ result.visit_code }}</strong></p>
              <p>التخصص: {{ result.specialty }} — الموعد: {{ result.scheduled_for }}</p>
              <p>هذا تأكيد محلي للتجربة وليس تأكيداً من منشأة صحية.</p>
            </section>{% endif %}""",
            specialties=SPECIALTIES,
            selected_specialty=selected_specialty,
            selected_urgency=selected_urgency,
            today=today.isoformat(),
            latest=(today + timedelta(days=MAX_BOOKING_DAYS)).isoformat(),
            result=result,
        )

    @app.get("/analytics")
    def analytics():
        with _connection(app.config["DATABASE"]) as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM appointments WHERE status IN ('attended','no_show')"
            ).fetchone()[0]
            no_shows = connection.execute(
                "SELECT COUNT(*) FROM appointments WHERE status='no_show'"
            ).fetchone()[0]
            attended = total - no_shows
            rows = connection.execute(
                """SELECT specialty,
                          SUM(CASE WHEN status IN ('attended','no_show') THEN 1 ELSE 0 END) AS resolved,
                          SUM(CASE WHEN status='no_show' THEN 1 ELSE 0 END) AS no_shows
                   FROM appointments GROUP BY specialty ORDER BY specialty"""
            ).fetchall()
            pending = connection.execute(
                """SELECT id, visit_code, specialty, scheduled_for FROM appointments
                   WHERE status='scheduled' ORDER BY scheduled_for LIMIT 50"""
            ).fetchall()
        rate = round(no_shows / total * 100, 1) if total else None
        return _render(
            "تحليل الحضور",
            """<section>
              <h2>تحليل تاريخي وصفي للحضور</h2>
              <p class="notice">هذه إحصاءات من سجلات مكتملة فقط، وليست نموذجاً تنبؤياً. لا تتوفر بيانات كافية لتوقع احتمال غياب فرد.</p>
              <div class="metrics">
                <div class="metric"><strong>{{ attended }}</strong>حضروا</div>
                <div class="metric"><strong>{{ no_shows }}</strong>لم يحضروا</div>
                <div class="metric"><strong>{{ (rate|string + '%') if rate is not none else '—' }}</strong>معدل الغياب التاريخي</div>
              </div>
              {% if by_specialty %}<table><thead><tr><th>التخصص</th><th>سجلات مكتملة</th><th>غياب</th><th>النسبة التاريخية</th></tr></thead><tbody>
                {% for row in by_specialty %}<tr><td>{{ row.specialty }}</td><td>{{ row.resolved }}</td><td>{{ row.no_shows }}</td>
                <td>{{ ((row.no_shows / row.resolved * 100)|round(1)) if row.resolved else 0 }}%</td></tr>{% endfor %}
              </tbody></table>{% else %}<p>لا توجد نتائج حضور/غياب بعد.</p>{% endif %}
              <h3>مواعيد بانتظار تسجيل الحضور</h3>
              {% if pending %}<table><thead><tr><th>رمز الزيارة</th><th>التخصص</th><th>الموعد</th><th>الحالة</th></tr></thead><tbody>
              {% for row in pending %}<tr><td>{{ row.visit_code }}</td><td>{{ row.specialty }}</td><td>{{ row.scheduled_for }}</td><td>
                <form method="post" action="{{ url_for('update_status', appointment_id=row.id) }}">
                  <input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
                  <select name="status"><option value="attended">حضر</option><option value="no_show">لم يحضر</option><option value="cancelled">أُلغي</option></select>
                  <button type="submit">حفظ الحالة</button>
                </form>
              </td></tr>{% endfor %}
              </tbody></table>{% else %}<p>لا توجد مواعيد معلقة.</p>{% endif %}
            </section>""",
            attended=attended,
            no_shows=no_shows,
            rate=rate,
            by_specialty=rows,
            pending=pending,
        )

    @app.post("/appointments/<int:appointment_id>/status")
    def update_status(appointment_id: int):
        _validate_csrf()
        status = request.form.get("status", "")
        if status not in ("attended", "no_show", "cancelled"):
            abort(400, description="حالة الموعد غير صالحة.")
        with _connection(app.config["DATABASE"]) as connection:
            cursor = connection.execute(
                "UPDATE appointments SET status=? WHERE id=? AND status='scheduled'",
                (status, appointment_id),
            )
            if cursor.rowcount == 0:
                abort(404, description="الموعد غير موجود أو تم تحديثه سابقاً.")
        flash("تم تحديث حالة الموعد التجريبي.")
        return redirect(url_for("analytics"))

    @app.errorhandler(400)
    def bad_request(error):
        return _render("طلب غير صالح", "<section class='notice danger'><h2>تعذر تنفيذ الطلب</h2><p>{{ message }}</p><a href='{{ url_for('dashboard') }}'>العودة للرئيسية</a></section>", message=error.description), 400

    return app


if __name__ == "__main__":
    if os.environ.get("SMART_CLINIC_ALLOW_REMOTE") == "1":
        raise SystemExit("Remote binding is intentionally disabled for this prototype.")
    app = create_app()
    app.run(host="127.0.0.1", port=int(os.environ.get("SMART_CLINIC_PORT", "5000")), debug=False)
