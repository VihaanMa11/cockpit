# Cockpit Spotify Bridge for Windows

This helper reads the **Spotify desktop app's** Windows media session and sends the current title, artist, album, playback state, progress and album-art thumbnail to a Cockpit backend on your local network. Cockpit play/pause and previous/next commands are sent back to Spotify; volume commands adjust the laptop's Windows master volume. It does not stream or change the audio route. Windows 10 (1809+) or Windows 11 and Python 3.11+ are required.

## First run

1. Extract this ZIP to a normal folder, such as `Documents\Cockpit-Spotify-Bridge`.
2. Double-click `Start-Cockpit-Spotify-Bridge.bat`. It installs the small Windows Runtime Python bindings into a private `.venv` in this folder.
3. When asked, enter the Cockpit server URL (for example, `http://192.168.1.25:8000`) and the bridge token created on the Cockpit server. The token is stored in your `%APPDATA%\CockpitMusicBridge\config.json` file.
4. Open the Spotify desktop app on this laptop and start a song. Cockpit's Music page should show its track details and artwork. Use the Pi's touchscreen or controls for play/pause, previous/next, and volume. Leave the bridge console window running; press Ctrl+C to stop it.

To find the Pi address, run `hostname -I` on the Pi. Do not use `localhost` unless Cockpit itself is running on the same Windows laptop.

## Server setup (one time)

On the Cockpit host, in its `backend` folder, generate a private token:

```sh
python -c "import secrets,pathlib; pathlib.Path('companion_token.txt').write_text(secrets.token_urlsafe(32))"
```

Keep that file private; it is ignored by Git. Copy its contents and paste it into the bridge prompt. Restart Cockpit after creating the token. The helper sends it only in the `X-Cockpit-Token` header. Keep both devices on a trusted local network and allow inbound TCP port 8000 from your laptop in the Pi firewall.

The existing Music UI will switch to Spotify data while the bridge is connected, then fall back to the Cockpit host's local player after the bridge goes away. Album artwork is cached on the Cockpit host, not linked to a temporary Windows thumbnail stream. Windows does not report the volume percentage through this bridge, but volume-up/down commands change the laptop's system volume.

## Troubleshooting

- If setup says Python is missing or too old, install 64-bit Python 3.11+ from [python.org](https://www.python.org/downloads/windows/) and run the batch file again.
- If Cockpit reports an invalid token, compare the token in `backend/companion_token.txt` with the one in `%APPDATA%\CockpitMusicBridge\config.json`.
- If there is no Spotify track, make sure the Spotify desktop app is open and playing. The helper intentionally ignores other media apps.
- If Cockpit cannot connect, check the Pi IP, same Wi-Fi/LAN, TCP 8000 firewall rule, and the Cockpit server process.
- To reconfigure the URL or token, edit `%APPDATA%\CockpitMusicBridge\config.json` or delete it and launch the batch file again.
