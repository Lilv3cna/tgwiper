#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TG Wiper - Kivy GUI version
----------------------------
Same tool as the CLI script, but as a touch-friendly Android app.
Flow:
  1) Enter API ID / API HASH / Phone number / Channel link
  2) Enter the login code Telegram sends you (and 2FA password if enabled)
  3) Pick how many messages to delete (last 1 / 100 / 200 ... 10000 / ALL)
  4) Confirm -> deletes, showing live progress in a log view
"""

import asyncio
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ---------------------------------------------------------
# "Hacker" theme colors
# ---------------------------------------------------------
BG = (0.02, 0.02, 0.02, 1)
FG = (0.15, 1, 0.4, 1)
ACCENT = (1, 0.2, 0.2, 1)
DIM = (0.5, 0.5, 0.5, 1)

Window.clearcolor = BG


# ---------------------------------------------------------
# Background asyncio loop, bridged to the Kivy main thread
# ---------------------------------------------------------
class AsyncRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


runner = AsyncRunner()


def on_ui(callback, *args):
    """Call `callback(*args)` safely on Kivy's main thread from any thread."""
    Clock.schedule_once(lambda dt: callback(*args))


def styled_input(hint):
    return TextInput(
        hint_text=hint,
        multiline=False,
        size_hint_y=None,
        height=48,
        background_color=(0.05, 0.05, 0.05, 1),
        foreground_color=FG,
        hint_text_color=DIM,
        cursor_color=FG,
        padding=[10, 12, 10, 12],
    )


def styled_button(text, bg=FG):
    return Button(
        text=text,
        size_hint_y=None,
        height=52,
        background_normal="",
        background_color=bg,
        color=(0, 0, 0, 1),
        bold=True,
    )


def styled_label(text, color=FG, size_hint_y=None, height=30):
    return Label(text=text, color=color, size_hint_y=size_hint_y, height=height)


# ---------------------------------------------------------
# Screen 1: credentials
# ---------------------------------------------------------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=20, spacing=12)

        root.add_widget(styled_label(">> TG WIPER // LOGIN", color=FG, height=40))
        root.add_widget(styled_label("Enter your Telegram API credentials", color=DIM, height=24))

        self.api_id = styled_input("API ID")
        self.api_hash = styled_input("API HASH")
        self.phone = styled_input("Phone number (+2010xxxxxxx)")
        self.channel = styled_input("Channel link or @username")

        for w in (self.api_id, self.api_hash, self.phone, self.channel):
            root.add_widget(w)

        self.status = styled_label("", color=ACCENT, height=40)
        root.add_widget(self.status)

        connect_btn = styled_button("CONNECT")
        connect_btn.bind(on_release=lambda *_: self.connect())
        root.add_widget(connect_btn)

        root.add_widget(BoxLayout())  # spacer
        self.add_widget(root)

    def connect(self):
        api_id_raw = self.api_id.text.strip()
        api_hash = self.api_hash.text.strip()
        phone = self.phone.text.strip()
        channel = self.channel.text.strip()

        if not api_id_raw.isdigit() or not api_hash or not phone or not channel:
            self.status.text = "Fill all fields correctly."
            return

        app = App.get_running_app()
        app.api_id = int(api_id_raw)
        app.api_hash = api_hash
        app.phone = phone
        app.channel = channel

        self.status.text = "Connecting..."
        runner.submit(self._do_connect(app))

    async def _do_connect(self, app):
        try:
            app.client = TelegramClient("tgwiper_session", app.api_id, app.api_hash)
            await app.client.connect()

            if not await app.client.is_user_authorized():
                await app.client.send_code_request(app.phone)
                on_ui(self._go_to_code_screen)
            else:
                entity = await app.client.get_entity(app.channel)
                app.entity = entity
                on_ui(self._go_to_menu_screen, getattr(entity, "title", app.channel))
        except Exception as e:
            on_ui(self._set_status, f"Connection failed: {e}")

    def _set_status(self, text):
        self.status.text = text

    def _go_to_code_screen(self):
        self.status.text = "Code sent. Enter it on the next screen."
        self.manager.current = "code"

    def _go_to_menu_screen(self, title):
        self.manager.get_screen("menu").set_channel_title(title)
        self.manager.current = "menu"


# ---------------------------------------------------------
# Screen 2: login code (+ optional 2FA password)
# ---------------------------------------------------------
class CodeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=20, spacing=12)

        root.add_widget(styled_label(">> ENTER LOGIN CODE", color=FG, height=40))
        self.code = styled_input("Code from Telegram")
        self.password = styled_input("2FA password (leave empty if none)")
        self.password.password = True

        root.add_widget(self.code)
        root.add_widget(self.password)

        self.status = styled_label("", color=ACCENT, height=40)
        root.add_widget(self.status)

        submit_btn = styled_button("SIGN IN")
        submit_btn.bind(on_release=lambda *_: self.sign_in())
        root.add_widget(submit_btn)
        root.add_widget(BoxLayout())
        self.add_widget(root)

    def sign_in(self):
        code = self.code.text.strip()
        password = self.password.text.strip()
        if not code:
            self.status.text = "Enter the code first."
            return
        self.status.text = "Signing in..."
        runner.submit(self._do_sign_in(code, password))

    async def _do_sign_in(self, code, password):
        app = App.get_running_app()
        try:
            try:
                await app.client.sign_in(app.phone, code)
            except SessionPasswordNeededError:
                if not password:
                    on_ui(self._set_status, "2FA enabled: enter your password too.")
                    return
                await app.client.sign_in(password=password)

            entity = await app.client.get_entity(app.channel)
            app.entity = entity
            on_ui(self._go_to_menu, getattr(entity, "title", app.channel))
        except Exception as e:
            on_ui(self._set_status, f"Sign in failed: {e}")

    def _set_status(self, text):
        self.status.text = text

    def _go_to_menu(self, title):
        self.manager.get_screen("menu").set_channel_title(title)
        self.manager.current = "menu"


# ---------------------------------------------------------
# Screen 3: pick scope + delete
# ---------------------------------------------------------
def build_scope_options():
    options = [("Last message only", 1)]
    n = 100
    while n <= 10000:
        options.append((f"Last {n} messages", n))
        n += 100
    options.append(("ALL messages (entire history)", "ALL"))
    return options


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.options = build_scope_options()
        self.value_by_label = {label: value for label, value in self.options}

        root = BoxLayout(orientation="vertical", padding=20, spacing=12)
        self.title_label = styled_label(">> TARGET: -", color=FG, height=36)
        root.add_widget(self.title_label)

        root.add_widget(styled_label("Choose delete scope:", color=DIM, height=24))
        self.spinner = Spinner(
            text=self.options[0][0],
            values=[label for label, _ in self.options],
            size_hint_y=None,
            height=48,
            background_color=(0.05, 0.05, 0.05, 1),
            color=FG,
        )
        root.add_widget(self.spinner)

        delete_btn = styled_button("DELETE", bg=ACCENT)
        delete_btn.bind(on_release=lambda *_: self.confirm_delete())
        root.add_widget(delete_btn)

        self.status = styled_label("", color=ACCENT, height=30)
        root.add_widget(self.status)

        # scrollable log
        self.log_label = Label(
            text="", color=FG, size_hint_y=None, halign="left", valign="top",
        )
        self.log_label.bind(texture_size=self._update_log_height)
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        self.add_widget(root)

    def _update_log_height(self, instance, size):
        instance.height = size[1]
        instance.text_size = (instance.width, None)

    def set_channel_title(self, title):
        self.title_label.text = f">> TARGET: {title}"

    def log(self, line):
        self.log_label.text += line + "\n"

    def confirm_delete(self):
        label = self.spinner.text
        value = self.value_by_label[label]

        content = BoxLayout(orientation="vertical", padding=16, spacing=12)
        content.add_widget(Label(
            text=f"Delete: {label}\nThis cannot be undone.",
            color=ACCENT,
        ))
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=10)
        yes_btn = styled_button("YES, DELETE", bg=ACCENT)
        no_btn = styled_button("CANCEL", bg=DIM)
        btn_row.add_widget(yes_btn)
        btn_row.add_widget(no_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title="Are you sure you want to delete?",
            content=content,
            size_hint=(0.85, 0.4),
            auto_dismiss=False,
        )
        yes_btn.bind(on_release=lambda *_: (popup.dismiss(), self.start_delete(value, label)))
        no_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def start_delete(self, value, label):
        self.status.text = f"Deleting: {label} ..."
        self.log_label.text = ""
        runner.submit(self._do_delete(value))

    async def _do_delete(self, value):
        app = App.get_running_app()
        deleted = 0
        failed = 0
        limit = None if value == "ALL" else value
        try:
            async for message in app.client.iter_messages(app.entity, limit=limit):
                try:
                    await message.delete()
                    deleted += 1
                    if deleted % 25 == 0:
                        on_ui(self.log, f"[+] Deleted so far: {deleted}")
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed += 1
                    on_ui(self.log, f"[!] Failed message {message.id}: {e}")
            on_ui(self._finish, deleted, failed)
        except Exception as e:
            on_ui(self._finish_error, str(e))

    def _finish(self, deleted, failed):
        self.status.text = f"Done. Deleted: {deleted}  Failed: {failed}"

    def _finish_error(self, err):
        self.status.text = f"Error: {err}"


# ---------------------------------------------------------
# App
# ---------------------------------------------------------
class TGWiperApp(App):
    api_id = None
    api_hash = None
    phone = None
    channel = None
    client = None
    entity = None

    def build(self):
        self.title = "TG Wiper"
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(CodeScreen(name="code"))
        sm.add_widget(MenuScreen(name="menu"))
        return sm


if __name__ == "__main__":
    TGWiperApp().run()
