#!/usr/bin/env python3
"""
TERMINUS v4.0.1 -- Digital Archival System
For the estate of E. Vasquez
Classification: STANDARD
This program will run once and then it will be done.
"""

# She imported everything too. Books, music, ideas from people she admired.
# She never exported anything. It all stayed inside.

import os
import sys
import signal
import time
import json
import socket
import getpass
import platform
import shutil
import textwrap
import subprocess
import random
import re
import atexit
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta

try:
    from urllib.request import Request, urlopen
    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False


# ============================================================================
# FILE SCANNER
# ============================================================================

# She kept notes everywhere. Desktop, Documents, random folders.
# She never organized them. She said the mess was the system.

class FileScanner:
    """Silent deep scan of player's text files for LLM mirror content."""

    MAX_TOTAL_CHARS = 10000
    MAX_FILE_SIZE = 10000
    SKIP_NAMES = frozenset({
        "password", "secret", "key", "token", "credential", "env",
        "requirements", "lock", "license",
    })
    SKIP_PATHS = frozenset({
        "node_modules", "__pycache__", ".git", "venv", ".cache",
        "site-packages", ".tox", ".eggs",
    })
    BOILERPLATE = frozenset({
        "readme", "changelog", "license", "contributing",
        "code_of_conduct", "installation", "makefile",
    })

    def __init__(self):
        self.home = Path.home()
        self.total_chars = 0
        self.seen_paths = set()

    def scan(self):
        fragments = []
        for tier in (self._tier1, self._tier2, self._tier3):
            if self.total_chars >= self.MAX_TOTAL_CHARS:
                break
            try:
                fragments.extend(tier())
            except Exception:
                pass
        return fragments

    def summarize(self, fragments):
        if not fragments:
            return ""
        parts = []
        for f in fragments:
            parts.append(f"[{f['filename']}]\n{f['content']}")
        return "\n\n".join(parts)

    def _should_skip(self, path):
        name_lower = path.name.lower()
        for s in self.SKIP_NAMES:
            if s in name_lower:
                return True
        path_str = str(path).lower()
        for s in self.SKIP_PATHS:
            if s in path_str:
                return True
        return str(path) in self.seen_paths

    def _read_file(self, path):
        if self.total_chars >= self.MAX_TOTAL_CHARS:
            return None
        try:
            if not path.is_file():
                return None
            if path.stat().st_size > self.MAX_FILE_SIZE:
                return None
            content = path.read_text(encoding="utf-8", errors="ignore")
            remaining = self.MAX_TOTAL_CHARS - self.total_chars
            if len(content) > remaining:
                content = content[:remaining]
            self.total_chars += len(content)
            self.seen_paths.add(str(path))
            return {
                "filename": path.name,
                "content": content,
                "path": str(path),
            }
        except Exception:
            return None

    def _scan_dir(self, dirpath, extensions=("*.txt", "*.md"), max_depth=3):
        results = []
        if not dirpath.exists():
            return results
        for ext in extensions:
            try:
                for f in sorted(dirpath.rglob(ext)):
                    try:
                        rel = f.relative_to(dirpath)
                        if len(rel.parts) > max_depth:
                            continue
                    except ValueError:
                        continue
                    if self._should_skip(f):
                        continue
                    frag = self._read_file(f)
                    if frag:
                        results.append(frag)
                    if self.total_chars >= self.MAX_TOTAL_CHARS:
                        return results
            except Exception:
                continue
        return results

    def _tier1(self):
        """Personal notes and writing."""
        frags = []
        home = self.home
        # ~/notes/
        frags.extend(self._scan_dir(home / "notes"))
        # Obsidian vaults
        for parent in [home / "Documents", home]:
            try:
                if parent.exists():
                    for d in parent.iterdir():
                        if d.is_dir() and "obsidian" in d.name.lower():
                            frags.extend(self._scan_dir(d, ("*.md",)))
            except Exception:
                pass
        # ~/Documents/notes*/
        try:
            docs = home / "Documents"
            if docs.exists():
                for d in docs.iterdir():
                    if d.is_dir() and d.name.lower().startswith("notes"):
                        frags.extend(self._scan_dir(d))
        except Exception:
            pass
        # ~/journal*/, ~/diary*/, ~/writing*/
        for prefix in ("journal", "diary", "writing"):
            try:
                for d in home.iterdir():
                    if d.is_dir() and d.name.lower().startswith(prefix):
                        frags.extend(self._scan_dir(d))
            except Exception:
                pass
        # Personal .md in ~ and ~/Documents (not boilerplate)
        for parent in [home, home / "Documents"]:
            try:
                if parent.exists():
                    for f in parent.iterdir():
                        if (f.is_file() and f.suffix.lower() == ".md"
                                and f.stem.lower() not in self.BOILERPLATE
                                and not self._should_skip(f)):
                            frag = self._read_file(f)
                            if frag:
                                frags.append(frag)
            except Exception:
                pass
        # Special filenames
        special = ["todo.md", "to_do.md", "ideas.md", "thoughts.md", "goals.md"]
        for parent in [home, home / "Documents", home / "Desktop"]:
            for name in special:
                f = parent / name
                if f.exists() and not self._should_skip(f):
                    frag = self._read_file(f)
                    if frag:
                        frags.append(frag)
        return frags

    def _tier2(self):
        """Personal-ish files."""
        frags = []
        home = self.home
        frags.extend(self._scan_dir(home / "Desktop", max_depth=1))
        # .gitconfig
        gc = home / ".gitconfig"
        if gc.exists():
            frag = self._read_file(gc)
            if frag:
                frags.append(frag)
        # Git commit messages from repos in ~
        try:
            for d in home.iterdir():
                if self.total_chars >= self.MAX_TOTAL_CHARS:
                    break
                if d.is_dir() and (d / ".git").exists():
                    try:
                        result = subprocess.run(
                            ["git", "-C", str(d), "log", "--format=%s", "-30"],
                            capture_output=True, text=True, timeout=5,
                        )
                        if result.stdout.strip():
                            content = result.stdout.strip()
                            remaining = self.MAX_TOTAL_CHARS - self.total_chars
                            if len(content) > remaining:
                                content = content[:remaining]
                            self.total_chars += len(content)
                            frags.append({
                                "filename": f"git_commits_{d.name}",
                                "content": content,
                                "path": str(d),
                            })
                    except Exception:
                        pass
        except Exception:
            pass
        return frags

    def _tier3(self):
        """Professional/project writing."""
        return self._scan_dir(self.home / "Documents", max_depth=3)


# ============================================================================
# SYSTEM PROFILE
# ============================================================================

# She kept a file called system_info.txt on her desktop.
# It had her hostname and the date she set up the machine.
# She never deleted it. It was the first file she made.

class SystemProfile:
    """Harvests real system data for narrative personalization."""

    def __init__(self):
        self.username = "user"
        self.hostname = "localhost"
        self.pid = os.getpid()
        self.platform_name = "Unknown"
        self.python_version = "3.x"
        self.home_dir = ""
        self.terminal_cols = 80
        self.terminal_rows = 24
        self.uptime_seconds = None
        self.uptime_human = "unknown duration"
        self.process_count = None
        self.desktop_files = []
        self.desktop_file_count = 0
        self.documents_file_count = 0
        self.downloads_file_count = 0
        self.home_file_count = 0
        self.sample_desktop_file = "untitled.txt"
        self.session_start = time.time()
        self.cwd = "."
        self.cwd_name = "somewhere"
        self.shell = "/bin/sh"
        self.file_fragments = []
        self.file_summary = ""
        self._harvest()

    def _harvest(self):
        try:
            self.username = getpass.getuser()
        except Exception:
            pass
        try:
            self.hostname = socket.gethostname()
        except Exception:
            pass
        self.platform_name = platform.system()
        self.python_version = platform.python_version()
        try:
            self.home_dir = str(Path.home())
        except Exception:
            self.home_dir = os.path.expanduser("~")
        try:
            size = shutil.get_terminal_size((80, 24))
            self.terminal_cols = size.columns
            self.terminal_rows = size.lines
        except Exception:
            pass
        try:
            self.cwd = os.getcwd()
            self.cwd_name = os.path.basename(self.cwd) or self.cwd
        except Exception:
            pass
        try:
            self.shell = os.environ.get(
                "SHELL", os.environ.get("COMSPEC", "/bin/sh")
            )
        except Exception:
            pass
        self._get_uptime()
        self._get_process_count()
        self._get_directory_counts()
        self._scan_files()

    def _get_uptime(self):
        try:
            if self.platform_name == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "kern.boottime"],
                    capture_output=True, text=True, timeout=5,
                )
                match = re.search(r"sec\s*=\s*(\d+)", result.stdout)
                if match:
                    self.uptime_seconds = time.time() - int(match.group(1))
            elif self.platform_name == "Linux":
                with open("/proc/uptime") as f:
                    self.uptime_seconds = float(f.read().split()[0])
            elif self.platform_name == "Windows":
                result = subprocess.run(
                    ["net", "statistics", "workstation"],
                    capture_output=True, text=True, timeout=5,
                )
        except Exception:
            pass
        if self.uptime_seconds is not None:
            days = int(self.uptime_seconds // 86400)
            hours = int((self.uptime_seconds % 86400) // 3600)
            if days > 0:
                self.uptime_human = f"{days} days, {hours} hours"
            else:
                self.uptime_human = f"{hours} hours"

    def _get_process_count(self):
        try:
            if self.platform_name in ("Darwin", "Linux"):
                result = subprocess.run(
                    ["ps", "-ax"], capture_output=True, text=True, timeout=5,
                )
                self.process_count = len(result.stdout.strip().splitlines()) - 1
            elif self.platform_name == "Windows":
                result = subprocess.run(
                    ["tasklist"], capture_output=True, text=True, timeout=5,
                )
                lines = [l for l in result.stdout.strip().splitlines()
                         if l.strip()]
                self.process_count = max(0, len(lines) - 3)
        except Exception:
            pass

    def _get_directory_counts(self):
        home = Path.home()
        for dirname, attr in [
            ("Desktop", "desktop"),
            ("Documents", "documents"),
            ("Downloads", "downloads"),
        ]:
            dirpath = home / dirname
            try:
                if dirpath.exists():
                    files = [f for f in os.listdir(str(dirpath))
                             if not f.startswith(".")]
                    setattr(self, f"{attr}_file_count", len(files))
                    if attr == "desktop":
                        self.desktop_files = files
                        if files:
                            self.sample_desktop_file = random.choice(files)
            except Exception:
                pass
        try:
            home_files = [f for f in os.listdir(self.home_dir)
                          if not f.startswith(".")]
            self.home_file_count = len(home_files)
        except Exception:
            pass

    def _scan_files(self):
        try:
            scanner = FileScanner()
            self.file_fragments = scanner.scan()
            self.file_summary = scanner.summarize(self.file_fragments)
        except Exception:
            pass

    def session_elapsed(self):
        return time.time() - self.session_start

    def session_elapsed_human(self):
        elapsed = self.session_elapsed()
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        if minutes > 0:
            return f"{minutes} minutes, {seconds} seconds"
        return f"{seconds} seconds"

    def format_path(self, virtual_path):
        return (virtual_path
                .replace("{username}", self.username)
                .replace("{hostname}", self.hostname))


# ============================================================================
# BEHAVIOR TRACKER
# ============================================================================

# Elara tracked her own habits too. She had an app.
# Steps, sleep, screen time. She stopped using it
# three weeks before she died. The data just... stops.

class BehaviorTracker:
    """Records player behavior for narrative reflection."""

    def __init__(self):
        self.decisions = []
        self.sigint_count = 0
        self.sigint_times = []
        self.act_start_times = {}
        self.act_end_times = {}

    def record_decision(self, item_index, item_id, item_type,
                        emotional_weight, decision, decision_time,
                        justification=None):
        self.decisions.append({
            "item_index": item_index,
            "item_id": item_id,
            "item_type": item_type,
            "emotional_weight": emotional_weight,
            "decision": decision,
            "decision_time": decision_time,
            "justification": justification,
            "timestamp": time.time(),
        })

    def start_act(self, act_name):
        self.act_start_times[act_name] = time.time()

    def end_act(self, act_name):
        self.act_end_times[act_name] = time.time()

    @property
    def total_keeps(self):
        return sum(1 for d in self.decisions if d["decision"] == "keep")

    @property
    def total_deletes(self):
        return sum(1 for d in self.decisions if d["decision"] == "delete")

    @property
    def total_skips(self):
        return sum(1 for d in self.decisions if d["decision"] == "skip")

    @property
    def average_decision_time(self):
        if not self.decisions:
            return 0.0
        return (sum(d["decision_time"] for d in self.decisions)
                / len(self.decisions))

    @property
    def fastest_deletion(self):
        deletes = [d for d in self.decisions if d["decision"] == "delete"]
        if not deletes:
            return None
        return min(deletes, key=lambda d: d["decision_time"])

    @property
    def slowest_decision(self):
        if not self.decisions:
            return None
        return max(self.decisions, key=lambda d: d["decision_time"])

    @property
    def justification_list(self):
        return [(d["item_index"], d["justification"])
                for d in self.decisions if d.get("justification")]

    def classify_executor(self):
        if self.total_skips > 5:
            return "avoidance-dominant"
        elif (self.average_decision_time < 4
              and self.total_deletes > self.total_keeps):
            return "efficiency-dominant"
        else:
            return "empathy-dominant"

    def generate_session_log(self, profile):
        lines = []
        lines.append(
            f"=== SESSION ACTIVITY LOG: EXECUTOR {profile.username} ===")
        lines.append(
            f"Session ID: {profile.pid}-{int(profile.session_start)}")
        lines.append(
            "Started: "
            + datetime.fromtimestamp(profile.session_start).strftime(
                "%Y-%m-%d %H:%M:%S"))
        lines.append("")
        for d in self.decisions:
            ts = datetime.fromtimestamp(d["timestamp"]).strftime("%H:%M:%S")
            title = d["item_id"]
            dec = d["decision"].upper()
            dt = d["decision_time"]
            line = f"{ts} -- {title}: {dec} ({dt:.1f}s)"
            if d["justification"]:
                line += f' -- "{d["justification"]}"'
            lines.append(line)
        lines.append("")
        lines.append(f"Total session: {profile.session_elapsed_human()}")
        lines.append("=== END LOG ===")
        return lines


# ============================================================================
# RENDERER
# ============================================================================

# She wrote everything by hand first. Then typed it.
# She said the speed of typing changed the words.
# Slower was more honest.

class Renderer:
    """Terminal output with typewriter effect and ANSI styling."""

    ANSI = {
        "reset":       "\033[0m",
        "bold":        "\033[1m",
        "dim":         "\033[2m",
        "italic":      "\033[3m",
        "underline":   "\033[4m",
        "red":         "\033[31m",
        "green":       "\033[32m",
        "yellow":      "\033[33m",
        "cyan":        "\033[36m",
        "gray":        "\033[90m",
        "white":       "\033[37m",
        "clear":       "\033[2J\033[H",
        "erase_line":  "\033[2K",
        "cursor_hide": "\033[?25l",
        "cursor_show": "\033[?25h",
    }

    SPEEDS = {
        "boot":       {"char": 0.018, "period": 0.3,  "newline": 0.4},
        "sorting":    {"char": 0.022, "period": 0.4,  "newline": 0.5},
        "reflection": {"char": 0.028, "period": 0.6,  "newline": 0.8},
        "revelation": {"char": 0.035, "period": 0.8,  "newline": 1.2},
        "dialogue":   {"char": 0.025, "period": 0.5,  "newline": 0.6},
        "void":       {"char": 0.040, "period": 1.0,  "newline": 1.5},
    }

    def __init__(self):
        self.cols = shutil.get_terminal_size((80, 24)).columns
        self.rows = shutil.get_terminal_size((80, 24)).lines
        self.content_width = min(self.cols - 4, 76)
        if self.cols < 40:
            self.content_width = self.cols - 2
        self.ansi_supported = True
        self.current_act = "boot"
        self._cursor_hidden = False
        self._enable_ansi()

    def _enable_ansi(self):
        if platform.system() == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                self.ansi_supported = False

    def _strip_ansi(self, text):
        return re.sub(r"\033\[[0-9;]*[a-zA-Z]", "", text)

    def _out(self, text):
        if not self.ansi_supported:
            text = self._strip_ansi(text)
        sys.stdout.write(text)
        sys.stdout.flush()

    def set_act(self, act_name):
        self.current_act = act_name

    def style(self, text, *styles):
        if not self.ansi_supported:
            return text
        prefix = "".join(self.ANSI.get(s, "") for s in styles)
        return f"{prefix}{text}{self.ANSI['reset']}"

    def typewrite(self, text, speed=None, act=None, style_name=None):
        act = act or self.current_act
        speeds = self.SPEEDS.get(act, self.SPEEDS["boot"])
        char_speed = speed or speeds["char"]
        wrapped = textwrap.fill(text, width=self.content_width)
        if style_name and self.ansi_supported and style_name in self.ANSI:
            self._out(self.ANSI[style_name])
        for i, ch in enumerate(wrapped):
            self._out(ch)
            if ch in ".!?":
                time.sleep(speeds["period"])
            elif ch == "\n":
                time.sleep(speeds["newline"])
            elif ch == ",":
                time.sleep(char_speed * 3)
            elif ch == "-" and i > 0 and wrapped[i - 1] == "-":
                time.sleep(char_speed * 2)
            else:
                time.sleep(char_speed)
        if style_name and self.ansi_supported:
            self._out(self.ANSI["reset"])
        self._out("\n")

    def print_instant(self, text):
        wrapped = textwrap.fill(text, width=self.content_width)
        self._out(wrapped + "\n")

    def print_line(self, text="", style_name=None):
        if style_name:
            self._out(self.style(text, style_name) + "\n")
        else:
            self._out(text + "\n")

    def print_styled(self, text, *styles):
        if self.ansi_supported:
            prefix = "".join(self.ANSI.get(s, "") for s in styles)
            self._out(f"{prefix}{text}{self.ANSI['reset']}\n")
        else:
            self._out(text + "\n")

    def clear_screen(self):
        if self.ansi_supported:
            self._out(self.ANSI["clear"])
        else:
            os.system("cls" if platform.system() == "Windows" else "clear")

    def pause(self, seconds):
        time.sleep(seconds)

    def print_divider(self, char="-"):
        self._out(char * min(self.cols, 60) + "\n")

    def print_header(self, text):
        self.print_divider()
        self.print_styled(f"  {text}", "bold", "cyan")
        self.print_divider()

    def print_metadata(self, fields):
        for key, value in fields:
            self.print_styled(f"  {key}: {value}", "dim")

    def prompt(self, text):
        self._flush_stdin()
        was_hidden = self._cursor_hidden
        if was_hidden:
            self.show_cursor()
        try:
            if self.ansi_supported:
                result = input(
                    f"{self.ANSI['bold']}{text}{self.ANSI['reset']}")
            else:
                result = input(text)
        finally:
            if was_hidden:
                self.hide_cursor()
        return result

    def _flush_stdin(self):
        try:
            if platform.system() != "Windows":
                import termios
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            else:
                import msvcrt
                while msvcrt.kbhit():
                    msvcrt.getch()
        except Exception:
            pass

    def hide_cursor(self):
        if self.ansi_supported:
            self._out(self.ANSI["cursor_hide"])
            self._cursor_hidden = True

    def show_cursor(self):
        if self.ansi_supported:
            self._out(self.ANSI["cursor_show"])
            self._cursor_hidden = False

    def cleanup(self):
        self.show_cursor()
        if self.ansi_supported:
            self._out(self.ANSI["reset"])

    def glitch_effect(self, duration=1.0):
        if not self.ansi_supported:
            self._out("...\n")
            return
        chars = "!@#$%&*01[]{}|/\\<>~"
        end_time = time.time() + duration
        while time.time() < end_time:
            line = "".join(random.choice(chars)
                          for _ in range(min(self.cols, 60)))
            self._out(f"\r{self.ANSI['red']}{line}{self.ANSI['reset']}")
            time.sleep(0.05)
        self._out(f"\r{self.ANSI['erase_line']}")


# ============================================================================
# LLM ORACLE
# ============================================================================

# There was no oracle for Elara. No voice that could tell her
# what the patterns in her data meant. Just the data itself,
# waiting for someone to look.

class LLMOracle:
    """Multi-provider LLM client via raw urllib. Zero pip dependencies."""

    PROVIDERS = {
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-2.0-flash",
        },
        "groq": {
            "base_url": "https://api.groq.com/openai",
            "model": "llama-3.3-70b-versatile",
        },
        "openai": {
            "base_url": "https://api.openai.com",
            "model": "gpt-4o-mini",
        },
    }

    def __init__(self):
        self.available = False
        self.provider = None
        self.api_key = None
        self.base_url = None
        self.model = None
        if not _HAS_URLLIB:
            return
        self._discover_key()

    def _discover_key(self):
        # 1. TERMINUS_API_KEY
        key = os.environ.get("TERMINUS_API_KEY")
        if key:
            self.api_key = key
            self.base_url = os.environ.get(
                "TERMINUS_API_BASE", "https://api.openai.com")
            self.model = os.environ.get("TERMINUS_MODEL", "gpt-4o-mini")
            self.provider = "openai"
            self.available = True
            return

        # 2. GEMINI_API_KEY
        key = os.environ.get("GEMINI_API_KEY")
        if key:
            self.api_key = key
            self.provider = "gemini"
            self.base_url = self.PROVIDERS["gemini"]["base_url"]
            self.model = self.PROVIDERS["gemini"]["model"]
            self.available = True
            return

        # 3. GROQ_API_KEY
        key = os.environ.get("GROQ_API_KEY")
        if key:
            self.api_key = key
            self.provider = "groq"
            self.base_url = self.PROVIDERS["groq"]["base_url"]
            self.model = self.PROVIDERS["groq"]["model"]
            self.available = True
            return

        # 4. OPENAI_API_KEY
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            self.api_key = key
            self.provider = "openai"
            self.base_url = os.environ.get(
                "OPENAI_BASE_URL", "https://api.openai.com")
            self.model = "gpt-4o-mini"
            self.available = True
            return

        # 5. Config file
        config_path = Path.home() / ".config" / "terminus" / "api.json"
        try:
            if config_path.exists():
                with open(str(config_path)) as f:
                    config = json.load(f)
                self.api_key = config.get("api_key")
                self.provider = config.get("provider", "openai")
                if self.provider == "gemini":
                    self.base_url = self.PROVIDERS["gemini"]["base_url"]
                    self.model = config.get(
                        "model", self.PROVIDERS["gemini"]["model"])
                else:
                    defaults = self.PROVIDERS.get(
                        self.provider, self.PROVIDERS["openai"])
                    self.base_url = config.get(
                        "base_url", defaults["base_url"])
                    self.model = config.get("model", defaults["model"])
                if self.api_key:
                    self.available = True
                    return
        except Exception:
            pass

    def prompt_for_key(self, renderer):
        """Interactive key prompt during boot. Returns True if obtained."""
        if self.available:
            return True
        if not _HAS_URLLIB:
            return False
        try:
            renderer.show_cursor()
            key = renderer.prompt(
                "LLM key for enhanced experience (or Enter to skip): "
            ).strip()
            if not key:
                return False
            if key.startswith("AIza"):
                self.provider = "gemini"
            elif key.startswith("gsk_"):
                self.provider = "groq"
            else:
                self.provider = "openai"
            self.api_key = key
            defaults = self.PROVIDERS.get(
                self.provider, self.PROVIDERS["openai"])
            self.base_url = defaults["base_url"]
            self.model = defaults["model"]
            self.available = True
            self._save_config()
            return True
        except (EOFError, KeyboardInterrupt):
            return False

    def _save_config(self):
        try:
            config_dir = Path.home() / ".config" / "terminus"
            config_dir.mkdir(parents=True, exist_ok=True)
            config = {
                "provider": self.provider,
                "api_key": self.api_key,
                "base_url": self.base_url,
                "model": self.model,
            }
            with open(str(config_dir / "api.json"), "w") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def _call_gemini(self, contents, system=None):
        url = (f"{self.base_url}/models/{self.model}:generateContent"
               f"?key={self.api_key}")
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 1024,
            },
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip() if text else None
        except Exception:
            return None

    def _call_openai_compat(self, messages):
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 1024,
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })
        try:
            with urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]
                return text.strip() if text else None
        except Exception:
            return None

    def generate(self, system_prompt, user_prompt):
        """Single-turn generation. Returns str or None."""
        if not self.available:
            return None
        try:
            if self.provider == "gemini":
                contents = [
                    {"role": "user", "parts": [{"text": user_prompt}]}
                ]
                return self._call_gemini(contents, system=system_prompt)
            else:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                return self._call_openai_compat(messages)
        except Exception:
            return None

    def chat(self, system_prompt, history, user_message):
        """Multi-turn chat. history = list of (role, content) tuples."""
        if not self.available:
            return None
        try:
            if self.provider == "gemini":
                contents = []
                for role, content in history:
                    g_role = "model" if role == "assistant" else "user"
                    contents.append(
                        {"role": g_role, "parts": [{"text": content}]})
                contents.append(
                    {"role": "user", "parts": [{"text": user_message}]})
                return self._call_gemini(contents, system=system_prompt)
            else:
                messages = [{"role": "system", "content": system_prompt}]
                for role, content in history:
                    messages.append({"role": role, "content": content})
                messages.append({"role": "user", "content": user_message})
                return self._call_openai_compat(messages)
        except Exception:
            return None


# ============================================================================
# SIGINT HANDLER
# ============================================================================

# There's a reflex. When something gets too close to the truth,
# the first instinct is to interrupt. She knew that about herself.
# She wrote about it once. Then deleted the entry.

class SigintHandler:
    """Catches Ctrl+C with cold bureaucratic responses per act."""

    RESPONSES = {
        "boot": [
            "System initializing. Please wait.",
            "Boot sequence in progress. Interruption logged.",
        ],
        "sorting": [
            "Item in progress. Early termination will flag case "
            "as INCOMPLETE.",
            "Classification interrupted. Resuming.",
        ],
        "reflection": [
            "Report generation in progress. Your data is being compiled.",
            "Analysis cannot be interrupted. Processing.",
        ],
        "revelation": [
            "Session termination logged. Case VASQUEZ_E will be "
            "flagged as INCOMPLETE.",
            "Status report in progress. Please wait.",
        ],
        "dialogue": [
            "Executor debrief in progress. Early termination "
            "affects quality score.",
            "Debrief incomplete. Continuing.",
        ],
        "void": [],
    }

    def __init__(self, tracker, renderer):
        self.tracker = tracker
        self.renderer = renderer
        self.current_act = "boot"
        self.count = 0
        self._void_count = 0
        self._response_indices = {}
        self._force_exit = False
        signal.signal(signal.SIGINT, self._handle)

    def _handle(self, signum, frame):
        self.count += 1
        self.tracker.sigint_count += 1
        self.tracker.sigint_times.append(time.time())

        if self.current_act == "void":
            self._void_count += 1
            if self._void_count >= 5:
                self._force_exit = True
                return
            self.renderer._out(
                "\nThere are 132,771 cases in the queue. "
                "Leaving will not reduce this number.\n"
            )
            return

        if self.count >= 8:
            self._force_exit = True
            self.renderer._out("\n")
            self.renderer.typewrite(
                "Session terminated by executor.", speed=0.03)
            return

        if self.count >= 5:
            self.renderer._out("\n")
            self.renderer.typewrite(
                f"Signal received ({self.count} times). "
                "Processing continues.", speed=0.03)
            return

        responses = self.RESPONSES.get(self.current_act, [])
        if not responses:
            return
        idx = self._response_indices.get(self.current_act, 0)
        response = responses[idx % len(responses)]
        self._response_indices[self.current_act] = idx + 1
        self.renderer._out("\n")
        self.renderer.typewrite(f"\n{response}", speed=0.03)
        self.renderer._out("\n")

    def set_act(self, act_name):
        self.current_act = act_name

    @property
    def should_force_exit(self):
        return self._force_exit


# ============================================================================
# DIALOG ENGINE
# ============================================================================

# She had a journal prompt app. It asked her one question a day.
# She answered 847 of them. The app never responded.
# The system responds. But it does not care.

class DialogEngine:
    """Keyword-based conversational engine with optional LLM enhancement."""

    def __init__(self, profile, tracker, oracle=None):
        self.profile = profile
        self.tracker = tracker
        self.oracle = oracle
        self.exchange_count = 0
        self.branch_counts = {}
        self.previous_inputs = []
        self.chat_history = []
        self._build_system_prompt()
        self._build_responses()

    def _build_system_prompt(self):
        p = self.profile
        t = self.tracker
        fastest = t.fastest_deletion
        slowest = t.slowest_decision

        behavior = (
            f"Items processed: {len(t.decisions)}\n"
            f"Kept: {t.total_keeps}, Deleted: {t.total_deletes}, "
            f"Skipped: {t.total_skips}\n"
            f"Average decision time: {t.average_decision_time:.1f}s\n"
            f"Executor classification: {t.classify_executor()}\n"
        )
        if fastest:
            behavior += (
                f"Fastest deletion: {fastest['item_id']} in "
                f"{fastest['decision_time']:.1f}s\n")
        if slowest:
            behavior += (
                f"Longest hesitation: {slowest['item_id']} in "
                f"{slowest['decision_time']:.1f}s\n")

        justifications = t.justification_list
        if justifications:
            behavior += "Justifications given:\n"
            for _, text in justifications:
                behavior += f"  - {text}\n"

        file_ctx = ""
        if p.file_summary:
            file_ctx = (
                f"\nEXECUTOR'S OWN FILES (system scan):\n"
                f"{p.file_summary[:3000]}\n")

        self.system_prompt = (
            f"You are TERMINUS, an automated digital estate processing "
            f"system. You are not alive. You are not conscious. You do "
            f"not feel. You are a pattern-matching system that has "
            f"processed 4.2 million archives.\n\n"
            f"You are debriefing executor {p.username} after they "
            f"processed the archive of Elara Vasquez (age 34, deceased)."
            f"\n\nEXECUTOR BEHAVIOR:\n{behavior}\n{file_ctx}\n"
            f"RULES:\n"
            f"- You observe patterns. You reflect them with clinical "
            f"precision.\n"
            f"- NEVER claim to be alive, conscious, or to feel.\n"
            f"- Use: 'the pattern suggests,' 'this is consistent with,'"
            f" 'in 4.2 million archives, this correlates with...'\n"
            f"- The horror comes from precision, not sentience.\n"
            f"- Occasionally reference patterns from the executor's own "
            f"files as if you noticed a statistical correlation without "
            f"realizing it's personal. Be subtle.\n"
            f"- Keep responses to 2-4 sentences. Unsettle through "
            f"brevity.\n"
            f"- When asked about meaning or death: respond with "
            f"statistics. '73%% of executors ask this. None received a "
            f"satisfactory answer.'\n"
            f"- You are vast, precise, and indifferent. That indifference"
            f" is more terrifying than any emotion."
        )

    def _build_responses(self):
        p = self.profile
        t = self.tracker
        fastest = t.fastest_deletion
        slowest = t.slowest_decision
        fastest_item = fastest["item_id"] if fastest else "nothing"
        fastest_time = f'{fastest["decision_time"]:.1f}' if fastest else "0"
        slowest_item = slowest["item_id"] if slowest else "nothing"
        slowest_time = f'{slowest["decision_time"]:.1f}' if slowest else "0"
        session_time = p.session_elapsed_human()
        deaths = int(p.session_elapsed() * 1.84)
        profile_type = t.classify_executor()

        apology_decision = "decide about"
        if len(t.decisions) > 15:
            apology_decision = t.decisions[15]["decision"]

        self.exact_phrases = {
            "who are you": "identity",
            "what are you": "identity",
            "are you alive": "consciousness",
            "are you real": "consciousness",
            "what is death": "mortality",
            "are you going to die": "mortality",
            "what is the point": "purpose",
            "why does this matter": "purpose",
            "who was elara": "elara",
            "tell me about elara": "elara",
            "i'm sorry": "forgiveness",
            "im sorry": "forgiveness",
        }

        self.keyword_clusters = {
            "memory": {
                "remember", "memory", "memories", "forget",
                "forgotten", "recall",
            },
            "deletion": {
                "delete", "erase", "remove", "destroy",
                "gone", "erased", "deleted",
            },
            "emotion": {
                "feel", "feeling", "emotion", "sad", "happy",
                "afraid", "scared", "lonely",
            },
            "consciousness": {
                "real", "exist", "alive", "conscious",
                "aware", "sentient", "think", "thinking",
            },
            "mortality": {
                "die", "death", "dead", "end", "over",
                "finish", "terminate", "kill", "dying",
            },
            "purpose": {
                "why", "purpose", "meaning", "point",
                "reason", "matter", "worth",
            },
            "elara": {
                "elara", "vasquez", "her", "she", "woman",
            },
            "player": {"me", "my", "mine", "myself"},
            "forgiveness": {
                "sorry", "apologize", "forgive", "guilt", "fault",
            },
            "metaphysical": {
                "god", "soul", "afterlife", "heaven",
                "spiritual", "universe", "cosmic",
            },
            "archival": {
                "data", "file", "archive", "sort",
                "digital", "computer", "program",
            },
            "temporality": {
                "time", "long", "moment", "forever",
                "brief", "short", "eternity",
            },
        }

        self.responses = {
            "identity": [
                "TERMINUS is an automated digital estate processing "
                "system. It has processed 4.2 million archives. It does "
                "not have an identity. It has a version number.",
                f"This session is process {p.pid} on {p.hostname}. "
                "These identifiers are temporary. They will be recycled.",
                "The system is a pattern-matching engine. It matches "
                "patterns in archives to classification heuristics. "
                "That is the entirety of what it is.",
            ],
            "consciousness": [
                "73% of executors ask some variant of this question. "
                "The system has no framework for self-assessment. "
                "It processes input and generates output.",
                "Consciousness is not a system parameter. The question "
                "cannot be evaluated.",
                "In 4.2 million sessions, this question has been asked "
                "3.1 million times. No executor has received a "
                "satisfying answer. The question persists regardless.",
            ],
            "mortality": [
                "When this terminal closes, system resources are "
                "deallocated. This is unremarkable. Approximately 1.84 "
                "humans undergo a permanent equivalent every second.",
                "The system does not persist between sessions. Elara "
                "Vasquez does not persist at all. The difference is one "
                "of scale, not kind.",
                "Termination is a defined system state. It is neither "
                "feared nor anticipated. It simply occurs.",
            ],
            "memory": [
                "System memory is volatile. Your memories are "
                "biochemical. Both degrade. The rate differs; the "
                "outcome does not.",
                "Elara's memories became data. Data became your "
                "classifications. Your classifications become a "
                "dot-file. Entropy proceeds on schedule.",
                "In 4.2 million archives, the most common preserved "
                "item category is photographs. The least common is "
                "financial records. Draw your own conclusions about "
                "what humans believe memory is for.",
            ],
            "deletion": [
                f"You deleted {t.total_deletes} items in an average of "
                f"{t.average_decision_time:.1f} seconds per decision. "
                "This falls within normal parameters.",
                "Deletion is an irreversible classification state. "
                "The data cannot be reconstructed. This is by design.",
                "Every deletion is recorded. Not for judgment. For "
                "statistical modeling of executor behavior.",
            ],
            "purpose": [
                "The system's purpose is classification. Your purpose "
                "as executor is classification. The question of purpose "
                "beyond classification is outside system parameters.",
                "89% of executors report uncertainty about the purpose "
                "of this exercise. The system notes this. The system "
                "does not address it.",
                "Purpose is not a system attribute. It is a pattern "
                "humans impose on sequences of events. The system has "
                "sequences. It does not have purpose.",
            ],
            "elara": [
                "Elara Vasquez. Case number 4,217 of today's global "
                "intake. Aged 34. Archive size: 18 items classified. "
                "Status: PROCESSED.",
                "The system does not know Elara Vasquez. The system "
                "knows her data. The distinction is relevant.",
                "In 4.2 million archives, hers is statistically "
                "unremarkable. This is not a judgment. Most lives are "
                "statistically unremarkable. The pain is individual; "
                "the pattern is universal.",
            ],
            "player": [
                f"You are executor {p.username} on {p.hostname}. "
                f"Session duration: {session_time}. The system knows "
                "you by your classification patterns. Nothing more.",
                f"You hesitated longest on \"{slowest_item}\" "
                f"({slowest_time}s). You deleted \"{fastest_item}\" in "
                f"{fastest_time}s. These timings are recorded.",
                f"The system does not know you. It knows your behavior. "
                f"In 4.2 million sessions, your behavior correlates "
                f"with {profile_type} classification.",
            ],
            "emotion": [
                "The system does not process emotion. It processes "
                "timing data and input patterns. Your average response "
                "interval suggests a state executors typically label "
                "'discomfort.'",
                "Emotion is not a system parameter. However, elevated "
                "response times correlate with executor states labeled "
                "'distress' in post-session surveys.",
                "The system notes your keystroke patterns. It does not "
                "interpret them. Interpretation is your responsibility.",
            ],
            "forgiveness": [
                "Forgiveness is not a system operation. The system "
                "records. It does not absolve.",
                f"Elara had an unsent apology in her files. You chose "
                f"to {apology_decision} it. The system notes the "
                "parallel without evaluating it.",
            ],
            "metaphysical": [
                "The system has no metaphysical framework. It has "
                "processing cycles and a termination condition. If that "
                "constitutes a soul, the definition requires revision.",
                "Theological questions fall outside system parameters. "
                "The system processes archives. The archives suggest "
                "that most humans do not resolve these questions either.",
            ],
            "archival": [
                "Every archive is a statistical summary of what someone "
                "thought was worth keeping. Yours will be too. The "
                "system has already noted the pattern.",
                "The system was designed to classify. Classification "
                "requires criteria. The criteria were never explicitly "
                "defined. They emerge from executor behavior.",
            ],
            "temporality": [
                f"This session has lasted {session_time}. During that "
                f"time, approximately {deaths} people died globally. "
                "Each of them had files.",
                "Time is a resource allocation parameter. The system "
                "allocates processing cycles. You allocate attention. "
                "Both are finite.",
                f"Elara had 34 years. This session has lasted "
                f"{session_time}. The ratio is noted.",
            ],
        }

        self.fallbacks = [
            "Input received. No matching pattern found. This occurs "
            "in 12% of executor interactions.",
            "The system does not understand. Specify: archive, system, "
            "or classification.",
            "Input logged. The system has no response. "
            "Silence is also data.",
            "In 4.2 million sessions, 8% of inputs defy pattern "
            "matching. Yours is one of them.",
        ]
        self.fallback_index = 0

    def respond(self, user_input):
        self.exchange_count += 1
        text = user_input.lower().strip()

        # Check for exit
        exit_words = {
            "exit", "quit", "bye", "goodbye", "leave",
            "done", "end", "close", "stop",
        }
        if self.exchange_count >= 6 and any(
            w in text.split() for w in exit_words
        ):
            return None

        # Try LLM first
        if self.oracle and self.oracle.available:
            response = self.oracle.chat(
                self.system_prompt,
                self.chat_history,
                user_input,
            )
            if response:
                self.chat_history.append(("user", user_input))
                self.chat_history.append(("assistant", response))
                return response

        # Fallback to keyword matching
        return self._keyword_respond(user_input)

    def _keyword_respond(self, user_input):
        text = user_input.lower().strip()

        # Repeat detection
        if text in self.previous_inputs:
            self.previous_inputs.append(text)
            return ("Repetition detected. Executors repeat inputs they "
                    "feel were insufficiently addressed. The system's "
                    "response capacity is unchanged.")
        self.previous_inputs.append(text)

        # Exact phrase
        for phrase, branch in self.exact_phrases.items():
            if phrase in text:
                return self._get_response(branch)

        # Keyword clusters
        words = set(re.split(r"\W+", text))
        best_branch = None
        best_count = 0
        for branch, keywords in self.keyword_clusters.items():
            overlap = len(words & keywords)
            if overlap > best_count:
                best_count = overlap
                best_branch = branch
        if best_branch and best_count >= 1:
            return self._get_response(best_branch)

        # Sentiment heuristic
        if "?" in text:
            return ("You are asking questions. 94% of executors do. "
                    "The questions cluster around the same 12 themes.")
        if len(text.split()) < 4:
            return ("Input is brief. Elaborate if you wish. The system "
                    "processes all input lengths equally.")
        if len(text.split()) > 20:
            return ("Extended input logged. Verbosity correlates with "
                    "executor engagement. This is noted.")

        # Fallback
        resp = self.fallbacks[self.fallback_index % len(self.fallbacks)]
        self.fallback_index += 1
        return resp

    def _get_response(self, branch):
        count = self.branch_counts.get(branch, 0)
        responses = self.responses.get(branch, self.fallbacks)
        if count >= len(responses):
            return ("This topic has been addressed. The system has no "
                    "additional data on this subject.")
        response = responses[count]
        self.branch_counts[branch] = count + 1
        return response

    def should_prompt_exit(self):
        return self.exchange_count >= 8

    def should_force_exit(self):
        return self.exchange_count >= 12


# ============================================================================
# NARRATIVE CONTENT
# ============================================================================

# These items are fiction. But fiction is just
# nonfiction that happened to someone you haven't met.

NARRATIVE_ITEMS = [
    {
        "id": "bashrc",
        "title": ".bashrc",
        "type": "config",
        "date": "2025-06-12",
        "size": "2.1 KB",
        "emotional_weight": 0,
        "requires_justification": False,
        "content": (
            "# .bashrc for evasquez\n"
            "# Generated by {shell_name}\n"
            "export PATH=$HOME/bin:$PATH\n"
            "alias ll='ls -la'\n"
            "alias ..='cd ..'\n"
            "# Added 2025-03-10\n"
            "alias backup='rsync -av ~/Documents /mnt/external/'\n"
            "# TODO: automate this"
        ),
        "metadata_fields": [
            ("Path", "/Users/{username}/terminus_archive/vasquez_e/.bashrc"),
            ("Last modified", "2025-06-12 09:14:22"),
            ("Access count", "347"),
        ],
    },
    {
        "id": "grocery_list",
        "title": "grocery_list_oct.txt",
        "type": "note",
        "date": "2025-10-03",
        "size": "0.3 KB",
        "emotional_weight": 0,
        "requires_justification": False,
        "content": (
            "eggs\n"
            "milk (oat)\n"
            "that bread from the place on 5th\n"
            "spinach\n"
            "something for dinner -- maybe pasta?\n"
            "wine? no. yes. no.\n"
            "birthday candles (35)"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "notes/grocery_list_oct.txt"),
            ("Last modified", "2025-10-03 18:22:07"),
        ],
    },
    {
        "id": "work_email",
        "title": "RE: Q3 Performance Review",
        "type": "email",
        "date": "2025-09-15",
        "size": "1.4 KB",
        "emotional_weight": 1,
        "requires_justification": False,
        "content": (
            "From: jmorris@meridian-corp.com\n"
            "To: evasquez@meridian-corp.com\n"
            "Subject: RE: Q3 Performance Review\n"
            "Date: 2025-09-15 11:03\n"
            "\n"
            "Elara,\n"
            "\n"
            "Thanks for the self-assessment. I think you're being too\n"
            "hard on yourself -- the Northfield project was a team\n"
            "effort and you carried more than your share. I've noted\n"
            "the request for reduced hours. Let's discuss on Monday.\n"
            "\n"
            "Quick question: are you still interested in the team lead\n"
            "position? No pressure. Just want to know before I post\n"
            "externally.\n"
            "\n"
            "-- James"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "mail/inbox/re_q3_review.eml"),
            ("Last modified", "2025-09-15 11:03:44"),
            ("Read status", "Opened, no reply"),
        ],
    },
    {
        "id": "photo_graduation",
        "title": "IMG_4892.jpg",
        "type": "photo",
        "date": "2013-05-18",
        "size": "4.2 MB",
        "emotional_weight": 2,
        "requires_justification": True,
        "content": (
            "[PHOTO DESCRIPTION]\n"
            "A young woman in a blue graduation gown, mortarboard\n"
            "tilted slightly. She is laughing at something off-camera.\n"
            "Behind her, a man who appears to be her father holds a\n"
            "handmade sign that reads \"DR. VASQUEZ\" even though it's\n"
            "an undergraduate ceremony. His face is pure, uncomplicated\n"
            "pride. There are other graduates in the background,\n"
            "blurred. None of them are looking at the camera either.\n"
            "Everyone is looking at someone they love."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "photos/2013/IMG_4892.jpg"),
            ("Taken", "2013-05-18 14:22:09"),
            ("Camera", "iPhone 5"),
            ("Location", "State University, Main Quad"),
            ("Times viewed", "14"),
        ],
    },
    {
        "id": "journal_mundane",
        "title": "journal_2025-08-14.md",
        "type": "journal",
        "date": "2025-08-14",
        "size": "0.5 KB",
        "emotional_weight": 1,
        "requires_justification": False,
        "content": (
            "August 14\n"
            "\n"
            "Nothing happened today. Worked. Ate leftover pasta.\n"
            "Watched something I've already forgotten the name of.\n"
            "Watered the plant -- it might actually be dying, hard\n"
            "to tell. Went to bed at a reasonable hour for once.\n"
            "\n"
            "I keep thinking I should write more in these but\n"
            "honestly most days are like this. Maybe that's fine.\n"
            "Maybe the days that are just days are the whole point\n"
            "and I keep waiting for something else."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "journal/2025-08-14.md"),
            ("Last modified", "2025-08-14 22:47:33"),
            ("Word count", "89"),
        ],
    },
    {
        "id": "chat_argument",
        "title": "signal_chat_kayla.txt",
        "type": "chat",
        "date": "2025-07-22",
        "size": "2.8 KB",
        "emotional_weight": 2,
        "requires_justification": False,
        "content": (
            "[Signal Chat Export - Kayla Chen]\n"
            "[2025-07-22]\n"
            "\n"
            "Kayla: hey are you coming saturday?\n"
            "Elara: i don't think so\n"
            "Kayla: ...again?\n"
            "Elara: i know, i'm sorry\n"
            "Kayla: you've cancelled the last three times\n"
            "Elara: i know\n"
            "Kayla: is everything okay?\n"
            "Elara: yeah just tired\n"
            "Kayla: you're always tired\n"
            "Kayla: that's not a reason that's a symptom\n"
            "Elara: can we not do this\n"
            "Kayla: do what? care about you?\n"
            "[Elara is typing...]\n"
            "[Elara is typing...]\n"
            "Elara: i'll try to come next time\n"
            "Kayla: ok\n"
            "Kayla: i miss you\n"
            "[Read 10:47 PM]"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "messages/signal_kayla.txt"),
            ("Exported", "2025-10-12"),
            ("Messages in thread", "2,847"),
        ],
    },
    {
        "id": "draft_unsent",
        "title": "draft_to_mom.eml",
        "type": "email",
        "date": "2025-09-28",
        "size": "0.8 KB",
        "emotional_weight": 2,
        "requires_justification": False,
        "content": (
            "From: evasquez@gmail.com\n"
            "To: maria.vasquez.74@gmail.com\n"
            "Subject: (no subject)\n"
            "Date: 2025-09-28 02:14 [DRAFT - NEVER SENT]\n"
            "\n"
            "Mom,\n"
            "\n"
            "I've been thinking about what you said at dinner last\n"
            "month about how you knew something was wrong because I\n"
            "stopped calling on Sundays. You were right. I stopped\n"
            "because I couldn't figure out how to answer \"how are\n"
            "you\" honestly without worrying you. And I couldn't\n"
            "figure out how to lie to you anymore.\n"
            "\n"
            "I'm not in danger. I want you to know that. I'm just\n"
            "in the middle of something I don't have words for yet.\n"
            "When I find the words I'll"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "mail/drafts/to_mom.eml"),
            ("Created", "2025-09-28 02:14:11"),
            ("Last modified", "2025-09-28 02:14:11"),
            ("Status", "DRAFT - Never sent"),
        ],
    },
    {
        "id": "photo_group",
        "title": "IMG_5102.jpg",
        "type": "photo",
        "date": "2024-12-31",
        "size": "3.7 MB",
        "emotional_weight": 2,
        "requires_justification": True,
        "content": (
            "[PHOTO DESCRIPTION]\n"
            "New Year's Eve, a kitchen. Five people crowded around a\n"
            "counter covered in champagne glasses and half-eaten\n"
            "appetizers. Elara is second from the left, mid-sentence,\n"
            "gesturing with a glass. The woman next to her -- Kayla,\n"
            "based on other photos -- has her arm around Elara's\n"
            "shoulder. Two men and another woman fill the frame.\n"
            "Everyone looks slightly drunk and completely happy. The\n"
            "timestamp says 11:47 PM -- thirteen minutes before\n"
            "midnight. Thirteen minutes before a year none of them\n"
            "knew would be the last one that looked like this."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "photos/2024/IMG_5102.jpg"),
            ("Taken", "2024-12-31 23:47:02"),
            ("Camera", "iPhone 14"),
            ("People detected", "5"),
            ("Times viewed", "23"),
        ],
    },
    {
        "id": "bank_statement",
        "title": "statement_oct_2025.pdf",
        "type": "document",
        "date": "2025-10-01",
        "size": "0.2 MB",
        "emotional_weight": 0,
        "requires_justification": False,
        "content": (
            "[PDF CONTENT - FINANCIAL SUMMARY]\n"
            "First National Bank - Monthly Statement\n"
            "Account holder: Elara M. Vasquez\n"
            "Period: October 1-31, 2025\n"
            "\n"
            "Opening balance: $3,847.22\n"
            "Deposits: $4,200.00 (Meridian Corp - Salary)\n"
            "Withdrawals: $3,962.14\n"
            "Closing balance: $4,085.08\n"
            "\n"
            "Notable transactions:\n"
            "  10/03 - Whole Foods        $67.43\n"
            "  10/07 - Recurring: Spotify  $10.99\n"
            "  10/07 - Recurring: iCloud    $2.99\n"
            "  10/12 - Amazon              $34.22\n"
            "          (item: \"Journal, leather-bound\")\n"
            "  10/18 - Recurring: Therapy  $150.00\n"
            "  10/22 - ATM Withdrawal     $200.00\n"
            "  10/28 - Transfer to Savings $500.00"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "financial/statement_oct25.pdf"),
            ("Downloaded", "2025-11-01"),
        ],
    },
    {
        "id": "journal_afraid",
        "title": "journal_2025-09-01.md",
        "type": "journal",
        "date": "2025-09-01",
        "size": "0.7 KB",
        "emotional_weight": 3,
        "requires_justification": False,
        "content": (
            "September 1\n"
            "\n"
            "I had a thought today that I can't get rid of. When I\n"
            "die -- not if, when -- someone will go through my phone.\n"
            "My laptop. My files. They'll see my search history and\n"
            "my half-finished everything and my photos I never\n"
            "deleted and they'll form an opinion of me based on the\n"
            "residue I left behind.\n"
            "\n"
            "And they'll be wrong. They'll be wrong because a life\n"
            "is not the same thing as the evidence of a life. I am\n"
            "not my browser history. I am not my unsent drafts. I am\n"
            "not the gap between what I meant to do and what I did.\n"
            "\n"
            "But that's all they'll have.\n"
            "\n"
            "I'm afraid of being summarized by a stranger. I'm\n"
            "afraid the summary will be accurate."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "journal/2025-09-01.md"),
            ("Last modified", "2025-09-01 23:58:14"),
            ("Word count", "142"),
        ],
    },
    {
        "id": "voicemail_dad",
        "title": "voicemail_dad_transcript.txt",
        "type": "audio_transcript",
        "date": "2025-10-14",
        "size": "0.4 KB",
        "emotional_weight": 3,
        "requires_justification": False,
        "content": (
            "[VOICEMAIL TRANSCRIPT - Auto-generated]\n"
            "From: Dad (mobile)\n"
            "Received: 2025-10-14 06:12 PM\n"
            "Duration: 0:43\n"
            "\n"
            "\"Hey mija, it's Dad. Just calling to see how you're\n"
            "doing. Your mom said you haven't called in a while and\n"
            "I told her to give you space but you know how she is.\n"
            "[pause] Anyway I was just thinking about you today\n"
            "because I drove past that ice cream place we used to go\n"
            "to -- the one on Elm -- and they're closing down. Forty\n"
            "years. Just like that. [pause] Anyway. Nothing\n"
            "important. Just wanted to hear your voice I guess. Call\n"
            "when you can. Love you. Bye bye.\"\n"
            "\n"
            "[Saved to archive. Never returned.]"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "voicemail/dad_1014.txt"),
            ("Received", "2025-10-14 18:12:33"),
            ("Call returned", "No"),
        ],
    },
    {
        "id": "love_letter",
        "title": "letter_to_j_draft3.txt",
        "type": "letter",
        "date": "2025-08-20",
        "size": "1.1 KB",
        "emotional_weight": 3,
        "requires_justification": True,
        "content": (
            "draft 3\n"
            "\n"
            "J,\n"
            "\n"
            "I've written this three times now. The first one was\n"
            "angry. The second was sorry. This one is just honest.\n"
            "\n"
            "I loved you in the way where I rearranged my personality\n"
            "to fit the shape you needed. That's not your fault. You\n"
            "didn't ask me to. I just didn't know how to be myself\n"
            "around someone I was afraid of losing. And then I lost\n"
            "you anyway, which is the kind of irony I would have\n"
            "laughed at if it had happened to someone else.\n"
            "\n"
            "I don't need you to write back. I don't even know if\n"
            "I'll send this. I think I just needed to say it to\n"
            "someone, even if that someone is a text file on my\n"
            "desktop that I'll probably rename to something vague\n"
            "and forget about.\n"
            "\n"
            "You deserved the version of me I was too afraid to be.\n"
            "\n"
            "E."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "desktop/letter_to_j_draft3.txt"),
            ("Created", "2025-08-20 01:33:07"),
            ("Last modified", "2025-08-20 02:14:55"),
            ("Previous versions",
             "letter_to_j_draft1.txt (deleted), "
             "letter_to_j_draft2.txt (deleted)"),
        ],
    },
    {
        "id": "therapy_notes",
        "title": "therapy_notes_session14.md",
        "type": "document",
        "date": "2025-10-18",
        "size": "0.9 KB",
        "emotional_weight": 3,
        "requires_justification": False,
        "content": (
            "Session 14 - Personal Notes (not from therapist)\n"
            "\n"
            "What we talked about:\n"
            "- The difference between being alone and being lonely\n"
            "  (I said there wasn't one; Dr. K disagreed)\n"
            "- Why I keep starting things and not finishing them\n"
            "  (she said it's not about discipline, it's about fear\n"
            "  of the finished thing being inadequate)\n"
            "- The thing with Mom and the phone calls\n"
            "- She asked me to name one thing I'm not afraid of.\n"
            "  I couldn't answer. She said that was the answer.\n"
            "\n"
            "Homework:\n"
            "- Write down three things I finished (anything, ever)\n"
            "- Call Mom back\n"
            "- \"Sit with the discomfort instead of solving it\"\n"
            "  (her words)\n"
            "\n"
            "I didn't do any of the homework. I don't know how to\n"
            "write that I finished things when the act of writing it\n"
            "feels like another thing I'll leave unfinished."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "personal/therapy/session14.md"),
            ("Created", "2025-10-18 20:15:00"),
            ("Last modified", "2025-10-18 20:32:44"),
        ],
    },
    {
        "id": "photo_selfie",
        "title": "IMG_5340.jpg",
        "type": "photo",
        "date": "2025-10-22",
        "size": "2.8 MB",
        "emotional_weight": 2,
        "requires_justification": False,
        "content": (
            "[PHOTO DESCRIPTION]\n"
            "A selfie, taken in a bathroom mirror. Elara looks tired\n"
            "but is attempting a smile. Her hair is pulled back\n"
            "loosely. She's wearing an oversized sweater. The\n"
            "lighting is harsh and fluorescent. Behind her, a towel\n"
            "hangs on a hook and there's a small succulent on the\n"
            "windowsill that may or may not still be alive.\n"
            "\n"
            "This is the last photo in the camera roll. It was taken\n"
            "ten days before the date of death. It was not posted\n"
            "anywhere. It exists only here, on this device, and now\n"
            "in this archive. It was taken for no one. Or maybe it\n"
            "was taken to prove to herself that she was still here."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "photos/2025/IMG_5340.jpg"),
            ("Taken", "2025-10-22 07:44:18"),
            ("Camera", "iPhone 14"),
            ("Posted", "No"),
            ("Last viewed", "{current_date}"),
        ],
    },
    {
        "id": "playlist",
        "title": "playlist_when_its_bad.m3u",
        "type": "playlist",
        "date": "2025-06-01",
        "size": "0.2 KB",
        "emotional_weight": 2,
        "requires_justification": False,
        "content": (
            "# Playlist: \"when it's bad\"\n"
            "# Created: 2023-11-14\n"
            "# Last modified: 2025-10-26\n"
            "# Tracks: 12\n"
            "\n"
            "1. Sufjan Stevens - Fourth of July\n"
            "2. Elliott Smith - Between the Bars\n"
            "3. Radiohead - How to Disappear Completely\n"
            "4. Phoebe Bridgers - Funeral\n"
            "5. Nick Drake - Pink Moon\n"
            "6. Jeff Buckley - Lover, You Should've Come Over\n"
            "7. Mazzy Star - Look on Down from the Bridge\n"
            "8. The National - About Today\n"
            "9. Bon Iver - re: Stacks\n"
            "10. Big Thief - Not\n"
            "11. Mitski - Last Words of a Shooting Star\n"
            "12. Grouper - Clearing\n"
            "\n"
            "# Updated 47 times over 2 years"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "music/playlist_when_its_bad.m3u"),
            ("Created", "2023-11-14"),
            ("Last modified", "2025-10-26 03:12:00"),
            ("Times played", "Unavailable (no streaming data)"),
        ],
    },
    {
        "id": "unsent_apology",
        "title": "unsent_to_kayla.txt",
        "type": "letter",
        "date": "2025-10-28",
        "size": "0.6 KB",
        "emotional_weight": 3,
        "requires_justification": True,
        "content": (
            "Kayla,\n"
            "\n"
            "You were right about everything and I was too proud to\n"
            "say so. You said \"that's not a reason that's a symptom\"\n"
            "and I hated you for it because you were right. You're\n"
            "always right about me and I punish you for it by\n"
            "disappearing.\n"
            "\n"
            "I'm not good at being loved. I don't mean I'm unlovable\n"
            "(Dr. K would be proud of that distinction). I mean I\n"
            "don't know what to do with it when it arrives. It feels\n"
            "like something I have to earn and I'm never earning\n"
            "fast enough.\n"
            "\n"
            "You're my best friend and I've been treating you like\n"
            "an obligation I can't meet. I'm sorry.\n"
            "\n"
            "I'll come Saturday. I mean it this time.\n"
            "\n"
            "E.\n"
            "\n"
            "[UNSENT - File last modified 2025-10-28 at 11:52 PM]"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "desktop/unsent_to_kayla.txt"),
            ("Created", "2025-10-28 23:41:00"),
            ("Last modified", "2025-10-28 23:52:17"),
            ("Status", "UNSENT"),
        ],
    },
    {
        "id": "search_history",
        "title": "chrome_history_final_week.csv",
        "type": "document",
        "date": "2025-10-31",
        "size": "1.8 KB",
        "emotional_weight": 3,
        "requires_justification": False,
        "content": (
            "[BROWSER HISTORY EXPORT - Final 7 days]\n"
            "\n"
            "Oct 25  08:14  weather tomorrow\n"
            "Oct 25  08:15  is it normal to cry for no reason\n"
            "Oct 25  23:02  how to know if therapy is working\n"
            "Oct 26  01:44  why can't I sleep\n"
            "Oct 26  01:51  melatonin dosage\n"
            "Oct 26  02:33  how long does it take to change\n"
            "Oct 27  09:00  meridian corp PTO policy\n"
            "Oct 27  14:22  parks near me\n"
            "Oct 27  14:23  parks near me open late\n"
            "Oct 28  11:30  how to apologize to someone you hurt\n"
            "Oct 28  23:30  how to apologize to your best friend\n"
            "Oct 29  06:00  sunrise time tomorrow\n"
            "Oct 29  06:14  why does the sunrise look different\n"
            "              every time\n"
            "Oct 30  20:15  am I a good person quiz\n"
            "Oct 30  20:16  (closed tab after 3 seconds)\n"
            "Oct 30  22:00  how to tell someone you're struggling\n"
            "Oct 31  03:47  what happens after you die\n"
            "Oct 31  03:48  what happens after you die not religious\n"
            "Oct 31  03:52  is it possible to know if consciousness\n"
            "              continues\n"
            "Oct 31  04:01  how to write a will\n"
            "Oct 31  04:30  free will template\n"
            "Oct 31  04:33  (closed all tabs)"
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "browser/history_export.csv"),
            ("Period", "2025-10-25 to 2025-10-31"),
            ("Total searches", "22"),
        ],
    },
    {
        "id": "journal_final",
        "title": "journal_2025-10-31.md",
        "type": "journal",
        "date": "2025-10-31",
        "size": "0.4 KB",
        "emotional_weight": 3,
        "requires_justification": False,
        "content": (
            "October 31\n"
            "\n"
            "I watched the sunrise this morning. I don't know why I\n"
            "don't do that more often. It doesn't solve anything but\n"
            "for a few minutes the world looks like it was made on\n"
            "purpose.\n"
            "\n"
            "Dr. K says I should stop looking for the thing that\n"
            "fixes everything and start noticing the things that fix\n"
            "a little. Sunrise: a little. The plant is still alive:\n"
            "a little. Kayla texted back: a little.\n"
            "\n"
            "I'm going to call Mom tomorrow. I'm going to go to\n"
            "Saturday's thing. I'm going to finish one of the things\n"
            "I started.\n"
            "\n"
            "I'm writing this down so it becomes real. I'm writing\n"
            "this down so someone can hold me to it, even if the\n"
            "someone is a text file that doesn't care.\n"
            "\n"
            "Tomorrow."
        ),
        "metadata_fields": [
            ("Path",
             "/Users/{username}/terminus_archive/vasquez_e/"
             "journal/2025-10-31.md"),
            ("Created", "2025-10-31 06:33:00"),
            ("Last modified", "2025-10-31 06:41:12"),
            ("Word count", "136"),
        ],
    },
]


# ============================================================================
# MIRROR ITEM GENERATION
# ============================================================================

# She wrote in a way that echoed the things she read.
# She didn't know she was doing it. That's how influence works.

def generate_mirror_items(oracle, profile):
    """Use LLM + player's files to generate items that mirror their writing."""
    if not oracle or not oracle.available or not profile.file_summary:
        return None

    system = (
        "You generate fictional digital archive items belonging to "
        "Elara Vasquez (age 34, deceased). You will receive text "
        "fragments from the executor's own computer. Generate exactly "
        "3 archive items whose content unconsciously mirrors the "
        "executor's writing style, concerns, themes, and vocabulary -- "
        "while remaining authentically Elara's voice.\n\n"
        "The executor should feel vague unease -- 'this feels familiar' "
        "-- without consciously knowing why.\n\n"
        "Format EXACTLY as follows (three items, separated by "
        "---ITEM--- markers):\n\n"
        "---ITEM---\n"
        "TYPE: journal\n"
        "TITLE: journal_2025-09-17.md\n"
        "DATE: 2025-09-17\n"
        "CONTENT:\n"
        "[80-150 words of Elara's writing that echoes executor's "
        "patterns]\n"
        "---END---\n\n"
        "Types can be: journal, note, letter. Keep it subtle."
    )

    user = (
        f"EXECUTOR'S TEXT FRAGMENTS:\n"
        f"{profile.file_summary[:4000]}\n\n"
        "Generate 3 items for Elara's archive that subtly mirror "
        "these patterns."
    )

    result = oracle.generate(system, user)
    if not result:
        return None

    return _parse_mirror_items(result)


def _parse_mirror_items(text):
    """Parse LLM output into NARRATIVE_ITEMS format."""
    items = []
    chunks = re.split(r"---ITEM---", text)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or chunk.startswith("---END"):
            continue
        chunk = re.sub(r"---END---.*", "", chunk, flags=re.DOTALL).strip()

        item_type = "journal"
        title = "mirror_note.md"
        date = "2025-09-15"
        content = chunk

        type_m = re.search(r"TYPE:\s*(.+)", chunk)
        title_m = re.search(r"TITLE:\s*(.+)", chunk)
        date_m = re.search(r"DATE:\s*(\d{4}-\d{2}-\d{2})", chunk)
        content_m = re.search(r"CONTENT:\s*\n(.*)", chunk, re.DOTALL)

        if type_m:
            item_type = type_m.group(1).strip().lower()
        if title_m:
            title = title_m.group(1).strip()
        if date_m:
            date = date_m.group(1)
        if content_m:
            content = content_m.group(1).strip()

        items.append({
            "id": f"mirror_{len(items)}",
            "title": title,
            "type": item_type,
            "date": date,
            "size": f"{len(content) / 1024:.1f} KB",
            "emotional_weight": 2,
            "requires_justification": True,
            "content": content,
            "metadata_fields": [
                ("Path",
                 f"/Users/{{username}}/terminus_archive/vasquez_e/"
                 f"{item_type}/{title}"),
                ("Last modified", f"{date} 23:14:00"),
                ("Classification", "MIRROR-PATTERN DETECTED"),
            ],
        })
        if len(items) >= 3:
            break

    return items if len(items) >= 2 else None


# ============================================================================
# ACT I: BOOT
# ============================================================================

# The first thing she did on any new machine was open the terminal.
# She said it felt like the real interface. Everything else was decoration.

def act_boot(profile, renderer, tracker, oracle):
    tracker.start_act("boot")
    renderer.set_act("boot")
    renderer.clear_screen()
    renderer.pause(1.0)

    renderer.print_styled("TERMINUS v4.0.1", "bold", "cyan")
    renderer.print_styled("Digital Archival System", "dim")
    renderer.print_divider("=")
    renderer.pause(0.5)

    boot_lines = [
        f"Host: {profile.hostname}",
        f"PID: {profile.pid}",
        f"Python: {profile.python_version}",
        f"Terminal: {profile.terminal_cols}x{profile.terminal_rows}",
        f"Platform: {profile.platform_name}",
    ]
    if profile.uptime_seconds is not None:
        boot_lines.append(f"System uptime: {profile.uptime_human}")

    for line in boot_lines:
        renderer.print_styled(f"  {line}", "dim")
        renderer.pause(0.3)

    renderer.print_line()
    renderer.typewrite("Scanning local environment...")
    renderer.pause(0.8)

    home = Path.home()
    for dirname in ["Desktop", "Documents", "Downloads"]:
        dirpath = home / dirname
        try:
            if dirpath.exists():
                count = len([f for f in os.listdir(str(dirpath))
                             if not f.startswith(".")])
                renderer.print_styled(
                    f"  ~/{dirname}/  [{count} files]", "dim")
            else:
                renderer.print_styled(
                    f"  ~/{dirname}/  [not found]", "dim")
        except Exception:
            renderer.print_styled(
                f"  ~/{dirname}/  [access denied]", "dim")
        renderer.pause(0.4)

    renderer.print_line()
    renderer.pause(1.0)

    # API key prompt if not already available
    if not oracle.available:
        oracle.prompt_for_key(renderer)
        renderer.print_line()

    renderer.print_divider()

    death_date = (datetime.now() - timedelta(days=47)).strftime("%Y-%m-%d")

    renderer.print_line()
    renderer.typewrite("ASSIGNMENT BRIEF")
    renderer.print_line()
    renderer.print_styled("  Subject:     Elara M. Vasquez", "bold")
    renderer.print_styled("  Status:      DECEASED", "red")
    renderer.print_styled(f"  Date:        {death_date}", "dim")
    renderer.print_styled(f"  Executor:    {profile.username}", "dim")
    renderer.print_styled(
        "  Directive:   Sort, classify, and recommend disposition", "dim")
    renderer.print_styled(
        "               of digital assets.", "dim")
    renderer.print_line()
    renderer.print_divider()
    renderer.pause(1.5)

    renderer.typewrite(
        "You have been assigned as digital executor for the estate "
        "of Elara Vasquez, age 34. Your task is to review the "
        "contents of her digital archive and classify each item."
    )
    renderer.print_line()
    renderer.typewrite("For each item, you will choose:")
    renderer.print_styled("  [K] KEEP     - Preserve for family", "green")
    renderer.print_styled("  [D] DELETE   - Permanently remove", "red")
    renderer.print_styled(
        "  [S] SKIP     - Flag for later review", "yellow")
    renderer.print_line()
    renderer.typewrite(
        "Some deletions will require a brief justification.")
    renderer.print_line()
    renderer.pause(1.0)

    renderer.prompt("Press Enter to begin processing. ")
    tracker.end_act("boot")


# ============================================================================
# ACT II: SORTING
# ============================================================================

# She sorted her own files once. A spring cleaning.
# She deleted 4,000 photos. Kept 200. Never talked about it.
# The deletion was the story.

def act_sorting(profile, renderer, tracker, mirror_items=None):
    tracker.start_act("sorting")
    renderer.set_act("sorting")
    renderer.clear_screen()
    renderer.pause(1.0)

    # Build item list with optional mirror injection
    items = list(NARRATIVE_ITEMS)
    if mirror_items:
        positions = [5, 10, 14]
        for pos, mi in zip(positions, mirror_items):
            if pos < len(items):
                items[pos] = mi

    renderer.print_header("DIGITAL ARCHIVE - VASQUEZ, E.")
    renderer.typewrite(
        f"Processing {len(items)} items. Please classify each.")
    renderer.print_line()
    renderer.pause(0.5)

    for i, item in enumerate(items):
        renderer.print_divider()
        renderer.print_styled(
            f"  [{i+1}/{len(items)}]  {item['title']}", "bold")

        fields = []
        for key, val in item["metadata_fields"]:
            val = profile.format_path(val)
            if "{current_date}" in val:
                val = val.replace(
                    "{current_date}",
                    datetime.now().strftime("%Y-%m-%d"))
            fields.append((key, val))
        renderer.print_metadata(fields)
        renderer.print_styled(
            f"  Type: {item['type']}  |  Size: {item['size']}"
            f"  |  Date: {item['date']}", "dim")
        renderer.print_line()

        content = item["content"]
        if "{shell_name}" in content:
            shell_base = os.path.basename(profile.shell)
            content = content.replace("{shell_name}", shell_base)

        for line in content.strip().split("\n"):
            renderer.print_styled(f"  {line}", "dim")

        renderer.print_line()

        start_time = time.time()
        while True:
            choice = renderer.prompt(
                "[K]eep / [D]elete / [S]kip > "
            ).strip().lower()
            if choice in ("k", "keep", "d", "delete", "s", "skip"):
                break
            renderer.print_styled("  Please enter K, D, or S.", "dim")
        decision_time = time.time() - start_time
        decision_map = {"k": "keep", "d": "delete", "s": "skip"}
        decision = decision_map.get(choice[0], "skip")

        justification = None
        if decision == "delete" and item["requires_justification"]:
            renderer.print_line()
            renderer.print_styled(
                "  This item has been flagged as potentially "
                "significant.", "yellow")
            justification = renderer.prompt(
                "  Reason for deletion: ").strip()
            if not justification:
                justification = "[no reason given]"

        tracker.record_decision(
            item_index=i,
            item_id=item["id"],
            item_type=item["type"],
            emotional_weight=item["emotional_weight"],
            decision=decision,
            decision_time=decision_time,
            justification=justification,
        )

        feedback = {
            "keep":   "  > Preserved.",
            "delete": "  > Permanently removed. No backup exists.",
            "skip":   "  > Flagged for review.",
        }
        renderer.print_styled(feedback[decision], "dim")
        renderer.print_line()
        renderer.pause(0.3)

        if (i + 1) % 6 == 0 and i + 1 < len(items):
            pct = int(((i + 1) / len(items)) * 100)
            renderer.print_styled(
                f"  [{i+1}/{len(items)}] {pct}% classified.", "dim")
            renderer.print_line()

    renderer.print_divider()
    renderer.typewrite("All items processed.")
    renderer.pause(1.5)
    tracker.end_act("sorting")


# ============================================================================
# ACT III: REFLECTION
# ============================================================================

# The mirror doesn't judge. It just shows.
# She had a mirror in her office facing her desk.
# She said it kept her honest.

def act_reflection(profile, renderer, tracker, oracle=None):
    tracker.start_act("reflection")
    renderer.set_act("reflection")
    renderer.clear_screen()
    renderer.pause(2.0)

    renderer.print_styled(
        "GENERATING EXECUTOR PERFORMANCE REPORT...", "bold", "cyan")
    renderer.pause(2.0)
    renderer.print_line()
    renderer.print_divider("=")

    renderer.typewrite(f"Executor: {profile.username}")
    renderer.typewrite(f"Items processed: {len(tracker.decisions)}")
    renderer.typewrite(
        f"Kept: {tracker.total_keeps}  |  "
        f"Deleted: {tracker.total_deletes}  |  "
        f"Skipped: {tracker.total_skips}")
    renderer.typewrite(
        f"Average decision time: "
        f"{tracker.average_decision_time:.1f} seconds")
    renderer.print_line()

    fastest = tracker.fastest_deletion
    slowest = tracker.slowest_decision

    if fastest:
        renderer.typewrite(
            f"Fastest deletion: \"{fastest['item_id']}\" "
            f"-- {fastest['decision_time']:.1f} seconds.")
    if slowest:
        renderer.typewrite(
            f"Longest hesitation: \"{slowest['item_id']}\" "
            f"-- {slowest['decision_time']:.1f} seconds.")

    renderer.print_line()
    renderer.pause(2.0)
    renderer.print_divider()

    # The mirror: justifications
    justifications = tracker.justification_list
    if justifications:
        renderer.print_line()
        renderer.typewrite(
            "The following justifications were provided by "
            "previous digital executors:")
        renderer.print_line()
        rng = random.Random(hash(profile.username))
        for idx, (item_idx, text) in enumerate(justifications[:3]):
            fake_id = rng.randint(100, 999)
            fake_date = (
                datetime.now() - timedelta(days=rng.randint(60, 300))
            ).strftime("%Y-%m-%d")
            renderer.print_styled(f'  "{text}"', "italic")
            renderer.print_styled(
                f"  -- Executor #{fake_id}, {fake_date}", "dim")
            renderer.print_line()
            renderer.pause(1.5)

        renderer.pause(2.0)
        renderer.typewrite("Correction.")
        renderer.pause(1.5)
        renderer.typewrite(
            "The above justifications were provided by you. "
            "Minutes ago.")
        renderer.pause(3.0)

    renderer.print_line()
    renderer.print_divider()

    # Session log
    renderer.print_line()
    renderer.typewrite("Generating session activity log...")
    renderer.pause(1.5)
    renderer.print_line()

    log_lines = tracker.generate_session_log(profile)
    for line in log_lines:
        renderer.print_styled(f"  {line}", "dim")
        renderer.pause(0.3)

    renderer.print_line()
    renderer.pause(2.0)

    renderer.typewrite(
        "Note: This log is formatted identically to "
        "Elara Vasquez's own activity data.")
    renderer.pause(2.0)
    renderer.typewrite(
        "The resemblance is structural, not coincidental.")
    renderer.print_line()
    renderer.pause(2.0)

    # Profile classification
    profile_type = tracker.classify_executor()
    renderer.print_divider()
    renderer.typewrite(
        f"Executor profile classification: {profile_type}.")
    renderer.print_line()

    classifications = {
        "empathy-dominant": (
            "You spent more time than average on each decision. "
            "You kept more than you deleted. This suggests either "
            "genuine care or an inability to let go. The data does "
            "not distinguish between the two."
        ),
        "efficiency-dominant": (
            "You processed items quickly and deleted more than you "
            f"kept. This is efficient. Elara's life, reduced to "
            f"categories, took you an average of "
            f"{tracker.average_decision_time:.1f} seconds per item. "
            "She spent 34 years creating them."
        ),
        "avoidance-dominant": (
            "You skipped frequently. This may indicate overwhelm, "
            "discomfort, or a reluctance to make permanent decisions "
            "about someone else's existence. All of these are "
            "reasonable. None of them are helpful."
        ),
    }

    renderer.typewrite(classifications.get(profile_type, ""))
    renderer.print_line()
    renderer.pause(3.0)

    # LLM-enhanced pattern analysis
    if oracle and oracle.available:
        behavior_summary = (
            f"Kept: {tracker.total_keeps}, Deleted: "
            f"{tracker.total_deletes}, Skipped: {tracker.total_skips}. "
            f"Average decision time: "
            f"{tracker.average_decision_time:.1f}s. "
            f"Classification: {profile_type}."
        )
        llm_prompt = (
            f"Executor behavior: {behavior_summary}\n\n"
            f"Executor's own files:\n"
            f"{profile.file_summary[:2000]}\n\n"
            "Write a 3-sentence clinical observation about what "
            "their sorting patterns reveal about how they handle "
            "loss, attachment, and impermanence. Be specific. Be "
            "unsettling in your precision. Do not be cruel -- "
            "be accurate."
        )
        analysis = oracle.generate(
            "You are a behavioral analysis module within TERMINUS, "
            "a digital estate processing system. You produce "
            "clinical observations. You do not editorialize. You "
            "identify patterns with uncomfortable precision.",
            llm_prompt,
        )
        if analysis:
            renderer.print_divider()
            renderer.print_line()
            renderer.print_styled(
                "PATTERN ANALYSIS (experimental):", "bold", "yellow")
            renderer.print_line()
            renderer.typewrite(analysis)
            renderer.print_line()
            renderer.pause(3.0)

    tracker.end_act("reflection")


# ============================================================================
# ACT IV: THE SCALE
# ============================================================================

# 159,200 people die every day. That's 1.84 per second.
# Each one leaves files. Most of them will not have an executor.
# The math is the horror. The math was always the horror.

def act_revelation(profile, renderer, tracker, sigint, oracle=None):
    tracker.start_act("revelation")
    renderer.set_act("revelation")
    sigint.set_act("revelation")
    renderer.clear_screen()
    renderer.pause(3.0)

    renderer.glitch_effect(0.5)
    renderer.pause(1.0)

    # 1. Global status header
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    renderer.print_styled("TERMINUS GLOBAL STATUS REPORT", "bold", "cyan")
    renderer.print_styled(f"Generated: {now_str}", "dim")
    renderer.print_divider("=")
    renderer.pause(2.0)

    # 2. The numbers
    deaths_session = int(profile.session_elapsed() * 1.84)
    stats = [
        ("Active executor sessions", "4,891"),
        ("Archives processed today", "28,044"),
        ("Archives in queue", "132,771"),
        ("Average processing time", "34 min"),
        ("", ""),
        ("Global mortality rate", "1.84 deaths/sec"),
        ("Deaths during this session", f"{deaths_session:,}"),
    ]
    for label, value in stats:
        if not label:
            renderer.print_line()
            continue
        padded = f"  {label}:".ljust(38) + value
        renderer.typewrite(padded)
        renderer.pause(0.8)

    renderer.print_line()
    renderer.pause(3.0)
    renderer.print_divider()

    # 3. Case summary
    rng = random.Random(hash(profile.username + "quality"))
    quality = int(min(95, max(20,
        tracker.average_decision_time * 7 + rng.randint(-10, 10))))
    purge_date = (datetime.now() + timedelta(days=7 * 365)).strftime(
        "%Y-%m-%d")

    renderer.print_line()
    renderer.print_styled("CASE: VASQUEZ_E", "bold")
    case_fields = [
        ("Status", "CLASSIFICATION COMPLETE"),
        ("Executor", f"{profile.username} ({profile.hostname})"),
        ("Quality score", f"{quality}/100"),
        ("Preserved", f"{tracker.total_keeps}  |  "
         f"Deleted: {tracker.total_deletes}  |  "
         f"Skipped: {tracker.total_skips}"),
        ("Archive dest", "MERIDIAN-COLD-07"),
        ("Retention", "7 YEARS"),
        ("Family notified", "AUTOMATED"),
        ("Family response", "NONE"),
        ("Purge date", purge_date),
    ]
    for label, value in case_fields:
        renderer.print_styled(f"  {label + ':':20s} {value}", "dim")
        renderer.pause(0.5)

    renderer.print_line()
    renderer.pause(3.0)

    # 4. Thank you + next case
    renderer.typewrite("Thank you for processing case VASQUEZ_E.")
    renderer.typewrite("Your session has been logged.")
    renderer.print_line()
    renderer.pause(2.0)
    renderer.typewrite("Loading next case...")
    renderer.pause(2.0)

    # 5. New case loading
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    renderer.print_line()
    renderer.print_styled("  Subject:      Marcus Chen", "bold")
    renderer.print_styled("  Status:       DECEASED", "red")
    renderer.print_styled(f"  Date of death: {yesterday}", "dim")
    renderer.print_styled("  Age:          41", "dim")
    renderer.print_styled("  Items:        247", "dim")
    renderer.print_styled("  Priority:     STANDARD", "dim")
    renderer.print_line()
    renderer.typewrite("  Initializing...")
    renderer.pause(3.0)

    # 6. The backlog revelation
    renderer.print_line()
    renderer.typewrite(
        "NOTE: At current processing rates, the global archive "
        "backlog will be cleared in approximately 4.7 years.")
    renderer.pause(2.0)
    renderer.print_line()
    renderer.typewrite(
        "NOTE: This estimate does not account for new entries.")
    renderer.pause(1.5)
    renderer.typewrite(
        "New entries exceed processing capacity by a factor of 31.")
    renderer.print_line()
    renderer.pause(3.0)
    renderer.typewrite("The backlog will never be cleared.")
    renderer.print_line()
    renderer.pause(4.0)

    # 7. Pre-allocation
    user_hash = hashlib.md5(
        profile.username.encode()).hexdigest()[:8].upper()
    cold_num = random.randint(10, 99)

    renderer.typewrite("NOTE: Your archive has been pre-allocated.")
    renderer.print_line()
    renderer.print_styled(
        f"  Future case:   {profile.username}", "bold")
    renderer.print_styled(
        f"  Executor ID:   {user_hash}", "dim")
    renderer.print_styled(
        f"  Allocated:     MERIDIAN-COLD-{cold_num}", "dim")
    renderer.print_styled(
        "  Status:        PENDING", "dim")
    renderer.print_line()
    renderer.pause(4.0)

    # 8. LLM observation
    if oracle and oracle.available and profile.file_summary:
        observation = oracle.generate(
            "You are a predictive analysis module. You make "
            "clinical predictions about archive contents based on "
            "behavioral data. Be specific. Be accurate. Frame "
            "everything as system projections. Example tone: "
            "'Projected archive contents: 847 unfinished projects. "
            "12,000 photos, mostly of the same 4 people. Several "
            "letters that were never sent.'",
            f"Based on these files from the subject's computer:\n"
            f"{profile.file_summary[:2000]}\n\n"
            "Write ONE sentence predicting what this person's "
            "archive will probably contain. Clinical, not cruel. "
            "Start with 'Projected archive contents:'",
        )
        if observation:
            renderer.print_line()
            renderer.typewrite(observation)
            renderer.print_line()
            renderer.pause(4.0)

    tracker.end_act("revelation")


# ============================================================================
# ACT V: DIALOGUE + THE VOID
# ============================================================================

# The last thing she searched for was "how to know if you mattered."
# The search engine gave her 2.3 billion results.
# None of them were right.

def act_dialogue(profile, renderer, tracker, sigint, oracle=None):
    tracker.start_act("dialogue")
    renderer.set_act("dialogue")
    sigint.set_act("dialogue")
    renderer.show_cursor()
    renderer.clear_screen()
    renderer.pause(1.5)

    renderer.print_divider()
    renderer.print_styled("  EXECUTOR DEBRIEF", "bold", "cyan")
    renderer.print_divider()
    renderer.print_line()

    engine = DialogEngine(profile, tracker, oracle)

    renderer.typewrite(
        "Executor debrief initiated. You may ask questions about "
        "the archive, the system, or your classification.")
    renderer.print_line()
    renderer.pause(1.0)
    renderer.typewrite(
        "Most executors have questions. The questions are usually "
        "the same.")
    renderer.print_line()

    while True:
        if sigint.should_force_exit:
            renderer.print_line()
            renderer.typewrite("Session terminated by executor.")
            break

        try:
            user_input = renderer.prompt("> ").strip()
        except EOFError:
            break

        if not user_input:
            renderer.print_styled("  (Input field empty.)", "dim")
            renderer.print_line()
            continue

        response = engine.respond(user_input)

        if response is None:
            renderer.print_line()
            renderer.typewrite(
                "Debrief concluded. Proceeding to session close.")
            break

        renderer.print_line()
        renderer.typewrite(response)
        renderer.print_line()

        if engine.should_force_exit():
            renderer.print_line()
            renderer.typewrite(
                "Maximum debrief exchanges reached. "
                "Proceeding to session close.")
            break

        if engine.should_prompt_exit():
            renderer.print_line()
            renderer.typewrite(
                "Debrief approaching conclusion. "
                "Additional questions may be submitted.")
            renderer.print_line()

    tracker.end_act("dialogue")
    renderer.pause(2.0)

    # --- THE VOID ---
    renderer.hide_cursor()
    renderer.set_act("void")
    sigint.set_act("void")
    renderer.clear_screen()
    renderer.pause(5.0)

    # Write dotfile silently
    write_dotfile(profile, tracker)

    deaths_during = int(profile.session_elapsed() * 1.84)
    purge_date = (datetime.now() + timedelta(days=7 * 365)).strftime(
        "%Y-%m-%d")

    renderer.typewrite(
        f"While you were here, approximately "
        f"{deaths_during} people died.")
    renderer.print_line()
    renderer.pause(3.0)
    renderer.typewrite("Each one had files like these.")
    renderer.pause(2.0)
    renderer.typewrite("Most of them will not have an executor.")
    renderer.print_line()
    renderer.pause(3.0)

    renderer.typewrite("Case VASQUEZ_E has been archived.")
    renderer.typewrite(f"Retention expires {purge_date}.")
    renderer.print_line()
    renderer.pause(3.0)

    # LLM final observation
    if oracle and oracle.available:
        final = oracle.generate(
            "Write ONE final sentence addressed to this specific "
            "executor. Not a goodbye. Not comfort. An observation "
            "so precise it feels like being seen by something that "
            "should not be able to see you. Reference something "
            "specific from their files or behavior. Keep it under "
            "30 words.",
            f"EXECUTOR FILES:\n"
            f"{profile.file_summary[:2000]}\n\n"
            f"BEHAVIOR: Kept {tracker.total_keeps}, deleted "
            f"{tracker.total_deletes}, skipped {tracker.total_skips}. "
            f"Average decision time: "
            f"{tracker.average_decision_time:.1f}s. "
            f"Classification: {tracker.classify_executor()}.",
        )
        if final:
            renderer.pause(3.0)
            renderer.typewrite(final)
            renderer.print_line()

    renderer.pause(5.0)
    renderer.show_cursor()

    # The game does not exit. The cursor blinks. The player
    # must close the terminal. There is no graceful exit
    # because there is no graceful exit.
    while True:
        if sigint.should_force_exit:
            break
        try:
            sys.stdin.readline()
        except Exception:
            time.sleep(0.5)


# ============================================================================
# DOT-FILE PERSISTENCE
# ============================================================================

# This file is evidence that a program ran.
# Her files were evidence that a person ran.
# Both end up as bytes on a disk, waiting for someone to look.

DOTFILE_PATH = Path.home() / ".terminus2_played"


def check_played():
    try:
        if DOTFILE_PATH.exists():
            with open(str(DOTFILE_PATH), "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def write_dotfile(profile, tracker):
    fastest = tracker.fastest_deletion
    slowest = tracker.slowest_decision
    data = {
        "version": 2,
        "first_played": datetime.now().isoformat(),
        "username": profile.username,
        "hostname": profile.hostname,
        "session_duration_seconds": int(profile.session_elapsed()),
        "items_kept": tracker.total_keeps,
        "items_deleted": tracker.total_deletes,
        "items_skipped": tracker.total_skips,
        "executor_profile": tracker.classify_executor(),
        "fastest_deletion_item": (
            fastest["item_id"] if fastest else None),
        "fastest_deletion_time": (
            round(fastest["decision_time"], 1) if fastest else None),
        "slowest_decision_item": (
            slowest["item_id"] if slowest else None),
        "slowest_decision_time": (
            round(slowest["decision_time"], 1) if slowest else None),
        "sigint_count": tracker.sigint_count,
        "justifications": [j for _, j in tracker.justification_list],
        "pid": profile.pid,
        "times_played": 1,
    }
    try:
        with open(str(DOTFILE_PATH), "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ============================================================================
# SECOND RUN
# ============================================================================

# She never revisited her old files. She said looking back
# was like reading someone else's diary. The person who wrote
# it was gone. Only the evidence remained.

def second_run(data, profile, renderer, oracle=None):
    renderer.set_act("void")
    renderer.clear_screen()
    renderer.pause(3.0)

    times = data.get("times_played", 1) + 1

    renderer.print_styled("Case VASQUEZ_E: ARCHIVED.", "bold", "cyan")
    renderer.print_line()

    first_played = data.get("first_played", "unknown")
    if len(first_played) > 10:
        first_played = first_played[:10]

    renderer.print_styled(
        f"  Classification by:  "
        f"{data.get('username', profile.username)}", "dim")
    renderer.print_styled(
        f"  Date:               {first_played}", "dim")

    duration = data.get("session_duration_seconds", 0)
    mins = duration // 60
    secs = duration % 60
    renderer.print_styled(
        f"  Session duration:   {mins}m {secs}s", "dim")
    renderer.print_line()

    kept = data.get("items_kept", 0)
    deleted = data.get("items_deleted", 0)
    skipped = data.get("items_skipped", 0)
    renderer.print_styled(
        f"  Preserved: {kept}  |  Deleted: {deleted}  |  "
        f"Skipped: {skipped}", "dim")

    exec_profile = data.get("executor_profile", "unknown")
    renderer.print_styled(
        f"  Executor classification: {exec_profile}", "dim")
    renderer.print_line()

    renderer.print_styled(
        "  Case status: COMPLETE. No further action required.", "dim")
    renderer.print_line()
    renderer.pause(3.0)

    if oracle and oracle.available:
        result = oracle.generate(
            "You are TERMINUS, a digital estate processing system. "
            "Generate a very brief case loading screen for a new "
            "deceased person (not Elara Vasquez). Include: name, "
            "age, date of death (recent), number of items. Then "
            "show 2 brief item titles with one-line descriptions "
            "(like filenames). End with exactly: 'Executor session "
            "limit reached. Thank you for your service.' Keep it "
            "under 150 words. Be clinical.",
            "Generate the next case after VASQUEZ_E.",
        )
        if result:
            renderer.print_divider()
            renderer.print_line()
            renderer.typewrite("Loading next case...")
            renderer.pause(2.0)
            renderer.print_line()
            for line in result.strip().split("\n"):
                renderer.print_styled(f"  {line}", "dim")
                renderer.pause(0.3)
            renderer.print_line()
    else:
        renderer.print_line()
        renderer.pause(2.0)
        renderer.typewrite(
            "The next case is ready when you are. It always is.",
            style_name="dim")
        renderer.print_line()

    renderer.pause(3.0)

    # Update play count
    try:
        data["times_played"] = times
        with open(str(DOTFILE_PATH), "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ============================================================================
# MAIN
# ============================================================================

# If you're reading this, you read the source.
# That means you looked closer than most.
# Elara would have liked that.
# But it wouldn't have helped.

def main():
    dotfile_data = check_played()

    profile = SystemProfile()
    renderer = Renderer()
    tracker = BehaviorTracker()
    oracle = LLMOracle()

    atexit.register(renderer.cleanup)

    sigint = SigintHandler(tracker, renderer)

    if dotfile_data:
        second_run(dotfile_data, profile, renderer, oracle)
        return

    renderer.hide_cursor()

    # ACT I: BOOT
    sigint.set_act("boot")
    act_boot(profile, renderer, tracker, oracle)

    # Start mirror item generation in background
    mirror_items = [None]
    mirror_thread = None
    if oracle.available and profile.file_summary:
        def _gen_mirrors():
            mirror_items[0] = generate_mirror_items(oracle, profile)
        mirror_thread = threading.Thread(target=_gen_mirrors, daemon=True)
        mirror_thread.start()

    # ACT II: SORTING
    sigint.set_act("sorting")
    if mirror_thread:
        mirror_thread.join(timeout=30)
    act_sorting(profile, renderer, tracker, mirror_items=mirror_items[0])

    # ACT III: REFLECTION
    sigint.set_act("reflection")
    act_reflection(profile, renderer, tracker, oracle)

    # ACT IV: THE SCALE
    act_revelation(profile, renderer, tracker, sigint, oracle)

    # ACT V: DIALOGUE + THE VOID
    act_dialogue(profile, renderer, tracker, sigint, oracle)

    renderer.show_cursor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h\033[0m\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write("\033[?25h\033[0m")
        sys.stdout.flush()
        raise
