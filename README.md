# sshman

A simple interactive TUI SSH connection manager built with [Textual](https://textual.textualize.io/).

## Features

- **Interactive TUI** - Navigate with keyboard, no memorizing commands
- **Quick connect** - Select a host and press Enter to SSH
- **Search/filter** - Find connections quickly with `/`
- **Import from ~/.ssh/config** - Bring in your existing SSH hosts
- **Add/edit/delete** - Manage connections directly in the app
- **Cross-platform** - Works on macOS, Linux, and Windows

## Installation

```bash
pip install sshmanager
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install sshmanager
```

## Usage

Run the application:

```bash
sshman
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Connect to selected host |
| `a` | Add new connection |
| `e` | Edit selected connection |
| `d` | Delete selected connection |
| `i` | Import from ~/.ssh/config |
| `/` | Focus search input |
| `Escape` | Clear search and return to list |
| `q` | Quit |

## Configuration

Connections are stored in `~/.config/sshman/connections.json`.

## Requirements

- Python 3.12+
- A terminal with modern capabilities (most terminals work)

## License

MIT
