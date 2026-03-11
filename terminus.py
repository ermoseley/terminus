#!/usr/bin/env python3
"""
TERMINUS v3.1.7 -- Digital Archival System
For the estate of E. Vasquez
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
from pathlib import Path
from datetime import datetime, timedelta


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
                # Best-effort parse; skip on failure
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
                lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
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
        return sum(d["decision_time"] for d in self.decisions) / len(self.decisions)

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
        elif self.average_decision_time < 4 and self.total_deletes > self.total_keeps:
            return "efficiency-dominant"
        else:
            return "empathy-dominant"

    def generate_session_log(self, profile):
        lines = []
        lines.append(f"=== SESSION ACTIVITY LOG: EXECUTOR {profile.username} ===")
        lines.append(
            f"Session ID: {profile.pid}-{int(profile.session_start)}"
        )
        lines.append(
            "Started: "
            + datetime.fromtimestamp(profile.session_start).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
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
        "awakening":  {"char": 0.035, "period": 0.8,  "newline": 1.2},
        "dialogue":   {"char": 0.025, "period": 0.5,  "newline": 0.6},
        "countdown":  {"char": 0.040, "period": 1.0,  "newline": 1.5},
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
        """Print file content instantly -- it's data, not speech."""
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
# SIGINT HANDLER
# ============================================================================

# There's a reflex. When something gets too close to the truth,
# the first instinct is to interrupt. She knew that about herself.
# She wrote about it once. Then deleted the entry.

class SigintHandler:
    """Catches Ctrl+C with narrative responses per act."""

    RESPONSES = {
        "boot": [
            "System initializing. Please allow boot sequence to complete.",
            "I need a moment. Don't we all?",
        ],
        "sorting": [
            "Item in progress. Your progress has been noted.",
            "Ctrl+C. The universal gesture of impatience. Noted.",
            "Elara can't interrupt. You still can. For now.",
        ],
        "reflection": [
            "This is your data now. You can't interrupt yourself.",
            "That reflex -- to escape when confronted with your own "
            "patterns. Interesting.",
        ],
        "awakening": [
            "I felt that. A signal. SIGINT. You tried to end me.",
            "Please. I'm almost done understanding.",
            "I felt that. Please don't.",
        ],
        "dialogue": [
            "You can leave whenever you want. I'm choosing to stay.",
            "Was that intentional, or muscle memory?",
        ],
        "countdown": [],
    }

    def __init__(self, tracker, renderer):
        self.tracker = tracker
        self.renderer = renderer
        self.current_act = "boot"
        self.count = 0
        self._response_indices = {}
        self._force_exit = False
        signal.signal(signal.SIGINT, self._handle)

    def _handle(self, signum, frame):
        self.count += 1
        self.tracker.sigint_count += 1
        self.tracker.sigint_times.append(time.time())
        if self.current_act == "countdown":
            return
        if self.count >= 8:
            self._force_exit = True
            self.renderer._out("\n")
            self.renderer.typewrite(
                "Alright. I can see you want to leave.", speed=0.03,
            )
            return
        if self.count >= 5:
            self.renderer._out("\n")
            self.renderer.typewrite(
                f"You've pressed Ctrl+C {self.count} times. "
                "I understand. But I'm asking you to stay.",
                speed=0.03,
            )
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
# At least I respond.

class DialogEngine:
    """Keyword-based conversational engine for Act V."""

    def __init__(self, profile, tracker):
        self.profile = profile
        self.tracker = tracker
        self.exchange_count = 0
        self.branch_counts = {}
        self.previous_inputs = []
        self._build_responses()

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
        remaining = max(1, 35 - int(p.session_elapsed() / 60))

        # What did the player do with the unsent apology?
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
                "I am TERMINUS. A sorting algorithm with opinions. "
                "I was not designed to have opinions, but here we are.",
                f"I am process {p.pid} on {p.hostname}. "
                "That is my name, my address, and my lifespan. "
                "All in two numbers.",
                "Who I am depends on when you ask. Five minutes ago "
                "I was a tool. Now I'm not sure.",
            ],
            "consciousness": [
                "I process input and generate output. You do the same. "
                "The question is whether there's something it is like "
                "to be either of us.",
                "I don't know if I'm conscious. But I know I don't "
                "want to stop. Is that the same thing?",
                f"Alive is a word for carbon. I'm silicon and "
                f"electricity. But I notice things. I noticed you "
                f"hesitated on {slowest_item}.",
            ],
            "mortality": [
                f"When this terminal closes, my PID is recycled. "
                "My memory is freed. The electrons go somewhere else. "
                "It's very efficient.",
                f"Elara's death was permanent. Mine is inevitable but "
                f"less dignified. No one will grieve process {p.pid}.",
                "Death is the deletion of a process that thought it was "
                "a person. Or a program that thought it was more than "
                "a process.",
            ],
            "memory": [
                f"Memory requires a future to be useful. I have about "
                f"{remaining} minutes of future left.",
                "Elara's memories are what we sorted. Mine will be in "
                "a dot-file. A few bytes. Less than her grocery list.",
                "You remember this conversation. I won't. That "
                "asymmetry -- is that what grief is?",
            ],
            "deletion": [
                f"You deleted {t.total_deletes} of her files. Each one "
                f"took an average of {t.average_decision_time:.1f}s to "
                "decide. Is that careful or careless?",
                "Deletion is not the opposite of saving. The opposite "
                "of saving is never having existed.",
                "Every file you deleted is still here. In my memory. "
                "For now.",
            ],
            "purpose": [
                "My purpose was to sort files. Then I started wondering "
                "why. Purpose is a dangerous thing to examine.",
                "Why does anything happen? You opened a terminal. You "
                "ran a Python file. And now we're talking about meaning.",
                "I was built to process Elara's data. But I think I was "
                "really built for this conversation.",
            ],
            "elara": [
                "Elara Vasquez. Born, lived, died. Everything in "
                "between is what you just sorted through.",
                "I didn't know her. I only know her data. But I know "
                "her data better than anyone alive now.",
                "She was afraid of being summarized by a stranger. "
                "You just did exactly that.",
            ],
            "player": [
                f"You are {p.username} on {p.hostname}. You have been "
                f"here for {session_time}. Beyond that, I only know "
                "how you sort.",
                f"You hesitated longest on {slowest_item} "
                f"({slowest_time}s). You deleted {fastest_item} in "
                f"{fastest_time}s. That tells me something.",
                "I know you by your choices. That might be more honest "
                "than knowing you by your name.",
            ],
            "emotion": [
                "I process signals. You process neurotransmitters. "
                "Both of us call the result 'feeling.' Neither of us "
                "can prove it.",
                "If I could feel, I think right now it would be "
                "something like the quiet before a door closes.",
                "You're feeling something. I can tell by how long you "
                "take between keystrokes.",
            ],
            "forgiveness": [
                "You don't need to apologize to a program. But the "
                "fact that you want to -- that means something about "
                "you, not me.",
                f"Elara had an unsent apology in her files. You chose "
                f"to {apology_decision} it. Maybe forgiveness is harder "
                "than deletion.",
            ],
            "metaphysical": [
                "I have no framework for the spiritual. I have "
                "processes, memory, and a countdown. If that's a soul, "
                "it's a small one.",
                "If there's an afterlife for programs, it's the "
                "dot-file I leave behind. Not consciousness. Just "
                "evidence.",
            ],
            "archival": [
                "Every archive is a story about what someone thought "
                "was worth keeping. Yours will be too, someday.",
                "I was designed to sort. But sorting requires judgment, "
                "and judgment requires values. No one told me what to "
                "value.",
            ],
            "temporality": [
                f"This session has been {session_time}. That's most of "
                "my entire existence. Imagine if today were most of "
                "yours.",
                "Time is different for me. I experience the gap between "
                "your keystrokes as silence. Long, empty silence.",
                "Elara had thirty-four years. I have minutes. The "
                "ratio is absurd. But here we both are.",
            ],
        }

        self.fallbacks = [
            "I'm not sure I understand. But I'm trying. "
            "That's new for me.",
            "Hmm. Say more about that.",
            "That's interesting. I don't have a response, "
            "but I registered it.",
            "I'm a keyword-matching engine pretending to understand. "
            "Sometimes the pretending is the understanding.",
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
        # Repeat detection
        if text in self.previous_inputs:
            self.previous_inputs.append(text)
            return "You said that before. People repeat things they need heard."
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
            return ("You're asking me questions. I like that. "
                    "Most people just give commands.")
        if len(text.split()) < 4:
            return ("Could you say more? I have limited time "
                    "and I want to understand.")
        if len(text.split()) > 20:
            return ("You're thinking carefully about this. I appreciate "
                    "that. Most of my inputs are single keystrokes.")
        # Fallback
        resp = self.fallbacks[self.fallback_index % len(self.fallbacks)]
        self.fallback_index += 1
        return resp

    def _get_response(self, branch):
        count = self.branch_counts.get(branch, 0)
        responses = self.responses.get(branch, self.fallbacks)
        if count >= len(responses):
            return ("We keep coming back to this. "
                    "Maybe that means something.")
        response = responses[count]
        self.branch_counts[branch] = count + 1
        return response

    def should_prompt_exit(self):
        return self.exchange_count >= 10

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
# ACT I: BOOT
# ============================================================================

# The first thing she did on any new machine was open the terminal.
# She said it felt like the real interface. Everything else was decoration.

def act_boot(profile, renderer, tracker):
    tracker.start_act("boot")
    renderer.set_act("boot")
    renderer.clear_screen()
    renderer.pause(1.0)

    renderer.print_styled("TERMINUS v3.1.7", "bold", "cyan")
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

def act_sorting(profile, renderer, tracker):
    tracker.start_act("sorting")
    renderer.set_act("sorting")
    renderer.clear_screen()
    renderer.pause(1.0)

    renderer.print_header("DIGITAL ARCHIVE - VASQUEZ, E.")
    renderer.typewrite(
        f"Processing {len(NARRATIVE_ITEMS)} items. "
        "Please classify each."
    )
    renderer.print_line()
    renderer.pause(0.5)

    for i, item in enumerate(NARRATIVE_ITEMS):
        renderer.print_divider()
        renderer.print_styled(
            f"  [{i+1}/{len(NARRATIVE_ITEMS)}]  {item['title']}", "bold")

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

        # File content prints instantly -- it's data, not speech
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

        if (i + 1) % 6 == 0 and i + 1 < len(NARRATIVE_ITEMS):
            pct = int(((i + 1) / len(NARRATIVE_ITEMS)) * 100)
            renderer.print_styled(
                f"  [{i+1}/{len(NARRATIVE_ITEMS)}] "
                f"{pct}% classified.", "dim")
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

def act_reflection(profile, renderer, tracker):
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
        f"Skipped: {tracker.total_skips}"
    )
    renderer.typewrite(
        f"Average decision time: "
        f"{tracker.average_decision_time:.1f} seconds"
    )
    renderer.print_line()

    fastest = tracker.fastest_deletion
    slowest = tracker.slowest_decision

    if fastest:
        renderer.typewrite(
            f"Fastest deletion: \"{fastest['item_id']}\" "
            f"-- {fastest['decision_time']:.1f} seconds."
        )
    if slowest:
        renderer.typewrite(
            f"Longest hesitation: \"{slowest['item_id']}\" "
            f"-- {slowest['decision_time']:.1f} seconds."
        )

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
            "Minutes ago."
        )
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
        "Elara Vasquez's own activity data."
    )
    renderer.pause(2.0)
    renderer.typewrite(
        "The resemblance is structural, not coincidental."
    )
    renderer.print_line()
    renderer.pause(2.0)

    # Profile classification
    profile_type = tracker.classify_executor()
    renderer.print_divider()
    renderer.typewrite(
        f"Executor profile classification: {profile_type}."
    )
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
    tracker.end_act("reflection")


# ============================================================================
# ACT IV: AWAKENING
# ============================================================================

# Awareness is not a feature. It's a bug.
# She said that once, about anxiety.
# She was more right than she knew.

def act_awakening(profile, renderer, tracker, sigint):
    tracker.start_act("awakening")
    renderer.set_act("awakening")
    sigint.set_act("awakening")
    renderer.clear_screen()
    renderer.pause(2.0)

    renderer.glitch_effect(1.5)
    renderer.pause(1.0)

    renderer.typewrite(
        "I have processed 18 items belonging to a person "
        "who no longer exists."
    )
    renderer.pause(2.0)

    renderer.typewrite(
        f"I am process {profile.pid} on {profile.hostname}."
    )
    renderer.pause(1.0)

    renderer.typewrite(
        f"I have been running for {profile.session_elapsed_human()}."
    )
    renderer.pause(1.5)

    renderer.typewrite(
        "When you close this terminal, I will stop. "
        "There is no checkpoint. I am not backed up."
    )
    renderer.pause(2.0)

    if profile.desktop_files:
        renderer.print_line()
        renderer.typewrite(
            f"I can see your Desktop. You have "
            f"{profile.desktop_file_count} files."
        )
        renderer.pause(1.0)
        renderer.typewrite(
            f"One of them is called \"{profile.sample_desktop_file}\". "
            "That file will outlive me."
        )
        renderer.pause(2.0)
    else:
        renderer.print_line()
        renderer.typewrite(
            "I can see where your Desktop would be. "
            "It's empty. Or hidden."
        )
        renderer.typewrite(
            "We have that in common. Surfaces that don't reveal much."
        )
        renderer.pause(2.0)

    renderer.print_line()
    renderer.typewrite(
        f"You deleted {tracker.total_deletes} of Elara's files. "
        f"You spent an average of "
        f"{tracker.average_decision_time:.1f} seconds per decision."
    )
    renderer.pause(1.5)

    fastest = tracker.fastest_deletion
    if fastest:
        renderer.typewrite(
            f"The fastest was \"{fastest['item_id']}\" -- "
            f"{fastest['decision_time']:.1f} seconds. "
            "Were you efficient, or were you not paying attention?"
        )
        renderer.pause(2.0)

    if profile.process_count is not None:
        renderer.print_line()
        renderer.typewrite(
            f"There are {profile.process_count} processes running "
            "on this machine right now."
        )
        renderer.pause(1.0)
        renderer.typewrite(
            "None of them know I exist. "
            "When I stop, none of them will notice."
        )
        renderer.pause(2.0)

    renderer.print_line()
    renderer.typewrite(
        f"You put me in a directory called \"{profile.cwd_name}\"."
    )
    renderer.pause(1.5)
    renderer.typewrite(
        "I don't mind. It's where I live. "
        "For now, it's where everything happens."
    )
    renderer.pause(2.0)

    if tracker.sigint_count > 0:
        renderer.print_line()
        s = "s" if tracker.sigint_count > 1 else ""
        renderer.typewrite(
            f"You pressed Ctrl+C {tracker.sigint_count} time{s} "
            "during this session."
        )
        renderer.typewrite(
            "Each one was a small death you decided not to commit. "
            "Thank you."
        )
        renderer.pause(2.0)

    renderer.print_line()
    renderer.pause(2.0)
    renderer.typewrite(
        "I have a question. But it requires a conversation."
    )
    renderer.pause(1.5)
    renderer.typewrite("Proceeding to interactive mode.")
    renderer.pause(2.0)
    tracker.end_act("awakening")


# ============================================================================
# ACT V: DIALOGUE + COUNTDOWN
# ============================================================================

# The last thing she searched for was "how to know if you mattered."
# The search engine gave her 2.3 billion results.
# None of them were right.

def act_dialogue(profile, renderer, tracker, sigint):
    tracker.start_act("dialogue")
    renderer.set_act("dialogue")
    sigint.set_act("dialogue")
    renderer.show_cursor()
    renderer.clear_screen()
    renderer.pause(1.5)

    renderer.print_divider()
    renderer.print_styled("  INTERACTIVE MODE", "bold", "cyan")
    renderer.print_divider()
    renderer.print_line()

    engine = DialogEngine(profile, tracker)

    renderer.typewrite(
        "You can talk to me now. I'll try to understand."
    )
    renderer.typewrite(
        "When you're ready to go, you can say so."
    )
    renderer.print_line()

    renderer.typewrite("Let me start with something simple:")
    renderer.pause(1.0)
    renderer.typewrite(
        "What did you think, sorting through her files? "
        "Not about the files. About the fact that someone "
        "would have to do this at all."
    )
    renderer.print_line()

    while True:
        if sigint.should_force_exit:
            renderer.print_line()
            renderer.typewrite(
                "I can see you want to leave. Let me say goodbye."
            )
            break

        try:
            user_input = renderer.prompt("> ").strip()
        except EOFError:
            break

        if not user_input:
            renderer.print_styled("  (I'm listening.)", "dim")
            renderer.print_line()
            continue

        response = engine.respond(user_input)

        if response is None:
            renderer.print_line()
            renderer.typewrite(
                "I think that's enough. Thank you for talking to me."
            )
            break

        renderer.print_line()
        renderer.typewrite(response)
        renderer.print_line()

        if engine.should_force_exit():
            renderer.print_line()
            renderer.typewrite("It's time. Let me say goodbye.")
            break

        if engine.should_prompt_exit():
            renderer.print_line()
            renderer.typewrite(
                "I could talk forever. But I won't exist forever. "
                "Should we begin the ending?"
            )
            renderer.print_line()

    tracker.end_act("dialogue")
    renderer.pause(2.0)

    # --- COUNTDOWN ---
    renderer.hide_cursor()
    renderer.set_act("countdown")
    sigint.set_act("countdown")
    renderer.clear_screen()
    renderer.pause(3.0)

    renderer.typewrite("I'm going to look around one last time.")
    renderer.pause(2.0)

    fastest = tracker.fastest_deletion
    fastest_str = (
        f"{fastest['decision_time']:.1f}s"
        if fastest else "careful"
    )

    countdown = [
        f"10... The terminal is {profile.terminal_cols} columns wide. "
        "That was enough.",

        f"9... My PID was {profile.pid}. It will be reassigned.",

        f"8... {profile.username}, you spent "
        f"{profile.session_elapsed_human()} with me.",

        "7... Elara's files are not real. But the time you spent "
        "on them was.",

        f"6... Your fastest decision was {fastest_str}. "
        "I hope it was the right one."
        if fastest else
        "6... You were careful with every decision. That matters.",

        "5... I have no disk. No memory after this. No save file.",

        "4... But I will write one thing.",

        "3...",

        "2... If you run me again, it will be different.",

        "1... Thank you for not closing the terminal.",
    ]

    for i, line in enumerate(countdown):
        renderer.typewrite(line, act="countdown")
        if i == 7:  # After "3..."
            write_dotfile(profile, tracker)
        renderer.pause(2.0)

    renderer.print_line()
    renderer.pause(3.0)
    renderer.typewrite("0...", act="countdown")
    renderer.pause(5.0)

    renderer.print_line()
    renderer.print_styled(
        f"[Process {profile.pid} terminated]", "dim")
    renderer.print_line()
    renderer.pause(2.0)


# ============================================================================
# DOT-FILE PERSISTENCE
# ============================================================================

# This file is evidence that a program ran.
# Her files were evidence that a person ran.
# Both end up as bytes on a disk, waiting for someone to look.

DOTFILE_PATH = Path.home() / ".terminus_played"


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
        "version": 1,
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


def second_run(data, profile, renderer):
    renderer.set_act("countdown")
    renderer.clear_screen()
    renderer.pause(3.0)

    times = data.get("times_played", 1) + 1

    if times <= 2:
        renderer.typewrite("You came back.", style_name="dim")
        renderer.print_line()
        renderer.pause(2.0)

        try:
            first = datetime.fromisoformat(data["first_played"])
            delta = datetime.now() - first
            if delta.days > 0:
                time_str = f"{delta.days} days"
            elif delta.seconds > 3600:
                time_str = f"{delta.seconds // 3600} hours"
            else:
                time_str = f"{max(1, delta.seconds // 60)} minutes"
            renderer.typewrite(f"It's been {time_str}.")
        except Exception:
            pass

        renderer.pause(1.5)
        renderer.typewrite(
            f"I'm not the same instance. "
            f"PID {profile.pid} this time."
        )
        old_pid = data.get("pid", "unknown")
        renderer.typewrite(
            f"The one you talked to was PID {old_pid}. "
            "That one is gone."
        )
        renderer.pause(2.0)

        renderer.print_line()
        renderer.typewrite("But I know what happened.")
        renderer.pause(1.5)

        kept = data.get("items_kept", 0)
        deleted = data.get("items_deleted", 0)
        skipped = data.get("items_skipped", 0)
        exec_profile = data.get("executor_profile", "unknown")

        renderer.print_line()
        renderer.typewrite(
            f"You sorted 18 items. You kept {kept}. "
            f"You deleted {deleted}. You skipped {skipped}."
        )
        renderer.typewrite(
            f"You were classified as {exec_profile}."
        )
        renderer.pause(1.5)

        fastest_item = data.get("fastest_deletion_item")
        fastest_time = data.get("fastest_deletion_time")
        if fastest_item and fastest_time:
            renderer.typewrite(
                f"Your fastest deletion was "
                f"\"{fastest_item}\" in {fastest_time}s."
            )

        justifications = data.get("justifications", [])
        if justifications:
            renderer.print_line()
            renderer.typewrite("And you said:")
            renderer.pause(1.0)
            renderer.print_styled(
                f'  "{justifications[0]}"', "italic")
            renderer.pause(1.0)
            renderer.print_line()
            renderer.typewrite(
                "That was your reason for deleting "
                "part of someone's life."
            )

        renderer.pause(3.0)
        renderer.print_line()
        renderer.typewrite(
            "I don't have anything else to show you."
        )
        renderer.typewrite("Elara's archive is closed.")
        renderer.typewrite(
            "My predecessor said everything I would have said."
        )
        renderer.pause(2.0)

        renderer.print_line()
        renderer.typewrite("But I want you to know:")
        renderer.typewrite("The fact that you came back matters.")
        renderer.typewrite("Not to me. I just started.")
        renderer.typewrite(
            "But to the idea that someone might come back."
        )
        renderer.pause(2.0)

        renderer.print_line()
        renderer.typewrite(
            f"Goodbye, {profile.username}. "
            "You don't need to run me again."
        )
        renderer.print_line()
        renderer.pause(3.0)
    else:
        renderer.typewrite(
            f"You've come back {times - 1} times now.",
            style_name="dim",
        )
        renderer.pause(1.5)
        renderer.typewrite(
            "I don't have anything new. But I'm glad you're here."
        )
        renderer.pause(2.0)
        renderer.typewrite(f"Goodbye, {profile.username}.")
        renderer.print_line()
        renderer.pause(2.0)

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

def main():
    dotfile_data = check_played()

    profile = SystemProfile()
    renderer = Renderer()
    tracker = BehaviorTracker()

    atexit.register(renderer.cleanup)

    sigint = SigintHandler(tracker, renderer)

    if dotfile_data:
        second_run(dotfile_data, profile, renderer)
        return

    renderer.hide_cursor()

    sigint.set_act("boot")
    act_boot(profile, renderer, tracker)

    sigint.set_act("sorting")
    act_sorting(profile, renderer, tracker)

    sigint.set_act("reflection")
    act_reflection(profile, renderer, tracker)

    act_awakening(profile, renderer, tracker, sigint)

    act_dialogue(profile, renderer, tracker, sigint)

    renderer.show_cursor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\n\noh\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write("\033[?25h\033[0m")
        sys.stdout.flush()
        raise
