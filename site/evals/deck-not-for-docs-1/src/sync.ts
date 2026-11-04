import Database from 'better-sqlite3';
import { readGauges } from './nmea.js';

const db = new Database('data/tidepool.db');
db.exec('CREATE TABLE IF NOT EXISTS readings (gauge TEXT, at INTEGER, level_cm REAL)');
const insert = db.prepare('INSERT INTO readings VALUES (?, ?, ?)');

// Gauges report every 6 minutes; poll a little faster so no reading is missed.
setInterval(async () => {
  for (const r of await readGauges()) insert.run(r.gauge, r.at, r.levelCm);
}, 5 * 60 * 1000);
