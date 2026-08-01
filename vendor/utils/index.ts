// Reconstructed from @repo/utils (monorepo package `packages/utils`).

export async function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(), ms);
  });
}
