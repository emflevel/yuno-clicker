<div align="center">

# Yuno Clicker

**A clean, lightweight autoclicker for Windows.**<br>
Bind any key or mouse button, set your speed, and it stays out of your way.

<br>

[![Download](https://img.shields.io/badge/download-latest-b8f53d?style=for-the-badge&labelColor=0a0a0b&logo=github&logoColor=ededf0)](https://github.com/emflevel/yuno-clicker/releases/latest)

![Windows](https://img.shields.io/badge/windows-10%20%2F%2011-ededf0?style=flat-square&labelColor=111113)
![Python](https://img.shields.io/badge/made%20in-python-ededf0?style=flat-square&labelColor=111113)

</div>

---

### `// features`

| | |
|---|---|
| **Left, right and middle click** | Give each mouse button its own bind. Use any keyboard key or a mouse side button. |
| **Toggle or hold** | Press once to start and again to stop, or only click while the key is held down. |
| **1–50 CPS** | Drag the slider to set exactly how many clicks per second you want. |
| **Randomised timing** | Add 0–30% randomness so the clicks don't land at a perfectly even rhythm. |
| **Hidden menu** | No taskbar icon. Show or hide the window with your own menu key. |
| **Remembers your settings** | Your binds, speed and window position are saved and loaded next time. |

---

### `// install`

```
01  Download Yuno Clicker.exe from the latest release
02  Run it. Everything it needs is built in, so no Python or setup needed
03  Pick the key that shows and hides the window
04  Click a bind, press a key or mouse button, set your CPS, done
```

> If Windows shows a blue "protected your PC" box, click **More info** then **Run anyway**.
> This happens with most new programs that aren't signed.

---

### `// settings`

Settings and the error log are saved in:

```
%APPDATA%\yunoclicker
```

Paste that into File Explorer's address bar to open it. Delete the folder to reset everything.

---

### `// faq`

<details>
<summary><b>Where did the window go?</b></summary>
<br>
It has no taskbar icon. Press the menu key you picked during setup to bring it back.
</details>

<details>
<summary><b>Nothing happens when I open it.</b></summary>
<br>
It can take a few seconds to open, since it unpacks itself first. If something goes wrong, it shows an error popup and writes the details to <code>yuno_error.log</code> in <code>%APPDATA%\yunoclicker</code>.
</details>

<details>
<summary><b>My antivirus flagged it.</b></summary>
<br>
Python programs turned into an .exe sometimes get false alarms, especially autoclickers. The .exe is built automatically by GitHub from the source in this repo, so you can check exactly what it does.
</details>

<details>
<summary><b>Can I use it in any game?</b></summary>
<br>
Some online games ban autoclickers, so check a game's rules before using it there.
</details>

---

### `// run from source`

```
pip install pynput
pythonw yuno_clicker.pyw
```

---

<div align="center">
<sub>made by <a href="https://github.com/emflevel">emflevel</a> · <a href="https://emflevel.github.io">emflevel.github.io</a></sub>
</div>
