const BOX_WIDTH = 42;
const PIXEL_COLS = 16; // pixel art grid width
const CHARS_PER_PIXEL = 2;
const ART_WIDTH = PIXEL_COLS * CHARS_PER_PIXEL; // 32 terminal chars
const PAD = " ".repeat(Math.floor((BOX_WIDTH - ART_WIDTH) / 2)); // 5 each side

// Color palette
const R: [number, number, number] = [192, 57, 43]; // red headband
const D: [number, number, number] = [26, 26, 80]; // dark navy mask/head
const S: [number, number, number] = [243, 156, 107]; // warm skin
const E: [number, number, number] = [44, 62, 80]; // dark eye pupil
const W: [number, number, number] = [220, 230, 235]; // eye white
const _ = null; // transparent — shows terminal background

type Cell = [number, number, number] | null;

// 16×12 pixel art ninja face
// Each row = one terminal line; each cell = 2 terminal chars wide
const NINJA: Cell[][] = [
  [_, _, _, _, R, R, R, R, R, R, R, R, _, _, _, _],
  [_, _, R, R, R, R, R, R, R, R, R, R, R, R, _, _],
  [_, R, R, D, D, D, D, D, D, D, D, D, D, R, R, _],
  [_, R, D, D, D, D, D, D, D, D, D, D, D, D, R, _],
  [_, _, D, D, D, D, D, D, D, D, D, D, D, D, _, _],
  [_, _, D, D, D, S, S, S, S, S, S, S, D, D, _, _],
  [_, _, D, D, S, S, W, E, S, S, W, E, S, D, _, _],
  [_, _, D, D, S, S, W, E, S, S, W, E, S, D, _, _],
  [_, _, D, D, D, S, S, S, S, S, S, S, D, D, _, _],
  [_, _, D, D, D, D, D, D, D, D, D, D, D, D, _, _],
  [_, _, _, D, D, D, D, D, D, D, D, D, D, _, _, _],
  [_, _, _, _, D, D, D, D, D, D, D, D, _, _, _, _],
];

function center(text: string, width: number): string {
  const pad = Math.max(0, width - text.length);
  const left = Math.floor(pad / 2);
  return " ".repeat(left) + text + " ".repeat(pad - left);
}

async function buildArtLines(): Promise<string[]> {
  const { Chalk } = await import("chalk");
  const chalk = new Chalk({ level: 3 }); // force true color

  return NINJA.map((row) => {
    let line = "";
    for (const cell of row) {
      if (cell === null) {
        line += " ".repeat(CHARS_PER_PIXEL);
      } else {
        const [r, g, b] = cell;
        line += chalk.bgRgb(r, g, b)(" ".repeat(CHARS_PER_PIXEL));
      }
    }
    return line;
  });
}

export async function printBanner(): Promise<void> {
  let artLines: string[] = [];
  try {
    artLines = await buildArtLines();
  } catch {
    // chalk unavailable — artLines stays empty, box still shows
  }

  const border = "─".repeat(BOX_WIDTH);
  console.log("");
  console.log(`╭${border}╮`);

  if (artLines.length > 0) {
    for (const line of artLines) {
      process.stdout.write(`│${PAD}${line}${PAD}│\n`);
    }
  } else {
    console.log(`│${" ".repeat(BOX_WIDTH)}│`);
    console.log(`│${center("install agent skills", BOX_WIDTH)}│`);
    console.log(`│${" ".repeat(BOX_WIDTH)}│`);
  }

  console.log(`│${center("✦  s k i l l u p  ✦", BOX_WIDTH)}│`);
  console.log(`╰${border}╯`);
  console.log("");
}
