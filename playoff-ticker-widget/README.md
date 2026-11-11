# Playoff Ticker Widget (NBA + NHL)

A native Android home-screen widget for a Pixel 8 (or any Android 8+ device).
For every remaining playoff series it shows:

- **Teams in the series** (e.g. `BOS @ NYK`)
- **Series score** (e.g. `BOS leads 2-1` — straight from ESPN's published summary when available)
- **Last game's score** (final score + date of the most recent completed game)
- **Live score** of any game currently in progress, with the period/clock

Data is pulled from ESPN's public scoreboard JSON endpoints — no API key required:

- NBA: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard`
- NHL: `https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard`

The widget filters for postseason games (`season.type == 3`) and groups them by
matchup. Series that have already been clinched/eliminated are dropped, so the
list shrinks as the playoffs progress.

## Refresh behavior

- A `WorkManager` periodic job refreshes every 15 minutes (the OS-imposed
  minimum for periodic work).
- The system also re-renders the widget at the `updatePeriodMillis` cadence
  (30 minutes, the OS minimum for that path).
- Tapping the **↻** button in the widget header triggers an immediate refresh.
- The header shows the time of the last successful refresh.

## Build

The simplest path: open this folder in **Android Studio Hedgehog or later**,
let Gradle sync, then **Build → Build Bundle(s) / APK(s) → Build APK(s)**.

From the command line (with Android SDK installed and `ANDROID_HOME` set):

```bash
cd playoff-ticker-widget
gradle wrapper      # one time, to generate ./gradlew
./gradlew assembleDebug
```

The APK lands at `app/build/outputs/apk/debug/app-debug.apk`.

## Install on your Pixel 8

1. On the phone: **Settings → About phone → tap "Build number" 7 times** to
   enable Developer options, then **Settings → System → Developer options →
   USB debugging → ON**.
2. Plug into your computer and approve the debugging prompt.
3. From this directory:
   ```bash
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```
4. On the home screen, long-press an empty area → **Widgets** → scroll to
   **Playoff Ticker** → drag the widget onto your home screen.

(No launcher icon is needed — the app is purely a widget provider.)

## Notes / caveats

- ESPN's scoreboard endpoints are unofficial; if ESPN changes the response
  shape the parser in `EspnApi.kt` may need an update. The code is defensive
  and falls back to tallying wins from completed games if the `series.summary`
  field is missing.
- "Live" refresh means polling every 15 minutes via `WorkManager`. Android
  doesn't allow widgets to update faster than that on battery; if you want
  near-realtime in-game updates, sideload a foreground service variant (out
  of scope for this widget-only build).
- Outside the NBA/NHL postseasons the widget will simply show the empty
  state ("No active playoff series").

## File map

```
app/src/main/
  AndroidManifest.xml                — declares the widget receiver + service
  java/com/playoffticker/
    EspnApi.kt                      — fetches & parses ESPN scoreboard JSON
    Models.kt                       — SeriesRow data class
    PlayoffRepository.kt            — in-memory cache + refresh
    PlayoffWidgetProvider.kt        — AppWidgetProvider, click handlers, scheduling
    PlayoffWidgetService.kt         — RemoteViewsService bridge for the list
    PlayoffWidgetFactory.kt         — RemoteViewsFactory (per-row binding)
    RefreshWorker.kt                — periodic WorkManager refresh
  res/
    layout/widget_playoff.xml       — root widget layout (header + ListView)
    layout/widget_row.xml           — one series row
    xml/playoff_widget_info.xml     — AppWidgetProviderInfo metadata
    drawable/                        — background, icon, refresh glyph
    values/                          — strings, colors, theme
```
