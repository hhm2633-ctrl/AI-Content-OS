import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import {Resvg} from "@resvg/resvg-js";
import satori from "satori";

const MAX_STDIN_BYTES = 2 * 1024 * 1024;
const MAX_SLIDES = 10;
const ALLOWED_SIZES = new Set(["1080x566", "1080x1080", "1080x1350", "1080x1440"]);
const REMOTE_PATTERN = /(?:https?|ftp):\/\//i;
const PROTECTED_KINDS = new Set(["hair", "outfit", "product", "comment"]);
const CANVAS_PROFILES = {
  instagram_portrait_4_5: {profile_id: "instagram_portrait_4_5", width: 1080, height: 1350, aspect_ratio: "4:5", safe_previews: {central_square: {x: 0, y: 135, width: 1080, height: 1080}, profile_grid_3_4: {x: 30, y: 0, width: 1020, height: 1350}}},
  instagram_square_1_1: {profile_id: "instagram_square_1_1", width: 1080, height: 1080, aspect_ratio: "1:1", safe_previews: {central_square: {x: 0, y: 0, width: 1080, height: 1080}, profile_grid_3_4: {x: 135, y: 0, width: 810, height: 1080}}},
  instagram_landscape_1_91_1: {profile_id: "instagram_landscape_1_91_1", width: 1080, height: 566, aspect_ratio: "1.91:1", safe_previews: {central_square: {x: 257, y: 0, width: 566, height: 566}, profile_grid_3_4: {x: 328, y: 0, width: 424, height: 566}}},
  instagram_portrait_3_4: {profile_id: "instagram_portrait_3_4", width: 1080, height: 1440, aspect_ratio: "3:4", safe_previews: {central_square: {x: 0, y: 180, width: 1080, height: 1080}, profile_grid_3_4: {x: 0, y: 0, width: 1080, height: 1440}}},
};

function fail(message) {
  throw new Error(message);
}

function assertSafeTree(value) {
  if (typeof value === "string") {
    if (REMOTE_PATTERN.test(value) || value.toLowerCase().includes("file://")) {
      fail("external_or_file_url_not_allowed");
    }
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) assertSafeTree(item);
    return;
  }
  if (value && typeof value === "object") {
    for (const item of Object.values(value)) assertSafeTree(item);
  }
}

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function equalJson(left, right) {
  return canonical(left) === canonical(right);
}

function validBounds(value, normalized) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const numbers = [value.x, value.y, value.width, value.height];
  if (numbers.some((item) => typeof item !== "number" || !Number.isFinite(item))) return false;
  if (value.x < 0 || value.y < 0 || value.width <= 0 || value.height <= 0) return false;
  return !normalized || (value.x + value.width <= 1 && value.y + value.height <= 1);
}

function contained(inner, outer) {
  return inner.x >= outer.x && inner.y >= outer.y &&
    inner.x + inner.width <= outer.x + outer.width &&
    inner.y + inner.height <= outer.y + outer.height;
}

function centerCoverWindow(sourceWidth, sourceHeight, targetWidth, targetHeight) {
  const sourceRatio = sourceWidth / sourceHeight;
  const targetRatio = targetWidth / targetHeight;
  if (sourceRatio > targetRatio) {
    const width = targetRatio / sourceRatio;
    return {x: (1 - width) / 2, y: 0, width, height: 1};
  }
  const height = sourceRatio / targetRatio;
  return {x: 0, y: (1 - height) / 2, width: 1, height};
}

async function readRequest() {
  const chunks = [];
  let total = 0;
  for await (const chunk of process.stdin) {
    total += chunk.length;
    if (total > MAX_STDIN_BYTES) fail("render_request_too_large");
    chunks.push(chunk);
  }
  const value = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  if (!value || typeof value !== "object" || Array.isArray(value)) fail("render_request_invalid");
  return value;
}

function validate(request) {
  if (request.schema_version !== "cardnews_renderer_request_v1") fail("render_schema_invalid");
  if (!/^[Ff]:[\\/]/.test(String(request.output_root || ""))) fail("output_root_must_be_f_drive");
  if (!Array.isArray(request.slides) || request.slides.length < 1 || request.slides.length > MAX_SLIDES) {
    fail("slide_count_out_of_bounds");
  }
  if (!request.authorization || typeof request.authorization !== "object") fail("authorization_missing");
  if (!request.controller_state || typeof request.controller_state !== "object") fail("controller_state_missing");
  if (!Array.isArray(request.local_media_receipt_hashes) || request.local_media_receipt_hashes.length < 1) {
    fail("local_media_hashes_missing");
  }
  if (!request.canvas_profile || typeof request.canvas_profile !== "object") fail("canvas_profile_missing");
  const expectedProfile = CANVAS_PROFILES[request.canvas_profile.profile_id];
  if (!expectedProfile || !equalJson(request.canvas_profile, expectedProfile)) fail("canvas_profile_invalid");
  if (sha256(Buffer.from(canonical(request.canvas_profile), "utf8")) !== request.canvas_profile_hash) {
    fail("canvas_profile_hash_invalid");
  }
  const state = request.controller_state;
  const stateBody = {...state};
  delete stateBody.state_hash;
  if (state.schema_version !== "cardnews_production_controller_state_v1") fail("controller_schema_invalid");
  if (sha256(Buffer.from(canonical(stateBody), "utf8")) !== state.state_hash) fail("controller_state_hash_invalid");
  if (state.hard_rule_hash !== sha256(Buffer.from(canonical(state.hard_rule_evidence), "utf8"))) {
    fail("controller_hard_rule_hash_invalid");
  }
  const expectedState = request.mode === "representative" ? "representative_authorized" :
    request.mode === "batch" ? "batch_authorized" : "";
  if (!expectedState || state.state !== expectedState) fail("controller_state_not_authorized");
  const candidates = request.mode === "representative" ? Object.values(state.representatives || {}) : state.candidate_ids;
  if (!Array.isArray(candidates) || !candidates.includes(request.candidate_id)) fail("candidate_not_authorized");
  const boundHashes = state.local_media_receipt_hashes?.[request.candidate_id];
  if (!Array.isArray(boundHashes) || !equalJson([...boundHashes].sort(), [...request.local_media_receipt_hashes].sort())) {
    fail("local_media_hash_binding_mismatch");
  }
  if (
    request.authorization.controller_state_hash !== state.state_hash ||
    request.authorization.batch_hash !== state.batch_hash ||
    request.authorization.hard_rule_hash !== state.hard_rule_hash
  ) fail("authorization_binding_mismatch");
  if (request.mode === "batch") {
    if (!state.batch_authorization_hash) fail("batch_authorization_hash_missing");
    if (!equalJson(request.authorization.representative_qa_receipt_ids, state.representative_qa_receipt_ids)) {
      fail("representative_qa_binding_mismatch");
    }
  }
  const names = new Set();
  for (const slide of request.slides) {
    if (!slide || typeof slide !== "object") fail("slide_invalid");
    if (!ALLOWED_SIZES.has(`${slide.width}x${slide.height}`)) fail("canvas_size_not_allowed");
    if (slide.width !== request.canvas_profile.width || slide.height !== request.canvas_profile.height) {
      fail("carousel_canvas_profile_mismatch");
    }
    if (!slide.tree || typeof slide.tree !== "object" || Array.isArray(slide.tree)) fail("slide_tree_invalid");
    if (!/^[0-9A-Za-z._-]+\.png$/.test(String(slide.output_filename || ""))) fail("output_filename_invalid");
    if (names.has(slide.output_filename)) fail("output_filename_duplicate");
    names.add(slide.output_filename);
    assertSafeTree(slide.tree);
    if (!["source_evidence", "generated_editorial", "motion_graphic"].includes(slide.media_classification)) {
      fail("media_classification_invalid");
    }
    if (slide.media_classification !== "source_evidence" && !String(slide.display_label || "").trim()) {
      fail("generated_or_motion_label_missing");
    }
    if (slide.media_classification === "motion_graphic") fail("motion_canvas_not_production_connected");
    if (!Array.isArray(slide.assets)) fail("asset_metadata_missing");
    const canvas = {x: 0, y: 0, width: slide.width, height: slide.height};
    for (const asset of slide.assets) {
      if (!asset || typeof asset !== "object" || !asset.asset_id) fail("asset_metadata_invalid");
      if (!Number.isInteger(asset.source_width) || asset.source_width < 1 ||
          !Number.isInteger(asset.source_height) || asset.source_height < 1) fail("asset_size_invalid");
      if (!validBounds(asset.focus_bounds, true) || !validBounds(asset.target_bounds, false) ||
          !contained(asset.target_bounds, canvas)) fail("asset_bounds_invalid");
      if (!Array.isArray(asset.protected_subjects)) fail("protected_subjects_missing");
      if (!["contain", "no_crop", "focus_fit", "center_cover"].includes(asset.crop_strategy)) {
        fail("crop_strategy_invalid");
      }
      const centerCrop = asset.crop_strategy === "center_cover" ? centerCoverWindow(
        asset.source_width, asset.source_height, asset.target_bounds.width, asset.target_bounds.height,
      ) : null;
      if (centerCrop && !contained(asset.focus_bounds, centerCrop)) fail("center_cover_would_crop_focus");
      for (const subject of asset.protected_subjects) {
        if (!subject || !PROTECTED_KINDS.has(subject.kind) ||
            !validBounds(subject.source_bounds, true) || !validBounds(subject.canvas_bounds, false)) {
          fail("protected_subject_invalid");
        }
        if (!contained(subject.canvas_bounds, canvas) ||
            !Object.values(request.canvas_profile.safe_previews || {}).every((preview) => contained(subject.canvas_bounds, preview))) {
          fail("protected_subject_outside_safe_preview");
        }
        if (asset.crop_strategy === "center_cover") {
          if (!contained(subject.source_bounds, centerCrop)) fail("center_cover_would_crop_protected_subject");
        }
      }
    }
  }
}

const request = await readRequest();
validate(request);
const outputRoot = path.resolve(request.output_root);
fs.mkdirSync(outputRoot, {recursive: true});
const realOutputRoot = fs.realpathSync(outputRoot);
if (!/^[Ff]:[\\/]/.test(realOutputRoot)) fail("resolved_output_root_must_be_f_drive");
const font = fs.readFileSync("C:/Windows/Fonts/malgun.ttf");
const rendered = [];

for (const slide of request.slides) {
  const outputPath = path.resolve(realOutputRoot, slide.output_filename);
  if (path.dirname(outputPath).toLowerCase() !== realOutputRoot.toLowerCase()) fail("output_path_escape");
  if (fs.existsSync(outputPath)) fail("output_already_exists");
  const svg = await satori(slide.tree, {
    fonts: [{data: font, name: "Malgun Gothic", style: "normal", weight: 400}],
    height: slide.height,
    width: slide.width,
  });
  const png = new Resvg(svg).render().asPng();
  rendered.push({slide, outputPath, png});
}

const created = [];
try {
  for (const item of rendered) {
    fs.writeFileSync(item.outputPath, item.png, {flag: "wx"});
    created.push(item.outputPath);
  }
} catch (error) {
  for (const createdPath of created) {
    try { fs.unlinkSync(createdPath); } catch {}
  }
  throw error;
}

const outputHashes = {};
for (const item of rendered) outputHashes[String(item.slide.page)] = sha256(item.png);
console.log(JSON.stringify({
  schema_version: "cardnews_renderer_receipt_v1",
  status: "render_completed_pending_visual_qa",
  render_request_id: request.render_request_id,
  candidate_id: request.candidate_id,
  mode: request.mode,
  output_set_id: request.output_set_id,
  controller_state_hash: request.authorization.controller_state_hash,
  batch_hash: request.authorization.batch_hash,
  hard_rule_hash: request.authorization.hard_rule_hash,
  local_media_receipt_hashes: request.local_media_receipt_hashes,
  canvas_profile_hash: request.canvas_profile_hash,
  safe_previews: request.canvas_profile.safe_previews,
  expected_slide_count: request.slides.length,
  rendered_slide_count: request.slides.length,
  output_root: request.output_root,
  output_hashes: outputHashes,
  invoked_engines: ["satori", "resvg"],
  capability_only_engines: ["fabric", "motion_canvas"],
  visual_preservation_verified: false,
  media_labels: request.slides.map(({page, media_classification, display_label}) => ({
    page, media_classification, display_label,
  })),
  requires_independent_visual_qa: true,
}));
