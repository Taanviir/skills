// Harmonic tide model: sum of the main constituents fitted by least squares.
export const CONSTITUENTS = ['M2', 'S2', 'N2', 'K1', 'O1'] as const;

export function predict(fit: Record<string, { amp: number; phase: number; speed: number }>, t: number, mean: number) {
  return mean + Object.values(fit).reduce((sum, c) => sum + c.amp * Math.cos(c.speed * t - c.phase), 0);
}
