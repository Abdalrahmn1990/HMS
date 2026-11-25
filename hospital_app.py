"""Local desktop prototype for hospital workflows. Run with: python hospital_app.py"""

from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import shutil
import sqlite3
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from urllib.parse import quote


APP_DIR = Path.home() / ".hospital_manager"
DB_PATH = APP_DIR / "hospital.db"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

USERS = {
    "admin": ("1234", "د.عبدالرحمن بهجت العثمان", "admin"),
    "doctor": ("1234", "د. ليلى ناصر", "doctor"),
    "reception": ("1234", "سامر العلي", "reception"),
}

DEFAULT_CLINICS = [
    {"id": 1, "name": "عيادة القلب", "specialty": "قلبية", "icon": "❤️", "description": "أمراض القلب والأوعية الدموية", "status": "مفتوحة"},
    {"id": 2, "name": "عيادة الأطفال", "specialty": "أطفال", "icon": "🧸", "description": "طب الأطفال ومتابعة النمو", "status": "مفتوحة"},
    {"id": 3, "name": "عيادة الطوارئ", "specialty": "طوارئ", "icon": "🚑", "description": "استقبال الحالات العاجلة", "status": "مفتوحة"},
    {"id": 4, "name": "عيادة الجراحة العامة", "specialty": "جراحة عامة", "icon": "🩺", "description": "الجراحة العامة والمتابعة", "status": "مفتوحة"},
    {"id": 5, "name": "عيادة الباطنية", "specialty": "باطنية", "icon": "🫁", "description": "الأمراض الباطنية", "status": "مفتوحة"},
    {"id": 6, "name": "عيادة العظام", "specialty": "عظام", "icon": "🦴", "description": "العظام والمفاصل", "status": "مفتوحة"},
    {"id": 7, "name": "عيادة الجلدية", "specialty": "جلدية", "icon": "🧴", "description": "الأمراض الجلدية", "status": "مفتوحة"},
    {"id": 8, "name": "عيادة العيون", "specialty": "عيون", "icon": "👁️", "description": "طب وجراحة العيون", "status": "مفتوحة"},
    {"id": 9, "name": "عيادة الأنف والأذن والحنجرة", "specialty": "أنف وأذن وحنجرة", "icon": "👂", "description": "الأنف والأذن والحنجرة", "status": "مفتوحة"},
    {"id": 10, "name": "عيادة النسائية والتوليد", "specialty": "نسائية وتوليد", "icon": "🌸", "description": "صحة المرأة والولادة", "status": "مفتوحة"},
    {"id": 11, "name": "عيادة الأسنان", "specialty": "أسنان", "icon": "🦷", "description": "طب الأسنان", "status": "مفتوحة"},
    {"id": 12, "name": "عيادة الأعصاب", "specialty": "أعصاب", "icon": "🧠", "description": "الأمراض العصبية", "status": "مفتوحة"},
    {"id": 13, "name": "عيادة التبرع بالدم", "specialty": "تبرع بالدم", "icon": "🩸", "description": "تسجيل المتبرعين والتبرعات بالدم ومكوناته", "status": "مفتوحة"},
]

DEMO_MEDICATION_CATALOG = (
    ("مسكنات ومضادات التهاب", (
        "سيليكوكسيب", "كيتوبروفين", "ميلوكسيكام", "إيتوريكوكسيب", "حمض الميفيناميك",
        "إندوميثاسين", "بيروكسيكام", "ميثاميزول", "ليدوكايين", "ديكلوفيناك موضعي",
    )),
    ("مضادات حيوية", (
        "سيفالكسين", "سيفوروكسيم", "سيفيكسيم", "سيفترياكسون", "أزيثروميسين",
        "كلاريثروميسين", "دوكسيسيكلين", "سيبروفلوكساسين", "ميترونيدازول", "كليندامايسين",
    )),
    ("مضادات فطريات وفيروسات", (
        "فلوكونازول", "إيتراكونازول", "تيربينافين", "نيستاتين", "أسيكلوفير",
        "فالاسيكلوفير", "أوسيلتاميفير", "لاميفودين", "كيتوكونازول", "كلوتريمازول مهبلي",
    )),
    ("أدوية الجهاز الهضمي", (
        "بانتوبرازول", "لانسوبرازول", "فاموتيدين", "دومبيريدون", "ميتوكلوبراميد",
        "أوندانسيترون", "لاكتولوز", "محلول الإماهة الفموية", "سيميثيكون", "ميسالازين",
    )),
    ("القلب والأوعية", (
        "أملوديبين", "ليسينوبريل", "لوسارتان", "فالسارتان", "بيسوبرولول",
        "ميتوبرولول", "أتورفاستاتين", "روسوفاستاتين", "كلوبيدوغريل", "فوروسيميد",
    )),
    ("أدوية السكري", (
        "ميتفورمين", "غليميبيريد", "غليكلازيد", "سيتاغلبتين", "ليناگلبتين",
        "إمباغليفلوزين", "داباغليفلوزين", "إنسولين غلارجين", "إنسولين عادي", "إنسولين أسبارت",
    )),
    ("الجهاز التنفسي", (
        "سالبوتامول", "بوديزونيد", "إبراتروبيوم", "مونتيلوكاست", "أسيتيل سيستئين",
        "ديكستروميثورفان", "أمبروكسول", "ثيوفيلين", "فلوتيكازون بخاخ", "محلول ملحي للاستنشاق",
    )),
    ("الحساسية", (
        "سيتريزين", "لوراتادين", "فيكسوفينادين", "ديسلوراتادين", "كلورفينيرامين",
        "هيدروكسيزين", "كيتوتيفين", "أزيلاستين", "كروموغليكات الصوديوم", "ليفوسيتريزين",
    )),
    ("الفيتامينات والمعادن", (
        "فيتامين د3", "فيتامين ج", "فيتامين ب12", "حمض الفوليك", "كبريتات الحديدوز",
        "كربونات الكالسيوم", "أكسيد المغنيسيوم", "كبريتات الزنك", "متعدد الفيتامينات", "ثيامين",
    )),
    ("مستلزمات وأدوية متنوعة", (
        "هيدروكورتيزون كريم", "ميوبيروسين مرهم", "حمض الفيوسيديك", "أدابالين جل", "دموع اصطناعية",
        "تيمولول قطرة عين", "سيبروفلوكساسين قطرة عين", "لاتانوبروست قطرة عين", "محلول رينغر لاكتات", "محلول كلوريد الصوديوم",
    )),
)

DEFAULT_DATA = {
    "doctors": [
        {"id": 1, "name": "د. ليلى ناصر", "spec": "قلبية", "phone": "0911111111", "status": "نشط"},
        {"id": 2, "name": "د. أحمد الحسن", "spec": "جراحة عامة", "phone": "0922222222", "status": "نشط"},
        {"id": 3, "name": "د. رامي سعد", "spec": "طوارئ", "phone": "0933333333", "status": "نشط"},
    ],
    "nurses": [],
    "clinics": DEFAULT_CLINICS,
    "patients": [
        {"id": 1, "name": "سمير خليل", "age": 45, "gender": "ذكر", "phone": "0955555555", "status": "مستقر", "allergies": [], "chronicConditions": []},
        {"id": 2, "name": "هدى عمران", "age": 32, "gender": "أنثى", "phone": "0966666666", "status": "قيد العلاج", "allergies": [], "chronicConditions": []},
        {"id": 3, "name": "كرم يوسف", "age": 60, "gender": "ذكر", "phone": "0977777777", "status": "حرج", "allergies": [], "chronicConditions": []},
        {"id": 4, "name": "نور حمدان", "age": 28, "gender": "أنثى", "phone": "0988888888", "status": "مستقر", "allergies": [], "chronicConditions": []},
    ],
    "appts": [
        {"id": 1, "patient": "سمير خليل", "doctor": "د. ليلى ناصر", "date": date.today().isoformat(), "time": "09:30", "status": "مكتمل"},
        {"id": 2, "patient": "هدى عمران", "doctor": "د. أحمد الحسن", "date": date.today().isoformat(), "time": "10:15", "status": "بالانتظار"},
        {"id": 3, "patient": "كرم يوسف", "doctor": "د. رامي سعد", "date": date.today().isoformat(), "time": "11:00", "status": "عاجل"},
    ],
    "meds": [
        {"id": 1, "name": "باراسيتامول", "cat": "مسكنات", "qty": 120, "price": 500, "status": "متوفر"},
        {"id": 2, "name": "أموكسيسيلين", "cat": "مضادات حيوية", "qty": 8, "price": 1200, "status": "منخفض"},
        {"id": 3, "name": "أوميبرازول", "cat": "معدة", "qty": 0, "price": 900, "status": "نفد"},
    ],
    "labs": [
        {"id": 1, "patient": "سمير خليل", "type": "صورة دم كاملة", "date": date.today().isoformat(), "status": "جاهز"},
        {"id": 2, "patient": "هدى عمران", "type": "سكر صائم", "date": date.today().isoformat(), "status": "قيد التنفيذ"},
    ],
    "bills": [
        {"id": 1001, "patient": "سمير خليل", "amount": 75000, "balance": 0, "items": [{"description": "خدمات طبية", "quantity": 1, "unitPrice": 75000}], "date": date.today().isoformat(), "status": "مدفوعة", "paymentMethod": "نقدي", "insuranceCovered": 0, "insuranceCoverage": 0},
        {"id": 1002, "patient": "كرم يوسف", "amount": 150000, "balance": 150000, "items": [{"description": "خدمات طبية", "quantity": 1, "unitPrice": 150000}], "date": date.today().isoformat(), "status": "غير مدفوعة", "paymentMethod": "نقدي", "insuranceCovered": 0, "insuranceCoverage": 0},
    ],
    "prescriptions": [], "vitals": [],
    "wards": [{"id": 1, "name": "الجناح العام", "capacity": 12}],
    "beds": [{"id": 1, "ward": "الجناح العام", "room": "101", "number": "1", "patient": "", "status": "متاح"}],
    "payments": [], "insurance": [], "payroll": [], "attendance": [], "ratings": [], "attachments": [],
    "reminders": [], "activity": [], "patientNotes": [], "death_certificate_requests": [],
    "support_tickets": [], "medication_batches": [], "insurance_claims": [],
    "assets": [], "sterilization_cycles": [], "feedback": [], "service_prices": [],
    "donations": [], "messages": [], "operation_rooms": [
        {"id": 1, "name": "غرفة العمليات 1", "location": "الطابق الأول", "status": "متاحة"},
        {"id": 2, "name": "غرفة العمليات 2", "location": "الطابق الأول", "status": "متاحة"},
        {"id": 3, "name": "غرفة العمليات 3", "location": "الطابق الثاني", "status": "متاحة"},
    ],
    "surgeries": [],
}


def field(label, kind="text", default="", options=None):
    return {"label": label, "kind": kind, "default": default, "options": options or []}


PAGES = {
    "dashboard": {"title": "لوحة التحكم", "entity": None, "columns": []},
    "clinics": {"title": "إدارة العيادات", "entity": "clinics", "columns": [("name", "العيادة"), ("specialty", "التخصص"), ("description", "الوصف"), ("status", "الحالة")]},
    "doctors": {"title": "الأطباء", "entity": "doctors", "columns": [("name", "الاسم"), ("spec", "التخصص"), ("phone", "الهاتف"), ("status", "الحالة"), ("verification", "التحقق")]},
    "nurses": {"title": "التمريض", "entity": "nurses", "columns": [("name", "الاسم"), ("department", "القسم"), ("shift", "المناوبة"), ("status", "الحالة")]},
    "patients": {"title": "المرضى", "entity": "patients", "columns": [("name", "الاسم"), ("age", "العمر"), ("gender", "الجنس"), ("phone", "الهاتف"), ("status", "الحالة")]},
    "appts": {"title": "المواعيد", "entity": "appts", "columns": [("patient", "المريض"), ("doctor", "الطبيب"), ("date", "التاريخ"), ("time", "الوقت"), ("status", "الحالة"), ("wait_minutes", "مدة الانتظار (دقيقة)")]},
    "meds": {"title": "الصيدلية", "entity": "meds", "columns": [("name", "الدواء"), ("cat", "الفئة"), ("qty", "الكمية"), ("min_qty", "حد التنبيه"), ("price", "السعر"), ("status", "الحالة"), ("data_source", "مصدر البيانات")]},
    "labs": {"title": "المختبر", "entity": "labs", "columns": [("patient", "المريض"), ("type", "التحليل"), ("date", "التاريخ"), ("status", "الحالة")]},
    "bills": {"title": "الفواتير", "entity": "bills", "columns": [("id", "رقم الفاتورة"), ("patient", "المريض"), ("amount", "الإجمالي"), ("balance", "المتبقي"), ("date", "التاريخ"), ("status", "الحالة")]},
    "prescriptions": {"title": "الوصفات الطبية", "entity": "prescriptions", "columns": [("patient", "المريض"), ("doctor", "الطبيب"), ("medicine", "الدواء"), ("dosage", "الجرعة"), ("quantity", "الكمية"), ("date", "التاريخ")]},
    "vitals": {"title": "العلامات الحيوية", "entity": "vitals", "columns": [("patient", "المريض"), ("bloodPressure", "الضغط"), ("bloodSugar", "السكر"), ("temperature", "الحرارة"), ("pulse", "النبض"), ("date", "التاريخ")]},
    "wards": {"title": "الأجنحة", "entity": "wards", "columns": [("name", "الجناح"), ("capacity", "السعة"), ("occupied", "مشغول")]},
    "beds": {"title": "الأسرّة", "entity": "beds", "columns": [("ward", "الجناح"), ("room", "الغرفة"), ("number", "السرير"), ("patient", "المريض"), ("status", "الحالة")]},
    "payments": {"title": "المدفوعات", "entity": "payments", "columns": [("patient", "المريض"), ("bill_id", "الفاتورة"), ("amount", "المبلغ"), ("method", "الطريقة"), ("date", "التاريخ")]},
    "insurance": {"title": "التأمين", "entity": "insurance", "columns": [("patient", "المريض"), ("company", "الشركة"), ("coverage", "التغطية %")]},
    "payroll": {"title": "الرواتب", "entity": "payroll", "columns": [("employee", "الموظف"), ("base", "الراتب الأساسي"), ("deductions", "الخصومات"), ("advance", "السلف"), ("net", "الصافي"), ("date", "الشهر")]},
    "attendance": {"title": "الحضور والانصراف", "entity": "attendance", "columns": [("employee", "الموظف"), ("department", "القسم"), ("shift", "المناوبة"), ("date", "التاريخ"), ("time", "الوقت"), ("status", "الحالة")]},
    "messages": {"title": "المحادثة الداخلية", "entity": "messages", "columns": [("sent_at", "التاريخ والوقت"), ("sender", "المرسل"), ("recipient", "إلى"), ("message", "الرسالة")]},
    "emergency": {"title": "متابعة الطوارئ", "entity": None, "columns": []},
    "ratings": {"title": "تقييم الخدمة", "entity": "ratings", "columns": [("patient", "المريض"), ("doctor", "الطبيب"), ("score", "التقييم"), ("comment", "ملاحظة"), ("date", "التاريخ")]},
    "attachments": {"title": "مستندات المرضى", "entity": "attachments", "columns": [("patient", "المريض"), ("name", "الملف"), ("type", "النوع"), ("date", "التاريخ")]},
    "reminders": {"title": "تذكيرات المواعيد", "entity": "reminders", "columns": [("patient", "المريض"), ("date", "التاريخ"), ("time", "الوقت"), ("message", "التذكير"), ("status", "الحالة")]},
    "activity": {"title": "سجل النشاط", "entity": "activity", "columns": [("user", "المستخدم"), ("action", "العملية"), ("date", "التاريخ")]},
    "death_certificate_requests": {"title": "طلبات وثائق الوفاة", "entity": "death_certificate_requests", "columns": [("deceased_name", "اسم المتوفى"), ("death_date", "تاريخ الوفاة"), ("applicant", "مقدم الطلب"), ("purpose", "الغرض"), ("copies", "النسخ"), ("status", "الحالة"), ("date", "تاريخ الطلب")]},
    "donations": {"title": "التبرع بالدم", "entity": "donations", "columns": [("donor_name", "اسم المتبرع"), ("identity_number", "رقم الهوية"), ("blood_type", "فصيلة الدم"), ("date", "تاريخ التبرع"), ("donation_type", "نوع التبرع"), ("quantity_ml", "الكمية مل"), ("status", "الحالة")]},
    "operation_rooms": {"title": "غرف العمليات", "entity": "operation_rooms", "columns": [("name", "الغرفة"), ("location", "الموقع"), ("status", "الحالة")]},
    "surgeries": {"title": "جدولة العمليات", "entity": "surgeries", "columns": [("patient", "المريض"), ("procedure", "الإجراء"), ("doctor", "الطبيب"), ("room", "الغرفة"), ("team", "الفريق"), ("equipment", "التجهيزات"), ("date", "التاريخ"), ("time", "الوقت"), ("duration_minutes", "المدة بالدقائق"), ("status", "الحالة")]},
    "support_tickets": {"title": "تذاكر الدعم الداخلي", "entity": "support_tickets", "columns": [("created_at", "تاريخ البلاغ"), ("reported_by", "مقدم البلاغ"), ("title", "العنوان"), ("category", "القسم"), ("priority", "الأولوية"), ("status", "الحالة"), ("assigned_to", "المسؤول")]},
    "medication_batches": {"title": "دفعات الأدوية والصلاحية", "entity": "medication_batches", "columns": [("medicine", "الدواء"), ("batch_number", "رقم الدفعة"), ("quantity", "الكمية"), ("expiry_month", "انتهاء الصلاحية"), ("supplier", "المورد")]},
    "insurance_claims": {"title": "مطالبات التأمين", "entity": "insurance_claims", "columns": [("company", "شركة التأمين"), ("patient", "المريض"), ("bill_id", "الفاتورة"), ("submitted_at", "تاريخ التقديم"), ("amount", "المبلغ"), ("approved_amount", "المعتمد"), ("rejected_amount", "المرفوض"), ("status", "الحالة")]},
    "assets": {"title": "الأصول والصيانة", "entity": "assets", "columns": [("name", "الأصل"), ("serial_number", "الرقم التسلسلي"), ("location", "الموقع"), ("maintenance_due", "موعد الصيانة"), ("maintenance_cost", "تكلفة الصيانة"), ("status", "الحالة")]},
    "sterilization_cycles": {"title": "دورات التعقيم CSSD", "entity": "sterilization_cycles", "columns": [("instrument_set", "مجموعة الأدوات"), ("operator", "المعقّم"), ("sterilized_at", "تاريخ التعقيم"), ("expires_at", "انتهاء الصلاحية"), ("result", "النتيجة")]},
    "feedback": {"title": "آراء المرضى", "entity": "feedback", "columns": [("created_at", "التاريخ"), ("score", "التقييم"), ("comment", "الملاحظة"), ("status", "الحالة")]},
    "service_prices": {"title": "قائمة أسعار الخدمات", "entity": "service_prices", "columns": [("service", "الخدمة"), ("cash_price", "السعر النقدي"), ("insurance_price", "سعر التأمين"), ("corporate_price", "سعر الشركات"), ("discount_percent", "الخصم %")]},
}

ENGLISH = {
    "الاسم": "Name", "التخصص": "Specialty", "الهاتف": "Phone", "الحالة": "Status",
    "العمر": "Age", "الجنس": "Gender", "المريض": "Patient", "الطبيب": "Doctor",
    "التاريخ": "Date", "الوقت": "Time", "الدواء": "Medicine", "الفئة": "Category",
    "الكمية": "Quantity", "حد التنبيه": "Alert threshold", "حد التنبيه الأدنى": "Minimum alert threshold",
    "مدة الانتظار (دقيقة)": "Wait (minutes)", "الحضور والانصراف": "Attendance",
    "اسم الموظف": "Employee", "القسم": "Department", "المناوبة": "Shift",
    "الرسالة": "Message", "إلى": "To", "المرسل": "Sender",
    "حاضر": "Present", "متأخر": "Late", "غائب": "Absent", "إجازة": "Leave",
    "الكل": "All", "المدير": "Administrator", "الاستقبال": "Reception", "الصيدلية": "Pharmacy",
    "تنبيهات عاجلة": "Urgent alerts", "حالات حرجة": "Critical cases", "حالات طوارئ": "Emergency cases",
    "مخزون منخفض": "Low stock", "فواتير متأخرة": "Overdue invoices",
    "تسجيل حضور": "Check in", "إلغاء الموعد": "Cancel appointment", "طباعة بطاقة المريض": "Print patient card",
    "متوسط الانتظار": "Average wait",
    "السعر": "Price", "التحليل": "Lab test", "الإجمالي": "Total",
    "المتبقي": "Balance", "الضغط": "Blood pressure", "السكر": "Blood sugar",
    "الحرارة": "Temperature", "النبض": "Pulse", "الجناح": "Ward", "السعة": "Capacity",
    "مصدر البيانات": "Data source", "بيانات تجريبية": "Demo data",
    "الغرفة": "Room", "السرير": "Bed", "الفاتورة": "Invoice", "المبلغ": "Amount",
    "الطريقة": "Method", "التغطية %": "Coverage %", "الراتب الأساسي": "Base salary",
    "الخصومات": "Deductions", "السلف": "Advances", "الصافي": "Net pay", "التقييم": "Rating",
    "ملاحظة": "Note", "الملف": "File", "النوع": "Type", "التذكير": "Reminder",
    "بحث": "Search", "رجوع": "Back", "＋ إضافة": "＋ Add", "حذف المحدد": "Delete selected",
    "الملف الطبي": "Medical record", "بطاقة QR": "QR card", "طباعة الفاتورة": "Print invoice",
    "طباعة الوصفة": "Print prescription", "فتح الملف": "Open file", "التقارير والرسوم": "Reports and charts",
    "تصدير CSV": "Export CSV", "نسخة احتياطية": "Backup", "استعادة": "Restore",
    "هوية المشفى": "Hospital branding", "إجمالي المرضى": "Total patients",
    "الأطباء النشطون": "Active doctors", "أصناف الأدوية": "Medicine items",
    "المواعيد القادمة": "Upcoming appointments", "مؤشرات الحالة": "Patient status",
    "ملخص التشغيل اليومي": "Daily operations overview", "تحديث اللوحة": "Refresh dashboard",
    "مواعيد اليوم": "Today's appointments", "لا توجد مواعيد مسجلة لهذا اليوم": "No appointments recorded for today",
    "متابعة تشغيلية": "Operational follow-up", "تنبيهات المخزون": "Inventory alerts",
    "نتائج جاهزة للمراجعة": "Results ready for review", "حالات حرجة مسجلة": "Recorded critical cases",
    "العيادات": "Clinics", "إجراءات سريعة": "Quick actions", "إضافة موعد": "Add appointment",
    "إضافة مريض": "Add patient", "شاشة الانتظار": "Waiting room", "جدول العمليات": "Surgery schedule",
    "اليوم": "Today", "انتظار/عاجل اليوم": "Waiting/urgent today",
    "سجلات مرضى": "Patient records", "موعد بالانتظار أو عاجل": "Waiting or urgent appointment",
    "إشغال الأسرة المسجلة": "Recorded bed occupancy", "تنبيه مخزون": "Stock alerts",
    "تحاليل جاهزة": "Ready lab results", "الطاقم النشط": "Active staff",
    "عيادات مفتوحة": "Open clinics", "من الأسرة المسجلة": "of recorded beds",
    "لا توجد أسرّة مسجلة": "No beds recorded", "لا توجد تنبيهات مخزون": "No inventory alerts",
    "أصناف منخفضة أو نفدت": "Low or out-of-stock items", "طبيب وممرض بحالة نشط": "Active doctors and nurses",
    "بحسب الحالة المسجلة": "Based on recorded status", "التقارير": "Reports",
    "تحقق من السجلات قبل المتابعة السريرية": "Verify records before clinical follow-up",
    "تُعرض المواعيد غير الملغاة فقط": "Showing non-cancelled appointments only",
    "تعتمد المؤشرات على البيانات المدخلة وليست مراقبة سريرية مباشرة": "Indicators use entered data and are not live clinical monitoring",
    "فتح": "Open", "لا توجد مواعيد": "No appointments",
    "فتح صفحة العيادة": "Open clinic page",
    "لا تملك صلاحية فتح هذه العيادة": "You do not have permission to open this clinic",
    "حجز": "Book", "تسجيل تبرع": "Register donation",
    "العيادة مغلقة حالياً ولا تستقبل حجوزات": "This clinic is currently closed and not accepting bookings",
    "لا تملك صلاحية الحجز في هذه العيادة": "You do not have permission to book at this clinic",
    "إضافة ملاحظة": "Add note", "إغلاق": "Close", "إرسال": "Send",
    "الاسم YYYY-MM-DD": "Date YYYY-MM-DD", "التاريخ YYYY-MM-DD": "Date YYYY-MM-DD",
    "التاريخ YYYY-MM": "Month YYYY-MM", "الجنس": "Gender", "حالة المريض": "Patient status",
    "التخصص": "Specialty", "نوع التحليل": "Lab test", "ضغط الدم": "Blood pressure",
    "سكر الدم": "Blood sugar", "الحرارة": "Temperature", "النبض": "Pulse",
    "الاسم": "Name", "اسم الدواء": "Medicine name", "اسم الجناح": "Ward name",
    "السعة": "Capacity", "الموظف": "Employee", "الراتب الأساسي": "Base salary",
    "الخصومات": "Deductions", "السلف": "Advances", "شركة التأمين": "Insurance company",
    "نسبة التغطية %": "Coverage %", "رسالة التذكير": "Reminder message",
    "ملاحظة": "Note", "الجرعة": "Dosage", "التكرار": "Frequency", "المدة": "Duration",
    "الحساسية (افصل بفواصل)": "Allergies (comma-separated)",
    "الأمراض المزمنة (افصل بفواصل)": "Chronic conditions (comma-separated)",
    "البنود (وصف | كمية | سعر الوحدة، كل بند بسطر)": "Invoice items (description | quantity | unit price; one per line)",
    "الكمية": "Quantity", "التقييم من 1 إلى 5": "Rating from 1 to 5",
    "التذكير": "Reminder", "الملف": "File", "الجناح": "Ward",
    "المريض (اتركه فارغاً إذا متاح)": "Patient (leave blank if available)",
    "رقم الفاتورة (اختياري)": "Invoice ID (optional)", "اختر ملفاً": "Choose a file",
    "الوقت HH:MM": "Time HH:MM", "اسم المشفى": "Hospital name",
    "رقم الفاتورة": "Invoice #", "مشغول": "Occupied", "الشهر": "Month",
    "المستخدم": "User", "العملية": "Action", "الشركة": "Company",
    "القسم": "Section", "النتيجة": "Result", "تسجيل خروج": "Log out",
    "هوية المشفى": "Hospital branding", "استعراض": "Browse", "حفظ": "Save", "إلغاء": "Cancel",
    "نشط": "Active", "إجازة": "On leave", "ذكر": "Male", "أنثى": "Female",
    "مستقر": "Stable", "قيد العلاج": "Under treatment", "حرج": "Critical",
    "بالانتظار": "Waiting", "مكتمل": "Completed", "عاجل": "Urgent", "ملغي": "Cancelled",
    "جار الكشف": "In consultation", "متاح": "Available", "قيد التنظيف": "Being cleaned",
    "متوفر": "In stock", "منخفض": "Low stock", "نفد": "Out of stock", "جاهز": "Ready",
    "قيد التنفيذ": "In progress", "غير مدفوعة": "Unpaid", "مدفوعة": "Paid",
    "نقدي": "Cash", "بطاقة": "Card", "تأمين": "Insurance", "تقسيط": "Installments",
    "مجدول": "Scheduled", "تم الإشعار": "Notified",
    "التمريض": "Nursing", "القسم": "Department", "المناوبة": "Shift",
    "طلبات وثائق الوفاة": "Death document requests", "اسم المتوفى": "Deceased full name",
    "تاريخ الوفاة": "Date of death", "مقدم الطلب": "Applicant", "الغرض": "Purpose",
    "النسخ": "Extra copies", "تاريخ الطلب": "Request date", "الاسم الرباعي للمتوفى": "Deceased full name",
    "تاريخ الوفاة YYYY-MM-DD": "Date of death YYYY-MM-DD", "الغرض من الطلب": "Purpose of request",
    "عدد النسخ الإضافية": "Number of extra copies", "اسم مقدم الطلب": "Applicant name",
    "صفة القرابة": "Relationship to deceased", "رقم التواصل": "Contact phone",
    "صورة الهوية مرفقة؟": "Applicant ID copy attached?", "إثبات صلة القرابة مرفق؟": "Proof of relationship attached?",
    "وثائق أخرى": "Other documents", "الرسوم (إن وجدت)": "Fees (if any)",
    "طريقة السداد / ملاحظات": "Payment method / notes", "الجهة البديلة عند تعذر الإصدار": "Alternative office if issuance unavailable",
    "المدة الزمنية المتوقعة": "Estimated processing time", "التوقيع": "Signature",
    "صباحي": "Morning", "مسائي": "Evening", "ليلي": "Night",
    "طباعة التقرير الطبي": "Print medical report", "طباعة الطلب": "Print request",
    "نعم": "Yes", "لا": "No",
    "إدارة العيادات": "Clinic management", "العيادة": "Clinic", "اسم العيادة": "Clinic name",
    "رمز العيادة": "Clinic icon", "وصف العيادة": "Clinic description", "مفتوحة": "Open",
    "مغلقة مؤقتاً": "Temporarily closed", "بانتظار التحقق": "Pending verification",
    "التحقق": "Verification", "ملاحظة التحقق": "Verification note",
    "📥 نسخة احتياطية": "📥 Backup", "استعادة": "Restore", "عربي / English": "العربية",
    "🌙 / ☀️": "🌙 / ☀️", "إنشاء تذكير": "Create reminder",
    "إرسال عبر WhatsApp": "Send via WhatsApp", "الطبيب": "Doctor",
    "الدواء": "Medicine", "الوقت": "Time", "التاريخ": "Date",
    "📺 شاشة الانتظار": "📺 Waiting room", "حجز موعد سريع": "Quick appointment",
    "المساعد": "Assistant", "التحاليل": "Lab tests", "سجل المريض": "Patient record",
    "اسم المتبرع": "Donor name", "فصيلة الدم": "Blood type", "تاريخ التبرع": "Donation date",
    "نوع التبرع": "Donation type", "الكمية مل": "Quantity (ml)", "رقم الهوية": "ID number",
    "الاسم الكامل للمتبرع": "Donor full name", "رقم الهوية / الرقم الوطني": "ID / national number",
    "تاريخ التبرع YYYY-MM-DD": "Donation date YYYY-MM-DD", "الكمية المسحوبة بالمل (إن وجدت)": "Collected amount in ml (optional)",
    "اسم المركز / المستشفى": "Center / hospital name", "حالة الفحوصات الأولية (حسب السجل)": "Initial screening status (as recorded)",
    "حالة التبرع": "Donation status", "طباعة نموذج التبرع": "Print donation form",
    "تبرع بالدم": "Blood donation", "دم كامل": "Whole blood", "صفائح دموية": "Platelets", "بلازما": "Plasma",
    "غير مسجلة": "Not recorded", "مسجلة - راجع الملف": "Recorded - verify file", "إحالة / متابعة": "Referral / follow-up",
    "مسجل": "Recorded", "تم التبرع": "Donation completed", "مجدولة": "Scheduled",
    "جارية": "In progress", "مكتملة": "Completed", "ملغاة": "Cancelled",
    "غرف العمليات": "Operating rooms", "جدولة العمليات": "Surgery schedule",
    "الغرفة": "Room", "الموقع": "Location", "اسم غرفة العمليات": "Operating room name",
    "غرفة العمليات": "Operating room", "الإجراء": "Procedure", "الإجراء / نوع العملية": "Procedure / surgery type",
    "المدة بالدقائق": "Duration (minutes)", "الحالة": "Status", "متاحة": "Available",
    "خارج الخدمة": "Out of service", "رجوع": "Back",
    "تذاكر الدعم الداخلي": "Internal support tickets",
    "تاريخ البلاغ": "Reported at",
    "مقدم البلاغ": "Reported by",
    "عنوان العطل": "Issue title",
    "وصف العطل وموقعه": "Issue description and location",
    "القسم": "Department",
    "الأولوية": "Priority",
    "عادية": "Normal",
    "منخفضة": "Low",
    "عالية": "High",
    "حرجة": "Critical",
    "جديدة": "New",
    "قيد المعالجة": "In progress",
    "مغلقة": "Closed",
    "المسؤول عن الإصلاح": "Assigned to",
    "دفعات الأدوية والصلاحية": "Medicine batches and expiry",
    "رقم الدفعة": "Batch number",
    "انتهاء الصلاحية YYYY-MM": "Expiry YYYY-MM",
    "المورد": "Supplier",
    "مطالبات التأمين": "Insurance claims",
    "تاريخ التقديم": "Submitted at",
    "المبلغ المطالب به": "Claim amount",
    "المبلغ المعتمد": "Approved amount",
    "المبلغ المرفوض": "Rejected amount",
    "مقدمة": "Submitted",
    "موافقة جزئية": "Partially approved",
    "الأصول والصيانة": "Assets and maintenance",
    "اسم الأصل": "Asset name",
    "الرقم التسلسلي": "Serial number",
    "موعد الصيانة YYYY-MM-DD": "Maintenance due YYYY-MM-DD",
    "دورات التعقيم CSSD": "Sterilization cycles",
    "مجموعة الأدوات": "Instrument set",
    "المعقّم": "Sterilized by",
    "تاريخ التعقيم YYYY-MM-DD": "Sterilized at YYYY-MM-DD",
    "انتهاء الصلاحية YYYY-MM-DD": "Expiry YYYY-MM-DD",
    "النتيجة": "Result",
    "ناجحة": "Passed",
    "فاشلة": "Failed",
    "آراء المرضى": "Patient feedback",
    "قائمة أسعار الخدمات": "Service price list",
    "السعر النقدي": "Cash price",
    "سعر التأمين": "Insurance price",
    "سعر الشركات": "Corporate price",
    "الخصم %": "Discount %",
    "نوع المريض": "Patient type",
    "أولوية الطابور": "Queue priority",
    "طارئة": "Emergency",
    "موعد مسبق": "Scheduled",
    "مراجعة": "Follow-up",
    "يعمل": "Operational",
    "قيد الصيانة": "Under maintenance",
    "الفريق": "Team",
    "تجهيزات الغرفة": "Room equipment",
    "تقييم الخدمة": "Service rating",
    "أرسل التقييم": "Submit rating",
    "شكوى": "Complaint",
    "موعد الطابور": "Queue appointment",
    "الاستشارة الصوتية/المرئية": "Audio/video consultation",
}

FORM_FIELDS = {
    "clinics": [("name", field("اسم العيادة")), ("specialty", field("التخصص")), ("icon", field("رمز العيادة", "choice", "🏥", [clinic["icon"] for clinic in DEFAULT_CLINICS])), ("description", field("وصف العيادة")), ("status", field("الحالة", "choice", "مفتوحة", ["مفتوحة", "مغلقة مؤقتاً"]))],
    "doctors": [("name", field("الاسم")), ("spec", field("التخصص", "clinic_specialty")), ("phone", field("الهاتف")), ("status", field("الحالة", "choice", "بانتظار التحقق", ["بانتظار التحقق", "نشط", "إجازة"])), ("verification", field("ملاحظة التحقق", "text", "يلزم التحقق من الهوية والترخيص"))],
    "patients": [("name", field("الاسم")), ("age", field("العمر", "number")), ("gender", field("الجنس", "choice", "ذكر", ["ذكر", "أنثى"])), ("phone", field("الهاتف")), ("status", field("الحالة", "choice", "مستقر", ["مستقر", "قيد العلاج", "حرج"])), ("allergies", field("الحساسية (افصل بفواصل)", "text")), ("chronicConditions", field("الأمراض المزمنة (افصل بفواصل)", "text"))],
    "appts": [("patient", field("المريض", "patient")), ("doctor", field("الطبيب", "doctor")), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat())), ("time", field("الوقت HH:MM", "text", "09:00")), ("priority", field("أولوية الطابور", "choice", "موعد مسبق", ["طارئة", "موعد مسبق", "مراجعة"])), ("status", field("الحالة", "choice", "بالانتظار", ["بالانتظار", "عاجل", "جار الكشف", "مكتمل", "ملغي"]))],
    "meds": [("name", field("اسم الدواء")), ("cat", field("الفئة")), ("qty", field("الكمية", "number", "0")), ("min_qty", field("حد التنبيه الأدنى", "number", "10")), ("price", field("السعر", "number", "0")), ("status", field("الحالة", "choice", "متوفر", ["متوفر", "منخفض", "نفد"]))],
    "medication_batches": [
        ("medicine", field("اسم الدواء", "medicine")),
        ("batch_number", field("رقم الدفعة")),
        ("quantity", field("الكمية", "number", "0")),
        ("expiry_month", field("انتهاء الصلاحية YYYY-MM")),
        ("supplier", field("المورد")),
    ],
    "labs": [("patient", field("المريض", "patient")), ("type", field("نوع التحليل")), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat())), ("status", field("الحالة", "choice", "قيد التنفيذ", ["قيد التنفيذ", "جاهز"]))],
    "bills": [("patient", field("المريض", "patient")), ("billing_type", field("نوع المريض", "choice", "نقدي", ["نقدي", "تأمين", "تعاقد شركات"])), ("items_text", field("البنود (خدمة | كمية أو وصف | كمية | سعر الوحدة، كل بند بسطر)", "multiline")), ("paymentMethod", field("طريقة الدفع", "choice", "نقدي", ["نقدي", "بطاقة", "تأمين", "تقسيط"])), ("status", field("الحالة", "choice", "غير مدفوعة", ["غير مدفوعة", "مدفوعة"])), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat()))],
    "prescriptions": [("patient", field("المريض", "patient")), ("doctor", field("الطبيب", "doctor")), ("medicine", field("الدواء", "medicine")), ("dosage", field("الجرعة")), ("frequency", field("التكرار")), ("duration", field("المدة")), ("quantity", field("الكمية", "number", "1")), ("notes", field("ملاحظات", "multiline"))],
    "vitals": [("patient", field("المريض", "patient")), ("bloodPressure", field("ضغط الدم")), ("bloodSugar", field("سكر الدم", "number")), ("temperature", field("الحرارة", "number")), ("pulse", field("النبض", "number")), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat()))],
    "wards": [("name", field("اسم الجناح")), ("capacity", field("السعة", "number", "1"))],
    "beds": [("ward", field("الجناح", "ward")), ("room", field("الغرفة")), ("number", field("رقم السرير")), ("patient", field("المريض (اتركه فارغاً إذا متاح)", "patient_optional")), ("status", field("حالة السرير", "choice", "متاح", ["متاح", "مشغول", "قيد التنظيف"]))],
    "support_tickets": [
        ("title", field("عنوان العطل")),
        ("category", field("القسم", "choice", "تقنية المعلومات", ["تقنية المعلومات", "الأشعة", "المختبر", "الصيانة", "أخرى"])),
        ("description", field("وصف العطل وموقعه", "multiline")),
        ("priority", field("الأولوية", "choice", "عادية", ["منخفضة", "عادية", "عالية", "حرجة"])),
        ("status", field("الحالة", "choice", "جديدة", ["جديدة", "قيد المعالجة", "مغلقة"])),
        ("assigned_to", field("المسؤول عن الإصلاح")),
    ],
    "payments": [("patient", field("المريض", "patient")), ("bill_id", field("رقم الفاتورة (اختياري)", "text")), ("amount", field("المبلغ", "number")), ("method", field("طريقة الدفع", "choice", "نقدي", ["نقدي", "بطاقة", "تأمين", "تقسيط"])), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat()))],
    "insurance": [("patient", field("المريض", "patient")), ("company", field("شركة التأمين")), ("coverage", field("نسبة التغطية %", "number", "0"))],
    "insurance_claims": [
        ("company", field("شركة التأمين")),
        ("patient", field("المريض", "patient")),
        ("bill_id", field("رقم الفاتورة", "number")),
        ("amount", field("المبلغ المطالب به", "number")),
        ("approved_amount", field("المبلغ المعتمد", "number", "0")),
        ("rejected_amount", field("المبلغ المرفوض", "number", "0")),
        ("status", field("حالة المطالبة", "choice", "مقدمة", ["مقدمة", "موافق عليها", "مرفوضة", "موافقة جزئية"])),
        ("notes", field("ملاحظات", "multiline")),
    ],
    "assets": [
        ("name", field("اسم الأصل")),
        ("serial_number", field("الرقم التسلسلي")),
        ("location", field("الموقع")),
        ("maintenance_due", field("موعد الصيانة YYYY-MM-DD", "date", date.today().isoformat())),
        ("maintenance_cost", field("تكلفة الصيانة", "number", "0")),
        ("status", field("الحالة", "choice", "يعمل", ["يعمل", "قيد الصيانة", "خارج الخدمة"])),
    ],
    "sterilization_cycles": [
        ("instrument_set", field("مجموعة الأدوات")),
        ("operator", field("المعقّم")),
        ("sterilized_at", field("تاريخ التعقيم YYYY-MM-DD", "date", date.today().isoformat())),
        ("expires_at", field("انتهاء الصلاحية YYYY-MM-DD", "date", date.today().isoformat())),
        ("result", field("النتيجة", "choice", "ناجحة", ["ناجحة", "فاشلة"])),
    ],
    "service_prices": [
        ("service", field("اسم الخدمة")),
        ("cash_price", field("السعر النقدي", "number", "0")),
        ("insurance_price", field("سعر التأمين", "number", "0")),
        ("corporate_price", field("سعر الشركات", "number", "0")),
        ("discount_percent", field("الخصم %", "number", "0")),
    ],
    "payroll": [("employee", field("الموظف")), ("base", field("الراتب الأساسي", "number")), ("deductions", field("الخصومات", "number", "0")), ("advance", field("السلف", "number", "0")), ("date", field("الشهر YYYY-MM", "text", date.today().strftime("%Y-%m")))],
    "ratings": [("patient", field("المريض", "patient")), ("doctor", field("الطبيب", "doctor")), ("score", field("التقييم من 1 إلى 5", "choice", "5", ["1", "2", "3", "4", "5"])), ("comment", field("ملاحظة", "multiline")), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat()))],
    "attachments": [("patient", field("المريض", "patient")), ("path", field("اختر ملفاً", "file")), ("type", field("النوع", "text", "مستند"))],
    "reminders": [("patient", field("المريض", "patient")), ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat())), ("time", field("الوقت HH:MM", "text", "09:00")), ("message", field("رسالة التذكير")), ("status", field("الحالة", "choice", "مجدول", ["مجدول", "تم الإشعار", "ملغي"]))],
    "nurses": [("name", field("الاسم")), ("department", field("القسم")), ("shift", field("المناوبة", "choice", "صباحي", ["صباحي", "مسائي", "ليلي"])), ("status", field("الحالة", "choice", "نشط", ["نشط", "إجازة"]))],
    "attendance": [
        ("employee", field("اسم الموظف")),
        ("department", field("القسم")),
        ("shift", field("المناوبة", "choice", "صباحي", ["صباحي", "مسائي", "ليلي"])),
        ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat())),
        ("time", field("الوقت HH:MM", "text", datetime.now().strftime("%H:%M"))),
        ("status", field("الحالة", "choice", "حاضر", ["حاضر", "متأخر", "غائب", "إجازة"])),
    ],
    "messages": [
        ("recipient", field("إلى", "choice", "الكل", ["الكل", "المدير", "الطبيب", "الاستقبال", "الصيدلية"])),
        ("message", field("الرسالة", "multiline")),
    ],
    "death_certificate_requests": [
        ("deceased_name", field("الاسم الرباعي للمتوفى")),
        ("death_date", field("تاريخ الوفاة YYYY-MM-DD", "date", date.today().isoformat())),
        ("purpose", field("الغرض من الطلب", "multiline")),
        ("copies", field("عدد النسخ الإضافية", "number", "0")),
        ("applicant", field("اسم مقدم الطلب")),
        ("kinship", field("صفة القرابة")),
        ("phone", field("رقم التواصل")),
        ("identity_attached", field("صورة الهوية مرفقة؟", "choice", "لا", ["نعم", "لا"])),
        ("relationship_attached", field("إثبات صلة القرابة مرفق؟", "choice", "لا", ["نعم", "لا"])),
        ("other_documents", field("وثائق أخرى")),
        ("fee", field("الرسوم (إن وجدت)", "number", "0")),
        ("payment_method", field("طريقة السداد / ملاحظات")),
        ("alternative_office", field("الجهة البديلة عند تعذر الإصدار")),
        ("expected_time", field("المدة الزمنية المتوقعة")),
        ("signature", field("التوقيع")),
    ],
    "donations": [
        ("donor_name", field("الاسم الكامل للمتبرع")),
        ("identity_number", field("رقم الهوية / الرقم الوطني")),
        ("blood_type", field("فصيلة الدم", "choice", "", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])),
        ("date", field("تاريخ التبرع YYYY-MM-DD", "date", date.today().isoformat())),
        ("donation_type", field("نوع التبرع", "choice", "دم كامل", ["دم كامل", "بلازما", "صفائح دموية"])),
        ("quantity_ml", field("الكمية المسحوبة بالمل (إن وجدت)", "number", "")),
        ("center", field("اسم المركز / المستشفى")),
        ("screening_status", field("حالة الفحوصات الأولية (حسب السجل)", "choice", "غير مسجلة", ["غير مسجلة", "مسجلة - راجع الملف", "إحالة / متابعة"])),
        ("status", field("حالة التبرع", "choice", "مسجل", ["مسجل", "تم التبرع", "ملغي"])),
    ],
    "operation_rooms": [
        ("name", field("اسم غرفة العمليات")),
        ("location", field("الموقع")),
        ("status", field("الحالة", "choice", "متاحة", ["متاحة", "خارج الخدمة"])),
    ],
    "surgeries": [
        ("patient", field("المريض", "patient")),
        ("procedure", field("الإجراء / نوع العملية")),
        ("doctor", field("الطبيب", "doctor")),
        ("room", field("غرفة العمليات", "operation_room")),
        ("team", field("فريق العمل")),
        ("equipment", field("تجهيزات الغرفة")),
        ("date", field("التاريخ YYYY-MM-DD", "date", date.today().isoformat())),
        ("time", field("الوقت HH:MM", "text", "09:00")),
        ("duration_minutes", field("المدة بالدقائق", "number", "60")),
        ("status", field("الحالة", "choice", "مجدولة", ["مجدولة", "جارية", "مكتملة", "ملغاة"])),
    ],
}


def csv_safe(value):
    text = str(value if value is not None else "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def appointment_wait_minutes(appointment, now=None):
    check_in = appointment.get("check_in_at") or appointment.get("arrival_time")
    if not check_in:
        return None
    try:
        started = datetime.fromisoformat(str(check_in))
    except ValueError:
        return None
    current = now or datetime.now().astimezone()
    if started.tzinfo is None and current.tzinfo is not None:
        started = started.replace(tzinfo=current.tzinfo)
    elif started.tzinfo is not None and current.tzinfo is None:
        current = current.replace(tzinfo=started.tzinfo)
    return max(0, int((current - started).total_seconds() // 60))


def months_until_expiry(expiry_month, today=None):
    if not re.fullmatch(r"\d{4}-\d{2}", str(expiry_month)):
        return None
    try:
        expiry = datetime.strptime(str(expiry_month), "%Y-%m").date()
    except ValueError:
        return None
    today = today or date.today()
    return (expiry.year - today.year) * 12 + expiry.month - today.month


def appointment_priority_rank(appointment):
    status = str(appointment.get("status", "")).casefold()
    priority = str(appointment.get("priority", "")).casefold()
    if status in ("عاجل", "urgent") or priority in ("طارئة", "طارئ", "emergency"):
        return 0
    if priority in ("موعد مسبق", "scheduled"):
        return 1
    if priority in ("مراجعة", "follow-up"):
        return 2
    return 3


def financial_forecast(store, today=None):
    today = today or date.today()
    current_month = today.year * 12 + today.month - 1
    revenue_by_month = []
    payroll_by_month = []
    bills = store.list("bills")
    payroll = store.list("payroll")
    for offset in (3, 2, 1):
        month_index = current_month - offset
        year, month_zero = divmod(month_index, 12)
        month_key = f"{year:04d}-{month_zero + 1:02d}"
        revenue_by_month.append(sum(
            float(item.get("amount", 0) or 0)
            for item in bills if str(item.get("date", "")).startswith(month_key)
        ))
        payroll_by_month.append(sum(
            float(item.get("net", float(item.get("base", 0)) - float(item.get("deductions", 0)) - float(item.get("advance", 0))) or 0)
            for item in payroll if str(item.get("date", "")).startswith(month_key)
        ))
    if not any(revenue_by_month) and not any(payroll_by_month):
        return None
    return {
        "revenue": round(sum(revenue_by_month) / len(revenue_by_month), 2),
        "payroll": round(sum(payroll_by_month) / len(payroll_by_month), 2),
        "months": 3,
    }


def dashboard_snapshot(store, today=None, now=None):
    today = today or date.today().isoformat()
    now = now or datetime.now().astimezone()
    cancelled_statuses = {"ملغي", "ملغاة", "ملغى", "cancelled", "canceled"}
    appointments_today = [
        item for item in store.list("appts")
        if item.get("date") == today and str(item.get("status", "")).casefold() not in cancelled_statuses
    ]
    appointments_today.sort(key=lambda item: (str(item.get("time", "")), str(item.get("patient", "")).casefold()))
    waiting_today = sum(
        1 for item in appointments_today
        if str(item.get("status", "")).casefold() in ("بالانتظار", "عاجل", "waiting", "urgent")
    )
    waiting_times = [
        minutes for item in appointments_today
        if str(item.get("status", "")).casefold() in ("بالانتظار", "عاجل", "waiting", "urgent")
        for minutes in (appointment_wait_minutes(item, now),)
        if minutes is not None
    ]
    beds = store.list("beds")
    occupied_beds = sum(
        1 for item in beds
        if str(item.get("patient", "")).strip() or str(item.get("status", "")).casefold() in ("مشغول", "occupied")
    )
    low_stock_medicines = []
    for item in store.list("meds"):
        status = str(item.get("status", "")).casefold()
        try:
            quantity = float(item.get("qty", 1))
            no_stock = quantity <= 0
            minimum = item.get("min_qty")
            below_minimum = minimum not in (None, "") and quantity <= float(minimum)
        except (TypeError, ValueError):
            no_stock = False
            below_minimum = False
        if status in ("منخفض", "نفد", "low", "out of stock") or no_stock or below_minimum:
            low_stock_medicines.append(item)
    expiring_batches = [
        item for item in store.list("medication_batches")
        if (months := months_until_expiry(item.get("expiry_month", ""), now.date())) is not None
        and months <= 3
    ]
    overdue_invoices = []
    for bill in store.list("bills"):
        try:
            has_balance = float(bill.get("balance", 0) or 0) > 0
        except (TypeError, ValueError):
            continue
        if has_balance and str(bill.get("date", "")) < today:
            overdue_invoices.append(bill)
    critical_patient_records = [
        item for item in store.list("patients")
        if str(item.get("status", "")).casefold() in ("حرج", "critical")
        and not item.get("sample_data")
        and not item.get("demo")
    ]
    return {
        "patients": len(store.list("patients")),
        "appointments_today": appointments_today,
        "waiting_today": waiting_today,
        "average_wait_minutes": round(sum(waiting_times) / len(waiting_times)) if waiting_times else None,
        "beds_total": len(beds),
        "beds_occupied": occupied_beds,
        "low_stock_medicines": low_stock_medicines,
        "expiring_batches": expiring_batches,
        "assets_due": [
            item for item in store.list("assets")
            if item.get("maintenance_due") and item.get("maintenance_due") <= today
            and item.get("status") != "خارج الخدمة"
        ],
        "sterilization_alerts": [
            item for item in store.list("sterilization_cycles")
            if item.get("result") != "ناجحة" or (
                item.get("expires_at") and item.get("expires_at") <= today
            )
        ],
        "feedback_complaints": [
            item for item in store.list("feedback")
            if item.get("status") == "شكوى" or item.get("score") in (1, 2)
        ],
        "ready_labs": sum(1 for item in store.list("labs") if str(item.get("status", "")).casefold() in ("جاهز", "ready")),
        "critical_patients": sum(1 for item in store.list("patients") if str(item.get("status", "")).casefold() in ("حرج", "critical")),
        "critical_patient_records": critical_patient_records,
        "critical_alert_patients": len(critical_patient_records),
        "urgent_appointments": [item for item in appointments_today if str(item.get("status", "")).casefold() in ("عاجل", "urgent")],
        "overdue_invoices": overdue_invoices,
        "active_staff": sum(
            1 for entity in ("doctors", "nurses")
            for item in store.list(entity)
            if str(item.get("status", "")).casefold() in ("نشط", "active")
        ),
        "open_clinics": sum(
            1 for item in store.list("clinics")
            if str(item.get("status", "")).casefold() in ("مفتوحة", "open")
        ),
    }


def bed_status(bed):
    status = str(bed.get("status", "")).strip()
    if str(bed.get("patient", "")).strip():
        return "مشغول"
    return status if status in ("مشغول", "قيد التنظيف") else "متاح"


def waiting_room_snapshot(store, today=None):
    today = today or date.today().isoformat()
    doctors = {item.get("name"): item for item in store.list("doctors")}
    clinics = {item.get("specialty"): item.get("name") for item in store.list("clinics")}
    appointments = [
        item for item in store.list("appts")
        if item.get("date") == today
    ]
    appointments.sort(key=lambda item: (appointment_priority_rank(item), str(item.get("time", "")), str(item.get("id", ""))))

    def with_clinic(appointment):
        doctor = doctors.get(appointment.get("doctor"), {})
        return {
            **appointment,
            "clinic": clinics.get(doctor.get("spec"), "غير محددة"),
        }

    active = [
        with_clinic(item) for item in appointments
        if str(item.get("status", "")).casefold() == "جار الكشف"
    ]
    upcoming = [
        with_clinic(item) for item in appointments
        if str(item.get("status", "")).casefold() in ("بالانتظار", "عاجل", "waiting", "urgent")
    ]
    return {"current": active[0] if active else None, "upcoming": upcoming}


class HospitalStore:
    def __init__(self, path=DB_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS records (entity TEXT NOT NULL, record_id INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(entity, record_id))"
        )
        self.connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.commit()
        if self.connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0:
            for entity, rows in DEFAULT_DATA.items():
                for row in rows:
                    self.connection.execute("INSERT INTO records VALUES (?, ?, ?)", (entity, row["id"], json.dumps(row, ensure_ascii=False)))
            self.connection.commit()
        self.ensure_clinics()
        self.ensure_operation_rooms()
        self.migrate_generic_doctors()
        self.seed_requested_demo_records()
        self.seed_demo_medications()
        self.ensure_inventory_thresholds()

    def ensure_clinics(self):
        seed_key = "clinic_catalog_v2"
        existing_specialties = {item.get("specialty") for item in self.list("clinics")}
        missing_clinics = [clinic for clinic in DEFAULT_CLINICS if clinic["specialty"] not in existing_specialties]
        if not missing_clinics and self.setting(seed_key):
            return
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for clinic in missing_clinics:
                record = dict(clinic)
                record["id"] = self.next_id("clinics")
                self.connection.execute(
                    "INSERT INTO records VALUES (?,?,?)",
                    ("clinics", record["id"], json.dumps(record, ensure_ascii=False)),
                )
            self.connection.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (seed_key, "done"))
            self._audit("النظام", "تهيئة دليل العيادات")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def ensure_operation_rooms(self):
        seed_key = "operation_rooms_v1"
        if self.setting(seed_key):
            return
        existing_names = {item.get("name") for item in self.list("operation_rooms")}
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for room in DEFAULT_DATA["operation_rooms"]:
                if room["name"] in existing_names:
                    continue
                record = dict(room)
                record["id"] = self.next_id("operation_rooms")
                self.connection.execute(
                    "INSERT INTO records VALUES (?,?,?)",
                    ("operation_rooms", record["id"], json.dumps(record, ensure_ascii=False)),
                )
            self.connection.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (seed_key, "done"))
            self._audit("النظام", "تهيئة غرف العمليات")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
    def seed_requested_demo_records(self):
        seed_key = "demo_staff_patients_20261030_v1"
        if self.setting(seed_key):
            return
        sample_doctors = [
            ("د. سليم النجار", "قلبية"), ("د. ميساء الحسن", "قلبية"),
            ("د. رائد الخطيب", "أطفال"), ("د. هبة منصور", "أطفال"),
            ("د. نادر العلي", "طوارئ"), ("د. رنا شريف", "طوارئ"),
            ("د. فادي الأسعد", "جراحة عامة"), ("د. لمى درويش", "جراحة عامة"),
            ("د. باسل مراد", "باطنية"), ("د. نور قاسم", "باطنية"),
            ("د. مازن حمود", "عظام"), ("د. دانا خليل", "عظام"),
            ("د. يامن يونس", "جلدية"), ("د. سارة ناصر", "جلدية"),
            ("د. حسام قدور", "عيون"), ("د. مروة عيسى", "عيون"),
            ("د. إياد صباغ", "أنف وأذن وحنجرة"), ("د. عبير مصطفى", "نسائية وتوليد"),
            ("د. جود شهاب", "أسنان"), ("د. لؤي كنعان", "أعصاب"),
        ]
        departments = ("الطوارئ", "الجناح العام", "العناية", "الأطفال", "الجراحة")
        existing_profiles = [item for item in self.list("doctors") if item.get("sample_data")]
        existing_names = {item.get("name") for item in self.list("doctors")}
        missing_profiles = max(0, len(sample_doctors) - len(existing_profiles))
        existing_nurses = [item for item in self.list("nurses") if item.get("sample_data") or item.get("demo")]
        existing_nurse_names = {item.get("name") for item in self.list("nurses")}
        missing_nurses = max(0, 50 - len(existing_nurses))
        existing_patients = [item for item in self.list("patients") if item.get("sample_data") or item.get("demo")]
        existing_patient_names = {item.get("name") for item in self.list("patients")}
        missing_patients = max(0, 100 - len(existing_patients))
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for name, specialty in sample_doctors:
                if missing_profiles == 0:
                    break
                if name in existing_names:
                    continue
                doctor = {
                    "id": self.next_id("doctors"),
                    "name": name,
                    "spec": specialty,
                    "phone": "",
                    "status": "بانتظار التحقق",
                    "verification": "اسم افتراضي غير موثق — استبدله ببيانات الطبيب المعتمدة",
                    "sample_data": True,
                }
                self.connection.execute("INSERT INTO records VALUES (?,?,?)", ("doctors", doctor["id"], json.dumps(doctor, ensure_ascii=False)))
                existing_names.add(name)
                missing_profiles -= 1
            for index in range(50):
                if missing_nurses == 0:
                    break
                nurse_name = f"ممرض تجريبي {index + 1:02d}"
                if nurse_name in existing_nurse_names:
                    continue
                nurse = {
                    "id": self.next_id("nurses"),
                    "name": nurse_name,
                    "department": departments[index % len(departments)],
                    "shift": ("صباحي", "مسائي", "ليلي")[index % 3],
                    "status": "نشط",
                    "demo": True,
                    "sample_data": True,
                }
                self.connection.execute("INSERT INTO records VALUES (?,?,?)", ("nurses", nurse["id"], json.dumps(nurse, ensure_ascii=False)))
                existing_nurse_names.add(nurse_name)
                missing_nurses -= 1
            statuses = ("مستقر", "قيد العلاج", "حرج")
            for index in range(100):
                if missing_patients == 0:
                    break
                patient_name = f"مريض تجريبي {index + 1:03d}"
                if patient_name in existing_patient_names:
                    continue
                patient = {
                    "id": self.next_id("patients"),
                    "name": patient_name,
                    "age": 18 + index % 70,
                    "gender": "أنثى" if index % 2 else "ذكر",
                    "phone": "غير متاح — بيانات تجريبية",
                    "status": statuses[index % len(statuses)],
                    "allergies": [],
                    "chronicConditions": [],
                    "demo": True,
                    "sample_data": True,
                }
                self.connection.execute("INSERT INTO records VALUES (?,?,?)", ("patients", patient["id"], json.dumps(patient, ensure_ascii=False)))
                existing_patient_names.add(patient_name)
                missing_patients -= 1
            self.connection.execute("INSERT INTO settings(key,value) VALUES (?,?)", (seed_key, "done"))
            self._audit("النظام", "إضافة بيانات أولية: 20 ملف طبيب توضيحي و50 ممرضاً و100 مريض")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def seed_demo_medications(self):
        seed_key = "demo_medication_catalog_100_v1"
        if self.setting(seed_key):
            return
        existing_names = {str(item.get("name", "")).casefold() for item in self.list("meds")}
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for category, names in DEMO_MEDICATION_CATALOG:
                for name in names:
                    if name.casefold() in existing_names:
                        continue
                    record_id = self.next_id("meds")
                    quantity = (record_id * 17) % 70
                    record = {
                        "id": record_id,
                        "name": name,
                        "cat": category,
                        "qty": quantity,
                        "price": 0,
                        "status": "نفد" if quantity == 0 else "منخفض" if quantity <= 10 else "متوفر",
                        "data_source": "بيانات تجريبية",
                        "sample_data": True,
                        "demo": True,
                    }
                    self.connection.execute(
                        "INSERT INTO records VALUES (?,?,?)",
                        ("meds", record["id"], json.dumps(record, ensure_ascii=False)),
                    )
                    existing_names.add(name.casefold())
            self.connection.execute(
                "INSERT INTO settings(key,value) VALUES (?,?)",
                (seed_key, "done"),
            )
            self._audit("النظام", "إضافة 100 صنف دوائي تجريبي إلى الصيدلية")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def ensure_inventory_thresholds(self):
        seed_key = "inventory_minimum_threshold_v1"
        if self.setting(seed_key):
            return
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            changed = 0
            rows = self.connection.execute(
                "SELECT record_id, payload FROM records WHERE entity='meds' ORDER BY record_id"
            ).fetchall()
            for row in rows:
                record = json.loads(row["payload"])
                if record.get("min_qty") not in (None, ""):
                    continue
                record["min_qty"] = 10
                self.connection.execute(
                    "UPDATE records SET payload=? WHERE entity='meds' AND record_id=?",
                    (json.dumps(record, ensure_ascii=False), row["record_id"]),
                )
                changed += 1
            self.connection.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)",
                (seed_key, "done"),
            )
            if changed:
                self._audit("النظام", "إضافة حد تنبيه افتراضي للمخزون (10 وحدات)")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def migrate_generic_doctors(self):
        seed_key = "named_clinic_doctors_v1"
        if self.setting(seed_key):
            return
        sample_doctors = [
            ("د. سليم النجار", "قلبية"), ("د. ميساء الحسن", "قلبية"),
            ("د. رائد الخطيب", "أطفال"), ("د. هبة منصور", "أطفال"),
            ("د. نادر العلي", "طوارئ"), ("د. رنا شريف", "طوارئ"),
            ("د. فادي الأسعد", "جراحة عامة"), ("د. لمى درويش", "جراحة عامة"),
            ("د. باسل مراد", "باطنية"), ("د. نور قاسم", "باطنية"),
            ("د. مازن حمود", "عظام"), ("د. دانا خليل", "عظام"),
            ("د. يامن يونس", "جلدية"), ("د. سارة ناصر", "جلدية"),
            ("د. حسام قدور", "عيون"), ("د. مروة عيسى", "عيون"),
            ("د. إياد صباغ", "أنف وأذن وحنجرة"), ("د. عبير مصطفى", "نسائية وتوليد"),
            ("د. جود شهاب", "أسنان"), ("د. لؤي كنعان", "أعصاب"),
        ]
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            doctors = self.list("doctors")
            for name, specialty in sample_doctors:
                doctor = next(
                    (
                        item for item in doctors
                        if item.get("demo") is True
                        and re.fullmatch(r"طبيب تجريبي \d+", str(item.get("name", "")))
                    ),
                    None,
                )
                if not doctor:
                    break
                doctor["name"] = name
                doctor["spec"] = specialty
                doctor["phone"] = ""
                doctor["status"] = "بانتظار التحقق"
                doctor["verification"] = "اسم افتراضي غير موثق — استبدله ببيانات الطبيب المعتمدة"
                doctor["sample_data"] = True
                doctor.pop("demo", None)
                self.connection.execute(
                    "UPDATE records SET payload=? WHERE entity='doctors' AND record_id=?",
                    (json.dumps(doctor, ensure_ascii=False), doctor["id"]),
                )
                doctors.remove(next(item for item in doctors if item["id"] == doctor["id"]))
            self.connection.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (seed_key, "done"))
            self._audit("النظام", "تحديث أسماء ملفات الأطباء التوضيحية وربطها بالتخصصات")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def list(self, entity):
        rows = self.connection.execute("SELECT payload FROM records WHERE entity=? ORDER BY record_id", (entity,))
        return [json.loads(row["payload"]) for row in rows]

    def get(self, entity, record_id):
        row = self.connection.execute("SELECT payload FROM records WHERE entity=? AND record_id=?", (entity, int(record_id))).fetchone()
        return json.loads(row["payload"]) if row else None

    def next_id(self, entity):
        value = self.connection.execute("SELECT COALESCE(MAX(record_id), 0)+1 FROM records WHERE entity=?", (entity,)).fetchone()[0]
        return int(value)

    def setting(self, key, default=""):
        row = self.connection.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.connection.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, str(value)))
        self.connection.commit()

    def _audit(self, actor, action):
        entity = "activity"
        record = {"id": self.next_id(entity), "user": actor, "action": action, "date": datetime.now().astimezone().isoformat(timespec="seconds")}
        self.connection.execute("INSERT INTO records VALUES (?,?,?)", (entity, record["id"], json.dumps(record, ensure_ascii=False)))

    def save(self, entity, record, actor, record_id=None, extra_updates=None):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if record_id is None:
                record["id"] = self.next_id(entity)
            else:
                record["id"] = int(record_id)
            self.connection.execute(
                "INSERT OR REPLACE INTO records VALUES (?,?,?)",
                (entity, record["id"], json.dumps(record, ensure_ascii=False)),
            )
            for update_entity, update_record in (extra_updates or []):
                self.connection.execute(
                    "INSERT OR REPLACE INTO records VALUES (?,?,?)",
                    (update_entity, int(update_record["id"]), json.dumps(update_record, ensure_ascii=False)),
                )
            self._audit(actor, ("تعديل" if record_id is not None else "إضافة") + f" سجل {entity} #{record['id']}")
            self.connection.commit()
            return record
        except Exception:
            self.connection.rollback()
            raise

    def delete(self, entity, record_id, actor, extra_updates=None):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            for update_entity, update_record in (extra_updates or []):
                self.connection.execute(
                    "INSERT OR REPLACE INTO records VALUES (?,?,?)",
                    (update_entity, int(update_record["id"]), json.dumps(update_record, ensure_ascii=False)),
                )
            self.connection.execute("DELETE FROM records WHERE entity=? AND record_id=?", (entity, int(record_id)))
            self._audit(actor, f"حذف سجل {entity} #{record_id}")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def export_data(self):
        result: dict[str, object] = {key: self.list(key) for key in DEFAULT_DATA}
        result["settings"] = {row["key"]: row["value"] for row in self.connection.execute("SELECT key,value FROM settings")}
        return result

    def import_data(self, data, actor):
        if not isinstance(data, dict):
            raise ValueError("بنية النسخة الاحتياطية غير صالحة")
        backward_compatible_entities = {
            "nurses", "attendance", "messages", "death_certificate_requests", "clinics", "donations", "operation_rooms", "surgeries", "support_tickets",
            "medication_batches", "insurance_claims", "assets", "sterilization_cycles", "feedback", "service_prices",
        }
        missing = [key for key in DEFAULT_DATA if key not in backward_compatible_entities and not isinstance(data.get(key), list)]
        if missing:
            raise ValueError("النسخة لا تحتوي القوائم المطلوبة: " + ", ".join(missing))
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute("DELETE FROM records")
            for entity in DEFAULT_DATA:
                for item in data.get(entity, []):
                    if not isinstance(item, dict) or not isinstance(item.get("id"), int):
                        raise ValueError(f"سجل غير صالح في {entity}")
                    self.connection.execute("INSERT INTO records VALUES (?,?,?)", (entity, item["id"], json.dumps(item, ensure_ascii=False)))
            self.connection.execute("DELETE FROM settings")
            for key, value in data.get("settings", {}).items():
                self.connection.execute("INSERT INTO settings VALUES (?,?)", (str(key), str(value)))
            self._audit(actor, "استعادة نسخة احتياطية")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        self.ensure_clinics()
        self.ensure_operation_rooms()
        self.ensure_inventory_thresholds()

    def close(self):
        self.connection.close()


def qr_numeric_matrix(value):
    """Create a version-1 QR matrix for numeric patient IDs."""
    value = str(value)
    if not value.isdigit() or not 1 <= len(value) <= 41:
        raise ValueError("يجب أن يكون رقم المريض رقماً من 1 إلى 41 خانة")
    bits = []

    def append(number, length):
        bits.extend((number >> shift) & 1 for shift in range(length - 1, -1, -1))

    append(1, 4)
    append(len(value), 10)
    for offset in range(0, len(value), 3):
        chunk = value[offset:offset + 3]
        append(int(chunk), 10 if len(chunk) == 3 else 7 if len(chunk) == 2 else 4)
    for _ in range(min(4, 152 - len(bits))):
        bits.append(0)
    while len(bits) % 8:
        bits.append(0)
    data = [sum(bits[i + j] << (7 - j) for j in range(8)) for i in range(0, len(bits), 8)]
    pad = 0
    while len(data) < 19:
        data.append(0xEC if pad % 2 == 0 else 0x11)
        pad += 1

    def multiply(left, right):
        result = 0
        while right:
            if right & 1:
                result ^= left
            left <<= 1
            if left & 0x100:
                left ^= 0x11D
            right >>= 1
        return result

    generator = [1]
    for root in range(7):
        next_generator = [0] * (len(generator) + 1)
        for index, coefficient in enumerate(generator):
            next_generator[index] ^= coefficient
            next_generator[index + 1] ^= multiply(coefficient, 1 << root)
        generator = next_generator
    remainder = [0] * 7
    for byte in data:
        factor = byte ^ remainder[0]
        remainder = remainder[1:] + [0]
        for index in range(7):
            remainder[index] ^= multiply(generator[index + 1], factor)
    codewords = data + remainder
    modules = [[False] * 21 for _ in range(21)]
    reserved = [[False] * 21 for _ in range(21)]

    def set_function(row, col, dark):
        if 0 <= row < 21 and 0 <= col < 21:
            modules[row][col] = dark
            reserved[row][col] = True

    for top, left in ((0, 0), (0, 14), (14, 0)):
        for row in range(-1, 8):
            for col in range(-1, 8):
                distance = max(abs(row - 3), abs(col - 3))
                set_function(top + row, left + col, distance not in (2, 4))
    for index in range(8, 13):
        set_function(6, index, index % 2 == 0)
        set_function(index, 6, index % 2 == 0)
    format_data = 8
    format_remainder = format_data
    for _ in range(10):
        format_remainder = (format_remainder << 1) ^ ((format_remainder >> 9) * 0x537)
    format_bits = ((format_data << 10) | format_remainder) ^ 0x5412
    for index in range(6):
        set_function(8, index, bool((format_bits >> index) & 1))
    set_function(8, 7, bool((format_bits >> 6) & 1))
    set_function(8, 8, bool((format_bits >> 7) & 1))
    set_function(7, 8, bool((format_bits >> 8) & 1))
    for index in range(9, 15):
        set_function(14 - index, 8, bool((format_bits >> index) & 1))
    for index in range(8):
        set_function(8, 20 - index, bool((format_bits >> index) & 1))
    for index in range(8, 15):
        set_function(6 + index, 8, bool((format_bits >> index) & 1))
    set_function(13, 8, True)
    stream = [((byte >> shift) & 1) for byte in codewords for shift in range(7, -1, -1)]
    bit_index = 0
    right = 20
    while right >= 1:
        if right == 6:
            right -= 1
        for step in range(21):
            row = 20 - step if ((right + 1) & 2) == 0 else step
            for offset in range(2):
                col = right - offset
                if reserved[row][col]:
                    continue
                dark = bool(stream[bit_index]) if bit_index < len(stream) else False
                bit_index += 1
                if (row + col) % 2 == 0:
                    dark = not dark
                modules[row][col] = dark
        right -= 2
    return modules


class HospitalApp:
    def __init__(self, root, store=None):
        self.root = root
        self.store = store or HospitalStore()
        self.user_name = ""
        self.role = ""
        self.language = self.store.setting("language", "ar")
        self.dark = self.store.setting("theme", "light") == "dark"
        self.search_var = tk.StringVar()
        self.current_page = "dashboard"
        self.page_history = []
        self.tree = None
        self.status_label = None
        self.table_count_label = None
        self.toast_window = None
        self.toast_after_id = None
        self.sort_state = {}
        self.clinic_booking_specialty = None
        self.hospital_name = self.store.setting("hospital_name", "المشفى العالمي")
        self.accent = self.store.setting("accent", "#0b3d91")
        self.root.title(self.hospital_name)
        self.root.geometry("1360x820")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.apply_theme()
        self.show_login()

    def apply_theme(self):
        self.bg, self.fg, self.panel = (
            ("#111827", "#f8fafc", "#1f2937") if self.dark
            else ("#eef3f7", "#1e293b", "#ffffff")
        )
        self.muted = "#94a3b8" if self.dark else "#64748b"
        self.line = "#334155" if self.dark else "#dfe8ef"
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=self.bg, foreground=self.fg)
        style.configure("TFrame", background=self.bg)
        style.configure("Panel.TFrame", background=self.panel)
        style.configure("Card.TFrame", background=self.panel, borderwidth=1, relief="solid")
        style.configure("Login.TFrame", background=self.panel, borderwidth=1, relief="solid")
        style.configure("TLabel", background=self.bg, foreground=self.fg)
        style.configure("Panel.TLabel", background=self.panel, foreground=self.fg)
        style.configure("Muted.TLabel", background=self.panel, foreground=self.muted)
        style.configure("TLabelframe", background=self.bg, foreground=self.fg, bordercolor=self.line, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=self.bg, foreground=self.accent, font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground=self.panel, foreground=self.fg, bordercolor=self.line, lightcolor=self.line, darkcolor=self.line, padding=(9, 7))
        style.map("TEntry", bordercolor=[("focus", self.accent)], lightcolor=[("focus", self.accent)], darkcolor=[("focus", self.accent)])
        style.configure("TButton", padding=(12, 8), font=("Segoe UI", 10))
        style.map("TButton", background=[("active", self.accent), ("pressed", self.accent)], foreground=[("active", "white"), ("pressed", "white")])
        style.configure("Nav.TButton", padding=(11, 10), anchor="e", background=self.panel, foreground=self.fg)
        style.map("Nav.TButton", background=[("active", self.accent)], foreground=[("active", "white")])
        style.configure("Accent.TButton", padding=(12, 8), background=self.accent, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", self.accent), ("pressed", self.accent)], foreground=[("active", "white"), ("pressed", "white")])
        style.configure("Treeview", rowheight=38, background=self.panel, fieldbackground=self.panel, foreground=self.fg, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=self.accent, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", self.accent)], foreground=[("selected", "white")])
        style.configure("TScrollbar", background=self.panel, troughcolor=self.bg, bordercolor=self.bg, arrowcolor=self.fg)
        style.configure("TSeparator", background=self.line)
        self.root.configure(bg=self.bg)

    def show_login(self):
        self.login = ttk.Frame(self.root, padding=4)
        self.login.place(relx=.5, rely=.5, anchor="center")
        card = ttk.Frame(self.login, padding=32, style="Login.TFrame")
        card.pack()
        brand = tk.Frame(card, bg=self.accent, padx=18, pady=12)
        brand.pack(fill="x", pady=(0, 18))
        tk.Label(
            brand,
            text=f"🏥  {self.hospital_name}",
            bg=self.accent,
            fg="white",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="center")
        ttk.Label(card, text="تسجيل الدخول إلى التطبيق المحلي", font=("Segoe UI", 11)).pack(pady=(0, 8))
        self.username_var = tk.StringVar(value="admin")
        self.password_var = tk.StringVar()
        ttk.Label(card, text="اسم المستخدم").pack(anchor="e", pady=(12, 4))
        self.username_entry = ttk.Entry(card, textvariable=self.username_var, width=34)
        self.username_entry.pack(ipady=4)
        ttk.Label(card, text="كلمة المرور").pack(anchor="e", pady=(12, 4))
        self.password_entry = ttk.Entry(card, textvariable=self.password_var, show="*", width=34)
        self.password_entry.pack(ipady=4)
        ttk.Button(card, text="تسجيل الدخول", command=self.login_user, style="Accent.TButton").pack(fill="x", pady=(18, 12), ipady=3)
        ttk.Label(
            card,
            text="حسابات تجريبية: admin / doctor / reception — كلمة المرور 1234",
            style="Muted.TLabel",
            wraplength=420,
            justify="center",
        ).pack(pady=(2, 0))
        self.password_entry.bind("<Return>", lambda _event: self.login_user())
        self.username_entry.focus_set()

    def login_user(self):
        username = self.username_var.get().strip()
        account = USERS.get(username)
        if not account or account[0] != self.password_var.get():
            messagebox.showerror("تعذر الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة")
            return
        self.user_name, self.role = account[1], account[2]
        self.login.destroy()
        self.build_main()
        self.audit("تسجيل دخول")
        self.notify(f"مرحباً {self.user_name}")
        self.check_reminders()

    def logout(self):
        self.audit("تسجيل خروج")
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
        if hasattr(self, "shell") and self.shell.winfo_exists():
            self.shell.destroy()
        self.user_name, self.role = "", ""
        self.page_history.clear()
        self.root.unbind("<Control-k>")
        self.root.unbind("<Control-K>")
        self.root.unbind("<Control-n>")
        self.root.unbind("<Control-N>")
        self.root.unbind("<Escape>")
        self.show_login()

    def build_main(self):
        self.root.title(self.hospital_name)
        shell = ttk.Frame(self.root)
        shell.pack(fill="both", expand=True)
        self.shell = shell
        self.sidebar = ttk.Frame(shell, padding=(8, 12), style="Panel.TFrame")
        self.sidebar.pack(side="right", fill="y", padx=(0, 6))
        brand = tk.Frame(self.sidebar, bg=self.accent, padx=8, pady=9)
        brand.pack(fill="x", pady=(0, 12))
        tk.Label(
            brand,
            text=self.hospital_name,
            bg=self.accent,
            fg="white",
            font=("Segoe UI", 12, "bold"),
            wraplength=175,
            justify="center",
        ).pack(fill="x")
        navigation = ttk.Frame(self.sidebar, style="Panel.TFrame")
        navigation.pack(fill="both", expand=True)
        self.nav_canvas = tk.Canvas(navigation, width=220, background=self.panel, highlightthickness=0, borderwidth=0)
        nav_scrollbar = ttk.Scrollbar(navigation, orient="vertical", command=self.nav_canvas.yview)
        self.nav_canvas.configure(yscrollcommand=nav_scrollbar.set)
        nav_scrollbar.pack(side="left", fill="y")
        self.nav_canvas.pack(side="right", fill="both", expand=True)
        self.nav_frame = ttk.Frame(self.nav_canvas, style="Panel.TFrame")
        self.nav_window = self.nav_canvas.create_window((0, 0), window=self.nav_frame, anchor="nw")
        self.nav_frame.bind("<Configure>", lambda _event: self.nav_canvas.configure(scrollregion=self.nav_canvas.bbox("all")))
        self.nav_canvas.bind("<Configure>", lambda event: self.nav_canvas.itemconfigure(self.nav_window, width=event.width))
        self.nav_canvas.bind("<Enter>", self.bind_navigation_wheel)
        self.nav_canvas.bind("<Leave>", self.unbind_navigation_wheel)
        self.nav_buttons = {}
        self.content = ttk.Frame(shell, padding=(14, 12, 12, 10))
        self.content.pack(side="left", fill="both", expand=True)
        self.header = ttk.Frame(self.content, style="Panel.TFrame", padding=(10, 8))
        self.header.pack(fill="x", pady=(0, 10))
        self.page_title = ttk.Label(self.header, text="", style="Panel.TLabel", font=("Segoe UI", 19, "bold"))
        self.page_title.pack(side="right", padx=8)
        self.user_label = ttk.Label(self.header, text=f"{self.user_name} — {self.label_text(self.role_label())}", style="Panel.TLabel")
        self.user_label.pack(side="left", padx=8)
        ttk.Button(self.header, text=self.label_text("رجوع"), command=self.go_back).pack(side="right", padx=4)
        ttk.Button(self.header, text=self.label_text("تسجيل خروج"), command=self.logout).pack(side="left", padx=4)
        toolbar = ttk.Frame(self.content)
        toolbar.pack(fill="x", pady=(0, 10))
        self.toolbar = toolbar
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="right", padx=4)
        self.search_entry.configure(foreground=self.fg)
        self.search_entry.bind("<Return>", lambda _event: self.show_global_search())
        self.search_entry.bind("<Control-a>", lambda event: self.select_all_text(event))
        ttk.Button(toolbar, text="×", width=3, command=lambda: self.search_var.set("")).pack(side="right", padx=(0, 4))
        ttk.Button(toolbar, text=self.label_text("بحث"), command=self.show_global_search).pack(side="right")
        ttk.Button(toolbar, text=self.label_text("🌙 / ☀️"), command=self.toggle_theme).pack(side="left", padx=3)
        ttk.Button(toolbar, text=self.label_text("عربي / English"), command=self.toggle_language).pack(side="left", padx=3)
        ttk.Button(toolbar, text=self.label_text("📥 نسخة احتياطية"), command=self.export_backup).pack(side="left", padx=3)
        ttk.Button(toolbar, text="تقييم المراجع", command=self.open_feedback_kiosk).pack(side="left", padx=3)
        if self.role == "admin":
            ttk.Button(toolbar, text=self.label_text("استعادة"), command=self.import_backup).pack(side="left", padx=3)
            ttk.Button(toolbar, text=self.label_text("هوية المشفى"), command=self.customize_brand).pack(side="left", padx=3)
            emergency_text = "إنهاء وضع الطوارئ" if self.store.setting("emergency_mode") == "1" else "تفعيل وضع الطوارئ"
            self.emergency_button = ttk.Button(toolbar, text=emergency_text, command=self.toggle_emergency_mode)
            self.emergency_button.pack(side="left", padx=3)
        self.body = ttk.Frame(self.content)
        self.body.pack(fill="both", expand=True)
        self.table_count_label = ttk.Label(self.content, text="")
        self.table_count_label.pack(anchor="e", pady=(5, 0))
        self.status_label = ttk.Label(self.content, text="💾 قاعدة بيانات محلية على هذا الجهاز")
        self.status_label.pack(fill="x", pady=(8, 0))
        for key, page in PAGES.items():
            if not self.can_view(key):
                continue
            title = str(self.page_title_text(key, page["title"]))
            button = ttk.Button(self.nav_frame, text=title, style="Nav.TButton", command=lambda item=key: self.show_page(item))
            button.pack(fill="x", pady=3)
            self.nav_buttons[key] = button
        ttk.Separator(self.nav_frame, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(self.nav_frame, text="العيادات", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(2, 4))
        for clinic in self.store.list("clinics"):
            clinic_key = f"clinic:{clinic['id']}"
            if not self.can_view(clinic_key):
                continue
            clinic_row = ttk.Frame(self.nav_frame, style="Panel.TFrame")
            clinic_row.pack(fill="x", pady=2)
            button = ttk.Button(
                clinic_row,
                text=f"{clinic.get('icon', '🏥')} {clinic.get('name', 'العيادة')}",
                style="Nav.TButton",
                command=lambda item=clinic_key: self.show_page(item),
            )
            button.pack(side="right", fill="x", expand=True)
            self.nav_buttons[clinic_key] = button
            if self.can_add("appts") or (
                clinic.get("specialty") == "تبرع بالدم" and self.can_add("donations")
            ):
                booking_button = ttk.Button(
                    clinic_row,
                    text=self.label_text("تسجيل تبرع" if clinic.get("specialty") == "تبرع بالدم" else "حجز"),
                    command=lambda specialty=clinic.get("specialty", ""): self.open_clinic_booking(specialty),
                )
                booking_button.pack(side="left", padx=(3, 0))
        self.search_var.trace_add("write", lambda *_args: self.refresh_page())
        self.root.bind("<Control-k>", self.focus_search)
        self.root.bind("<Control-K>", self.focus_search)
        self.root.bind("<Control-n>", self.add_current)
        self.root.bind("<Control-N>", self.add_current)
        self.root.bind("<Escape>", self.close_dialog)
        self.show_page("dashboard")
        self.root.after(30000, self.reminder_tick)

    def bind_navigation_wheel(self, _event=None):
        self.nav_canvas.bind_all("<MouseWheel>", self.scroll_navigation)
        self.nav_canvas.bind_all("<Button-4>", self.scroll_navigation)
        self.nav_canvas.bind_all("<Button-5>", self.scroll_navigation)

    def unbind_navigation_wheel(self, _event=None):
        self.nav_canvas.unbind_all("<MouseWheel>")
        self.nav_canvas.unbind_all("<Button-4>")
        self.nav_canvas.unbind_all("<Button-5>")

    def scroll_navigation(self, event):
        if getattr(event, "num", None) == 4:
            amount = -1
        elif getattr(event, "num", None) == 5:
            amount = 1
        else:
            amount = -1 if event.delta > 0 else 1
        self.nav_canvas.yview_scroll(amount, "units")
        return "break"

    def role_label(self):
        return {"admin": "مدير", "doctor": "طبيب", "reception": "استقبال"}.get(self.role, "")

    def can_view(self, key):
        if key in ("insurance_claims", "service_prices", "assets"):
            return self.role == "admin"
        if key in ("medication_batches", "sterilization_cycles", "surgeries", "operation_rooms"):
            return self.role in ("admin", "doctor")
        if key.startswith("clinic:"):
            if self.role not in ("admin", "doctor", "reception"):
                return False
            clinic_id = key.partition(":")[2]
            clinic = self.store.get("clinics", int(clinic_id)) if clinic_id.isdigit() else None
            if clinic and clinic.get("specialty") == "تبرع بالدم":
                return self.role in ("admin", "doctor")
            return True
        if key == "donations":
            return self.role in ("admin", "doctor")
        if key in ("payroll", "attendance", "insurance", "activity", "reports", "settings"):
            return self.role == "admin"
        if key == "death_certificate_requests":
            return self.role in ("admin", "reception")
        return True

    def can_add(self, key):
        if self.role == "admin":
            return True
        if self.role == "doctor":
            return key in {"patients", "appts", "labs", "prescriptions", "vitals", "ratings", "attachments", "donations", "surgeries", "messages", "support_tickets", "medication_batches", "sterilization_cycles"}
        if self.role == "reception":
            return key in {"patients", "appts", "bills", "payments", "reminders", "beds", "death_certificate_requests", "messages", "support_tickets"}
        return False

    def page_title_text(self, key, title):
        en = {
            "dashboard": "Dashboard", "clinics": "Clinics", "doctors": "Doctors", "patients": "Patients", "appts": "Appointments",
            "nurses": "Nursing",
            "attendance": "Staff attendance",
            "messages": "Internal chat",
            "emergency": "Emergency room",
            "attendance": "Staff attendance",
            "messages": "Internal chat",
            "emergency": "Emergency room",
            "meds": "Pharmacy", "labs": "Laboratory", "bills": "Invoices", "prescriptions": "Prescriptions",
            "vitals": "Vital signs", "wards": "Wards", "beds": "Beds", "payments": "Payments",
            "insurance": "Insurance", "payroll": "Payroll", "ratings": "Service ratings",
            "attachments": "Patient documents", "reminders": "Appointment reminders", "activity": "Audit log",
            "death_certificate_requests": "Death document requests", "donations": "Blood donations",
            "operation_rooms": "Operating rooms", "surgeries": "Surgery schedule",
            "support_tickets": "Internal support tickets",
            "medication_batches": "Medicine batches and expiry",
            "insurance_claims": "Insurance claims",
            "assets": "Assets and maintenance",
            "sterilization_cycles": "Sterilization cycles",
            "feedback": "Patient feedback",
            "service_prices": "Service price list",
        }
        return en.get(key, title) if self.language == "en" else title

    def label_text(self, arabic):
        return ENGLISH.get(arabic, arabic) if self.language == "en" else arabic

    def show_page(self, key, remember=True):
        if key.startswith("clinic:"):
            clinic_id = key.partition(":")[2]
            clinic = self.store.get("clinics", int(clinic_id)) if clinic_id.isdigit() else None
            if not clinic or not self.can_view(key):
                return
            if remember and key != self.current_page:
                self.page_history.append(self.current_page)
            self.current_page = key
            for nav_key, button in self.nav_buttons.items():
                button.configure(style="Accent.TButton" if nav_key == key else "Nav.TButton")
            for child in self.body.winfo_children():
                child.destroy()
            if self.table_count_label and self.table_count_label.winfo_exists():
                self.table_count_label.configure(text="")
            self.page_title.configure(text=f"{clinic.get('icon', '🏥')} {clinic.get('name', 'العيادة')}")
            self.render_clinic_page(clinic)
            return
        if key not in PAGES or not self.can_view(key):
            return
        if remember and key != self.current_page:
            self.page_history.append(self.current_page)
        self.current_page = key
        for nav_key, button in self.nav_buttons.items():
            button.configure(style="Accent.TButton" if nav_key == key else "Nav.TButton")
        for child in self.body.winfo_children():
            child.destroy()
        self.page_title.configure(text=str(self.page_title_text(key, PAGES[key]["title"])))
        if key == "dashboard":
            if self.table_count_label and self.table_count_label.winfo_exists():
                self.table_count_label.configure(text="")
            self.render_dashboard()
            return
        if key == "emergency":
            self.render_emergency_page()
            return
        if key == "clinics":
            self.render_table(key)
            return
        if key == "wards":
            self.render_table(key)
            return
        self.render_table(key)

    def go_back(self):
        while self.page_history:
            previous = self.page_history.pop()
            if previous in PAGES and self.can_view(previous):
                self.show_page(previous, remember=False)
                return
            if previous.startswith("clinic:") and self.can_view(previous):
                clinic_id = previous.partition(":")[2]
                if clinic_id.isdigit() and self.store.get("clinics", int(clinic_id)):
                    self.show_page(previous, remember=False)
                    return
        self.show_page("dashboard", remember=False)

    def render_table(self, key):
        meta = PAGES[key]
        entity = meta["entity"]
        controls = ttk.Frame(self.body)
        controls.pack(fill="x", pady=(0, 8))
        if self.can_add(key) and key in FORM_FIELDS:
            ttk.Button(controls, text=self.label_text("＋ إضافة"), command=lambda: self.open_form(key)).pack(side="right", padx=3)
        if key == "clinics":
            ttk.Button(
                controls,
                text=self.label_text("فتح صفحة العيادة"),
                command=self.open_selected_clinic,
            ).pack(side="right", padx=3)
        if key == "patients":
            ttk.Button(controls, text=self.label_text("الملف الطبي"), command=self.open_selected_profile).pack(side="right", padx=3)
            ttk.Button(controls, text=self.label_text("بطاقة QR"), command=self.open_selected_qr).pack(side="right", padx=3)
            if self.role in ("admin", "doctor"):
                ttk.Button(controls, text=self.label_text("طباعة التقرير الطبي"), command=self.print_selected_medical_report).pack(side="right", padx=3)
        if key == "bills":
            ttk.Button(controls, text=self.label_text("طباعة الفاتورة"), command=self.print_selected_invoice).pack(side="right", padx=3)
        if key == "prescriptions":
            ttk.Button(controls, text=self.label_text("طباعة الوصفة"), command=self.print_selected_prescription).pack(side="right", padx=3)
        if key == "attachments":
            ttk.Button(controls, text=self.label_text("فتح الملف"), command=self.open_selected_attachment).pack(side="right", padx=3)
        if key == "appts" and self.can_add("reminders"):
            ttk.Button(controls, text=self.label_text("إنشاء تذكير"), command=self.create_appointment_reminder).pack(side="right", padx=3)
        if key == "appts" and self.can_add("appts"):
            ttk.Button(controls, text="تسجيل حضور", command=self.check_in_selected_appointment).pack(side="right", padx=3)
            ttk.Button(controls, text="بدء الكشف", command=self.start_selected_appointment_consultation).pack(side="right", padx=3)
            ttk.Button(controls, text="إلغاء الموعد", command=self.cancel_selected_appointment).pack(side="right", padx=3)
            ttk.Button(controls, text="طباعة بطاقة المريض", command=self.print_appointment_patient_card).pack(side="right", padx=3)
        if key == "reminders" and self.can_add("reminders"):
            ttk.Button(controls, text=self.label_text("إرسال عبر WhatsApp"), command=self.send_whatsapp_reminder).pack(side="right", padx=3)
        if key == "death_certificate_requests":
            ttk.Label(controls, text="نموذج طلب إداري فقط — ليس شهادة وفاة رسمية").pack(side="right", padx=5)
            ttk.Button(controls, text=self.label_text("طباعة الطلب"), command=self.print_selected_death_request).pack(side="right", padx=3)
        if key == "donations":
            ttk.Label(controls, text="نموذج تبرع للمراجعة — لا يُعد شهادة رسمية أو إثباتاً للفحوصات").pack(side="right", padx=5)
            ttk.Button(controls, text="طباعة نموذج التبرع", command=self.print_selected_donation).pack(side="right", padx=3)
        if key in ("appts", "vitals"):
            ttk.Button(controls, text=self.label_text("التقارير والرسوم"), command=self.open_reports).pack(side="right", padx=3)
        if key == "activity":
            ttk.Label(controls, text="سجل تدقيقي محلي — آخر العمليات أولاً").pack(side="right", padx=5)
        if key == "beds":
            ttk.Label(controls, text="الأسرّة المتاحة والمشغولة بحسب الجناح").pack(side="left", padx=5)
            self.render_bed_map(self.body)
        if key == "dashboard":
            return
        if self.role == "admin" and key in FORM_FIELDS:
            ttk.Button(controls, text=self.label_text("حذف المحدد"), command=self.delete_selected).pack(side="left", padx=3)
        elif self.role == "admin" and key == "activity":
            ttk.Button(controls, text=self.label_text("حذف المحدد"), command=self.delete_selected).pack(side="left", padx=3)
        ttk.Button(controls, text=self.label_text("تصدير CSV"), command=lambda: self.export_csv(key)).pack(side="left", padx=3)
        columns = ["_id"] + [name for name, _label in meta["columns"]]
        self.tree = ttk.Treeview(self.body, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("_id", text="#")
        self.tree.column("_id", width=55, anchor="center")
        for name, label in meta["columns"]:
            self.tree.heading(name, text=str(self.label_text(label)), command=lambda column=name: self.sort_table(column))
            self.tree.column(name, width=155, anchor="center", stretch=True)
        self.tree.tag_configure("even", background=self.panel)
        self.tree.tag_configure("odd", background=self.bg)
        self.tree.tag_configure("critical", foreground="#dc2626")
        self.tree.tag_configure("waiting", foreground="#b45309")
        self.tree.tag_configure("appt_done", background="#14532d" if self.dark else "#dcfce7", foreground="#dcfce7" if self.dark else "#166534")
        self.tree.tag_configure("appt_waiting", background="#713f12" if self.dark else "#fef3c7", foreground="#fef3c7" if self.dark else "#92400e")
        self.tree.tag_configure("appt_alert", background="#7f1d1d" if self.dark else "#fee2e2", foreground="#fee2e2" if self.dark else "#b91c1c")
        yscroll = ttk.Scrollbar(self.body, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(self.body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        if key != "messages":
            self.tree.bind("<Double-1>", lambda _event: self.edit_selected())
        self.refresh_page()

    def render_clinic_page(self, clinic):
        specialty = clinic.get("specialty", "")
        if specialty == "تبرع بالدم":
            self.render_blood_donation_clinic_page(clinic)
            return
        doctors = [item for item in self.store.list("doctors") if item.get("spec") == specialty]
        doctor_names = {item.get("name") for item in doctors}
        appointments = [
            item for item in self.store.list("appts")
            if item.get("doctor") in doctor_names and item.get("status") != "ملغي"
        ]
        patient_names = {item.get("patient") for item in appointments if item.get("patient")}
        available = sum(1 for item in doctors if item.get("status") == "نشط")

        banner = ttk.Frame(self.body, style="Panel.TFrame", padding=18)
        banner.pack(fill="x", pady=(2, 10))
        ttk.Label(
            banner,
            text=f"{clinic.get('icon', '🏥')}  {clinic.get('name', 'العيادة')}",
            style="Panel.TLabel",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="e")
        ttk.Label(
            banner,
            text=f"{clinic.get('description', '')}  |  التخصص: {specialty}  |  الحالة: {clinic.get('status', 'مفتوحة')}",
            style="Panel.TLabel",
            wraplength=950,
        ).pack(anchor="e", pady=(6, 0))
        metrics = ttk.Frame(self.body)
        metrics.pack(fill="x", pady=5)
        for value, label in (
            (len(doctors), "إجمالي الأطباء"),
            (available, "أطباء معتمدون ونشطون"),
            (len(appointments), "المواعيد المسجلة"),
            (len(patient_names), "مرضى لديهم مواعيد"),
        ):
            card = ttk.Frame(metrics, style="Panel.TFrame", padding=12)
            card.pack(side="right", fill="x", expand=True, padx=4)
            ttk.Label(card, text=str(value), style="Panel.TLabel", font=("Segoe UI", 18, "bold")).pack()
            ttk.Label(card, text=label, style="Panel.TLabel").pack()

        actions = ttk.Frame(self.body)
        actions.pack(fill="x", pady=5)
        if self.can_add("appts") and clinic.get("status") == "مفتوحة":
            ttk.Button(
                actions,
                text="＋ حجز موعد لهذه العيادة",
                style="Accent.TButton",
                command=lambda: self.open_clinic_booking(specialty),
            ).pack(side="right", padx=4)
        if self.role == "admin":
            ttk.Button(
                actions,
                text="＋ إضافة طبيب",
                command=lambda: self.open_clinic_doctor(specialty),
            ).pack(side="right", padx=4)
            ttk.Button(
                actions,
                text="إعدادات العيادة",
                command=lambda: self.open_form("clinics", clinic),
            ).pack(side="right", padx=4)
        ttk.Button(actions, text="عرض المرضى", command=lambda: self.show_page("patients")).pack(side="left", padx=4)
        ttk.Button(actions, text="كل المواعيد", command=lambda: self.show_page("appts")).pack(side="left", padx=4)

        panels = ttk.Panedwindow(self.body, orient="vertical")
        panels.pack(fill="both", expand=True, pady=6)
        doctors_frame = ttk.Labelframe(panels, text="أطباء العيادة", padding=6)
        appointments_frame = ttk.Labelframe(panels, text="مواعيد العيادة", padding=6)
        panels.add(doctors_frame, weight=1)
        panels.add(appointments_frame, weight=2)
        self.clinic_doctor_tree = ttk.Treeview(
            doctors_frame,
            columns=("name", "status", "phone", "verification"),
            show="headings",
            height=5,
        )
        for key, label, width in (
            ("name", "الطبيب", 230), ("status", "الحالة", 140),
            ("phone", "الهاتف", 160), ("verification", "ملاحظة", 390),
        ):
            self.clinic_doctor_tree.heading(key, text=label)
            self.clinic_doctor_tree.column(key, width=width, anchor="center")
        self.clinic_doctor_tree.pack(fill="both", expand=True)
        for doctor in doctors:
            note = doctor.get("verification", "")
            if doctor.get("sample_data"):
                note = note or "ملف افتراضي — يلزم التحقق واستبداله"
            self.clinic_doctor_tree.insert(
                "", "end", iid=str(doctor["id"]),
                values=(doctor.get("name", ""), doctor.get("status", ""), doctor.get("phone") or "غير مسجل", note),
            )
        if self.role == "admin":
            self.clinic_doctor_tree.bind("<Double-1>", lambda _event: self.edit_clinic_doctor())

        self.clinic_appointment_tree = ttk.Treeview(
            appointments_frame,
            columns=("date", "time", "patient", "doctor", "status"),
            show="headings",
            height=8,
        )
        for key, label, width in (
            ("date", "التاريخ", 125), ("time", "الوقت", 95), ("patient", "المريض", 200),
            ("doctor", "الطبيب", 200), ("status", "الحالة", 130),
        ):
            self.clinic_appointment_tree.heading(key, text=label)
            self.clinic_appointment_tree.column(key, width=width, anchor="center")
        self.clinic_appointment_tree.pack(fill="both", expand=True)
        appointments.sort(key=lambda item: (item.get("date", ""), item.get("time", "")))
        for item in appointments:
            self.clinic_appointment_tree.insert(
                "", "end", iid=str(item["id"]),
                values=(item.get("date", ""), item.get("time", ""), item.get("patient", ""), item.get("doctor", ""), item.get("status", "")),
            )
        if clinic.get("status") != "مفتوحة":
            ttk.Label(
                self.body,
                text="هذه العيادة مغلقة مؤقتاً؛ لا يمكن حجز مواعيد جديدة.",
                foreground="#b45309",
            ).pack(anchor="e", pady=6)

    def render_blood_donation_clinic_page(self, clinic):
        donations = sorted(self.store.list("donations"), key=lambda item: (item.get("date", ""), item.get("id", 0)), reverse=True)
        completed = sum(1 for item in donations if item.get("status") == "تم التبرع")
        banner = ttk.Frame(self.body, style="Panel.TFrame", padding=18)
        banner.pack(fill="x", pady=(2, 10))
        ttk.Label(
            banner,
            text=f"{clinic.get('icon', '🩸')}  {clinic.get('name', 'عيادة التبرع بالدم')}",
            style="Panel.TLabel",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="e")
        ttk.Label(
            banner,
            text="تسجيل تبرعات الدم ومكوناته وإعداد نموذج إيصال للطباعة بعد مراجعة السجل.",
            style="Panel.TLabel",
            wraplength=950,
        ).pack(anchor="e", pady=(6, 0))
        cards = ttk.Frame(self.body)
        cards.pack(fill="x", pady=5)
        for value, label in ((len(donations), "سجلات التبرع"), (completed, "تبرعات مسجلة كمكتملة")):
            card = ttk.Frame(cards, style="Panel.TFrame", padding=12)
            card.pack(side="right", fill="x", expand=True, padx=4)
            ttk.Label(card, text=str(value), style="Panel.TLabel", font=("Segoe UI", 18, "bold")).pack()
            ttk.Label(card, text=label, style="Panel.TLabel").pack()
        actions = ttk.Frame(self.body)
        actions.pack(fill="x", pady=5)
        ttk.Button(actions, text="فتح سجل التبرعات", command=lambda: self.show_page("donations")).pack(side="right", padx=4)
        if self.can_add("donations"):
            ttk.Button(
                actions,
                text="＋ تسجيل تبرع",
                style="Accent.TButton",
                command=lambda: self.show_donation_form(),
            ).pack(side="right", padx=4)
        table = ttk.Treeview(
            self.body,
            columns=("date", "donor_name", "blood_type", "donation_type", "quantity_ml", "status"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width in (
            ("date", "التاريخ", 120), ("donor_name", "المتبرع", 200), ("blood_type", "الفصيلة", 100),
            ("donation_type", "نوع التبرع", 160), ("quantity_ml", "الكمية مل", 110), ("status", "الحالة", 130),
        ):
            table.heading(key, text=label)
            table.column(key, width=width, anchor="center")
        table.pack(fill="both", expand=True, pady=6)
        for item in donations:
            table.insert(
                "", "end", iid=str(item["id"]),
                values=tuple(item.get(key, "") for key in ("date", "donor_name", "blood_type", "donation_type", "quantity_ml", "status")),
            )

    def show_donation_form(self):
        if not self.can_add("donations"):
            self.notify("لا تملك صلاحية تسجيل التبرعات", "error")
            return
        self.show_page("donations")
        self.open_form("donations")

    def open_clinic_booking(self, specialty):
        clinic = next(
            (item for item in self.store.list("clinics") if item.get("specialty") == specialty),
            None,
        )
        if not clinic:
            self.notify("تعذر العثور على العيادة المطلوبة", "error")
            return
        if clinic.get("status") != "مفتوحة":
            self.notify(self.label_text("العيادة مغلقة حالياً ولا تستقبل حجوزات"), "error")
            return
        if specialty == "تبرع بالدم":
            if not self.can_add("donations"):
                self.notify(self.label_text("لا تملك صلاحية الحجز في هذه العيادة"), "error")
                return
            self.show_donation_form()
            return
        if not self.can_add("appts"):
            self.notify(self.label_text("لا تملك صلاحية الحجز في هذه العيادة"), "error")
            return
        if not any(item.get("spec") == specialty and item.get("status") == "نشط" for item in self.store.list("doctors")):
            messagebox.showwarning("لا يوجد طبيب معتمد", "لا يوجد طبيب نشط ومعتمد في هذه العيادة. راجع الإدارة لتحديث بيانات الطبيب والتحقق منها.")
            return
        self.clinic_booking_specialty = specialty
        try:
            self.open_form("appts")
        finally:
            self.clinic_booking_specialty = None

    def open_clinic_doctor(self, specialty):
        if self.role != "admin":
            return
        self.clinic_booking_specialty = specialty
        try:
            self.open_form("doctors")
        finally:
            self.clinic_booking_specialty = None

    def edit_clinic_doctor(self):
        selection = self.clinic_doctor_tree.selection()
        if not selection:
            return
        doctor = self.store.get("doctors", int(selection[0]))
        if doctor:
            self.open_form("doctors", doctor)

    def refresh_page(self):
        if self.current_page == "dashboard" or self.current_page not in PAGES:
            return
        if not self.tree or not self.tree.winfo_exists():
            return
        meta = PAGES[self.current_page]
        entity = meta["entity"]
        if not entity:
            return
        query = self.search_var.get().strip().casefold()
        self.tree.delete(*self.tree.get_children())
        rows = self.store.list(entity)
        if entity == "wards":
            beds = self.store.list("beds")
            for row in rows:
                row["occupied"] = sum(1 for bed in beds if bed.get("ward") == row.get("name") and bed.get("patient"))
        if entity == "appts":
            for row in rows:
                row["wait_minutes"] = appointment_wait_minutes(row)
        if entity == "beds" and hasattr(self, "bed_canvas") and self.bed_canvas.winfo_exists():
            self.draw_bed_map()
        sort_column, reverse = self.sort_state.get(self.current_page, ("id", False))
        if sort_column != "id":
            rows.sort(key=lambda record: self.table_sort_value(record.get(sort_column)), reverse=reverse)
        visible_count = 0
        for record in rows:
            searchable = json.dumps(record, ensure_ascii=False).casefold()
            if query and query not in searchable:
                continue
            values = [record.get("id", "")]
            for key, _label in meta["columns"]:
                value = record.get(key, "")
                if key == "wait_minutes":
                    value = f"{value} دقيقة" if value is not None else "—"
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                values.append(value)
            status = str(record.get("status", ""))
            if entity == "appts":
                appointment_date = str(record.get("date", ""))
                appointment_time = str(record.get("time", ""))
                is_late = False
                if status in ("بالانتظار", "عاجل") and appointment_date == date.today().isoformat():
                    try:
                        is_late = datetime.strptime(appointment_time, "%H:%M").time() < datetime.now().time()
                    except ValueError:
                        is_late = False
                if status in ("مكتمل", "completed"):
                    tags = ("appt_done",)
                elif status in ("ملغي", "ملغاة", "ملغى", "عاجل", "متأخر", "cancelled", "canceled") or is_late:
                    tags = ("appt_alert",)
                elif status in ("بالانتظار", "waiting"):
                    tags = ("appt_waiting",)
                else:
                    tags = ("even",) if len(self.tree.get_children()) % 2 == 0 else ("odd",)
            else:
                tags = ("critical",) if status == "حرج" else ("waiting",) if status in ("بالانتظار", "قيد المراجعة", "قيد العلاج") else (("even",) if len(self.tree.get_children()) % 2 == 0 else ("odd",))
            self.tree.insert("", "end", iid=str(record.get("id")), values=values, tags=tags)
            visible_count += 1
        if self.table_count_label and self.table_count_label.winfo_exists():
            total_count = len(rows)
            self.table_count_label.configure(text=f"{visible_count} من {total_count} سجل" if query else f"{total_count} سجل")

    @staticmethod
    def table_sort_value(value):
        if value is None:
            return (0, "")
        try:
            return (2, float(value))
        except (TypeError, ValueError):
            return (1, str(value).casefold())

    def sort_table(self, column):
        if not self.tree or not self.tree.winfo_exists():
            return
        previous_column, previous_reverse = self.sort_state.get(self.current_page, ("", False))
        reverse = not previous_reverse if previous_column == column else False
        self.sort_state[self.current_page] = (column, reverse)
        meta = PAGES[self.current_page]
        for key, label in meta["columns"]:
            arrow = (" ▼" if reverse else " ▲") if key == column else ""
            self.tree.heading(key, text=str(self.label_text(label)) + arrow, command=lambda item=key: self.sort_table(item))
        self.refresh_page()

    def show_global_search(self):
        query = self.search_var.get().strip().casefold()
        if not query:
            self.focus_search()
            return
        matches = []
        for key, meta in PAGES.items():
            entity = meta["entity"]
            if not entity or entity == "activity" or not self.can_view(key):
                continue
            for record in self.store.list(entity):
                if query in json.dumps(record, ensure_ascii=False).casefold():
                    summary = " — ".join(str(record.get(field, "")) for field in ("name", "patient", "doctor", "date", "status") if record.get(field))
                    matches.append((key, record["id"], summary or json.dumps(record, ensure_ascii=False)[:100]))
        window = tk.Toplevel(self.root)
        window.title(self.label_text("نتائج البحث"))
        window.geometry("760x480")
        tree = ttk.Treeview(window, columns=("section", "id", "summary"), show="headings")
        for name, label, width in (("section", "القسم", 160), ("id", "#", 70), ("summary", "النتيجة", 500)):
            tree.heading(name, text=self.label_text(label))
            tree.column(name, width=width, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for index, (key, record_id, summary) in enumerate(matches):
            tree.insert("", "end", iid=str(index), values=(self.page_title_text(key, PAGES[key]["title"]), record_id, summary))
        ttk.Label(window, text=f"{len(matches)} نتيجة").pack(pady=(0, 8))

        def open_match(_event=None):
            selection = tree.selection()
            if not selection:
                return
            key, record_id, _summary = matches[int(selection[0])]
            window.destroy()
            self.show_page(key)
            if self.tree and self.tree.exists(str(record_id)):
                self.tree.selection_set(str(record_id))
                self.tree.see(str(record_id))
        tree.bind("<Double-1>", open_match)

    @staticmethod
    def select_all_text(event):
        event.widget.selection_range(0, "end")
        return "break"

    def render_dashboard(self):
        snapshot = dashboard_snapshot(self.store)
        shell = ttk.Frame(self.body)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, background=self.bg, highlightthickness=0)
        self.dashboard_canvas = canvas
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="right", fill="both", expand=True)
        dashboard = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=dashboard, anchor="nw")
        dashboard.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=(0, 0, event.width, event.height)),
        )
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        alert_items = []
        if snapshot["critical_alert_patients"]:
            alert_items.append((f"حالات حرجة: {snapshot['critical_alert_patients']}", "emergency"))
        if snapshot["urgent_appointments"]:
            alert_items.append((f"حالات طوارئ: {len(snapshot['urgent_appointments'])}", "emergency"))
        if snapshot["low_stock_medicines"]:
            alert_items.append((f"مخزون منخفض: {len(snapshot['low_stock_medicines'])}", "meds"))
        if snapshot["overdue_invoices"]:
            alert_items.append((f"فواتير متأخرة: {len(snapshot['overdue_invoices'])}", "bills"))
        if snapshot["expiring_batches"] and self.can_view("medication_batches"):
            alert_items.append((f"دفعات منتهية/قريبة الانتهاء: {len(snapshot['expiring_batches'])}", "medication_batches"))
        if snapshot["assets_due"] and self.can_view("assets"):
            alert_items.append((f"أصول تحتاج صيانة: {len(snapshot['assets_due'])}", "assets"))
        if snapshot["sterilization_alerts"] and self.can_view("sterilization_cycles"):
            alert_items.append((f"دورات تعقيم تحتاج مراجعة: {len(snapshot['sterilization_alerts'])}", "sterilization_cycles"))
        if snapshot["feedback_complaints"] and self.can_view("feedback"):
            alert_items.append((f"شكاوى/تقييمات منخفضة: {len(snapshot['feedback_complaints'])}", "feedback"))
        alert_color = "#991b1b" if alert_items else "#166534"
        alert_bar = tk.Frame(dashboard, background=alert_color, padx=10, pady=8)
        alert_bar.pack(fill="x", pady=(0, 8))
        tk.Label(
            alert_bar,
            text="تنبيهات عاجلة" if alert_items else "لا توجد تنبيهات عاجلة مسجلة",
            background=alert_color,
            foreground="white",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="right", padx=(8, 12))
        for alert_text, page in alert_items:
            tk.Button(
                alert_bar,
                text=alert_text,
                command=lambda target=page: self.show_page(target),
                background=alert_color,
                foreground="white",
                activebackground="#7f1d1d" if alert_items else "#14532d",
                activeforeground="white",
                relief="flat",
                padx=8,
            ).pack(side="right", padx=3)
        if self.store.setting("emergency_mode") == "1":
            emergency_banner = tk.Frame(dashboard, background="#b91c1c", padx=12, pady=10)
            emergency_banner.pack(fill="x", pady=(0, 8))
            tk.Label(
                emergency_banner,
                text="وضع الطوارئ مفعّل — التسجيل العادي للمواعيد متوقف",
                background="#b91c1c",
                foreground="white",
                font=("Segoe UI", 13, "bold"),
            ).pack(anchor="center")

        intro = ttk.Frame(dashboard, style="Panel.TFrame", padding=(18, 12))
        intro.pack(fill="x", pady=(0, 8))
        intro_text = ttk.Frame(intro, style="Panel.TFrame")
        intro_text.pack(side="right", fill="x", expand=True)
        ttk.Label(
            intro_text,
            text=self.label_text("ملخص التشغيل اليومي"),
            style="Panel.TLabel",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="e")
        ttk.Label(
            intro_text,
            text=f"{self.label_text('اليوم')}: {date.today().isoformat()}  •  {self.user_name}",
            style="Panel.TLabel",
        ).pack(anchor="e", pady=(3, 0))
        ttk.Button(
            intro,
            text=self.label_text("تحديث اللوحة"),
            command=lambda: self.show_page("dashboard", remember=False),
        ).pack(side="left", padx=4)

        cards = ttk.Frame(dashboard)
        cards.pack(fill="x", pady=(0, 8))
        bed_ratio = (
            f"{snapshot['beds_occupied']} / {snapshot['beds_total']}"
            if snapshot["beds_total"]
            else "—"
        )
        metrics = (
            ("إجمالي المرضى", snapshot["patients"], "سجلات مرضى", "patients"),
            ("مواعيد اليوم", len(snapshot["appointments_today"]), "تُعرض المواعيد غير الملغاة فقط", "appts"),
            ("انتظار/عاجل اليوم", snapshot["waiting_today"], "موعد بالانتظار أو عاجل", "appts"),
            ("متوسط الانتظار", f"{snapshot['average_wait_minutes']} دقيقة" if snapshot["average_wait_minutes"] is not None else "—", "للمرضى المسجل حضورهم", "appts"),
            ("إشغال الأسرة المسجلة", bed_ratio, "من الأسرة المسجلة" if snapshot["beds_total"] else "لا توجد أسرّة مسجلة", "beds"),
            ("تنبيه مخزون", len(snapshot["low_stock_medicines"]), "أصناف منخفضة أو نفدت", "meds"),
            ("تحاليل جاهزة", snapshot["ready_labs"], "نتائج جاهزة للمراجعة", "labs"),
            ("الطاقم النشط", snapshot["active_staff"], "طبيب وممرض بحالة نشط", "doctors"),
            ("عيادات مفتوحة", snapshot["open_clinics"], "بحسب الحالة المسجلة", "clinics"),
        )
        for column in range(4):
            cards.columnconfigure(column, weight=1, uniform="dashboard_metric")
        for index, (title, value, detail, page) in enumerate(metrics):
            card = ttk.Frame(cards, style="Panel.TFrame", padding=(12, 10))
            card.grid(row=index // 4, column=index % 4, sticky="nsew", padx=4, pady=4)
            ttk.Label(card, text=self.label_text(title), style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="e")
            ttk.Label(card, text=str(value), style="Panel.TLabel", font=("Segoe UI", 21, "bold")).pack(anchor="e", pady=(3, 0))
            ttk.Label(card, text=self.label_text(detail), style="Panel.TLabel", wraplength=220).pack(anchor="e")
            ttk.Button(card, text=self.label_text("فتح"), command=lambda target=page: self.show_page(target)).pack(anchor="e", pady=(6, 0))

        charts = ttk.Frame(dashboard)
        charts.pack(fill="x", pady=(0, 8))
        bed_panel = ttk.LabelFrame(charts, text="إشغال الأسرّة", padding=8)
        bed_panel.pack(side="right", fill="both", expand=True, padx=(0, 4))
        bed_chart = tk.Canvas(bed_panel, height=150, background=self.panel, highlightthickness=0)
        bed_chart.pack(fill="x")
        occupied = snapshot["beds_occupied"]
        available = max(0, snapshot["beds_total"] - occupied)
        if snapshot["beds_total"]:
            bed_chart.create_arc(28, 12, 148, 132, start=90, extent=-360 * occupied / snapshot["beds_total"], fill="#2563eb", outline=self.panel, style="pieslice")
            if available:
                bed_chart.create_arc(28, 12, 148, 132, start=90 - 360 * occupied / snapshot["beds_total"], extent=-360 * available / snapshot["beds_total"], fill="#cbd5e1", outline=self.panel, style="pieslice")
            bed_chart.create_text(88, 72, text=f"{occupied}/{snapshot['beds_total']}", fill=self.fg, font=("Segoe UI", 11, "bold"))
            ttk.Label(bed_panel, text=f"مشغول {occupied}  •  متاح {available}").pack(anchor="center")
        else:
            bed_chart.create_text(88, 72, text="لا توجد أسرّة", fill=self.fg)

        appointment_panel = ttk.LabelFrame(charts, text="حالات مواعيد اليوم", padding=8)
        appointment_panel.pack(side="left", fill="both", expand=True, padx=(4, 0))
        appointment_chart = tk.Canvas(appointment_panel, height=150, background=self.panel, highlightthickness=0)
        appointment_chart.pack(fill="x")
        appointment_statuses = (
            ("مكتمل", "#16a34a"),
            ("بالانتظار", "#eab308"),
            ("عاجل", "#dc2626"),
        )
        status_counts = [
            (label, color, sum(1 for item in snapshot["appointments_today"] if item.get("status") == label))
            for label, color in appointment_statuses
        ]
        appointment_total = sum(count for _label, _color, count in status_counts)
        if appointment_total:
            start_angle = 90
            for label, color, count in status_counts:
                if not count:
                    continue
                extent = -360 * count / appointment_total
                appointment_chart.create_arc(28, 12, 148, 132, start=start_angle, extent=extent, fill=color, outline=self.panel, style="pieslice")
                start_angle += extent
            appointment_chart.create_text(88, 72, text=str(appointment_total), fill=self.fg, font=("Segoe UI", 11, "bold"))
            ttk.Label(
                appointment_panel,
                text="  •  ".join(f"{label} {count}" for label, _color, count in status_counts),
            ).pack(anchor="center")
        else:
            appointment_chart.create_text(88, 72, text="لا توجد مواعيد", fill=self.fg)

        operations = ttk.Frame(dashboard)
        operations.pack(fill="both", expand=True, pady=(0, 8))
        agenda_panel = ttk.LabelFrame(operations, text=self.label_text("مواعيد اليوم"), padding=8)
        agenda_panel.pack(side="right", fill="both", expand=True, padx=(0, 4))
        agenda = ttk.Treeview(agenda_panel, columns=("time", "patient", "doctor", "status", "wait"), show="headings", height=7)
        for column, label, width in (
            ("time", "الوقت", 75),
            ("patient", "المريض", 170),
            ("doctor", "الطبيب", 170),
            ("status", "الحالة", 100),
            ("wait", "الانتظار (دقيقة)", 110),
        ):
            agenda.heading(column, text=self.label_text(label))
            agenda.column(column, width=width, anchor="center", stretch=True)
        agenda.tag_configure("urgent", foreground="#b91c1c")
        agenda.tag_configure("waiting", foreground="#a16207")
        agenda.tag_configure("appt_done", background="#14532d" if self.dark else "#dcfce7", foreground="#dcfce7" if self.dark else "#166534")
        agenda.tag_configure("appt_waiting", background="#713f12" if self.dark else "#fef3c7", foreground="#fef3c7" if self.dark else "#92400e")
        agenda.tag_configure("appt_alert", background="#7f1d1d" if self.dark else "#fee2e2", foreground="#fee2e2" if self.dark else "#b91c1c")
        agenda.pack(fill="both", expand=True)
        if snapshot["appointments_today"]:
            for appointment in snapshot["appointments_today"][:20]:
                status = str(appointment.get("status", ""))
                tag = "appt_alert" if status == "عاجل" else "appt_waiting" if status == "بالانتظار" else "appt_done" if status == "مكتمل" else ""
                agenda.insert(
                    "",
                    "end",
                    values=(
                        appointment.get("time", ""),
                        appointment.get("patient", ""),
                        appointment.get("doctor", ""),
                        self.label_text(status),
                        appointment_wait_minutes(appointment) if appointment_wait_minutes(appointment) is not None else "—",
                    ),
                    tags=(tag,) if tag else (),
                )
        else:
            ttk.Label(
                agenda_panel,
                text=self.label_text("لا توجد مواعيد مسجلة لهذا اليوم"),
            ).pack(anchor="e", pady=6)
        ttk.Button(agenda_panel, text=self.label_text("فتح"), command=lambda: self.show_page("appts")).pack(anchor="e", pady=(6, 0))

        followup = ttk.LabelFrame(operations, text=self.label_text("متابعة تشغيلية"), padding=10)
        followup.pack(side="left", fill="both", expand=True, padx=(4, 0))
        stock_names = "، ".join(str(item.get("name", "")) for item in snapshot["low_stock_medicines"][:3])
        stock_text = (
            f"{len(snapshot['low_stock_medicines'])} — {stock_names}"
            if snapshot["low_stock_medicines"]
            else self.label_text("لا توجد تنبيهات مخزون")
        )
        ttk.Label(followup, text=self.label_text("تنبيهات المخزون"), font=("Segoe UI", 10, "bold")).pack(anchor="e")
        ttk.Label(followup, text=stock_text, wraplength=360).pack(anchor="e", fill="x", pady=(2, 8))
        ttk.Button(followup, text=self.label_text("فتح"), command=lambda: self.show_page("meds")).pack(anchor="e")
        ttk.Separator(followup).pack(fill="x", pady=8)
        ttk.Label(
            followup,
            text=f"{self.label_text('نتائج جاهزة للمراجعة')}: {snapshot['ready_labs']}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="e")
        ttk.Button(followup, text=self.label_text("فتح"), command=lambda: self.show_page("labs")).pack(anchor="e", pady=(2, 8))
        ttk.Separator(followup).pack(fill="x", pady=4)
        ttk.Label(
            followup,
            text=f"{self.label_text('حالات حرجة مسجلة')}: {snapshot['critical_patients']}",
            wraplength=360,
        ).pack(anchor="e", pady=(4, 0))
        ttk.Label(
            followup,
            text=self.label_text("تحقق من السجلات قبل المتابعة السريرية"),
            wraplength=360,
        ).pack(anchor="e", pady=(2, 4))
        ttk.Button(followup, text=self.label_text("فتح"), command=lambda: self.show_page("patients")).pack(anchor="e")
        actions = ttk.LabelFrame(dashboard, text=self.label_text("إجراءات سريعة"), padding=8)
        actions.pack(fill="x", pady=(0, 8))
        if self.can_add("appts"):
            ttk.Button(
                actions,
                text=self.label_text("إضافة موعد"),
                command=lambda: (self.show_page("appts"), self.open_form("appts")),
            ).pack(side="right", padx=3, pady=3)
        if self.can_add("patients"):
            ttk.Button(
                actions,
                text=self.label_text("إضافة مريض"),
                command=lambda: (self.show_page("patients"), self.open_form("patients")),
            ).pack(side="right", padx=3, pady=3)
        ttk.Button(
            actions,
            text=self.label_text("شاشة الانتظار"),
            command=self.open_waiting_room,
        ).pack(side="right", padx=3, pady=3)
        if self.can_view("surgeries"):
            ttk.Button(
                actions,
                text=self.label_text("جدول العمليات"),
                command=lambda: self.show_page("surgeries"),
            ).pack(side="right", padx=3, pady=3)
        if self.role == "admin":
            ttk.Button(
                actions,
                text="📊 " + self.label_text("التقارير"),
                command=self.open_reports,
            ).pack(side="right", padx=3, pady=3)
        ttk.Button(
            actions,
            text="تقييم المراجع",
            command=self.open_feedback_kiosk,
        ).pack(side="right", padx=3, pady=3)
        ttk.Button(
            actions,
            text="🚑 متابعة الطوارئ",
            command=lambda: self.show_page("emergency"),
        ).pack(side="right", padx=3, pady=3)
        ttk.Button(
            actions,
            text="💬 المحادثة الداخلية",
            command=lambda: self.show_page("messages"),
        ).pack(side="right", padx=3, pady=3)
        clinic_shortcuts = ttk.LabelFrame(dashboard, text=self.label_text("العيادات"), padding=8)
        clinic_shortcuts.pack(fill="x", pady=(0, 8))
        clinics = [
            clinic for clinic in self.store.list("clinics")
            if self.can_view(f"clinic:{clinic.get('id', '')}")
        ]
        for index, clinic in enumerate(clinics):
            clinic_card = ttk.Frame(clinic_shortcuts, style="Panel.TFrame", padding=4)
            clinic_card.grid(row=index // 3, column=index % 3, sticky="ew", padx=3, pady=3)
            button = ttk.Button(
                clinic_card,
                text=f"{clinic.get('icon', '🏥')} {clinic.get('name', 'العيادة')}",
                command=lambda clinic_id=clinic["id"]: self.show_page(f"clinic:{clinic_id}"),
            )
            button.pack(fill="x", pady=(0, 3))
            if clinic.get("status") == "مفتوحة" and (
                self.can_add("appts") or (
                    clinic.get("specialty") == "تبرع بالدم" and self.can_add("donations")
                )
            ):
                ttk.Button(
                    clinic_card,
                    text=self.label_text("تسجيل تبرع" if clinic.get("specialty") == "تبرع بالدم" else "حجز"),
                    command=lambda specialty=clinic.get("specialty", ""): self.open_clinic_booking(specialty),
                ).pack(fill="x")
        for column in range(3):
            clinic_shortcuts.columnconfigure(column, weight=1)
        ttk.Label(
            dashboard,
            text=self.label_text("تعتمد المؤشرات على البيانات المدخلة وليست مراقبة سريرية مباشرة"),
            wraplength=1000,
        ).pack(anchor="e", pady=(0, 6))
        ttk.Label(
            dashboard,
            text="أُضيفت سجلات تدريبية اصطناعية: 20 طبيباً و50 ممرضاً و100 مريض. لا تمثل أشخاصاً حقيقيين.",
            foreground="#b45309",
            wraplength=1000,
        ).pack(anchor="e", pady=(0, 4))

    def render_emergency_page(self):
        snapshot = dashboard_snapshot(self.store)
        controls = ttk.Frame(self.body)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(
            controls,
            text="تحديث الحالات",
            command=lambda: self.show_page("emergency", remember=False),
        ).pack(side="right", padx=4)
        ttk.Label(
            self.body,
            text="تعرض هذه الشاشة الحالات المسجلة محلياً فقط؛ لا تتصل بأجهزة مراقبة أو أنظمة طوارئ خارجية.",
            wraplength=1000,
        ).pack(anchor="e", pady=(0, 8))

        critical_panel = ttk.LabelFrame(self.body, text="المرضى بحالة حرجة", padding=8)
        critical_panel.pack(fill="both", expand=True, pady=4)
        critical = ttk.Treeview(
            critical_panel,
            columns=("patient", "status", "phone"),
            show="headings",
            height=6,
        )
        for column, title, width in (
            ("patient", "المريض", 220),
            ("status", "الحالة المسجلة", 150),
            ("phone", "الهاتف", 180),
        ):
            critical.heading(column, text=title)
            critical.column(column, width=width, anchor="center")
        critical.tag_configure("critical", background="#7f1d1d" if self.dark else "#fee2e2", foreground="#fee2e2" if self.dark else "#b91c1c")
        for patient in snapshot["critical_patient_records"]:
            critical.insert(
                "",
                "end",
                iid=str(patient.get("id", "")),
                values=(patient.get("name", ""), patient.get("status", ""), patient.get("phone", "")),
                tags=("critical",),
            )
        critical.pack(fill="both", expand=True)
        ttk.Button(
            critical_panel,
            text="فتح سجل المرضى",
            command=lambda: self.show_page("patients"),
        ).pack(anchor="e", pady=(6, 0))

        urgent_panel = ttk.LabelFrame(self.body, text="المواعيد العاجلة اليوم", padding=8)
        urgent_panel.pack(fill="both", expand=True, pady=4)
        urgent = ttk.Treeview(
            urgent_panel,
            columns=("time", "patient", "doctor", "wait"),
            show="headings",
            height=6,
        )
        for column, title, width in (
            ("time", "الوقت", 100),
            ("patient", "المريض", 220),
            ("doctor", "الطبيب", 220),
            ("wait", "مدة الانتظار", 150),
        ):
            urgent.heading(column, text=title)
            urgent.column(column, width=width, anchor="center")
        urgent.tag_configure("urgent", background="#7f1d1d" if self.dark else "#fee2e2", foreground="#fee2e2" if self.dark else "#b91c1c")
        for appointment in snapshot["urgent_appointments"]:
            wait = appointment_wait_minutes(appointment)
            urgent.insert(
                "",
                "end",
                values=(
                    appointment.get("time", ""),
                    appointment.get("patient", ""),
                    appointment.get("doctor", ""),
                    f"{wait} دقيقة" if wait is not None else "لم يسجل الحضور",
                ),
                tags=("urgent",),
            )
        urgent.pack(fill="both", expand=True)
        ttk.Button(
            urgent_panel,
            text="فتح المواعيد",
            command=lambda: self.show_page("appts"),
        ).pack(anchor="e", pady=(6, 0))

    def focus_search(self, _event=None):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        return "break"

    def add_current(self, _event=None):
        if self.current_page.startswith("clinic:") and self.can_add("appts"):
            clinic = self.store.get("clinics", int(self.current_page.partition(":")[2]))
            if clinic:
                self.open_clinic_booking(clinic.get("specialty", ""))
                return "break"
        if self.current_page in FORM_FIELDS and self.can_add(self.current_page):
            self.open_form(self.current_page)
            return "break"
        return None

    def close_dialog(self, _event=None):
        dialogs = [child for child in self.root.winfo_children() if isinstance(child, tk.Toplevel)]
        if dialogs:
            dialogs[-1].destroy()

    def render_bed_map(self, parent):
        self.bed_canvas = tk.Canvas(parent, height=125, bg=self.panel, highlightthickness=0)
        self.bed_canvas.pack(fill="x", pady=(0, 8))
        self.bed_canvas.bind("<Button-1>", self.click_bed_map)
        self.draw_bed_map()

    def draw_bed_map(self):
        if not hasattr(self, "bed_canvas") or not self.bed_canvas.winfo_exists():
            return
        canvas = self.bed_canvas
        canvas.delete("all")
        beds = self.store.list("beds")
        wards = self.store.list("wards")
        canvas.configure(height=max(125, len(wards) * 46 + 42))
        for ward_index, ward in enumerate(wards):
            canvas.create_text(8, 18 + ward_index * 42, text=ward.get("name", ""), fill=self.fg, anchor="w")
            ward_beds = [bed for bed in beds if bed.get("ward") == ward.get("name")]
            for index, bed in enumerate(ward_beds):
                x, y = 175 + index * 78, 4 + ward_index * 42
                status = bed_status(bed)
                color = {"متاح": "#16a34a", "مشغول": "#ef4444", "قيد التنظيف": "#6b7280"}[status]
                label = str(bed.get("number", bed.get("id")))
                canvas.create_rectangle(x, y, x + 64, y + 32, fill=color, outline="", tags=(f"bed-{bed['id']}",))
                canvas.create_text(x + 32, y + 16, text=f"سرير {label}", fill="white", tags=(f"bed-{bed['id']}",))
        canvas.create_text(8, len(wards) * 42 + 8, text="🟢 متاح    🔴 مشغول    ⚪ قيد التنظيف — اضغط على سرير لإدارته", fill=self.fg, anchor="w")

    def click_bed_map(self, event):
        current = self.bed_canvas.find_withtag("current")
        if not current:
            return
        tags = self.bed_canvas.gettags(current[0])
        bed_tag = next((tag for tag in tags if tag.startswith("bed-")), None)
        if not bed_tag:
            return
        bed = self.store.get("beds", int(bed_tag.split("-", 1)[1]))
        if bed and self.can_add("beds"):
            self.open_form("beds", bed)
        elif bed:
            messagebox.showinfo("حالة السرير", f"{bed_status(bed)} — {bed.get('patient') or 'لا يوجد مريض'}")

    def selected_record(self):
        if not self.tree:
            return None
        selection = self.tree.selection()
        if not selection:
            self.notify("اختر سجلاً أولاً", "info")
            return None
        return self.store.get(PAGES[self.current_page]["entity"], int(selection[0]))

    def check_in_selected_appointment(self):
        appointment = self.selected_record()
        if not appointment:
            return
        if appointment.get("status") in ("مكتمل", "ملغي", "ملغاة", "ملغى"):
            self.notify("لا يمكن تسجيل حضور موعد مكتمل أو ملغى", "error")
            return
        if appointment.get("check_in_at"):
            self.notify("تم تسجيل حضور هذا المريض مسبقاً", "info")
            return
        appointment["check_in_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if appointment.get("status") != "عاجل":
            appointment["status"] = "بالانتظار"
        try:
            self.store.save("appts", appointment, self.user_name, appointment["id"])
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر تسجيل الحضور", str(exc))
            return
        self.notify("تم تسجيل حضور المريض")
        self.refresh_page()

    def start_selected_appointment_consultation(self):
        appointment = self.selected_record()
        if not appointment:
            return
        if appointment.get("status") not in ("بالانتظار", "عاجل"):
            self.notify("يمكن بدء الكشف لموعد بالانتظار أو عاجل فقط", "error")
            return
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        appointment["status"] = "جار الكشف"
        appointment["check_in_at"] = appointment.get("check_in_at") or now
        appointment["consultation_started_at"] = now
        try:
            self.store.save("appts", appointment, self.user_name, appointment["id"])
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر بدء الكشف", str(exc))
            return
        self.notify("تم بدء الكشف")
        self.refresh_page()

    def cancel_selected_appointment(self):
        appointment = self.selected_record()
        if not appointment:
            return
        if appointment.get("status") == "مكتمل":
            self.notify("لا يمكن إلغاء موعد مكتمل", "error")
            return
        appointment["status"] = "ملغي"
        try:
            self.store.save("appts", appointment, self.user_name, appointment["id"])
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر إلغاء الموعد", str(exc))
            return
        self.notify("تم إلغاء الموعد")
        self.refresh_page()

    def print_appointment_patient_card(self):
        appointment = self.selected_record()
        if not appointment:
            return
        patient = next(
            (item for item in self.store.list("patients") if item.get("name") == appointment.get("patient")),
            None,
        )
        if not patient:
            self.notify("ملف المريض المرتبط بالموعد غير موجود", "error")
            return
        content = (
            f"<h1>{html.escape(self.hospital_name)}</h1><h2>بطاقة موعد المريض</h2>"
            f"<p>رقم الملف: {patient.get('id')}</p>"
            f"<p>اسم المريض: {html.escape(str(patient.get('name', '')))}</p>"
            f"<p>الطبيب: {html.escape(str(appointment.get('doctor', '')))}</p>"
            f"<p>الموعد: {html.escape(str(appointment.get('date', '')))} — "
            f"{html.escape(str(appointment.get('time', '')))}</p>"
        )
        self.open_print_document("بطاقة موعد المريض", content)

    def open_selected_clinic(self):
        clinic = self.selected_record()
        if not clinic:
            return
        clinic_key = f"clinic:{clinic['id']}"
        if not self.can_view(clinic_key):
            self.notify(self.label_text("لا تملك صلاحية فتح هذه العيادة"), "error")
            return
        self.show_page(clinic_key)

    def edit_selected(self):
        record = self.selected_record()
        if not record:
            return
        if self.current_page == "messages":
            self.notify("رسائل المحادثة للقراءة فقط", "info")
            return
        if self.current_page in FORM_FIELDS and (self.role == "admin" or self.can_add(self.current_page)):
            self.open_form(self.current_page, record)
        elif self.current_page == "patients":
            self.open_profile(record)
        elif self.current_page == "bills":
            self.print_invoice(record)
        elif self.current_page == "prescriptions":
            self.print_prescription(record)

    def delete_selected(self):
        if self.role != "admin":
            self.notify("الحذف متاح للمدير فقط", "error")
            return
        record = self.selected_record()
        if not record:
            return
        entity = self.current_page
        if entity == "patients":
            name = record.get("name")
            linked = any(
                any(item.get("patient") == name for item in self.store.list(other))
                for other in ("appts", "labs", "bills", "prescriptions", "vitals", "beds", "payments", "insurance", "reminders", "ratings", "attachments", "surgeries")
            )
            if linked:
                messagebox.showerror("تعذر الحذف", "لا يمكن حذف مريض مرتبط بسجلات أخرى")
                return
        if entity == "clinics" and (
            any(doctor.get("spec") == record.get("specialty") for doctor in self.store.list("doctors"))
            or (record.get("specialty") == "تبرع بالدم" and self.store.list("donations"))
        ):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف عيادة مرتبطة بأطباء أو بسجلات تبرع")
            return
        extra_updates = []
        if entity == "payments" and record.get("bill_id"):
            bill = self.store.get("bills", record["bill_id"])
            if bill:
                bill["balance"] = float(bill.get("balance", 0)) + float(record.get("amount", 0))
                bill["status"] = "مدفوعة" if bill["balance"] <= 0 else "غير مدفوعة"
                extra_updates.append(("bills", bill))
        if entity == "bills" and any(str(payment.get("bill_id", "")) == str(record["id"]) for payment in self.store.list("payments")):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف فاتورة مرتبطة بمدفوعات مسجلة")
            return
        if entity == "beds" and record.get("patient"):
            messagebox.showerror("تعذر الحذف", "أفرغ السرير قبل حذفه")
            return
        if entity == "wards" and any(bed.get("ward") == record.get("name") for bed in self.store.list("beds")):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف جناح مرتبط بأسرّة")
            return
        if entity == "operation_rooms" and any(surgery.get("room") == record.get("name") for surgery in self.store.list("surgeries")):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف غرفة مرتبطة بجدول عمليات")
            return
        if entity == "doctors" and any(
            item.get("doctor") == record.get("name")
            for collection in ("appts", "prescriptions", "ratings", "surgeries")
            for item in self.store.list(collection)
        ):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف طبيب مرتبط بسجلات")
            return
        if entity == "meds" and any(item.get("medicine") == record.get("name") for item in self.store.list("prescriptions")):
            messagebox.showerror("تعذر الحذف", "لا يمكن حذف دواء مرتبط بوصفات")
            return
        if not messagebox.askyesno("تأكيد الحذف", "هل تريد حذف السجل المحدد؟"):
            return
        try:
            self.store.delete(entity, record["id"], self.user_name, extra_updates)
            self.notify("تم حذف السجل")
            if entity == "clinics":
                self.rebuild()
            else:
                self.refresh_page()
        except sqlite3.Error as exc:
            messagebox.showerror("خطأ في قاعدة البيانات", str(exc))

    def open_form(self, page, record=None):
        if not self.can_add(page) and record is None:
            self.notify("لا تملك صلاحية الإضافة", "error")
            return
        entity = PAGES[page]["entity"]
        dialog = tk.Toplevel(self.root)
        self.dialog = dialog
        dialog.title(("تعديل " if record else "إضافة ") + PAGES[page]["title"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg)
        canvas = tk.Canvas(dialog, background=self.bg, highlightthickness=0, width=520, height=500)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        form = ttk.Frame(canvas, padding=18)
        window_id = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        widgets = {}
        initial = self.to_form_values(entity, record or {})
        for row_index, (key, spec) in enumerate(FORM_FIELDS[page]):
            spec_default = ""
            ttk.Label(form, text=str(self.label_text(spec["label"]))).grid(row=row_index, column=1, sticky="e", padx=6, pady=5)
            kind = spec["kind"]
            if kind == "multiline":
                widget = tk.Text(form, height=4, width=42, wrap="word", bg=self.panel, fg=self.fg, insertbackground=self.fg)
                widget.insert("1.0", str(initial.get(key, "")))
            elif kind in ("choice", "patient", "patient_optional", "doctor", "medicine", "ward", "clinic_specialty", "operation_room"):
                options = spec["options"]
                if kind == "choice":
                    options = [self.label_text(option) for option in options]
                elif kind == "clinic_specialty":
                    options = [item.get("specialty", "") for item in self.store.list("clinics")]
                    if self.clinic_booking_specialty:
                        options = [item for item in options if item == self.clinic_booking_specialty]
                    if not record and not self.clinic_booking_specialty and options:
                        spec_default = options[0]
                    else:
                        spec_default = ""
                if kind.startswith("patient"):
                    options = [item["name"] for item in self.store.list("patients")]
                    if kind == "patient_optional":
                        options = [""] + options
                elif kind == "doctor":
                    options = [
                        item["name"] for item in self.store.list("doctors")
                        if item.get("status") == "نشط"
                        and (not self.clinic_booking_specialty or item.get("spec") == self.clinic_booking_specialty)
                    ]
                    if record and record.get("doctor") and record["doctor"] not in options:
                        options.append(record["doctor"])
                elif kind == "medicine":
                    options = [item["name"] for item in self.store.list("meds")]
                elif kind == "ward":
                    options = [item["name"] for item in self.store.list("wards")]
                elif kind == "operation_room":
                    options = [item["name"] for item in self.store.list("operation_rooms") if item.get("status") == "متاحة"]
                    if record and record.get("room") not in options:
                        options.append(record.get("room", ""))
                options = [str(option) for option in options]
                widget = ttk.Combobox(form, values=options, width=39, state="normal")
                initial_value = initial.get(key, spec["default"])
                if key == "spec" and not initial_value:
                    initial_value = spec_default
                if key == "spec" and self.clinic_booking_specialty and not initial_value:
                    initial_value = self.clinic_booking_specialty
                if key == "doctor" and self.clinic_booking_specialty and options and not initial_value:
                    initial_value = options[0]
                widget.set(self.label_text(str(initial_value)) if kind == "choice" else str(initial_value))
            else:
                widget = ttk.Entry(form, width=42)
                widget.insert(0, str(initial.get(key, spec["default"])))
                if kind == "file":
                    browse = ttk.Button(form, text="استعراض", command=lambda target=widget: self.choose_file(target))
                    browse.grid(row=row_index, column=2, padx=3)
            widget.grid(row=row_index, column=0, sticky="ew", padx=6, pady=5)
            widgets[key] = widget
        buttons = ttk.Frame(form)
        buttons.grid(row=len(FORM_FIELDS[page]), column=0, columnspan=3, sticky="ew", pady=12)
        ttk.Button(buttons, text=self.label_text("حفظ"), command=lambda: self.save_form(page, widgets, dialog, record)).pack(side="right", padx=4)
        ttk.Button(buttons, text=self.label_text("إلغاء"), command=dialog.destroy).pack(side="right", padx=4)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.geometry("660x600")

    def to_form_values(self, entity, record):
        result = dict(record)
        if entity == "patients":
            result["allergies"] = ", ".join(record.get("allergies", [])) if isinstance(record.get("allergies"), list) else record.get("allergies", "")
            result["chronicConditions"] = ", ".join(record.get("chronicConditions", [])) if isinstance(record.get("chronicConditions"), list) else record.get("chronicConditions", "")
        if entity == "bills":
            result["items_text"] = "\n".join(f"{i.get('description', '')} | {i.get('quantity', 1)} | {i.get('unitPrice', 0)}" for i in record.get("items", []))
        if entity == "beds" and record.get("status") == "متاح":
            result["patient"] = ""
        if entity == "attachments":
            result["path"] = record.get("path", "")
        return result

    def choose_file(self, widget):
        path = filedialog.askopenfilename()
        if path:
            widget.delete(0, "end")
            widget.insert(0, path)

    @staticmethod
    def read_widget(widget, kind):
        return widget.get("1.0", "end-1c").strip() if kind == "multiline" else widget.get().strip()

    def save_form(self, page, widgets, dialog, existing=None):
        entity = PAGES[page]["entity"]
        values = {}
        for key, spec in FORM_FIELDS[page]:
            raw = self.read_widget(widgets[key], spec["kind"])
            if spec["kind"] == "choice" and self.language == "en":
                raw = next((option for option in spec["options"] if self.label_text(option) == raw), raw)
            values[key] = raw
        try:
            record = self.prepare_record(entity, values, existing)
            extra = []
            if entity == "prescriptions":
                record, extra = self.prepare_prescription(record, existing)
            elif entity == "payments":
                record, extra = self.prepare_payment(record, existing)
            self.store.save(entity, record, self.user_name, existing.get("id") if existing else None, extra)
        except (ValueError, sqlite3.Error, OSError) as exc:
            messagebox.showerror("تعذر الحفظ", str(exc), parent=dialog)
            return
        dialog.destroy()
        self.notify("تم حفظ السجل بنجاح")
        if entity == "clinics":
            self.rebuild()
        elif self.current_page.startswith("clinic:"):
            self.show_page(self.current_page)
        else:
            self.refresh_page()
            if self.current_page == "dashboard":
                self.show_page("dashboard")

    def prepare_record(self, entity, values, existing=None):
        record = dict(existing or {})
        for key, value in values.items():
            if key == "items_text":
                continue
            if key in ("age", "qty", "min_qty", "price", "capacity", "amount", "coverage", "base", "deductions", "advance", "score", "bloodSugar", "temperature", "pulse", "quantity", "bill_id", "copies", "fee", "quantity_ml", "duration_minutes", "approved_amount", "rejected_amount", "cash_price", "insurance_price", "corporate_price", "discount_percent", "maintenance_cost"):
                if value == "" and key in ("bill_id", "quantity_ml"):
                    record[key] = ""
                    continue
                try:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ValueError(f"{key} يجب أن يكون رقماً منتهياً")
                    if key in ("age", "qty", "min_qty", "capacity", "quantity", "score", "bill_id", "copies", "quantity_ml", "duration_minutes"):
                        if not number.is_integer():
                            raise ValueError(f"{key} يجب أن يكون عدداً صحيحاً")
                        number = int(number)
                    if number < 0:
                        raise ValueError(f"{key} لا يمكن أن يكون سالباً")
                    record[key] = number
                except ValueError as exc:
                    label = next((spec["label"] for field_key, spec in FORM_FIELDS[entity] if field_key == key), key)
                    raise ValueError(f"قيمة غير صالحة للحقل: {label}") from exc
            elif key in ("allergies", "chronicConditions"):
                record[key] = [item.strip() for item in value.split(",") if item.strip()]
            elif key in ("date", "expiry_month", "maintenance_due", "sterilized_at", "expires_at") and value and not self.valid_date(value, entity, key):
                raise ValueError("صيغة التاريخ غير صالحة")
            else:
                record[key] = value
        if entity == "patients" and not record.get("name"):
            raise ValueError("اسم المريض مطلوب")
        if entity == "meds":
            quantity = float(record.get("qty", 0))
            minimum = float(record.get("min_qty", 10))
            record["status"] = "نفد" if quantity <= 0 else "منخفض" if quantity <= minimum else "متوفر"
        if entity == "beds":
            patient = str(record.get("patient", "")).strip()
            status = str(record.get("status", "متاح")).strip()
            if patient and status == "قيد التنظيف":
                raise ValueError("أفرغ السرير قبل وضعه قيد التنظيف")
            if patient:
                record["status"] = "مشغول"
            elif status == "مشغول":
                raise ValueError("اختر مريضاً للسرير المشغول أو غيّر حالته")
            else:
                record["status"] = status if status == "قيد التنظيف" else "متاح"
        if entity == "support_tickets":
            for key, label in (("title", "عنوان العطل"), ("description", "وصف العطل وموقعه")):
                if not str(record.get(key, "")).strip():
                    raise ValueError(f"{label} مطلوب")
            if not existing:
                record["reported_by"] = self.user_name
                record["created_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if entity == "attendance" and not str(record.get("employee", "")).strip():
            raise ValueError("اسم الموظف مطلوب")
        if entity == "messages":
            if not str(record.get("message", "")).strip():
                raise ValueError("نص الرسالة مطلوب")
            record["sender"] = self.user_name
            record["sent_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if entity == "appts" and not existing and self.store.setting("emergency_mode") == "1" and record.get("priority") != "طارئة":
            raise ValueError("وضع الطوارئ مفعّل؛ لا يمكن تسجيل موعد عادي")
        if entity == "clinics":
            for key, label in (("name", "اسم العيادة"), ("specialty", "التخصص")):
                if not str(record.get(key, "")).strip():
                    raise ValueError(f"{label} مطلوب")
            for clinic in self.store.list("clinics"):
                if clinic.get("id") == (existing or {}).get("id"):
                    continue
                if clinic.get("name") == record.get("name"):
                    raise ValueError("اسم العيادة مستخدم بالفعل")
                if clinic.get("specialty") == record.get("specialty"):
                    raise ValueError("يوجد تخصص عيادة بهذا الاسم بالفعل")
            if existing and record.get("specialty") != existing.get("specialty") and any(
                doctor.get("spec") == existing.get("specialty") for doctor in self.store.list("doctors")
            ):
                raise ValueError("لا يمكن تغيير تخصص عيادة مرتبطة بأطباء؛ أضف عيادة جديدة أولاً")
            if existing and record.get("specialty") != existing.get("specialty") and (
                existing.get("specialty") == "تبرع بالدم" and self.store.list("donations")
            ):
                raise ValueError("لا يمكن تغيير تخصص عيادة مرتبطة بسجلات تبرع")
        if entity == "doctors":
            if not str(record.get("name", "")).strip():
                raise ValueError("اسم الطبيب مطلوب")
            specialties = {clinic.get("specialty") for clinic in self.store.list("clinics")}
            if record.get("spec") not in specialties:
                raise ValueError("اختر تخصصاً من دليل العيادات")
            record["phone"] = str(record.get("phone", "")).strip()
            if record.get("sample_data"):
                record["verification"] = "يلزم استبدال الاسم الافتراضي والتحقق من الترخيص"
            else:
                record["verification"] = "أُدخلت يدوياً؛ الاعتماد الرسمي يحتاج تحققاً خارج النظام"
        if entity == "death_certificate_requests":
            required = ("deceased_name", "applicant", "purpose", "kinship", "phone")
            missing = [key for key in required if not str(record.get(key, "")).strip()]
            if missing:
                labels = {key: next(spec["label"] for field_key, spec in FORM_FIELDS[entity] if field_key == key) for key in missing}
                raise ValueError("يرجى تعبئة الحقول المطلوبة: " + "، ".join(labels.values()))
            try:
                datetime.strptime(record.get("death_date", ""), "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("تاريخ الوفاة يجب أن يكون بصيغة YYYY-MM-DD") from exc
            record["status"] = "قيد المراجعة"
            record["date"] = date.today().isoformat()
        if entity == "donations":
            required = ("donor_name", "identity_number", "blood_type", "date", "donation_type", "center")
            missing = [key for key in required if not str(record.get(key, "")).strip()]
            if missing:
                labels = {
                    key: next(spec["label"] for field_key, spec in FORM_FIELDS[entity] if field_key == key)
                    for key in missing
                }
                raise ValueError("يرجى تعبئة الحقول المطلوبة: " + "، ".join(labels.values()))
            if not self.valid_date(record.get("date", ""), entity):
                raise ValueError("تاريخ التبرع يجب أن يكون بصيغة YYYY-MM-DD")
        if entity == "operation_rooms":
            if not str(record.get("name", "")).strip():
                raise ValueError("اسم غرفة العمليات مطلوب")
            if any(
                room.get("id") != (existing or {}).get("id")
                and room.get("name", "").casefold() == record["name"].strip().casefold()
                for room in self.store.list("operation_rooms")
            ):
                raise ValueError("اسم غرفة العمليات مستخدم بالفعل")
            record["name"] = record["name"].strip()
            if existing and record["name"] != existing.get("name") and any(
                surgery.get("room") == existing.get("name") for surgery in self.store.list("surgeries")
            ):
                raise ValueError("لا يمكن تغيير اسم غرفة مرتبطة بجدول عمليات")
            if record.get("status") == "خارج الخدمة" and any(
                surgery.get("room") == record["name"] and surgery.get("status") in ("مجدولة", "جارية")
                for surgery in self.store.list("surgeries")
            ):
                raise ValueError("لا يمكن إخراج غرفة من الخدمة أثناء وجود عمليات مجدولة أو جارية")
        if entity in ("appts", "reminders", "surgeries"):
            try:
                datetime.strptime(record.get("time", ""), "%H:%M")
            except ValueError as exc:
                raise ValueError("صيغة الوقت يجب أن تكون HH:MM") from exc
        valid_patients = {item.get("name") for item in self.store.list("patients")}
        valid_doctors = {item.get("name") for item in self.store.list("doctors")}
        if entity in {"appts", "labs", "prescriptions", "vitals", "insurance", "insurance_claims", "payments", "ratings", "reminders", "attachments", "surgeries"} and record.get("patient") not in valid_patients:
            raise ValueError("اختر مريضاً مسجلاً في النظام")
        if entity in {"appts", "prescriptions", "ratings", "surgeries"} and record.get("doctor") not in valid_doctors:
            raise ValueError("اختر طبيباً مسجلاً في النظام")
        if entity in {"appts", "prescriptions", "ratings", "surgeries"}:
            doctor = next((item for item in self.store.list("doctors") if item.get("name") == record.get("doctor")), None)
            if not doctor or doctor.get("status") != "نشط":
                raise ValueError("لا يمكن ربط سجل بطبيب قبل التحقق منه وتغيير حالته إلى نشط")
            if entity == "appts":
                clinic = next((item for item in self.store.list("clinics") if item.get("specialty") == doctor.get("spec")), None)
                emergency_booking = (
                    self.store.setting("emergency_mode") == "1"
                    and record.get("priority") == "طارئة"
                )
                if clinic and clinic.get("status") != "مفتوحة" and not emergency_booking:
                    raise ValueError("العيادة مغلقة مؤقتاً ولا تقبل مواعيد جديدة")
        if entity == "surgeries":
            if not str(record.get("procedure", "")).strip():
                raise ValueError("وصف العملية مطلوب")
            if not self.valid_date(record.get("date", ""), entity):
                raise ValueError("تاريخ العملية يجب أن يكون بصيغة YYYY-MM-DD")
            if not 0 < record.get("duration_minutes", 0) <= 24 * 60:
                raise ValueError("مدة العملية يجب أن تكون بين دقيقة واحدة و24 ساعة")
            room = next((item for item in self.store.list("operation_rooms") if item.get("name") == record.get("room")), None)
            if not room or room.get("status") != "متاحة":
                raise ValueError("اختر غرفة عمليات متاحة")
            start = datetime.combine(
                datetime.strptime(record["date"], "%Y-%m-%d").date(),
                datetime.strptime(record["time"], "%H:%M").time(),
            )
            end = start + timedelta(minutes=int(record["duration_minutes"]))
            for other in self.store.list("surgeries"):
                if other.get("id") == (existing or {}).get("id") or other.get("status") in ("ملغاة", "مكتملة"):
                    continue
                other_start = datetime.combine(
                    datetime.strptime(other.get("date", ""), "%Y-%m-%d").date(),
                    datetime.strptime(other.get("time", ""), "%H:%M").time(),
                )
                other_end = other_start + timedelta(minutes=int(other.get("duration_minutes", 0)))
                if start < other_end and other_start < end and (
                    other.get("room") == record.get("room") or other.get("doctor") == record.get("doctor")
                ):
                    raise ValueError("يوجد تعارض زمني للطبيب أو غرفة العمليات المختارة")
            if not existing:
                for key, label in (("team", "فريق العمل"), ("equipment", "تجهيزات الغرفة")):
                    if not str(record.get(key, "")).strip():
                        raise ValueError(f"{label} مطلوب")
        if entity == "medication_batches":
            medicines = {item.get("name") for item in self.store.list("meds")}
            if record.get("medicine") not in medicines or not str(record.get("batch_number", "")).strip():
                raise ValueError("اختر دواءً مسجلاً وأدخل رقم الدفعة")
            if record.get("quantity", 0) <= 0:
                raise ValueError("كمية الدفعة يجب أن تكون أكبر من صفر")
            if months_until_expiry(record.get("expiry_month", "")) is None:
                raise ValueError("انتهاء الصلاحية يجب أن يكون بصيغة YYYY-MM")
            duplicate = any(
                item.get("medicine") == record.get("medicine")
                and item.get("batch_number") == record.get("batch_number")
                and item.get("id") != (existing or {}).get("id")
                for item in self.store.list("medication_batches")
            )
            if duplicate:
                raise ValueError("رقم الدفعة مسجل لهذا الدواء بالفعل")
        if entity == "insurance_claims":
            bill = self.store.get("bills", record.get("bill_id"))
            if not bill or bill.get("patient") != record.get("patient"):
                raise ValueError("اختر فاتورة موجودة مرتبطة بالمريض نفسه")
            if not str(record.get("company", "")).strip():
                raise ValueError("اسم شركة التأمين مطلوب")
            if record.get("amount", 0) <= 0:
                raise ValueError("مبلغ المطالبة يجب أن يكون أكبر من صفر")
            if float(record["amount"]) > float(bill.get("amount", 0)):
                raise ValueError("مبلغ المطالبة يتجاوز إجمالي الفاتورة")
            approved = float(record.get("approved_amount", 0))
            rejected = float(record.get("rejected_amount", 0))
            if approved + rejected > float(record["amount"]):
                raise ValueError("المبلغ المعتمد والمرفوض يتجاوز مبلغ المطالبة")
            record["submitted_at"] = (existing or {}).get("submitted_at", datetime.now().astimezone().isoformat(timespec="seconds"))
            if approved and rejected:
                record["status"] = "موافقة جزئية"
            elif approved >= float(record["amount"]):
                record["status"] = "موافق عليها"
            elif rejected >= float(record["amount"]):
                record["status"] = "مرفوضة"
            elif approved > 0:
                record["status"] = "موافقة جزئية"
            else:
                record["status"] = "مقدمة"
        if entity == "assets":
            if not str(record.get("name", "")).strip():
                raise ValueError("اسم الأصل مطلوب")
            if not self.valid_date(record.get("maintenance_due", ""), entity, "maintenance_due"):
                raise ValueError("موعد الصيانة يجب أن يكون بصيغة YYYY-MM-DD")
        if entity == "sterilization_cycles":
            for key, label in (("instrument_set", "مجموعة الأدوات"), ("operator", "المعقّم")):
                if not str(record.get(key, "")).strip():
                    raise ValueError(f"{label} مطلوب")
            try:
                sterilized = datetime.strptime(record.get("sterilized_at", ""), "%Y-%m-%d").date()
                expires = datetime.strptime(record.get("expires_at", ""), "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValueError("تاريخا التعقيم والانتهاء يجب أن يكونا بصيغة YYYY-MM-DD") from exc
            if expires < sterilized:
                raise ValueError("انتهاء صلاحية التعقيم يجب أن يكون بعد تاريخ التعقيم")
        if entity == "service_prices":
            if not str(record.get("service", "")).strip():
                raise ValueError("اسم الخدمة مطلوب")
            if not 0 <= float(record.get("discount_percent", 0)) <= 100:
                raise ValueError("الخصم يجب أن يكون بين 0 و100")
            if any(
                item.get("service", "").casefold() == record["service"].strip().casefold()
                and item.get("id") != (existing or {}).get("id")
                for item in self.store.list("service_prices")
            ):
                raise ValueError("اسم الخدمة مسجل بالفعل في قائمة الأسعار")
        if entity == "beds":
            if record.get("patient") and record.get("patient") not in valid_patients:
                raise ValueError("اختر مريضاً مسجلاً في النظام")
        if entity == "meds":
            record["status"] = "نفد" if record.get("qty", 0) <= 0 else "منخفض" if record.get("qty", 0) < 10 else "متوفر"
        if entity == "payroll":
            if record.get("deductions", 0) + record.get("advance", 0) > record.get("base", 0):
                raise ValueError("الخصومات والسلف لا يمكن أن تتجاوز الراتب الأساسي")
            record["net"] = record.get("base", 0) - record.get("deductions", 0) - record.get("advance", 0)
        if entity == "insurance" and not 0 <= record.get("coverage", 0) <= 100:
            raise ValueError("نسبة التغطية يجب أن تكون بين 0 و100")
        if entity == "ratings" and not 1 <= record.get("score", 0) <= 5:
            raise ValueError("التقييم يجب أن يكون بين 1 و5")
        if entity == "wards":
            occupied = sum(1 for bed in self.store.list("beds") if bed.get("ward") == record.get("name") and bed.get("patient"))
            if record.get("capacity", 0) < occupied:
                raise ValueError(f"لا يمكن تقليل السعة إلى أقل من الأسرّة المشغولة ({occupied})")
        if entity == "beds" and record.get("ward") not in {ward.get("name") for ward in self.store.list("wards")}:
            raise ValueError("اختر جناحاً مسجلاً في النظام")
        if entity == "bills":
            lines = [line.strip() for line in values.get("items_text", "").splitlines() if line.strip()]
            items = []
            for line in lines:
                parts = [part.strip() for part in line.split("|")]
                if len(parts) == 2:
                    try:
                        quantity = float(parts[1])
                    except ValueError as exc:
                        raise ValueError("كمية الخدمة يجب أن تكون رقماً") from exc
                    price_key = {
                        "نقدي": "cash_price",
                        "تأمين": "insurance_price",
                        "تعاقد شركات": "corporate_price",
                    }.get(str(record.get("billing_type", "نقدي")), "cash_price")
                    service = next(
                        (item for item in self.store.list("service_prices") if item.get("service", "").casefold() == parts[0].casefold()),
                        None,
                    )
                    if not service:
                        raise ValueError(f"الخدمة «{parts[0]}» غير موجودة في قائمة الأسعار")
                    unit_price = float(service.get(price_key, 0))
                    unit_price *= 1 - float(service.get("discount_percent", 0)) / 100
                    parts = [parts[0], str(quantity), str(unit_price)]
                if len(parts) != 3:
                    raise ValueError("استخدم خدمة | كمية للأسعار المسجلة، أو وصف | كمية | سعر الوحدة")
                try:
                    quantity, unit_price = float(parts[1]), float(parts[2])
                except ValueError as exc:
                    raise ValueError("الكمية والسعر يجب أن يكونا رقمين") from exc
                if not parts[0] or not math.isfinite(quantity) or not math.isfinite(unit_price) or quantity <= 0 or unit_price < 0:
                    raise ValueError("كمية البند يجب أن تكون موجبة والسعر غير سالب")
                items.append({"description": parts[0], "quantity": quantity, "unitPrice": unit_price})
            if not items:
                raise ValueError("أضف بنداً واحداً على الأقل إلى الفاتورة")
            total = sum(item["quantity"] * item["unitPrice"] for item in items)
            policy = next((p for p in self.store.list("insurance") if p.get("patient") == record.get("patient")), None)
            coverage = float(policy.get("coverage", 0)) if policy else 0
            covered = round(total * coverage / 100)
            record.update({"items": items, "amount": total, "insuranceCoverage": coverage, "insuranceCovered": covered,
                           "balance": 0 if record.get("status") == "مدفوعة" else max(0, total - covered)})
        if entity == "attachments":
            path = Path(record.get("path", ""))
            if not path.is_file():
                raise ValueError("اختر ملفاً صالحاً")
            if path.stat().st_size > MAX_ATTACHMENT_BYTES:
                raise ValueError("حجم الملف يتجاوز الحد الأقصى 10MB")
            folder = APP_DIR / "attachments"
            folder.mkdir(parents=True, exist_ok=True)
            descriptor, local_path = tempfile.mkstemp(prefix="attachment_", suffix=path.suffix, dir=folder)
            os.close(descriptor)
            shutil.copy2(path, local_path)
            record.update({"path": local_path, "name": path.name, "type": path.suffix.lower().lstrip(".") or "ملف", "date": date.today().isoformat()})
        if entity == "reminders":
            record.setdefault("status", "مجدول")
        if entity == "vitals":
            record.setdefault("date", date.today().isoformat())
        if entity == "beds":
            occupied = next((bed for bed in self.store.list("beds") if bed.get("patient") == record.get("patient") and bed.get("id") != (existing or {}).get("id") and record.get("patient")), None)
            if occupied:
                raise ValueError("المريض لديه سرير مشغول بالفعل")
        return record

    @staticmethod
    def valid_date(value, page, key="date"):
        try:
            pattern = "%Y-%m" if page == "payroll" or key == "expiry_month" else "%Y-%m-%d"
            datetime.strptime(value, pattern)
            return True
        except ValueError:
            return False

    def prepare_prescription(self, record, existing):
        patient = next((p for p in self.store.list("patients") if p.get("name") == record.get("patient")), None)
        medicine = next((m for m in self.store.list("meds") if m.get("name") == record.get("medicine")), None)
        if not patient or not medicine:
            raise ValueError("اختر مريضاً ودواءً موجودين")
        quantity = int(record.get("quantity", 0))
        old_quantity = int(existing.get("quantity", 0)) if existing else 0
        old_medicine = next((m for m in self.store.list("meds") if existing and m.get("name") == existing.get("medicine")), None)
        changed_medicine = bool(existing and existing.get("medicine") != record.get("medicine"))
        required = quantity if changed_medicine else quantity - old_quantity
        if required > int(medicine.get("qty", 0)):
            raise ValueError(f"المخزون غير كافٍ؛ المتاح {medicine.get('qty', 0)}")
        warnings = []
        medication = str(record["medicine"]).casefold()
        allergies = [str(x).casefold() for x in patient.get("allergies", [])]
        allergy_groups = (("penicillin", "amoxicillin", "أموكسيسيلين", "بنسلين"), ("aspirin", "أسبرين"), ("sulfa", "سلفا"))
        allergy = any(token in medication or medication in token for token in allergies)
        allergy = allergy or any(any(token.casefold() in medication for token in group) and any(any(token.casefold() in item for token in group) for item in allergies) for group in allergy_groups)
        if allergy:
            warnings.append("توجد حساسية مسجلة مرتبطة بالدواء")
        interactions = (("warfarin", "aspirin"), ("وارفارين", "أسبرين"), ("simvastatin", "clarithromycin"), ("سيمفاستاتين", "كلاريثروميسين"))
        active = [p for p in self.store.list("prescriptions") if p.get("patient") == record.get("patient") and p.get("status") == "تم الصرف" and (not existing or p.get("id") != existing.get("id"))]
        for prior in active:
            prior_name = str(prior.get("medicine", "")).casefold()
            if any(all(term.casefold() in (prior_name + " " + medication) for term in pair) for pair in interactions):
                warnings.append(f"احتمال تفاعل دوائي مع {prior.get('medicine')}")
        if warnings and not messagebox.askyesno("تحذير سريري", "\n".join(warnings) + "\n\nهذه تنبيهات أولية وليست مرجعاً طبياً. هل تريد المتابعة؟"):
            raise ValueError("تم إلغاء الوصفة بعد التحذير")
        record.setdefault("date", date.today().isoformat())
        record["status"] = "تم الصرف"
        medicine["qty"] = int(medicine.get("qty", 0)) - required
        medicine["status"] = "نفد" if medicine["qty"] <= 0 else "منخفض" if medicine["qty"] < 10 else "متوفر"
        updates = [("meds", medicine)]
        if changed_medicine and old_medicine:
            old_medicine["qty"] = int(old_medicine.get("qty", 0)) + old_quantity
            old_medicine["status"] = "نفد" if old_medicine["qty"] <= 0 else "منخفض" if old_medicine["qty"] < 10 else "متوفر"
            updates.append(("meds", old_medicine))
        return record, updates

    def create_appointment_reminder(self):
        appointment = self.selected_record()
        if not appointment:
            return
        reminder = {
            "id": self.store.next_id("reminders"),
            "patient": appointment.get("patient", ""),
            "date": appointment.get("date", date.today().isoformat()),
            "time": appointment.get("time", "09:00"),
            "message": f"تذكير بموعدك مع {appointment.get('doctor', '')}",
            "status": "مجدول",
        }
        try:
            self.store.save("reminders", reminder, self.user_name)
            self.notify("تم إنشاء تذكير للموعد")
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر إنشاء التذكير", str(exc))

    def send_whatsapp_reminder(self):
        reminder = self.selected_record()
        if not reminder:
            return
        patient = next((item for item in self.store.list("patients") if item.get("name") == reminder.get("patient")), None)
        phone = re.sub(r"\D", "", str(patient.get("phone", ""))) if patient else ""
        if not phone:
            messagebox.showerror("رقم الهاتف غير متاح", "أضف رقم هاتف صالحاً للمريض أولاً")
            return
        if not messagebox.askyesno("فتح WhatsApp", "سيتم فتح رابط WhatsApp في المتصفح. لن تُرسل رسالة تلقائياً. متابعة؟"):
            return
        message = f"تذكير من {self.hospital_name}: {reminder.get('message')} — {reminder.get('date')} {reminder.get('time')}"
        webbrowser.open(f"https://wa.me/{phone}?text={quote(message)}")
        self.audit("فتح رسالة تذكير WhatsApp")

    def prepare_payment(self, record, existing=None):
        adjustments = {}
        if existing and existing.get("bill_id"):
            old_bill = self.store.get("bills", existing["bill_id"])
            if not old_bill:
                raise ValueError("فاتورة الدفعة الأصلية غير موجودة؛ لا يمكن تعديل هذه الدفعة")
            old_bill["balance"] = float(old_bill.get("balance", 0)) + float(existing.get("amount", 0))
            old_bill["status"] = "مدفوعة" if old_bill["balance"] <= 0 else "غير مدفوعة"
            adjustments[old_bill["id"]] = old_bill
        bill_id = str(record.get("bill_id", "")).strip()
        if not bill_id:
            return record, [("bills", bill) for bill in adjustments.values()]
        if not bill_id.isdigit():
            raise ValueError("رقم الفاتورة يجب أن يكون رقماً")
        bill = adjustments.get(int(bill_id)) or self.store.get("bills", int(bill_id))
        if not bill or bill.get("patient") != record.get("patient"):
            raise ValueError("الفاتورة غير موجودة أو لا تخص هذا المريض")
        amount = float(record.get("amount", 0))
        balance = float(bill.get("balance", 0))
        if amount <= 0 or amount > balance:
            raise ValueError(f"مبلغ الدفعة يجب أن يكون أكبر من صفر ولا يتجاوز المتبقي ({balance:g})")
        bill["balance"] = balance - amount
        bill["status"] = "مدفوعة" if bill["balance"] <= 0 else "غير مدفوعة"
        adjustments[bill["id"]] = bill
        return record, [("bills", item) for item in adjustments.values()]

    def audit(self, action):
        try:
            self.store.connection.execute("BEGIN IMMEDIATE")
            self.store._audit(self.user_name or "النظام", action)
            self.store.connection.commit()
            if self.current_page == "activity":
                self.refresh_page()
        except sqlite3.Error as exc:
            self.store.connection.rollback()
            self.notify(f"تعذر تسجيل النشاط: {exc}", "error")

    def notify(self, message, kind="success"):
        if not self.status_label or not self.status_label.winfo_exists():
            return
        colors = {"success": "#15803d", "error": "#dc2626", "info": "#2563eb"}
        color = colors.get(kind, colors["info"])
        self.status_label.configure(text=message, foreground=color)
        if self.toast_after_id is not None:
            self.root.after_cancel(self.toast_after_id)
            self.toast_after_id = None
        if self.toast_window is not None and self.toast_window.winfo_exists():
            self.toast_window.destroy()

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.transient(self.root)
        toast.configure(background=color)
        label = tk.Label(
            toast,
            text=message,
            background=color,
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=12,
            wraplength=420,
            justify="right",
        )
        label.pack()
        toast.update_idletasks()
        width, height = toast.winfo_reqwidth(), toast.winfo_reqheight()
        x = self.root.winfo_rootx() + self.root.winfo_width() - width - 20
        y = self.root.winfo_rooty() + self.root.winfo_height() - height - 48
        toast.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.toast_window = toast

        def dismiss():
            self.toast_after_id = None
            if toast.winfo_exists():
                toast.destroy()
            if self.toast_window is toast:
                self.toast_window = None
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.configure(text="💾 قاعدة بيانات محلية على هذا الجهاز", foreground=self.fg)

        self.toast_after_id = self.root.after(4200, dismiss)

    def toggle_emergency_mode(self):
        if self.role != "admin":
            self.notify("تفعيل وضع الطوارئ متاح للمدير فقط", "error")
            return
        enabled = self.store.setting("emergency_mode") == "1"
        prompt = (
            "سيُسمح بتسجيل الحالات الطارئة فقط، وستتوقف الحجوزات العادية الجديدة. هل تريد التفعيل؟"
            if not enabled else "هل تريد إنهاء وضع الطوارئ وإعادة السماح بالحجوزات العادية؟"
        )
        if not messagebox.askyesno("تأكيد وضع الطوارئ", prompt, parent=self.root):
            return
        try:
            self.store.set_setting("emergency_mode", "0" if enabled else "1")
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر تحديث وضع الطوارئ", str(exc), parent=self.root)
            return
        self.audit("إنهاء وضع الطوارئ" if enabled else "تفعيل وضع الطوارئ")
        self.rebuild()
        self.notify("تم إنهاء وضع الطوارئ" if enabled else "تم تفعيل وضع الطوارئ")

    def open_feedback_kiosk(self):
        window = tk.Toplevel(self.root)
        window.title("تقييم الخدمة")
        window.geometry("520x390")
        window.transient(self.root)
        form = ttk.Frame(window, padding=18)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="كيف تقيّم مستوى الخدمة؟", font=("Segoe UI", 17, "bold")).pack(pady=(5, 15))
        score = tk.IntVar(value=5)
        rating_row = ttk.Frame(form)
        rating_row.pack(pady=8)
        for value in range(1, 6):
            ttk.Radiobutton(rating_row, text=f"{value} ★", variable=score, value=value).pack(side="left", padx=5)
        ttk.Label(form, text="ملاحظة أو شكوى (اختياري)").pack(anchor="e", pady=(14, 4))
        comment = tk.Text(form, height=5, wrap="word")
        comment.pack(fill="x")

        def submit():
            value = score.get()
            note = comment.get("1.0", "end-1c").strip()
            record = {
                "id": self.store.next_id("feedback"),
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "score": value,
                "comment": note,
                "status": "شكوى" if value <= 2 else "جديد",
            }
            try:
                self.store.save("feedback", record, self.user_name or "استقبال")
            except sqlite3.Error as exc:
                messagebox.showerror("تعذر حفظ التقييم", str(exc), parent=window)
                return
            window.destroy()
            self.notify("شكراً لمشاركتك")
            if self.current_page == "dashboard":
                self.show_page("dashboard", remember=False)

        ttk.Button(form, text="إرسال التقييم", command=submit, style="Accent.TButton").pack(pady=14)

    def toggle_theme(self):
        self.dark = not self.dark
        self.store.set_setting("theme", "dark" if self.dark else "light")
        self.audit("تغيير المظهر")
        self.apply_theme()
        self.rebuild()

    def toggle_language(self):
        self.language = "en" if self.language == "ar" else "ar"
        self.store.set_setting("language", self.language)
        self.audit("تغيير اللغة")
        self.rebuild()

    def rebuild(self):
        page = self.current_page
        self.current_page = "dashboard"
        if hasattr(self, "shell") and self.shell.winfo_exists():
            self.shell.destroy()
        self.build_main()
        if page != "dashboard":
            self.show_page(page, remember=False)

    def customize_brand(self):
        name = simpledialog.askstring("هوية المشفى", "اسم المشفى:", initialvalue=self.hospital_name, parent=self.root)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showerror("قيمة غير صالحة", "اسم المشفى مطلوب")
            return
        color = colorchooser.askcolor(color=self.accent, title="اختر اللون الرئيسي")[1]
        self.hospital_name = name
        self.store.set_setting("hospital_name", name)
        if color:
            self.accent = color
            self.store.set_setting("accent", color)
        self.audit("تخصيص هوية المشفى")
        self.apply_theme()
        self.root.title(name)
        self.rebuild()

    def export_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile=f"hospital-backup-{date.today().isoformat()}.json")
        if not path:
            return
        try:
            self.audit("تصدير نسخة احتياطية")
            payload = {"app": "hospital-management-python", "version": 1, "exportedAt": datetime.now().astimezone().isoformat(), "data": self.store.export_data()}
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.notify("تم إنشاء النسخة الاحتياطية")
        except (OSError, sqlite3.Error) as exc:
            messagebox.showerror("تعذر التصدير", str(exc))

    def import_backup(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        if not messagebox.askyesno("استعادة", "سيتم استبدال جميع البيانات الحالية. متابعة؟"):
            return
        try:
            content = json.loads(Path(path).read_text(encoding="utf-8"))
            self.store.import_data(content.get("data", content), self.user_name)
            self.notify("تمت استعادة البيانات")
            self.show_page(self.current_page)
        except (OSError, json.JSONDecodeError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("تعذرت الاستعادة", str(exc))

    def export_csv(self, key):
        entity = PAGES[key]["entity"]
        if not entity:
            return
        rows = self.store.list(entity)
        if entity == "wards":
            beds = self.store.list("beds")
            for row in rows:
                row["occupied"] = sum(1 for bed in beds if bed.get("ward") == row.get("name") and bed.get("patient"))
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile=f"{entity}-{date.today().isoformat()}.csv")
        if not path:
            return
        try:
            columns = [key for key, _label in PAGES[key]["columns"]]
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["id"] + columns)
                for row in rows:
                    writer.writerow([csv_safe(row.get("id", ""))] + [csv_safe(json.dumps(row.get(col), ensure_ascii=False) if isinstance(row.get(col), (list, dict)) else row.get(col, "")) for col in columns])
            self.audit(f"تصدير CSV: {entity}")
            self.notify("تم تصدير الجدول")
        except OSError as exc:
            messagebox.showerror("تعذر التصدير", str(exc))

    def generate_demo_data(self):
        if self.role != "admin":
            messagebox.showerror("صلاحيات", "توليد البيانات التجريبية متاح للمدير فقط")
            return
        if not messagebox.askyesno("بيانات تجريبية", "سيتم إضافة 50 مريضاً و50 موعداً تجريبياً. متابعة؟"):
            return
        doctors = self.store.list("doctors")
        if not doctors:
            messagebox.showerror("تعذر التوليد", "أضف طبيباً واحداً على الأقل")
            return
        first = ["آدم", "ليان", "سليم", "جود", "راما", "يزن", "تالا", "كريم", "نور", "سارة"]
        last = ["الحسن", "الخليل", "العمر", "الناصر", "الحموي", "سعد", "يوسف", "فارس", "عمران", "حمدان"]
        for index in range(50):
            name = f"{first[index % len(first)]} {last[(index * 7) % len(last)]} {index + 1}"
            patient = {"id": self.store.next_id("patients"), "name": name, "age": 18 + (index * 13) % 70, "gender": "أنثى" if index % 2 else "ذكر", "phone": f"099{1000000 + index}", "status": ("مستقر", "قيد العلاج", "حرج")[index % 3], "allergies": [], "chronicConditions": []}
            appointment = {"id": self.store.next_id("appts"), "patient": name, "doctor": doctors[index % len(doctors)]["name"], "date": date.today().isoformat(), "time": f"{8 + index % 12:02d}:{(index * 7) % 60:02d}", "status": "بالانتظار"}
            self.store.save("patients", patient, self.user_name)
            self.store.save("appts", appointment, self.user_name)
        self.audit("إنشاء بيانات تجريبية")
        self.notify("أضيف 50 مريضاً و50 موعداً تجريبياً")
        self.show_page(self.current_page)

    def open_selected_profile(self):
        record = self.selected_record()
        if record:
            self.open_profile(record)

    def open_profile(self, patient):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"الملف الطبي — {patient.get('name')}")
        dialog.geometry("780x680")
        detail = ttk.Frame(dialog, padding=12)
        detail.pack(fill="both", expand=True)
        ttk.Label(detail, text=f"{patient.get('name')}  |  {patient.get('age', '')}  |  {patient.get('phone', '')}", font=("Segoe UI", 16, "bold")).pack(anchor="e")
        ttk.Label(detail, text=f"الحالة: {patient.get('status', '')}   الحساسية: {', '.join(patient.get('allergies', [])) or 'لا يوجد'}   الأمراض المزمنة: {', '.join(patient.get('chronicConditions', [])) or 'لا يوجد'}", wraplength=740).pack(anchor="e", pady=8)
        vitals = sorted(
            (item for item in self.store.list("vitals") if item.get("patient") == patient.get("name")),
            key=lambda item: item.get("date", ""),
        )
        chart = tk.Canvas(detail, height=145, bg=self.panel, highlightthickness=0)
        chart.pack(fill="x", pady=5)
        chart.create_text(740, 12, text="تطور العلامات الحيوية", fill=self.fg, anchor="ne", font=("Segoe UI", 10, "bold"))
        series = [
            ("السكر", "bloodSugar", "#2563eb"),
            ("الحرارة", "temperature", "#dc2626"),
            ("النبض", "pulse", "#16a34a"),
            ("الضغط الانقباضي", "bloodPressure", "#9333ea"),
        ]
        points_by_series = []
        for label, key, color in series:
            samples = []
            for index, item in enumerate(vitals):
                raw = item.get(key, "")
                match = re.search(r"\d+(?:\.\d+)?", str(raw))
                if match:
                    samples.append((index, float(match.group()), str(raw)))
            points_by_series.append((label, color, samples))
        drawable = [sample for _, _, samples in points_by_series for sample in samples]
        if len(vitals) < 1 or not drawable:
            chart.create_text(370, 75, text="لا توجد قياسات كافية للرسم", fill=self.fg)
        else:
            max_index = max(1, len(vitals) - 1)
            for series_index, (label, color, samples) in enumerate(points_by_series):
                if not samples:
                    continue
                numbers = [value for _, value, _ in samples]
                low, high = min(numbers), max(numbers)
                spread = high - low or 1
                coords = []
                for index, value, _raw in samples:
                    x = 35 + (index / max_index) * 650
                    y = 116 - ((value - low) / spread) * 68
                    coords.extend((x, y))
                if len(coords) >= 4:
                    chart.create_line(*coords, fill=color, width=2)
                for x, y in zip(coords[::2], coords[1::2]):
                    chart.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)
                chart.create_text(25 + series_index * 170, 135, text=label, fill=color, anchor="w", font=("Segoe UI", 8))
        body = tk.Text(detail, wrap="word", height=24, bg=self.panel, fg=self.fg)
        body.pack(fill="both", expand=True, pady=6)
        history = []
        for entity, label in (("appts", "المواعيد"), ("labs", "التحاليل"), ("prescriptions", "الوصفات"), ("vitals", "العلامات الحيوية"), ("bills", "الفواتير"), ("attachments", "المستندات"), ("reminders", "التذكيرات")):
            rows = [row for row in self.store.list(entity) if row.get("patient") == patient.get("name")]
            if rows:
                history.append(f"\n{label}")
                history.extend("  • " + json.dumps({k: v for k, v in row.items() if k != "id"}, ensure_ascii=False) for row in rows)
        notes = [row for row in self.store.list("patientNotes") if row.get("patient") == patient.get("name")]
        if notes:
            history.append("\nالملاحظات")
            history.extend("  • " + row.get("text", "") for row in notes)
        body.insert("1.0", "\n".join(history) or "لا يوجد سجل سابق.")
        body.configure(state="disabled")
        buttons = ttk.Frame(detail)
        buttons.pack(fill="x")
        if self.role in ("admin", "doctor"):
            ttk.Button(buttons, text=self.label_text("إضافة ملاحظة"), command=lambda: self.add_patient_note(patient, dialog)).pack(side="right", padx=4)
            ttk.Button(buttons, text="إضافة علامة حيوية", command=lambda: self.open_form("vitals")).pack(side="right", padx=4)
            ttk.Button(buttons, text=self.label_text("طباعة التقرير الطبي"), command=lambda: self.print_medical_report(patient)).pack(side="right", padx=4)
        ttk.Button(buttons, text="بطاقة QR", command=lambda: self.show_qr(patient)).pack(side="right", padx=4)
        ttk.Button(buttons, text="إغلاق", command=dialog.destroy).pack(side="left")

    def print_selected_medical_report(self):
        if self.role not in ("admin", "doctor"):
            messagebox.showerror("صلاحيات", "طباعة الملخص الطبي متاحة للطبيب أو المدير فقط")
            return
        patient = self.selected_record()
        if patient:
            self.print_medical_report(patient)

    def print_medical_report(self, patient):
        if self.role not in ("admin", "doctor"):
            messagebox.showerror("صلاحيات", "طباعة الملخص الطبي متاحة للطبيب أو المدير فقط")
            return
        name = patient.get("name", "")
        sections = [
            ("المواعيد", "appts", ("date", "التاريخ"), ("time", "الوقت"), ("doctor", "الطبيب"), ("status", "الحالة")),
            ("التحاليل", "labs", ("date", "التاريخ"), ("type", "نوع التحليل"), ("status", "الحالة")),
            ("الوصفات المسجلة", "prescriptions", ("date", "التاريخ"), ("doctor", "الطبيب"), ("medicine", "الدواء"), ("dosage", "الجرعة"), ("frequency", "التكرار"), ("duration", "المدة")),
            ("العلامات الحيوية المسجلة", "vitals", ("date", "التاريخ"), ("bloodPressure", "ضغط الدم"), ("bloodSugar", "سكر الدم"), ("temperature", "الحرارة"), ("pulse", "النبض")),
            ("الفواتير", "bills", ("date", "التاريخ"), ("amount", "المبلغ"), ("balance", "المتبقي"), ("status", "الحالة")),
            ("الملاحظات", "patientNotes", ("date", "التاريخ"), ("user", "المستخدم"), ("text", "الملاحظة")),
        ]
        sections_html = []
        for heading, entity, *columns in sections:
            records = [row for row in self.store.list(entity) if row.get("patient") == name]
            if not records:
                continue
            table_rows = "".join(
                "<tr>" + "".join(f"<td>{html.escape(str(record.get(key, '')))}</td>" for key, _label in columns) + "</tr>"
                for record in sorted(records, key=lambda row: str(row.get("date", "")))
            )
            table_headers = "".join(f"<th>{html.escape(label)}</th>" for _key, label in columns)
            sections_html.append(
                f"<h2>{html.escape(heading)}</h2><table><thead><tr>{table_headers}</tr></thead><tbody>{table_rows}</tbody></table>"
            )
        allergy_values = patient.get("allergies", [])
        chronic_values = patient.get("chronicConditions", [])
        allergies = "، ".join(allergy_values) if isinstance(allergy_values, list) else str(allergy_values or "")
        chronic = "، ".join(chronic_values) if isinstance(chronic_values, list) else str(chronic_values or "")
        allergies = allergies or "لا توجد بيانات مسجلة"
        chronic = chronic or "لا توجد بيانات مسجلة"
        details = f"""
        <h2>بيانات المريض المسجلة</h2>
        <p>الاسم: {html.escape(str(name))}　 رقم الملف: {html.escape(str(patient.get('id', '')))}</p>
        <p>العمر: {html.escape(str(patient.get('age', 'غير مسجل')))}　 الجنس: {html.escape(str(patient.get('gender', 'غير مسجل')))}
       　 الهاتف: {html.escape(str(patient.get('phone', 'غير مسجل')))}　 الحالة في السجل: {html.escape(str(patient.get('status', 'غير مسجلة')))}</p>
        <p>الحساسية المسجلة: {html.escape(allergies)}</p><p>الأمراض المزمنة المسجلة: {html.escape(chronic)}</p>
        """
        content = f"""
        <div class="notice">ملخص آلي للسجلات المدخلة فقط — ليس تشخيصاً أو رأياً طبياً. يجب على طبيب مخول مراجعة المحتوى واعتماده قبل استخدامه.</div>
        <h1>{html.escape(self.hospital_name)}</h1><h2>ملخص السجل الطبي للمراجعة</h2>
        <p>تاريخ استخراج الملخص: {date.today().isoformat()}</p>{details}{''.join(sections_html)}
        <p class="sign">اسم الطبيب المراجع: ____________________　 التوقيع: ____________________　 التاريخ: __________</p>
        """
        self.open_print_document("ملخص طبي للمراجعة", content)
        self.audit(f"إنشاء ملخص طبي للمريض #{patient.get('id')}")

    def add_patient_note(self, patient, parent):
        if self.role not in ("admin", "doctor"):
            messagebox.showerror("صلاحيات", "إضافة الملاحظات الطبية متاحة للطبيب أو المدير فقط", parent=parent)
            return
        note = simpledialog.askstring("ملاحظة طبية", "اكتب الملاحظة:", parent=parent)
        if note is None or not note.strip():
            return
        record = {"id": self.store.next_id("patientNotes"), "patient": patient["name"], "text": note.strip(), "date": date.today().isoformat(), "user": self.user_name}
        try:
            self.store.save("patientNotes", record, self.user_name)
            self.notify("تم حفظ الملاحظة")
        except sqlite3.Error as exc:
            messagebox.showerror("تعذر حفظ الملاحظة", str(exc), parent=parent)

    def open_selected_qr(self):
        patient = self.selected_record()
        if patient:
            self.show_qr(patient)

    def show_qr(self, patient):
        try:
            matrix = qr_numeric_matrix(patient["id"])
        except ValueError as exc:
            messagebox.showerror("تعذر إنشاء QR", str(exc))
            return
        window = tk.Toplevel(self.root)
        window.title("البطاقة الصحية QR")
        canvas = tk.Canvas(window, width=260, height=260, bg="white", highlightthickness=0)
        canvas.pack(padx=15, pady=10)
        scale, border = 8, 4
        for y, row in enumerate(matrix):
            for x, dark in enumerate(row):
                if dark:
                    canvas.create_rectangle((x + border) * scale, (y + border) * scale, (x + border + 1) * scale, (y + border + 1) * scale, fill="black", outline="black")
        ttk.Label(window, text=f"{patient['name']} — رقم الملف {patient['id']}").pack(pady=(0, 12))

    def open_selected_attachment(self):
        record = self.selected_record()
        if record:
            path = record.get("path", "")
            if not Path(path).is_file():
                messagebox.showerror("الملف غير موجود", "مسار المرفق لم يعد متاحاً")
            else:
                os.startfile(path)

    def print_selected_donation(self):
        if self.role not in ("admin", "doctor"):
            messagebox.showerror("صلاحيات", "طباعة نموذج التبرع متاحة للطبيب أو المدير فقط")
            return
        donation = self.selected_record()
        if not donation:
            return
        self.print_donation_receipt(donation)

    def print_donation_receipt(self, donation):
        if self.role not in ("admin", "doctor"):
            messagebox.showerror("صلاحيات", "طباعة نموذج التبرع متاحة للطبيب أو المدير فقط")
            return
        completed_status = next(spec["options"][1] for key, spec in FORM_FIELDS["donations"] if key == "status")
        if donation.get("status") != completed_status:
            messagebox.showwarning("السجل غير مكتمل", "لا يمكن طباعة نموذج تأكيد قبل تسجيل حالة التبرع «تم التبرع».")
            return
        value = lambda key: html.escape(str(donation.get(key) or "غير مسجل"))
        donation_type = donation.get("donation_type", "")
        types = ("دم كامل", "بلازما", "صفائح دموية")
        selected_types = "　".join(("☒ " if item == donation_type else "☐ ") + item for item in types)
        quantity = donation.get("quantity_ml")
        quantity_text = f"{quantity} مل" if quantity not in (None, "") else "غير مسجلة"
        content = f"""
        <div class="notice"><strong>نموذج إيصال للمراجعة — ليس شهادة رسمية ولا يثبت إجراء الفحوصات أو صلاحية الدم.</strong><br>
        أُعدّ بناءً على بيانات أُدخلت في النظام؛ يجب على المركز مراجعة السجل والتحقق من وقوع التبرع والفحوصات قبل اعتماده أو ختمه.</div>
        <h1>{html.escape(self.hospital_name)}</h1>
        <h2>نموذج إيصال / شهادة تبرع بالدم</h2>
        <h3>بيانات المتبرع</h3>
        <table>
          <tr><th>الاسم الكامل</th><td>{value('donor_name')}</td><th>رقم الهوية / الرقم الوطني</th><td>{value('identity_number')}</td></tr>
          <tr><th>فصيلة الدم (حسب السجل)</th><td>{value('blood_type')}</td><th>رقم سجل التبرع</th><td>{value('id')}</td></tr>
        </table>
        <h3>بيانات التبرع</h3>
        <table>
          <tr><th>تاريخ التبرع</th><td>{value('date')}</td><th>نوع التبرع</th><td>{selected_types}</td></tr>
          <tr><th>الكمية المسحوبة (إن وجدت)</th><td>{html.escape(quantity_text)}</td><th>المركز / المستشفى</th><td>{value('center')}</td></tr>
          <tr><th>حالة الفحوصات حسب السجل</th><td colspan="3">{value('screening_status')}</td></tr>
        </table>
        <p>إقرار المركز: تتم مراجعة هذا النموذج ومطابقة بياناته مع السجلات المعتمدة للمركز قبل التوقيع أو الختم.</p>
        <p>ختم المركز: ____________________　 توقيع المسؤول المخول: ____________________　 التاريخ: __________</p>
        """
        self.open_print_document("نموذج تبرع بالدم للمراجعة", content)
        self.audit(f"طباعة نموذج تبرع بالدم للسجل #{donation.get('id')}")

    def print_selected_invoice(self):
        record = self.selected_record()
        if record:
            self.print_invoice(record)

    def print_invoice(self, bill):
        items = "".join(f"<tr><td>{html.escape(str(item.get('description', '')))}</td><td>{item.get('quantity')}</td><td>{item.get('unitPrice')}</td><td>{float(item.get('quantity', 0))*float(item.get('unitPrice', 0)):.2f}</td></tr>" for item in bill.get("items", []))
        content = f"""<h1>{html.escape(self.hospital_name)}</h1><h2>فاتورة طبية</h2>
        <p>رقم الفاتورة: {bill.get('id')} | المريض: {html.escape(str(bill.get('patient', '')))} | التاريخ: {html.escape(str(bill.get('date', '')))}</p>
        <table><thead><tr><th>البند</th><th>الكمية</th><th>سعر الوحدة</th><th>الإجمالي</th></tr></thead><tbody>{items}</tbody></table>
        <p>الإجمالي: {bill.get('amount')} | التأمين: {bill.get('insuranceCovered', 0)} | المتبقي: {bill.get('balance', 0)} | طريقة الدفع: {html.escape(str(bill.get('paymentMethod', '')))}</p>"""
        self.open_print_document("فاتورة", content)

    def print_selected_prescription(self):
        record = self.selected_record()
        if record:
            self.print_prescription(record)

    def print_prescription(self, prescription):
        patient = next((p for p in self.store.list("patients") if p.get("name") == prescription.get("patient")), {})
        content = f"""<h1>{html.escape(self.hospital_name)}</h1><h2>وصفة طبية</h2>
        <p>المريض: {html.escape(str(prescription.get('patient', '')))} | العمر: {patient.get('age', '')} | التاريخ: {html.escape(str(prescription.get('date', '')))}</p>
        <p>الطبيب: {html.escape(str(prescription.get('doctor', '')))}</p><table><tr><th>الدواء</th><td>{html.escape(str(prescription.get('medicine', '')))}</td></tr>
        <tr><th>الجرعة</th><td>{html.escape(str(prescription.get('dosage', '')))}</td></tr><tr><th>التكرار</th><td>{html.escape(str(prescription.get('frequency', '')))}</td></tr>
        <tr><th>المدة</th><td>{html.escape(str(prescription.get('duration', '')))}</td></tr><tr><th>الكمية</th><td>{prescription.get('quantity', '')}</td></tr></table><p>التوقيع: __________________</p>"""
        self.open_print_document("وصفة", content)

    def print_selected_death_request(self):
        request = self.selected_record()
        if request:
            self.print_death_certificate_request(request)

    def print_death_certificate_request(self, request):
        value = lambda key: html.escape(str(request.get(key) or "غير مذكور"))
        checked = lambda key: "☒ نعم" if request.get(key) == "نعم" else "☐ لا"
        content = f"""
        <div class="notice"><strong>نموذج طلب إداري فقط — ليس شهادة وفاة رسمية ولا يثبت وقوع الوفاة.</strong><br>
        لا يتضمن هذا النموذج ختم المشفى أو اعتماداً رسمياً. إصدار الشهادة أو رفضها من اختصاص الجهة المخولة بعد التحقق من الوثائق والسجلات.</div>
        <h1>إلى إدارة المشفى / قسم السجلات الطبية</h1>
        <h2>طلب استخراج شهادة وفاة</h2>
        <p>تحية طيبة وبعد،</p>
        <p>أرجو التكرم بمراجعة طلبي لاستخراج شهادة وفاة للمتوفى/المتوفاة:</p>
        <table>
          <tr><th>الاسم الرباعي</th><td>{value('deceased_name')}</td><th>تاريخ الوفاة</th><td>{value('death_date')}</td></tr>
          <tr><th>الغرض من الطلب</th><td colspan="3">{value('purpose')}</td></tr>
          <tr><th>عدد النسخ الإضافية المطلوبة</th><td>{value('copies')}</td><th>حالة الطلب</th><td>{value('status')}</td></tr>
        </table>
        <h3>المرفقات</h3>
        <p>{checked('identity_attached')} صورة هوية مقدم الطلب</p>
        <p>{checked('relationship_attached')} إثبات صلة القرابة (إن لزم)</p>
        <p>وثائق أخرى: {value('other_documents')}</p>
        <h3>استفسارات وإجراءات</h3>
        <p>رسوم الإصدار: {value('fee')}　 طريقة السداد / ملاحظات: {value('payment_method')}</p>
        <p>الجهة البديلة عند تعذر الإصدار: {value('alternative_office')}</p>
        <p>المدة الزمنية المتوقعة: {value('expected_time')}</p>
        <p>يرجى التواصل عند الجاهزية على الرقم: {value('phone')}</p>
        <p>مقدم الطلب: {value('applicant')}　 صفة القرابة: {value('kinship')}</p>
        <p>التوقيع: {value('signature')}　 التاريخ: {value('date')}</p>
        <p class="sign">توقيع الموظف المختص: ____________________　 التاريخ: __________</p>
        <p class="notice">يرجى سؤال إدارة المشفى عن الرسوم والمدة والجهة البديلة؛ لم يتم تأكيدها في هذا الطلب.</p>
        """
        self.open_print_document("طلب شهادة وفاة — نموذج إداري", content)
        self.audit(f"طباعة طلب وثيقة وفاة #{request.get('id')}")

    def open_print_document(self, title, content):
        document = f"""<!doctype html><meta charset="utf-8"><title>{title}</title>
        <style>body{{font:16px Arial;direction:rtl;margin:40px;line-height:1.75;color:#1e293b}}h1,h2{{text-align:center;color:#0b3d91}}table{{width:100%;border-collapse:collapse;margin:20px 0}}td,th{{border:1px solid #94a3b8;padding:9px;text-align:right;vertical-align:top}}th{{background:#eff6ff}}.notice{{border:2px solid #b45309;background:#fffbeb;padding:12px;margin:14px 0;text-align:center}}.sign{{margin-top:42px}}@media print{{button{{display:none}}body{{margin:15mm}}}}</style>
        <button onclick="window.print()">طباعة / حفظ PDF</button>{content}"""
        with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as file:
            file.write(document)
            path = file.name
        webbrowser.open(Path(path).as_uri())
        self.audit(f"طباعة {title}")

    def open_reports(self):
        window = tk.Toplevel(self.root)
        window.title("التقارير والمؤشرات")
        window.geometry("760x570")
        controls = ttk.Frame(window, padding=10)
        controls.pack(fill="x")
        period = tk.StringVar(value="شهري")
        ttk.Label(controls, text="الفترة").pack(side="right")
        ttk.Combobox(controls, textvariable=period, values=["يومي", "شهري", "سنوي"], state="readonly", width=12).pack(side="right", padx=5)
        result = ttk.Label(window, text="", justify="right", font=("Segoe UI", 11))
        result.pack(fill="x", padx=12, pady=8)
        canvas = tk.Canvas(window, height=340, bg=self.panel, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=10, pady=10)

        def draw():
            bills = self.store.list("bills")
            now = date.today()
            if period.get() == "يومي":
                previous = now.fromordinal(now.toordinal() - 1)
            elif period.get() == "سنوي":
                previous = date(now.year - 1, 1, 1)
            else:
                previous = date(now.year - 1, 12, 1) if now.month == 1 else date(now.year, now.month - 1, 1)

            def matches(value):
                try:
                    stamp = datetime.strptime(value, "%Y-%m-%d").date()
                    if period.get() == "يومي":
                        return stamp == now
                    if period.get() == "سنوي":
                        return stamp.year == now.year
                    return stamp.year == now.year and stamp.month == now.month
                except ValueError:
                    return False

            def matches_previous(value):
                try:
                    stamp = datetime.strptime(value, "%Y-%m-%d").date()
                    if period.get() == "يومي":
                        return stamp == previous
                    if period.get() == "سنوي":
                        return stamp.year == previous.year
                    return stamp.year == previous.year and stamp.month == previous.month
                except ValueError:
                    return False

            selected = [bill for bill in bills if matches(str(bill.get("date", "")))]
            previous_rows = [bill for bill in bills if matches_previous(str(bill.get("date", "")))]
            total = sum(float(item.get("amount", 0)) for item in selected)
            paid = sum(float(item.get("amount", 0)) - float(item.get("balance", 0)) for item in selected)
            previous_total = sum(float(item.get("amount", 0)) for item in previous_rows)
            change = total - previous_total
            selected_appointments = [item for item in self.store.list("appts") if matches(str(item.get("date", "")))]
            productivity = {}
            for appointment in selected_appointments:
                doctor = str(appointment.get("doctor") or "غير محدد")
                productivity[doctor] = productivity.get(doctor, 0) + 1
            top_doctors = sorted(productivity.items(), key=lambda item: (-item[1], item[0]))[:3]
            conditions = {}
            for patient in self.store.list("patients"):
                values = patient.get("chronicConditions", [])
                if isinstance(values, str):
                    values = values.split(",")
                for condition in values:
                    name = str(condition).strip()
                    if name:
                        conditions[name] = conditions.get(name, 0) + 1
            top_conditions = sorted(conditions.items(), key=lambda item: (-item[1], item[0]))[:3]
            doctor_report = "، ".join(f"{name}: {count}" for name, count in top_doctors) or "لا توجد بيانات"
            condition_report = "، ".join(f"{name}: {count}" for name, count in top_conditions) or "لا توجد بيانات"
            forecast = financial_forecast(self.store, now)
            forecast_report = (
                f"تقدير الشهر القادم (متوسط آخر 3 أشهر): إيرادات {forecast['revenue']:,.2f}، "
                f"رواتب {forecast['payroll']:,.2f}"
                if forecast else "التوقع المالي: بيانات 3 أشهر غير متوفرة"
            )
            result.configure(
                text=(
                    f"الفواتير: {len(selected)}     الإجمالي: {total:,.2f}     المحصل: {paid:,.2f}     المتبقي: {total-paid:,.2f}\n"
                    f"مقارنة بالفترة السابقة: {previous_total:,.2f}   التغير: {change:+,.2f}\n"
                    f"إنتاجية الأطباء (عدد المواعيد): {doctor_report}\n"
                    f"الحالات المزمنة الأكثر تسجيلاً: {condition_report}\n"
                    f"{forecast_report}"
                )
            )
            canvas.delete("all")
            heat = [[0] * 24 for _ in range(7)]
            for appt in self.store.list("appts"):
                try:
                    stamp = datetime.strptime(appt.get("date", ""), "%Y-%m-%d")
                    hour = int(str(appt.get("time", "0")).split(":")[0]) % 24
                    heat[stamp.weekday()][hour] += 1
                except (ValueError, TypeError):
                    continue
            maximum = max((value for row in heat for value in row), default=0) or 1
            days = ("إث", "ث", "أر", "خ", "ج", "س", "أ")
            for day_index, row in enumerate(heat):
                canvas.create_text(18, 62 + day_index * 32, text=days[day_index], fill=self.fg, anchor="w")
                for hour, count in enumerate(row):
                    ratio = count / maximum
                    shade = int(235 - ratio * 150)
                    color = f"#20{shade:02x}65" if count else "#dbeafe"
                    x, y = 46 + hour * 27, 48 + day_index * 32
                    canvas.create_rectangle(x, y, x + 22, y + 24, fill=color, outline=self.bg)
            for hour in range(0, 24, 2):
                canvas.create_text(57 + hour * 27, 286, text=f"{hour:02d}", fill=self.fg, font=("Segoe UI", 8))
            canvas.create_text(355, 22, text="خريطة حرارية للمواعيد: اليوم والساعة", fill=self.fg, font=("Segoe UI", 11, "bold"))
        ttk.Button(controls, text="تحديث التقرير", command=draw).pack(side="right", padx=5)
        period.trace_add("write", lambda *_args: draw())
        draw()

    def open_waiting_room(self):
        window = tk.Toplevel(self.root)
        window.title("شاشة الانتظار")
        window.geometry("1100x700")
        ttk.Label(window, text=self.hospital_name, font=("Segoe UI", 23, "bold")).pack(pady=12)
        calls = ttk.Frame(window, padding=(12, 4))
        calls.pack(fill="x")
        current_call = ttk.Label(calls, text="", font=("Segoe UI", 18, "bold"), anchor="center")
        current_call.pack(fill="x", pady=4)
        next_call = ttk.Label(calls, text="", font=("Segoe UI", 15), anchor="center")
        next_call.pack(fill="x", pady=4)
        ttk.Button(
            calls,
            text="ملء الشاشة",
            command=lambda: window.attributes("-fullscreen", True),
        ).pack(pady=4)
        window.bind("<Escape>", lambda _event: window.attributes("-fullscreen", False))
        tree = ttk.Treeview(window, columns=("number", "clinic", "doctor", "time", "status"), show="headings", height=16)
        for column, label in (("number", "الدور"), ("clinic", "العيادة"), ("doctor", "الطبيب"), ("time", "الوقت"), ("status", "الحالة")):
            tree.heading(column, text=label)
            tree.column(column, anchor="center", width=160)
        tree.pack(fill="both", expand=True, padx=16, pady=12)

        def refresh():
            if not window.winfo_exists():
                return
            snapshot = waiting_room_snapshot(self.store)
            current = snapshot["current"]
            upcoming = snapshot["upcoming"]
            current_call.configure(
                text=(
                    f"الدور الحالي #{current.get('id')} — {current.get('clinic')} — {current.get('doctor')}"
                    if current else "لا يوجد دور جارٍ حالياً"
                )
            )
            next_appointment = upcoming[0] if upcoming else None
            next_call.configure(
                text=(
                    f"الدور القادم #{next_appointment.get('id')} — {next_appointment.get('clinic')} — "
                    f"{next_appointment.get('doctor')}"
                    if next_appointment else "لا يوجد موعد تالٍ بالانتظار"
                )
            )
            tree.delete(*tree.get_children())
            rows = ([current] if current else []) + upcoming
            for item in rows:
                tree.insert(
                    "",
                    "end",
                    values=(item.get("id"), item.get("clinic"), item.get("doctor"), item.get("time"), item.get("status")),
                )
            window.after(10000, refresh)

        refresh()

    def open_chatbot(self):
        window = tk.Toplevel(self.root)
        window.title("المساعد المعلوماتي")
        window.geometry("570x500")
        ttk.Label(window, text="مساعد معلوماتي بسيط، لا يقدم تشخيصاً طبياً. للطوارئ تواصل مع الطاقم الطبي.", wraplength=520).pack(padx=12, pady=10)
        transcript = tk.Text(window, wrap="word", height=18, bg=self.panel, fg=self.fg)
        transcript.pack(fill="both", expand=True, padx=10, pady=6)
        row = ttk.Frame(window, padding=8)
        row.pack(fill="x")
        question = ttk.Entry(row)
        question.pack(side="right", fill="x", expand=True, padx=5)

        def send():
            text = question.get().strip()
            if not text:
                return
            lower = text.casefold()
            if "موعد" in text or "appointment" in lower:
                answer = "يمكنك حجز موعد من صفحة المواعيد باستخدام زر إضافة."
            elif "دواء" in text or "medicine" in lower:
                answer = "يمكنك مراجعة صفحة الصيدلية. لا تعتمد على هذا المساعد لاختيار علاج."
            elif "ساعات" in text or "hours" in lower:
                answer = "يرجى التواصل مع الاستقبال لمعرفة ساعات العمل."
            else:
                answer = "لا أملك معلومات كافية. تواصل مع موظفي المشفى، ولا تستخدم المساعد للتشخيص."
            transcript.insert("end", f"\nأنت: {text}\nالمساعد: {answer}\n")
            question.delete(0, "end")
            transcript.see("end")
        ttk.Button(row, text="إرسال", command=send).pack(side="left")
        question.bind("<Return>", lambda _event: send())
        transcript.insert("1.0", "الأسئلة الشائعة: حجز موعد، معلومات الصيدلية، ساعات العمل.\n")
        ttk.Button(window, text="حجز موعد سريع", command=lambda: self.chatbot_quick_booking(window)).pack(pady=(0, 8))

    def chatbot_quick_booking(self, window):
        if not self.can_add("appts"):
            messagebox.showerror("صلاحيات", "لا تملك صلاحية حجز موعد")
            return
        window.destroy()
        self.show_page("appts")
        self.open_form("appts")

    def check_reminders(self):
        now = datetime.now().astimezone()
        today, clock = now.date().isoformat(), now.strftime("%H:%M")
        due = [item for item in self.store.list("reminders") if item.get("status") == "مجدول" and item.get("date") == today and item.get("time") <= clock]
        if not due:
            return
        for item in due:
            messagebox.showinfo("تذكير بموعد", f"{item.get('patient')} — {item.get('message')} ({item.get('time')})")
            item["status"] = "تم الإشعار"
            self.store.save("reminders", item, self.user_name, item["id"])

    def reminder_tick(self):
        if not self.root.winfo_exists():
            return
        self.check_reminders()
        if self.current_page == "dashboard":
            position = self.dashboard_canvas.yview()[0] if hasattr(self, "dashboard_canvas") else 0
            self.show_page("dashboard", remember=False)
            self.root.after_idle(lambda: self.dashboard_canvas.yview_moveto(position))
        elif self.current_page == "emergency":
            self.show_page("emergency", remember=False)
        self.root.after(30000, self.reminder_tick)

    def close(self):
        try:
            if self.user_name:
                self.audit("تسجيل خروج")
            self.store.close()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    HospitalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
