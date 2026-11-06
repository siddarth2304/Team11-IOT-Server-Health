import fs from "node:fs/promises";
import sharp from "/home/sahith-siddarth/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";

const root = "/home/sahith-siddarth/Documents/ChatGPT/IOT";
const svgPath = `${root}/docs/team11_architecture.svg`;
const pngPath = `${root}/docs/team11_architecture.png`;
const svg = await fs.readFile(svgPath);
await sharp(svg, { density: 144 }).png().toFile(pngPath);
console.log(pngPath);
