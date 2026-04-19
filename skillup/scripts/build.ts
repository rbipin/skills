const result = await Bun.build({
  entrypoints: ["./src/index.ts"],
  outdir: "./dist",
  target: "node", // Node-compatible output for npx/bunx distribution
  minify: true,
});

if (!result.success) {
  for (const msg of result.logs) {
    console.error(msg);
  }
  process.exit(1);
}

console.log("Build complete:", result.outputs.map((o) => o.path).join(", "));
