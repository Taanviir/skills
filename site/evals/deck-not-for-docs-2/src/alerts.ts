import { appendFileSync } from 'node:fs';

const MARGIN_M = 0.5;

// SMS sending waits on the provider contract; alerts go to a log for now.
export function checkShip(ship: { name: string; draftM: number }, depthM: number) {
  if (depthM - ship.draftM < MARGIN_M) {
    appendFileSync('data/alerts.log', `${new Date().toISOString()} LOW WATER ${ship.name} margin ${(depthM - ship.draftM).toFixed(2)} m\n`);
  }
}
