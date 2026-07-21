const fs = require("fs");
const path = require("path");
const { StaticCanvas, Image, Rect } = require("fabric/node");
const { pathToFileURL } = require("url");

async function loadImageObject(fileUrl) {
  const loaded = await Image.fromURL(fileUrl);
  const img = new Image();
  img.setElement(loaded._element);
  return { img, width: loaded.width, height: loaded.height };
}

async function saveCanvas(canvas, outputPath) {
  await fs.promises.mkdir(path.dirname(outputPath), { recursive: true });
  canvas.renderAll();
  const nodeCanvas = canvas.getNodeCanvas();
  const stream = nodeCanvas.createPNGStream({ compressionLevel: 9 });
  const out = fs.createWriteStream(outputPath);
  await new Promise((resolve, reject) => {
    stream.pipe(out);
    out.on('finish', resolve);
    out.on('error', reject);
    stream.on('error', reject);
  });
}

async function main() {
  const WIDTH = 1080;
  const HEIGHT = 1350;
  const sourceUrl = pathToFileURL('F:/AI-Content-OS-Data/source_intake/2026-07-19/deep_dive/screenshots/nate_pann--20260719-B-f7c153fdfe11/original_post.png').toString();
  const commentUrl = pathToFileURL('F:/AI-Content-OS-Data/source_intake/2026-07-19/deep_dive/screenshots/nate_pann--20260719-B-f7c153fdfe11/comment_005_masked.png').toString();
  const outputPath = 'C:/Users/가산 솔리드옴므/Documents/GitHub/AI-Content-OS/artifacts/fabric_single/fabric_single_20260719-B-f7c153fdfe11.png';

  const canvas = new StaticCanvas(null, {
    width: WIDTH,
    height: HEIGHT,
    backgroundColor: '#111111',
  });

  const { img: sourceLoaded, width: srcW, height: srcH } = await loadImageObject(sourceUrl);
  const cropW = srcW;
  const cropH = Math.min(srcH, Math.round((cropW * HEIGHT) / WIDTH));

  sourceLoaded.set({
    left: 0,
    top: 0,
    width: WIDTH,
    height: HEIGHT,
    cropX: 0,
    cropY: 0,
    cropWidth: cropW,
    cropHeight: cropH,
    objectCaching: false,
  });

  const { img: commentLoaded } = await loadImageObject(commentUrl);
  const targetCommentW = 1010;
  const commentScale = targetCommentW / commentLoaded.width;
  const commentW = targetCommentW;
  const commentH = commentLoaded.height * commentScale;
  const commentX = (WIDTH - commentW) / 2;
  const commentY = Math.max(0, HEIGHT - commentH - 36);

  commentLoaded.set({
    left: commentX,
    top: commentY,
    width: commentW,
    height: commentH,
    objectCaching: false,
    stroke: '#ffffff',
    strokeWidth: 2,
  });

  canvas.add(sourceLoaded);
  canvas.add(commentLoaded);

  const maskHeight = Math.min(118, Math.max(72, commentH * 0.34));
  const mask = new Rect({
    left: commentX + 14,
    top: commentY + 14,
    width: commentW - 28,
    height: maskHeight,
    fill: 'rgba(0,0,0,0.72)',
  });
  canvas.add(mask);

  await saveCanvas(canvas, outputPath);
  console.log(outputPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
