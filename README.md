# sshman

A simple interactive TUI SSH connection manager built with [Textual](https://textual.textualize.io/).

## Features

- **Interactive TUI** - Navigate with keyboard, no memorizing commands
- **Quick connect** - Select a host and press Enter to SSH
- **Search/filter** - Find connections quickly with `/`
- **Import from ~/.ssh/config** - Bring in your existing SSH hosts
- **Add/edit/delete** - Manage connections directly in the app
- **Docker integration** - Auto-detects running containers and connects via `docker exec`
- **Connection history** - Track past sessions with duration and status
- **Cross-platform** - Works on macOS, Linux, and Windows

## Installation

**PyPI** (macOS, Linux, Windows):

```bash
pip install clisshmanager
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install clisshmanager
```

**Windows** — download the standalone `.exe` (no Python required) from the
[GitHub Releases](https://github.com/dejan/sshman/releases) page and place it
somewhere on your `PATH`.

**Debian / Ubuntu** — download the `.deb` from
[GitHub Releases](https://github.com/dejan/sshman/releases):

```bash
sudo dpkg -i sshman_*.deb
```

**Fedora / RHEL / openSUSE** — download the `.rpm` from
[GitHub Releases](https://github.com/dejan/sshman/releases):

```bash
sudo rpm -i sshman_*.rpm
```

**winget** (Windows Package Manager):

```powershell
winget install Dejan.sshman
```

## Usage

Run the application:

```bash
sshman
```

The app has two tabs:

- **Connections** - Your saved SSH hosts and running Docker containers
- **History** - A log of past connection sessions

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Connect to selected host |
| `a` | Add new connection |
| `e` | Edit selected connection |
| `d` | Delete selected connection |
| `i` | Import from ~/.ssh/config |
| `r` | Refresh connections and Docker containers |
| `/` | Focus search input |
| `Escape` | Clear search and return to list |
| `Tab` | Switch to next tab |
| `1` | Switch to Connections tab |
| `2` | Switch to History tab |
| `q` | Quit |

## Configuration

Connections are stored in `~/.config/sshman/connections.json`.  
Connection history is stored in `~/.config/sshman/history.json`.

## Requirements

- Python 3.12+
- A terminal with modern capabilities (most terminals work)

## License

MIT
