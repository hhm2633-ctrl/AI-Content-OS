import fs from "node:fs";

import {Resvg} from "@resvg/resvg-js";
import {build} from "esbuild";
import satori from "satori";

const font = fs.readFileSync("C:/Windows/Fonts/malgun.ttf");
const svg = await satori(
  {
    type: "div",
    props: {
      lang: "ko-KR",
      style: {
        background: "#111",
        color: "#fff",
        display: "flex",
        fontFamily: "Malgun Gothic",
        height: "120px",
        width: "120px",
      },
      children: "확인",
    },
  },
  {
    fonts: [
      {
        data: font,
        name: "Malgun Gothic",
        style: "normal",
        weight: 400,
      },
    ],
    height: 120,
    width: 120,
  },
);
const png = new Resvg(svg).render().asPng();
const bundle = await build({
  bundle: true,
  format: "esm",
  logLevel: "silent",
  platform: "browser",
  stdin: {
    contents:
      "import {makeProject} from '@motion-canvas/core';" +
      "import {makeScene2D} from '@motion-canvas/2d';" +
      "console.log(makeProject, makeScene2D);",
    resolveDir: process.cwd(),
    sourcefile: "motion-smoke.js",
  },
  write: false,
});
const fabricBundle = await build({
  bundle: true,
  format: "esm",
  logLevel: "silent",
  platform: "browser",
  stdin: {
    contents:
      "import {Canvas, Rect} from 'fabric';" +
      "console.log(Canvas, Rect);",
    resolveDir: process.cwd(),
    sourcefile: "fabric-smoke.js",
  },
  write: false,
});

if (
  !svg.startsWith("<svg") ||
  png.length < 100 ||
  bundle.outputFiles.length !== 1 ||
  fabricBundle.outputFiles.length !== 1
) {
  throw new Error("Renderer dependency smoke check failed.");
}

console.log(
  JSON.stringify({
    korean_font: true,
    fabric_browser_bundle_bytes: fabricBundle.outputFiles[0].contents.length,
    motion_bundle_bytes: bundle.outputFiles[0].contents.length,
    resvg_png_bytes: png.length,
    satori_svg: true,
  }),
);
