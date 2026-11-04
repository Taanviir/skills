# Tidepool

Tidepool collects readings from coastal tide gauges and warns harbor crews when the water will be too low for a scheduled ship. It is built for small ports that cannot afford a commercial tide service.

<!-- Fictional project written for the project-presentation evals. -->

## What it does

- **Gauge sync.** Pulls readings every 6 minutes from up to 40 gauges over the public NMEA feed and stores them in SQLite.
- **Low-water alerts.** Compares each scheduled ship's draft with the predicted water depth at its berth and sends an SMS to the harbor master 12 hours ahead when the margin drops under 0.5 m.
- **Prediction.** Fits a harmonic tide model per gauge from 30 days of readings. The model is within 8 cm of observed water level 95% of the time at the two pilot ports.
- **Dashboard.** A web page per port shows the next 48 hours of predicted depth for each berth.

## How it works

1. `src/sync.ts` polls each gauge and writes readings to `data/tidepool.db`.
2. `src/model.ts` refits the harmonic model every night.
3. `src/alerts.ts` checks the ship schedule against predictions every 15 minutes.
4. `web/` serves the dashboard.

## Status

Running at two pilot ports, Port Calloway and Westhaven, since January 2026.

Working today:
- Gauge sync
- Prediction
- Dashboard

In progress:
- Low-water SMS alerts. The logic is done; the SMS provider contract is not signed yet, so alerts only go to a log file.

Planned:
- Storm surge adjustment using wind forecasts
- A mobile app for harbor crews

## Running it

```sh
npm install
npm run sync
npm run web
```
