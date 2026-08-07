import flet as ft
import json
import os
import threading
import time
from persian_datepicker import PersianDatePicker
import jdatetime

# ============= بخش کلاس‌ها =============

class TaskManager:
    def __init__(self):
        self.tasks = []
        self.data_file = "tasks.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
    
    def save(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add(self, title, category="سایر", priority="غیرفوری و مهم", deadline=None):
        task = {
            "id": len(self.tasks) + 1,
            "title": title,
            "category": category,
            "priority": priority,
            "done": False,
            "deadline": deadline,
            "created": jdatetime.date.today().strftime("%Y-%m-%d")
        }
        self.tasks.append(task)
        self.save()
        return task
    
    def delete(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            self.save()
    
    def toggle(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks[index]["done"] = not self.tasks[index]["done"]
            self.save()
    
    def get_stats(self):
        total = len(self.tasks)
        done = len([t for t in self.tasks if t.get("done")])
        return {
            "total": total,
            "done": done,
            "pending": total - done,
            "completion_rate": (done / total * 100) if total > 0 else 0
        }

class PomodoroTimer:
    def __init__(self, page):
        self.page = page
        self.work_time = 25 * 60
        self.break_time = 5 * 60
        self.is_running = False
        self.is_work = True
        self.remaining = self.work_time
        self.thread = None
        
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
    
    def stop(self):
        self.is_running = False
    
    def reset(self):
        self.stop()
        self.is_work = True
        self.remaining = self.work_time
    
    def _run(self):
        while self.is_running and self.remaining > 0:
            time.sleep(1)
            self.remaining -= 1
            self.update_display()
        
        if self.remaining == 0 and self.is_running:
            self.switch_mode()
    
    def switch_mode(self):
        self.is_work = not self.is_work
        self.remaining = self.work_time if self.is_work else self.break_time
        self.page.snack_bar = ft.SnackBar(
            ft.Text("⏰ زمان استراحت!" if not self.is_work else "⏰ زمان تمرکز!"),
            duration=3000
        )
        self.page.snack_bar.open = True
        self.page.update()
        self.start()
    
    def update_display(self):
        pass
    
    def get_time_string(self):
        minutes = self.remaining // 60
        seconds = self.remaining % 60
        return f"{minutes:02d}:{seconds:02d}"

class Gamification:
    def __init__(self):
        self.points = 0
        self.level = 1
        self.streak = 0
        self.badges = []
        
    def add_points(self, points):
        self.points += points
        self.streak += 1
        return self.check_level_up()
    
    def check_level_up(self):
        new_level = self.points // 100 + 1
        if new_level > self.level:
            self.level = new_level
            self.unlock_badge(f"سطح {self.level}")
            return True
        return False
    
    def unlock_badge(self, name):
        if name not in self.badges:
            self.badges.append(name)
            return True
        return False

# ============= صفحه اصلی برنامه =============

async def main(page: ft.Page):
    # تنظیمات اولیه
    page.title = "مدیریت زمان حرفه‌ای"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20
    page.rtl = True
    
    # ایجاد اشیاء اصلی
    task_manager = TaskManager()
    timer = PomodoroTimer(page)
    gamification = Gamification()
    
    # ===== بخش ویجت‌های رابط کاربری =====
    
    # نوار بالایی با دکمه‌های اصلی
    top_bar = ft.Row([
        ft.Text("📋 مدیریت زمان", size=28, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.IconButton(
                icon="VIEW_DASHBOARD",
                on_click=lambda _: show_dashboard(),
                tooltip="داشبورد"
            ),
            ft.IconButton(
                icon="CALENDAR_MONTH",
                on_click=lambda _: show_calendar(),
                tooltip="تقویم"
            ),
            ft.IconButton(
                icon="BRIGHTNESS_MEDIUM",
                on_click=lambda _: toggle_theme(),
                tooltip="تغییر تم"
            ),
        ])
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    # ===== بخش تایمر پومودورو =====
    timer_display = ft.Text(
        "25:00",
        size=48,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE_700
    )
    
    timer_controls = ft.Row([
        ft.IconButton(
            icon="PLAY_ARROW",
            on_click=lambda _: timer.start(),
            icon_size=40,
            icon_color=ft.Colors.GREEN
        ),
        ft.IconButton(
            icon="STOP",
            on_click=lambda _: timer.stop(),
            icon_size=40,
            icon_color=ft.Colors.RED
        ),
        ft.IconButton(
            icon="REFRESH",
            on_click=lambda _: timer.reset(),
            icon_size=40,
            icon_color=ft.Colors.ORANGE
        ),
    ], alignment=ft.MainAxisAlignment.CENTER)
    
    timer_section = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("⏱️ تایمر پومودورو", size=20, weight=ft.FontWeight.BOLD),
                timer_display,
                timer_controls,
                ft.Text("تمرکز ۲۵ دقیقه | استراحت ۵ دقیقه", size=14, color=ft.Colors.GREY_600)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            width=400
        )
    )
    
    # ===== بخش افزودن کار جدید =====
    task_input = ft.TextField(
        hint_text="کار جدید را وارد کنید...",
        width=300,
        on_submit=lambda e: add_task()
    )
    
    category_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("کار", "کار"),
            ft.dropdown.Option("شخصی", "شخصی"),
            ft.dropdown.Option("مطالعه", "مطالعه"),
            ft.dropdown.Option("سلامت", "سلامت"),
            ft.dropdown.Option("سایر", "سایر"),
        ],
        value="سایر",
        width=120,
    )
    
    priority_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("فوری و مهم", "فوری و مهم"),
            ft.dropdown.Option("غیرفوری و مهم", "غیرفوری و مهم"),
            ft.dropdown.Option("فوری و غیرمهم", "فوری و غیرمهم"),
            ft.dropdown.Option("غیرفوری و غیرمهم", "غیرفوری و غیرمهم"),
        ],
        value="غیرفوری و مهم",
        width=140,
    )
    
    add_button = ft.IconButton(
        icon="ADD",
        icon_size=40,
        icon_color=ft.Colors.BLUE,
        on_click=lambda _: add_task()
    )
    
    def add_task():
        if task_input.value and task_input.value.strip():
            task = task_manager.add(
                task_input.value.strip(),
                category_dropdown.value,
                priority_dropdown.value
            )
            task_input.value = ""
            task_input.update()
            gamification.add_points(3)
            update_task_list()
            page.snack_bar = ft.SnackBar(ft.Text("✅ کار جدید اضافه شد!"))
            page.snack_bar.open = True
            page.update()
    
    # ===== بخش نمایش لیست کارها =====
    task_list = ft.Column(spacing=8)
    
    def get_priority_color(priority):
        colors = {
            "فوری و مهم": ft.Colors.RED,
            "غیرفوری و مهم": ft.Colors.ORANGE,
            "فوری و غیرمهم": ft.Colors.YELLOW,
            "غیرفوری و غیرمهم": ft.Colors.GREY
        }
        return colors.get(priority, ft.Colors.GREY)
    
    def get_category_icon(category):
        icons = {
            "کار": "COMPUTER",
            "شخصی": "PERSON",
            "مطالعه": "SCHOOL",
            "سلامت": "FAVORITE",
            "سایر": "POST_ADD"
        }
        return icons.get(category, "ADD")
    
    def update_task_list():
        task_list.controls.clear()
        
        for i, task in enumerate(task_manager.tasks):
            task_card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Checkbox(
                            value=task.get("done", False),
                            on_change=lambda e, idx=i: toggle_task(idx),
                            fill_color=ft.Colors.GREEN if task.get("done") else None
                        ),
                        ft.Column([
                            ft.Text(
                                task.get("title", ""),
                                size=16,
                                weight=ft.FontWeight.BOLD if not task.get("done") else ft.FontWeight.NORMAL,
                                color=ft.Colors.GREY_600 if task.get("done") else ft.Colors.BLACK,
                            ),
                            ft.Row([
                                ft.Icon(
                                    name=get_category_icon(task.get("category", "سایر")),
                                    size=16,
                                    color=get_priority_color(task.get("priority", "غیرفوری و مهم"))
                                ),
                                ft.Text(
                                    task.get("category", "سایر"),
                                    size=12,
                                    color=ft.Colors.GREY_600
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        task.get("priority", "غیرفوری و مهم"),
                                        size=10,
                                        color=ft.Colors.WHITE
                                    ),
                                    bgcolor=get_priority_color(task.get("priority", "غیرفوری و مهم")),
                                    padding=5,
                                    border_radius=5
                                )
                            ])
                        ], spacing=2),
                        ft.Row([
                            ft.IconButton(
                                icon="EDIT",
                                icon_size=20,
                                on_click=lambda e, idx=i: edit_task(idx)
                            ),
                            ft.IconButton(
                                icon="DELETE_OUTLINE",
                                icon_color=ft.Colors.RED_400,
                                on_click=lambda e, idx=i: delete_task(idx),
                            )
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10
                )
            )
            task_list.controls.append(task_card)
        
        if not task_manager.tasks:
            task_list.controls.append(
                ft.Text("📭 هیچ کاری ثبت نشده است!", size=16, color=ft.Colors.GREY_500)
            )
        
        page.update()
    
    def toggle_task(index):
        task_manager.toggle(index)
        if task_manager.tasks[index].get("done"):
            gamification.add_points(10)
            page.snack_bar = ft.SnackBar(ft.Text("🎉 +۱۰ امتیاز!"))
            page.snack_bar.open = True
        update_task_list()
    
    def delete_task(index):
        task_manager.delete(index)
        update_task_list()
    
    def edit_task(index):
        task = task_manager.tasks[index]
        task_title = ft.TextField(
            value=task.get("title"),
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text("ویرایش کار"),
            content=ft.Column([
                task_title,
            ], tight=True),
            actions=[
                ft.TextButton("لغو", on_click=lambda _: close_dialog()),
                ft.TextButton("ذخیره", on_click=lambda _: save_edit()),
            ]
        )
        
        def save_edit():
            task["title"] = task_title.value
            task_manager.save()
            page.dialog.open = False
            update_task_list()
            page.update()
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    # ===== بخش داشبورد =====
    def show_dashboard():
        stats = task_manager.get_stats()
        
        dashboard_content = ft.AlertDialog(
            title=ft.Text("📊 داشبورد مدیریت زمان"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Card(ft.Text(f"📋 مجموع: {stats['total']}")),
                        ft.Card(ft.Text(f"✅ انجام‌شده: {stats['done']}")),
                        ft.Card(ft.Text(f"⏳ باقی‌مانده: {stats['pending']}")),
                    ]),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text(f"📈 پیشرفت: {stats['completion_rate']:.1f}%"),
                                ft.ProgressBar(value=stats['completion_rate']/100),
                            ]),
                            padding=20
                        )
                    ),
                    ft.Divider(),
                    ft.Text(f"⭐ امتیاز گیمیفیکیشن: {gamification.points}"),
                    ft.Text(f"🏅 سطح: {gamification.level}"),
                    ft.Text(f"🔥 رکورد: {gamification.streak} روز"),
                    ft.Row([
                        ft.Text("🎖️ نشان‌ها: "),
                        ft.Row([ft.Text(badge) for badge in gamification.badges])
                    ])
                ]),
                width=400,
                height=400
            ),
            actions=[
                ft.TextButton("بستن", on_click=lambda _: close_dialog())
            ]
        )
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        page.dialog = dashboard_content
        dashboard_content.open = True
        page.update()
    
    # ===== بخش تقویم =====
    def show_calendar():
        today = jdatetime.date.today().strftime("%Y/%m/%d")
        page.snack_bar = ft.SnackBar(ft.Text(f"📅 تاریخ امروز: {today}"))
        page.snack_bar.open = True
        page.update()
    
    # ===== بخش تغییر تم =====
    def toggle_theme():
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = ft.Colors.GREY_900
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = ft.Colors.WHITE
        page.update()
    
    # ===== اضافه کردن همه بخش‌ها به صفحه =====
    
    quick_actions = ft.Row([
        ft.ElevatedButton("📊 داشبورد", on_click=lambda _: show_dashboard()),
        ft.ElevatedButton("📅 تقویم", on_click=lambda _: show_calendar()),
        ft.ElevatedButton("🗑️ پاک کردن همه", on_click=lambda _: clear_all()),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
    
    def clear_all():
        if task_manager.tasks:
            def confirm_clear():
                task_manager.tasks.clear()
                task_manager.save()
                page.dialog.open = False
                update_task_list()
                page.update()
            
            def close_dialog():
                page.dialog.open = False
                page.update()
            
            page.dialog = ft.AlertDialog(
                title=ft.Text("⚠️ تأیید حذف"),
                content=ft.Text("آیا از حذف همه کارها مطمئن هستید؟"),
                actions=[
                    ft.TextButton("لغو", on_click=lambda _: close_dialog()),
                    ft.TextButton("حذف همه", on_click=lambda _: confirm_clear()),
                ]
            )
            page.dialog.open = True
            page.update()
    
    page.add(
        top_bar,
        ft.Divider(height=10),
        timer_section,
        ft.Divider(height=20),
        ft.Text("➕ افزودن کار جدید", size=18, weight=ft.FontWeight.BOLD),
        ft.Row([
            task_input,
            category_dropdown,
            priority_dropdown,
            add_button
        ], alignment=ft.MainAxisAlignment.CENTER, wrap=True),
        ft.Divider(height=20),
        ft.Text("📋 لیست کارها", size=18, weight=ft.FontWeight.BOLD),
        task_list,
        ft.Divider(height=10),
        quick_actions,
    )
    
    update_task_list()
    
    def update_timer_display():
        while True:
            time.sleep(1)
            timer_display.value = timer.get_time_string()
            timer_display.update()
    
    threading.Thread(target=update_timer_display, daemon=True).start()

ft.app(target=main)
