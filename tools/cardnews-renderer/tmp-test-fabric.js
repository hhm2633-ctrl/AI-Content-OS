const {StaticCanvas, Image, Rect, util, loadSVGFromString} = require("fabric/node");
const { readFileSync } = require("fs");
(async()=>{
  try {
    const canvas = new StaticCanvas(null, {width:1080,height:1350});
    const img = await Image.fromURL('C:/Users/가산 솔리드옴므/Documents/GitHub/AI-Content-OS/artifacts/cardnews_preupload_2026-07-19/fragments/account_B.json');
    console.log('loaded', !!img);
  } catch (e) {
    console.error('err', e.message);
    process.exit(1);
  }
})();
