# Changelog

## Windows Spotify companion

- Added a token-authenticated local-network endpoint that accepts Spotify now-playing metadata and thumbnail artwork from a Windows laptop, caches the artwork on the Cockpit host, and broadcasts the state over the existing WebSocket.
- Added a Windows companion script and launcher that reads Spotify's Windows media session and forwards track, artist, album, playback state, progress, and cover art without streaming audio or storing Spotify OAuth credentials.
- Added setup/troubleshooting documentation and ignored the host-only bridge token file.

## Reference-led Music screen refresh

- Rebuilt the Music screen around a metallic vinyl player with a cyan-to-lime illuminated edge, live track metadata, full-width playback progress, and clear previous/play-pause/next controls.
- Added a clickable volume level control, stronger playing/paused/no-player states, and a compact layout tuned for 480 × 320 while scaling on larger displays.
- Kept player-provided artwork and metadata live, retained keyboard and GPIO event mappings, and made the spinning record honor reduced-motion preferences.

## Screenshot-led landing screen refresh

- Reworked Home into a cinematic, alpine-inspired status dashboard modeled on the supplied visual reference, with an original vector dusk-mountain wallpaper, prominent clock/date, illuminated sensor tiles, and a glass-style room environment card.
- Added crisp inline SVG icons and lime, cyan, and mint accents; preserved live sensor values and stale/missing states rather than presenting fictional weather data.
- Tightened the layout and type scales around a 480 × 320 3.5-inch TFT while retaining responsive scaling for larger screens.

## Responsive display refinement

- Refined the console for a native 3:2, 480 × 320 layout on the 3.5-inch TFT and laptop scaling up to a 960 × 640 canvas.
- Reworked the visual system with instrument-panel status tiles, a sharper accent palette, and more breathing room in the music and workflow screens.
- Added a wider-screen workflow view and refreshed the 480 × 320 screenshots; `laptop.png` shows the scaled Agents screen.

## v2 desk-console rebuild

Compared with the original project:

- Replaced the configurable multi-tab workflow dashboard with Home, Music, and n8n Agents screens for the 480 × 320 display.
- Added a config-driven wallpaper, clock/date, live sensor/status strip, rotating CD player, track controls, and workflow run status.
- Replaced rotary-encoder/next-screen input handling with common configurable joystick and button events; button 4 is now VOICE.
- Added mock keyboard inputs, sample music, sensor values, and fake workflow success/failure/timeout cases.
- Added optional DHT22/CPU/Wi-Fi readings and MPRIS/playerctl and wpctl/pactl adapters. Existing RFID, voice, terminal, and history features are not removed; they are not presented in the new UI.
- Added scan/contributor docs, Pi deployment and Bluetooth guidance, screenshot/test directories, and focused input/music tests.
