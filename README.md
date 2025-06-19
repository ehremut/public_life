# Life Bot

![Build](https://github.com/ehremut/public_life/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/ehremut/public_life/branch/main/graph/badge.svg)
![License](https://img.shields.io/github/license/ehremut/public_life)
![Last Commit](https://img.shields.io/github/last-commit/ehremut/public_life)
![Stars](https://img.shields.io/github/stars/ehremut/public_life?style=social)

A Telegram bot that integrates with a 3x-ui panel to manage access configurations. The
API client caches the authorization token so you don't have to log in on every
request. The token is retrieved via the panel's ``/login`` endpoint using the
configured account credentials.


## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Copy `config.ini.template` to `config.ini` and replace the placeholder values
with your Telegram bot token, the URL of your 3x-ui instance, and the panel
login credentials. These values can also be provided via the `TELEGRAM_TOKEN`,
`XUI_API_URL`, `XUI_LOGIN`, `XUI_PSW` and `XUI_INBOUND_ID` environment
variables. Set `XUI_INBOUND_ID` to the inbound you want to manage (defaults to
`2`). Use `VPN_BACKEND_TYPE` to choose how the bot talks to 3x‑ui: `api`
communicates via HTTP while `local` edits the panel's `config.json` directly
using `VPN_CONFIG_PATH`.
Set `qr_logo_path` to an image file that will be placed in the centre of all
generated QR codes (defaults to `logo.png`). The QR generator automatically
adds a small white border around the logo so the code scans cleanly.


## Running the Bot

From the project root directory run the helper script:

```bash
./run.sh
```

It will create a virtual environment if needed, install the dependencies and
start the bot. The bot will then begin polling Telegram for updates.

User data is now stored in `users.db`. If a legacy `users.json` file exists it
will be migrated automatically on first run.

## Docker

A `Dockerfile` is provided so the bot can run in a container. Make sure Docker
is installed **and** that the daemon is running. The steps vary slightly by
operating system:

- **Linux** – install Docker from your distribution's package repository (for
  example `sudo apt install docker.io` on Debian/Ubuntu) and start the service
  with `sudo systemctl start docker`.
- **macOS** – download **Docker Desktop** from the official Docker website and
  launch the Docker app to start the daemon.
- **Windows** – also install Docker Desktop and start it from the Start menu.

After starting Docker you can verify it is ready by running `docker info`.

Build the image with:

```bash
# run this from the repository root and don't forget the final dot
docker build -t life-bot .
```

Run the container and provide configuration through environment variables or by mounting a `config.ini` file:

```bash
docker run \
  -e TELEGRAM_TOKEN=YOUR_TOKEN \
  -e XUI_API_URL=https://example.com/api/ \
  -e XUI_LOGIN=your_login \
  -e XUI_PSW=your_password \
  -v $(pwd)/users.db:/app/users.db \
  life-bot
```

You can also mount a prepared `config.ini` instead of passing environment variables:

```bash
docker run -v $(pwd)/config.ini:/app/config.ini \
           -v $(pwd)/users.db:/app/users.db \
           --name life-bot -d --restart unless-stopped life-bot
```

### Using Docker Compose

If you prefer, a sample `docker-compose.yml` is included. Create an `.env` file
with your credentials and run:

```bash
docker compose up -d  # use `docker-compose` if your Docker version is older
```

Full deployment steps:

1. Copy `config.ini.template` to `config.ini` and fill in your details.
2. Build the image with `docker build -t life-bot .` (note the trailing dot).
3. Start the container using `docker compose up -d` or the `docker run` command
   shown above. The database will be created in `users.db` next to the
   repository.


## Testing

Unit tests can run without network access thanks to lightweight stubs for `aiohttp`, `aiosqlite` and `python-telegram-bot`. Install the dependencies and run:

```bash
PYTHONPATH=. pytest -q
```

To generate a coverage report:

```bash
PYTHONPATH=. coverage run -m pytest -q
coverage xml
```

