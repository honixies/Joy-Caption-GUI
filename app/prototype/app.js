const healthOutput = document.querySelector("#healthOutput");
const resultOutput = document.querySelector("#resultOutput");
const healthBtn = document.querySelector("#healthBtn");
const loadBtn = document.querySelector("#loadBtn");
const demoBtn = document.querySelector("#demoBtn");
const sampleImageBtn = document.querySelector("#sampleImageBtn");
const sampleFolderBtn = document.querySelector("#sampleFolderBtn");
const singleForm = document.querySelector("#singleForm");
const batchForm = document.querySelector("#batchForm");
const loadPanel = document.querySelector("#loadPanel");
const loadSpinner = document.querySelector("#loadSpinner");
const loadMessage = document.querySelector("#loadMessage");
const loadProgress = document.querySelector("#loadProgress");
const loadMeta = document.querySelector("#loadMeta");
const workCurrent = document.querySelector("#workCurrent");
const workLog = document.querySelector("#workLog");
const clearWorkBtn = document.querySelector("#clearWorkBtn");
const modelBadge = document.querySelector("#modelBadge");
const backendBadge = document.querySelector("#backendBadge");
const imagePreview = document.querySelector("#imagePreview");
const previewPath = document.querySelector("#previewPath");
const previewProgress = document.querySelector("#previewProgress");
const previewMeta = document.querySelector("#previewMeta");
const openFileBtn = document.querySelector("#openFileBtn");
const openFolderBtn = document.querySelector("#openFolderBtn");
const fileInput = document.querySelector("#fileInput");
const folderInput = document.querySelector("#folderInput");
const dropZone = document.querySelector("#dropZone");
const targetPath = document.querySelector("#targetPath");
const targetSummary = document.querySelector("#targetSummary");
const runTargetBtn = document.querySelector("#runTargetBtn");
const sidecarMode = document.querySelector("#sidecarMode");
const combinedNameOption = document.querySelector("#combinedNameOption");
const combinedIncludeFilenames = document.querySelector("#combinedIncludeFilenames");
const combinedIncludeFilenamesBtn = document.querySelector("#combinedIncludeFilenamesBtn");
const folderRecursiveOption = document.querySelector("#folderRecursiveOption");
const includeSubfolders = document.querySelector("#includeSubfolders");
const includeSubfoldersBtn = document.querySelector("#includeSubfoldersBtn");

dropZone.textContent = "클릭하거나 파일/폴더를 끌어오면 원본 경로를 지정합니다.";

function hasNativeShell() {
  return Boolean(window.chrome?.webview);
}

function requestNativeShellPath(kind) {
  if (!hasNativeShell()) {
    return false;
  }
  window.chrome.webview.postMessage({
    type: kind === "folder" ? "pick-folder" : "pick-file",
  });
  return true;
}

function applyNativeShellPath(result) {
  if (!result?.path) {
    addWork("선택을 취소했습니다.");
    return;
  }
  const kind = result.kind === "folder" ? "folder" : "image";
  setTarget(result.path, kind);
  if (kind === "folder") {
    batchForm.elements.input_dir.value = result.path;
    addWork("폴더 원본 경로를 선택했습니다.");
  } else {
    singleForm.elements.image_path.value = result.path;
    addWork("파일 원본 경로를 선택했습니다.");
  }
}

if (hasNativeShell()) {
  window.chrome.webview.addEventListener("message", (event) => {
    const data = event.data;
    if (data?.type === "path-selected") {
      applyNativeShellPath(data);
    } else if (data?.type === "path-error") {
      failWork(addWork("경로 선택 중 오류가 발생했습니다."), new Error(data.message || "경로 선택 실패"));
    }
  });
}
const customPromptToggle = document.querySelector("#customPromptToggle");
const customPromptToggleBtn = document.querySelector("#customPromptToggleBtn");
const promptPanel = document.querySelector(".prompt-panel");
const promptBuilder = document.querySelector("#promptBuilder");
const customPresetName = document.querySelector("#customPresetName");
const promptBaseType = document.querySelector("#promptBaseType");
const promptBaseTypeBtn = document.querySelector("#promptBaseTypeBtn");
const promptBaseTypeLabel = document.querySelector("#promptBaseTypeLabel");
const promptBaseTypeMenu = document.querySelector("#promptBaseTypeMenu");
const promptLength = document.querySelector("#promptLength");
const promptTone = document.querySelector("#promptTone");
const tagFormat = document.querySelector("#tagFormat");
const promptLanguage = document.querySelector("#promptLanguage");
const customPromptText = document.querySelector("#customPromptText");
const promptPreview = document.querySelector("#promptPreview");
const promptSummary = document.querySelector("#promptSummary");
const savedPresetSelect = document.querySelector("#savedPresetSelect");
const loadPresetBtn = document.querySelector("#loadPresetBtn");
const savePresetBtn = document.querySelector("#savePresetBtn");
const deletePresetBtn = document.querySelector("#deletePresetBtn");
const closePromptBuilderBtn = document.querySelector("#closePromptBuilderBtn");
const applyPromptBuilderBtn = document.querySelector("#applyPromptBuilderBtn");

const tagPostprocessors = ["normalize-commas", "dedupe-tags", "strip-tag-period"];
const captionPostprocessors = ["trim-whitespace"];
const customPresetStorageKey = "joycaption.customPromptPresets.v1";
const imagePathExtensions = [".jpg", ".jpeg", ".png", ".webp", ".bmp"];
const presetForMode = {
  tags: "tags-dataset",
  short_caption: "caption-short",
  long_description: "description-long",
};

let appConfig = null;
let loadPollTimer = null;
let previewPollTimer = null;
let previewState = { path: "", kind: "" };
let targetKind = "image";
let promptModalOpen = false;
let folderImageRequestId = 0;
const folderImageCache = new Map();

function postprocessorsFor(mode) {
  return mode === "tags" ? tagPostprocessors : captionPostprocessors;
}

function updateToggleButton(button, checked) {
  button.classList.toggle("is-on", checked);
  button.setAttribute("aria-pressed", checked ? "true" : "false");
  const state = button.querySelector("strong");
  if (state) {
    state.textContent = checked ? "ON" : "OFF";
  }
}

function selectedPromptModeText() {
  return promptBaseType.options[promptBaseType.selectedIndex]?.text || "태그 목록";
}

function updatePromptModeButton() {
  promptBaseTypeLabel.textContent = selectedPromptModeText();
  for (const button of promptBaseTypeMenu.querySelectorAll("button")) {
    button.classList.toggle("is-selected", button.dataset.value === promptBaseType.value);
  }
}

function closePromptModeMenu() {
  promptBaseTypeMenu.hidden = true;
  promptBaseTypeBtn.setAttribute("aria-expanded", "false");
}

function togglePromptModeMenu() {
  const willOpen = promptBaseTypeMenu.hidden;
  promptBaseTypeMenu.hidden = !willOpen;
  promptBaseTypeBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
}

function renderPromptModeMenu() {
  clearElement(promptBaseTypeMenu);
  for (const option of promptBaseType.options) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.value = option.value;
    button.textContent = option.text;
    button.addEventListener("click", () => {
      promptBaseType.value = option.value;
      promptBaseType.dispatchEvent(new Event("change", { bubbles: true }));
      closePromptModeMenu();
    });
    promptBaseTypeMenu.append(button);
  }
  updatePromptModeButton();
}

function basePromptFor(type) {
  if (type === "tags") {
    return "Generate concise comma-separated visual tags for this image. Prefer concrete subjects, attributes, clothing, setting, style, composition, and visible actions. Do not write full sentences.";
  }
  if (type === "short_caption") {
    return "Write a short natural-language caption for this image.";
  }
  if (type === "long_description") {
    return "Write a detailed description of this image, including the main subject, setting, visual style, notable objects, and composition.";
  }
  if (type === "sd_prompt") {
    return "Output a Stable Diffusion prompt that captures the visible subject, style, composition, lighting, and important details.";
  }
  if (type === "midjourney") {
    return "Write a MidJourney prompt for this image with clear subject, style, lighting, composition, and visual details.";
  }
  if (type === "booru") {
    return "Generate Booru-like tags for this image, focusing on visible subjects, appearance, clothing, pose, expression, background, and style.";
  }
  if (type === "product") {
    return "Write a product-style description for this image, emphasizing visible features, material, color, condition, and use case.";
  }
  if (type === "social") {
    return "Write a social media caption for this image that is natural, concise, and visually grounded.";
  }
  if (type === "critic") {
    return "Analyze this image like an art critic, covering composition, color, light, style, medium, and visual effect.";
  }
  return "";
}

function lengthInstruction(value) {
  const map = {
    very_short: "Keep the output very short.",
    short: "Keep the output short.",
    medium: "Use a medium-length response.",
    long: "Use a detailed long response.",
    words_30: "Keep the output under 30 words.",
    words_60: "Keep the output under 60 words.",
    words_120: "Keep the output under 120 words.",
  };
  return map[value] || "";
}

function toneInstruction(value) {
  const map = {
    concise: "Use concise wording.",
    natural: "Use natural human-readable wording.",
    dataset: "Optimize the output for dataset sidecar files.",
    marketing: "Use polished marketing-friendly wording without inventing details.",
    technical: "Use precise technical visual description.",
  };
  return map[value] || "";
}

function tagFormatInstruction(value) {
  const map = {
    comma: "Use comma-separated output when producing tags or prompts.",
    underscore: "Use lowercase_underscore tag formatting when producing tags.",
    plain: "Use plain readable words without underscores when producing tags.",
    weighted: "Use concise weighted prompt fragments only when useful.",
  };
  return map[value] || "";
}

function languageInstruction(value) {
  const map = {
    english: "Write the output in English.",
    korean: "Write the output in Korean.",
    same: "Use the most appropriate language for the user's input.",
  };
  return map[value] || "";
}

function selectedPromptOptions() {
  return Array.from(promptBuilder.querySelectorAll(".option-grid input:checked")).map((input) => input.value);
}

function loadSavedPresets() {
  try {
    const raw = localStorage.getItem(customPresetStorageKey);
    const presets = raw ? JSON.parse(raw) : [];
    return Array.isArray(presets) ? presets : [];
  } catch {
    return [];
  }
}

function savePresets(presets) {
  localStorage.setItem(customPresetStorageKey, JSON.stringify(presets));
}

function presetFormState() {
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `preset-${Date.now()}`,
    name: customPresetName.value.trim() || "내 프리셋",
    baseType: promptBaseType.value,
    length: promptLength.value,
    tone: promptTone.value,
    tagFormat: tagFormat.value,
    language: promptLanguage.value,
    options: selectedPromptOptions(),
    extraText: customPromptText.value.trim(),
    prompt: buildCustomPrompt(),
    updatedAt: new Date().toISOString(),
  };
}

function applyPresetState(preset) {
  customPromptToggle.checked = true;
  promptModalOpen = true;
  customPresetName.value = preset.name || "내 프리셋";
  promptBaseType.value = preset.baseType || "tags";
  promptLength.value = preset.length || "any";
  promptTone.value = preset.tone || "neutral";
  tagFormat.value = preset.tagFormat || "comma";
  promptLanguage.value = preset.language || "english";
  customPromptText.value = preset.extraText || "";
  const selected = new Set(preset.options || []);
  for (const input of promptBuilder.querySelectorAll(".option-grid input")) {
    input.checked = selected.has(input.value);
  }
  updatePromptPreview();
}

function renderSavedPresetList(selectedId = "") {
  const presets = loadSavedPresets();
  clearElement(savedPresetSelect);
  if (!presets.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "저장된 프리셋 없음";
    savedPresetSelect.append(option);
    savedPresetSelect.disabled = true;
    loadPresetBtn.disabled = true;
    deletePresetBtn.disabled = true;
    return;
  }
  savedPresetSelect.disabled = false;
  loadPresetBtn.disabled = false;
  deletePresetBtn.disabled = false;
  for (const preset of presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    savedPresetSelect.append(option);
  }
  savedPresetSelect.value = selectedId || presets[0].id;
}

function saveCurrentPreset() {
  const state = presetFormState();
  const presets = loadSavedPresets();
  const existingIndex = presets.findIndex((preset) => preset.name === state.name);
  if (existingIndex >= 0) {
    state.id = presets[existingIndex].id;
    presets[existingIndex] = state;
  } else {
    presets.push(state);
  }
  presets.sort((a, b) => a.name.localeCompare(b.name, "ko"));
  savePresets(presets);
  renderSavedPresetList(state.id);
  addWork(`프리셋을 저장했습니다: ${state.name}`);
}

function loadSelectedPreset() {
  const presets = loadSavedPresets();
  const preset = presets.find((item) => item.id === savedPresetSelect.value);
  if (!preset) {
    addWork("불러올 프리셋이 없습니다.", "error");
    return;
  }
  applyPresetState(preset);
  addWork(`프리셋을 불러왔습니다: ${preset.name}`);
}

function deleteSelectedPreset() {
  const presets = loadSavedPresets();
  const preset = presets.find((item) => item.id === savedPresetSelect.value);
  if (!preset) {
    addWork("삭제할 프리셋이 없습니다.", "error");
    return;
  }
  savePresets(presets.filter((item) => item.id !== preset.id));
  renderSavedPresetList();
  addWork(`프리셋을 삭제했습니다: ${preset.name}`);
}

function buildCustomPrompt() {
  const parts = [
    basePromptFor(promptBaseType.value),
    lengthInstruction(promptLength.value),
    toneInstruction(promptTone.value),
    tagFormatInstruction(tagFormat.value),
    languageInstruction(promptLanguage.value),
    ...selectedPromptOptions(),
    customPromptText.value.trim(),
  ].filter(Boolean);
  return parts.join(" ") || "Describe this image.";
}

function updatePromptPreview() {
  const enabled = customPromptToggle.checked;
  updateToggleButton(customPromptToggleBtn, enabled);
  updatePromptModeButton();
  promptBaseTypeBtn.closest(".prompt-mode-control").hidden = enabled;
  closePromptModeMenu();
  promptPreview.value = buildCustomPrompt();
  promptPanel.classList.toggle("custom-enabled", enabled);
  promptPanel.classList.toggle("custom-modal-open", enabled && promptModalOpen);
  promptBuilder.classList.toggle("disabled", !enabled);
  for (const element of promptBuilder.querySelectorAll(".custom-only")) {
    element.hidden = !enabled || !promptModalOpen;
  }
  promptSummary.textContent = enabled
    ? `${customPresetName.value.trim() || "사용자 정의"} · 사용자 정의`
    : `${promptBaseType.options[promptBaseType.selectedIndex].text} 기본 프리셋을 사용합니다.`;
  for (const control of [
    customPresetName,
    customPromptText,
    ...promptBuilder.querySelectorAll(".option-grid input"),
  ]) {
    control.disabled = !enabled;
  }
}

function openPromptModal() {
  promptModalOpen = true;
  promptBuilder.setAttribute("role", "dialog");
  promptBuilder.setAttribute("aria-modal", "true");
  promptBuilder.setAttribute("aria-labelledby", "promptBuilderTitle");
  updatePromptPreview();
}

function closePromptModal({ keepEnabled = true } = {}) {
  promptModalOpen = false;
  promptBuilder.removeAttribute("role");
  promptBuilder.removeAttribute("aria-modal");
  promptBuilder.removeAttribute("aria-labelledby");
  if (!keepEnabled) {
    customPromptToggle.checked = false;
  }
  updatePromptPreview();
}

function generationPayloadOptions() {
  if (!customPromptToggle.checked) {
    return {};
  }
  const customPrompt = buildCustomPrompt();
  return {
    custom_prompt: customPrompt,
    custom_preset_name: customPresetName.value.trim() || "사용자 정의",
  };
}

function updateSidecarModeControls() {
  const combinedOption = sidecarMode.querySelector('option[value="combined"]');
  combinedOption.disabled = targetKind !== "folder";
  if (targetKind !== "folder" && sidecarMode.value === "combined") {
    sidecarMode.value = "beside";
  }
  combinedNameOption.hidden = sidecarMode.value !== "combined";
  folderRecursiveOption.hidden = targetKind !== "folder";
  updateToggleButton(combinedIncludeFilenamesBtn, combinedIncludeFilenames.checked);
  updateToggleButton(includeSubfoldersBtn, includeSubfolders.checked);
}

function selectedMode() {
  return ["tags", "short_caption", "long_description"].includes(promptBaseType.value)
    ? promptBaseType.value
    : "long_description";
}

function selectedPresetId() {
  return customPromptToggle.checked ? "custom" : presetForMode[selectedMode()];
}

async function api(path, body) {
  const options = body
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    : undefined;
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `요청 실패: ${response.status}`);
  }
  return data;
}

function uploadName(file) {
  return file.uploadRelativePath || file.webkitRelativePath || file.name;
}

async function readDirectoryEntry(reader) {
  const entries = [];
  while (true) {
    const batch = await new Promise((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    if (!batch.length) {
      return entries;
    }
    entries.push(...batch);
  }
}

async function collectDroppedFiles(dataTransfer) {
  const items = Array.from(dataTransfer?.items || []);
  const entries = items.map((item) => item.webkitGetAsEntry?.()).filter(Boolean);
  if (!entries.length) {
    return Array.from(dataTransfer?.files || []);
  }

  const files = [];
  async function walk(entry, parentPath = "") {
    if (entry.isFile) {
      const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
      try {
        file.uploadRelativePath = `${parentPath}${file.name}`;
      } catch {
        // Some browsers expose File objects as non-extensible. The plain name is still usable.
      }
      files.push(file);
      return;
    }
    if (entry.isDirectory) {
      const children = await readDirectoryEntry(entry.createReader());
      await Promise.all(children.map((child) => walk(child, `${parentPath}${entry.name}/`)));
    }
  }

  await Promise.all(entries.map((entry) => walk(entry)));
  return files;
}

async function uploadFiles(files, kind) {
  const selected = Array.from(files || []).filter((file) => file.type.startsWith("image/"));
  if (!selected.length) {
    throw new Error("이미지 파일이 없습니다.");
  }
  const body = new FormData();
  body.append("kind", kind);
  for (const file of selected) {
    body.append("files", file, uploadName(file));
  }
  const response = await fetch("/api/upload", {
    method: "POST",
    body,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `요청 실패: ${response.status}`);
  }
  return data;
}

function show(target, data) {
  target.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function clearElement(target) {
  target.textContent = "";
}

function setImagePreview(path, kind = "image") {
  const cleanPath = path || "";
  if (!cleanPath) {
    previewState = { path: "", kind: "" };
    clearElement(imagePreview);
    imagePreview.className = "image-preview empty";
    imagePreview.append("이미지를 선택하면 여기에서 미리 봅니다.");
    previewPath.textContent = "선택된 이미지 없음";
    renderPreviewProgress({ state: "idle", index: 0, total: 0 });
    return;
  }

  if (previewState.path === cleanPath && previewState.kind === kind) {
    previewPath.textContent = kind === "folder" ? `폴더: ${cleanPath}` : cleanPath;
    return;
  }

  previewState = { path: cleanPath, kind };
  clearElement(imagePreview);
  imagePreview.className = "image-preview";
  const image = document.createElement("img");
  const endpoint = kind === "folder" ? "/api/folder-preview-image" : "/api/preview-image";
  image.src = `${endpoint}?path=${encodeURIComponent(cleanPath)}`;
  image.alt = kind === "folder" ? "현재 폴더의 첫 번째 이미지 미리보기" : "현재 작업 이미지 미리보기";
  image.onerror = () => {
    imagePreview.className = "image-preview empty";
    clearElement(imagePreview);
    imagePreview.append("미리보기를 표시할 수 없습니다.");
  };
  imagePreview.append(image);
  previewPath.textContent = kind === "folder" ? `폴더: ${cleanPath}` : cleanPath;
}

function setTarget(path, kind) {
  targetKind = kind;
  targetPath.value = path || "";
  targetSummary.textContent =
    kind === "folder"
      ? "폴더가 선택되었습니다. 대상 이미지 수를 확인하는 중입니다."
      : "이미지 파일이 선택되었습니다. 실행하면 한 장을 생성합니다.";
  setImagePreview(path, kind === "folder" ? "folder" : "image");
  updateSidecarModeControls();
  if (path && kind === "folder") {
    renderFolderImages(path, "pending");
  }
}

function renderPreviewProgress(current) {
  const total = Number(current.total || 0);
  const index = Number(current.index || 0);
  const state = current.state || "idle";
  const percent = total > 0 ? Math.min(100, Math.max(0, Math.round((index / total) * 100))) : 0;

  previewProgress.className = "progress-bar";
  previewProgress.style.width = `${percent}%`;
  if (state === "running") {
    previewProgress.classList.add("active-determinate");
  } else if (state === "succeeded") {
    previewProgress.classList.add("done");
  } else if (state === "failed" || state === "error") {
    previewProgress.classList.add("error");
  }

  if (total > 1) {
    previewMeta.textContent = `작업률: ${percent}% · ${index}/${total}`;
  } else if (total === 1 && percent === 100) {
    previewMeta.textContent = "작업률: 100% · 완료";
  } else if (state === "running") {
    previewMeta.textContent = "작업률: 처리 중";
  } else {
    previewMeta.textContent = "작업 대기 중";
  }
}

async function refreshCurrentImage() {
  const current = await api("/api/current-image");
  if (current.path) {
    setImagePreview(current.path, current.kind || "image");
    previewPath.textContent = current.label || current.path;
  }
  renderPreviewProgress(current);
  return current;
}

function startPreviewPolling() {
  if (previewPollTimer) {
    clearInterval(previewPollTimer);
  }
  previewPollTimer = setInterval(() => {
    refreshCurrentImage().catch(() => {});
  }, 900);
}

async function stopPreviewPolling() {
  if (previewPollTimer) {
    clearInterval(previewPollTimer);
    previewPollTimer = null;
  }
  await refreshCurrentImage().catch(() => {});
}

function renderTextBlock(text) {
  const block = document.createElement("div");
  block.className = "generated-text";
  block.textContent = text || "결과 텍스트가 없습니다.";
  return block;
}

function renderMeta(label, value) {
  const item = document.createElement("div");
  item.className = "meta-item";
  const key = document.createElement("span");
  key.textContent = label;
  const body = document.createElement("strong");
  body.textContent = value || "-";
  item.append(key, body);
  return item;
}

function fileNameFromPath(path) {
  const cleanPath = String(path || "").trim();
  if (!cleanPath) {
    return "선택된 작업";
  }
  return cleanPath.split(/[\\/]/).filter(Boolean).pop() || cleanPath;
}

function inferTargetKind(path, fallback = targetKind) {
  const lower = String(path || "").toLowerCase();
  return imagePathExtensions.some((extension) => lower.endsWith(extension)) ? "image" : fallback === "image" ? "folder" : fallback;
}

function statusLabel(status) {
  if (status === "running") {
    return "작업 중";
  }
  if (status === "succeeded" || status === "done") {
    return "완료";
  }
  if (status === "failed" || status === "error") {
    return "실패";
  }
  return "대기";
}

function renderResultRow({ path, name, status = "pending", error = "", outputPath = "" }) {
  const row = document.createElement("div");
  row.className = `result-row ${status}`;
  const file = document.createElement("strong");
  file.className = "result-file";
  file.textContent = name || fileNameFromPath(path);
  file.title = path || name || "";
  const state = document.createElement("span");
  state.className = "result-state";
  state.textContent = statusLabel(status);
  row.append(file, state);
  if (error) {
    row.title = error;
  } else if (outputPath) {
    row.title = outputPath;
  }
  return row;
}

function renderPendingResults(items) {
  clearElement(resultOutput);
  const list = document.createElement("div");
  list.className = "result-list";
  for (const item of items) {
    list.append(renderResultRow(item));
  }
  resultOutput.append(list);
}

async function folderImageItems(folderPath, status = "pending") {
  const recursive = includeSubfolders.checked;
  const cacheKey = `${folderPath}\n${recursive ? "1" : "0"}`;
  let images = folderImageCache.get(cacheKey);
  const params = new URLSearchParams({
    path: folderPath,
    recursive: recursive ? "true" : "false",
  });
  if (!images) {
    const data = await api(`/api/folder-images?${params.toString()}`);
    images = data.images;
    if (folderImageCache.size > 24) {
      folderImageCache.clear();
    }
    folderImageCache.set(cacheKey, images);
  }
  return images.map((image) => ({
    path: image.path,
    name: recursive ? image.relative_path : image.name,
    status,
  }));
}

async function renderFolderImages(folderPath, status = "pending") {
  const requestId = ++folderImageRequestId;
  try {
    const items = await folderImageItems(folderPath, status);
    if (requestId !== folderImageRequestId) {
      return items;
    }
    if (targetKind === "folder" && targetPath.value === folderPath) {
      const recursiveLabel = includeSubfolders.checked ? "하위 폴더 포함" : "선택 폴더만";
      targetSummary.textContent = `폴더가 선택되었습니다. 대상 이미지 ${items.length}개 (${recursiveLabel}).`;
    }
    if (items.length) {
      renderPendingResults(items);
      return items;
    }
    renderPendingResults([{ path: folderPath, name: "이미지 파일 없음", status: "failed" }]);
    return [];
  } catch (error) {
    if (requestId !== folderImageRequestId) {
      return [];
    }
    renderPendingResults([{ path: folderPath, name: `${fileNameFromPath(folderPath)} 폴더`, status }]);
    addWork(`폴더 이미지 목록을 읽을 수 없습니다: ${error.message}`, "error");
    return [];
  }
}

function renderDetails(data) {
  const details = document.createElement("details");
  details.className = "raw-details";
  const summary = document.createElement("summary");
  summary.textContent = "상세 정보 보기";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(data, null, 2);
  details.append(summary, pre);
  return details;
}

function renderSaveNotice(message, paths = []) {
  const box = document.createElement("div");
  box.className = "save-notice";
  const text = document.createElement("strong");
  text.textContent = message || "저장 위치를 확인하세요.";
  box.append(text);
  const firstPath = paths.find(Boolean);
  if (firstPath) {
    const path = document.createElement("span");
    path.textContent = firstPath;
    box.append(path);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ghost-button small-button";
    button.textContent = "결과 폴더 열기";
    button.addEventListener("click", async () => {
      try {
        await api("/api/open-path", { path: firstPath });
        addWork("결과 폴더를 열었습니다.", "done");
      } catch (error) {
        failWork(addWork("결과 폴더를 열 수 없습니다."), error);
      }
    });
    box.append(button);
  }
  return box;
}

function savedPathMessage(paths = []) {
  const count = paths.filter(Boolean).length;
  if (!count) {
    return "결과 파일이 생성되지 않았습니다.";
  }
  return count === 1 ? "결과 파일 저장 위치" : `결과 파일 ${count}개 저장 위치`;
}

function firstSavedPathText(paths = []) {
  const firstPath = paths.find(Boolean);
  return firstPath ? ` 저장 위치: ${firstPath}` : "";
}

function renderSingleResult(result) {
  return renderResultRow({
    path: result.image_path,
    status: result.status === "succeeded" ? "succeeded" : "failed",
    error: result.error,
  });
}

function appendBatchResult(batch) {
  const list = document.createElement("div");
  list.className = "result-list";
  const succeeded = batch.results.filter((item) => item.status === "succeeded").length;
  const summary = document.createElement("div");
  summary.className = "result-summary";
  summary.textContent = `전체 ${batch.results.length}개 · 완료 ${succeeded}개 · 실패 ${batch.results.length - succeeded}개`;
  summary.title = batch.output_dir || "";
  list.append(summary);
  for (const item of batch.results) {
    list.append(renderSingleResult(item));
  }
  resultOutput.append(list);
  if (batch.save_warning || batch.sidecar_paths?.length) {
    resultOutput.append(renderSaveNotice(batch.save_warning || savedPathMessage(batch.sidecar_paths || []), batch.sidecar_paths || []));
  }
}

function renderResult(data) {
  clearElement(resultOutput);

  if (typeof data === "string") {
    resultOutput.append(renderTextBlock(data));
    return;
  }

  if (data?.result) {
    const list = document.createElement("div");
    list.className = "result-list";
    list.append(renderSingleResult(data.result));
    resultOutput.append(list);
    if (data.save_warning || data.sidecar_path) {
      resultOutput.append(renderSaveNotice(data.save_warning || savedPathMessage([data.sidecar_path]), [data.sidecar_path]));
    }
    resultOutput.append(renderDetails(data));
    return;
  }

  if (data?.results) {
    appendBatchResult(data);
    resultOutput.append(renderDetails(data));
    return;
  }

  if (data?.["단일 이미지"] || data?.["폴더 배치"]) {
    const single = data["단일 이미지"];
    const batch = data["폴더 배치"];
    if (single?.result) {
      const list = document.createElement("div");
      list.className = "result-list";
      list.append(renderSingleResult(single.result));
      resultOutput.append(list);
    }
    if (batch?.results) {
      appendBatchResult(batch);
    }
    resultOutput.append(renderDetails(data));
    return;
  }

  resultOutput.append(renderDetails(data));
}

function timeLabel() {
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
}

function addWork(message, state = "running") {
  workCurrent.textContent = message;
  const item = document.createElement("li");
  item.className = state;
  const time = document.createElement("span");
  time.className = "work-time";
  time.textContent = timeLabel();
  const text = document.createElement("span");
  text.textContent = message;
  item.append(time, text);
  workLog.prepend(item);
  return item;
}

function finishWork(item, message, state = "done") {
  if (item) {
    item.className = state;
    item.querySelector("span:last-child").textContent = message;
  }
  workCurrent.textContent = message;
}

function failWork(item, error) {
  const message = error instanceof Error ? error.message : String(error);
  finishWork(item, `오류: ${message}`, "error");
}

function setBusy(isBusy) {
  loadBtn.disabled = isBusy;
  demoBtn.disabled = isBusy;
  runTargetBtn.disabled = isBusy;
  openFileBtn.disabled = isBusy;
  openFolderBtn.disabled = isBusy;
  for (const button of document.querySelectorAll("form button[type='submit']")) {
    button.disabled = isBusy;
  }
}

function summarizeHealth(data) {
  const health = data.health;
  const missing = Object.entries(health.dependencies_available)
    .filter(([, available]) => !available)
    .map(([name]) => name);
  return {
    "실행 모드": appConfig?.real_model ? "실제 모델" : "테스트 결과",
    "프로필": appConfig?.profile,
    "모델 로드": health.model_loaded ? "로드됨" : "아직 로드 안 됨",
    "GPU 백엔드": health.backend,
    "장치": health.device_name || "감지 안 됨",
    "누락 패키지": missing,
    "경고": health.warnings,
    "오류": health.errors,
  };
}

function renderDiagnosticItem(label, value, state = "neutral") {
  const item = document.createElement("button");
  item.type = "button";
  item.className = `diagnostic-item ${state}`;
  const title = document.createElement("span");
  title.className = "diagnostic-label";
  title.textContent = label;
  const body = document.createElement("strong");
  body.textContent = value;
  const badge = document.createElement("span");
  badge.className = "diagnostic-badge";
  badge.textContent = state === "ok" ? "정상" : state === "warn" ? "주의" : state === "error" ? "오류" : "정보";
  item.title = `${label}: ${value}`;
  item.append(title, body, badge);
  return item;
}

function renderDiagnostics(data) {
  const health = data.health;
  const missing = Object.entries(health.dependencies_available)
    .filter(([, available]) => !available)
    .map(([name]) => name);

  clearElement(healthOutput);
  healthOutput.append(
    renderDiagnosticItem("실행 모드", appConfig?.real_model ? "실제 JoyCaption 모델" : "테스트 모드", "neutral"),
    renderDiagnosticItem("모델 상태", health.model_loaded ? "로드 완료" : "로드 필요", health.model_loaded ? "ok" : "warn"),
    renderDiagnosticItem("실행 장치", health.device_name || health.backend, health.ok ? "ok" : "warn"),
    renderDiagnosticItem("필수 패키지", missing.length ? `${missing.length}개 누락` : "모두 준비됨", missing.length ? "warn" : "ok"),
  );

  if (health.warnings.length) {
    healthOutput.append(renderDiagnosticItem("경고", health.warnings.join(", "), "warn"));
  }
  if (health.errors.length) {
    healthOutput.append(renderDiagnosticItem("오류", health.errors.join(", "), "error"));
  }
  healthOutput.append(renderDetails(summarizeHealth(data)));
}

function renderDiagnosticsError(error) {
  const message = error instanceof Error ? error.message : String(error);
  clearElement(healthOutput);
  healthOutput.append(renderDiagnosticItem("진단 실패", message, "error"));
}

function updateStatusBadges(data) {
  const health = data.health;
  modelBadge.textContent = health.model_loaded ? "로드 완료" : "로드 필요";
  backendBadge.textContent = health.device_name
    ? `${health.backend} · ${health.device_name}`
    : health.backend;
}

function renderLoadStatus(status) {
  const state = status.state;
  loadPanel.dataset.state = state;
  loadMessage.textContent = status.error
    ? `${status.message}: ${status.error}`
    : status.message;
  loadMeta.textContent =
    state === "idle"
      ? "대기 중"
      : `상태: ${state} · 경과 ${status.elapsed_seconds ?? 0}초`;

  loadSpinner.classList.toggle("active", state === "loading");
  loadProgress.className = "progress-bar";
  if (state === "loading") {
    loadProgress.classList.add("active");
  } else if (state === "ready") {
    loadProgress.classList.add("done");
  } else if (state === "error") {
    loadProgress.classList.add("error");
  }
  setBusy(state === "loading");
}

async function refreshLoadStatus() {
  const status = await api("/api/load-status");
  renderLoadStatus(status);
  return status;
}

async function waitForModelLoad() {
  const workItem = addWork("모델 로드를 시작합니다.");
  let initialStatus;
  try {
    initialStatus = await api("/api/start-load-model", {});
    renderLoadStatus(initialStatus);
  } catch (error) {
    failWork(workItem, error);
    throw error;
  }

  if (initialStatus.state === "ready") {
    finishWork(workItem, "모델 로드가 완료되었습니다.");
    return initialStatus;
  }

  if (initialStatus.state === "error") {
    const error = new Error(initialStatus.error || initialStatus.message);
    failWork(workItem, error);
    throw error;
  }

  return new Promise((resolve, reject) => {
    if (loadPollTimer) {
      clearInterval(loadPollTimer);
    }
    loadPollTimer = setInterval(async () => {
      try {
        const status = await refreshLoadStatus();
        if (status.state === "ready") {
          clearInterval(loadPollTimer);
          loadPollTimer = null;
          finishWork(workItem, "모델 로드가 완료되었습니다.");
          resolve(status);
        } else if (status.state === "error") {
          clearInterval(loadPollTimer);
          loadPollTimer = null;
          const error = new Error(status.error || status.message);
          failWork(workItem, error);
          reject(error);
        }
      } catch (error) {
        clearInterval(loadPollTimer);
        loadPollTimer = null;
        failWork(workItem, error);
        reject(error);
      }
    }, 750);
  });
}

async function loadConfig() {
  appConfig = await api("/api/config");
}

async function prepareAppOnStartup() {
  const startupWork = addWork("앱 준비를 시작합니다.");
  setBusy(true);
  try {
    workCurrent.textContent = "시스템 진단을 실행하는 중입니다.";
    const diagnosisWork = addWork("시스템 진단을 실행하는 중입니다.");
    const health = await api("/api/health");
    updateStatusBadges(health);
    renderDiagnostics(health);
    if (!health.health.ok) {
      finishWork(diagnosisWork, "시스템 진단에서 확인이 필요한 항목이 있습니다.", "error");
      throw new Error("시스템 진단에서 오류가 발견되었습니다.");
    }
    finishWork(diagnosisWork, "시스템 진단이 완료되었습니다.");

    workCurrent.textContent = "모델 로드를 준비하는 중입니다.";
    const status = await refreshLoadStatus();
    if (status.state !== "ready") {
      await waitForModelLoad();
    } else {
      addWork("모델이 이미 로드되어 있습니다.", "done");
    }

    const readyHealth = await api("/api/health");
    updateStatusBadges(readyHealth);
    renderDiagnostics(readyHealth);
    finishWork(startupWork, "준비가 완료되었습니다. 파일이나 폴더를 선택해 생성할 수 있습니다.");
  } catch (error) {
    renderDiagnosticsError(error);
    failWork(startupWork, error);
  } finally {
    setBusy(false);
  }
}

healthBtn.addEventListener("click", async () => {
  const workItem = addWork("시스템 진단을 확인하는 중입니다.");
  try {
    const health = await api("/api/health");
    updateStatusBadges(health);
    renderDiagnostics(health);
    finishWork(workItem, "시스템 진단이 완료되었습니다.");
  } catch (error) {
    renderDiagnosticsError(error);
    failWork(workItem, error);
  }
});

loadBtn.addEventListener("click", async () => {
  try {
    await waitForModelLoad();
    renderResult("모델 로드가 완료되었습니다.");
    const health = await api("/api/health");
    updateStatusBadges(health);
    renderDiagnostics(health);
  } catch (error) {
    renderResult(`오류: ${error.message}`);
  }
});

clearWorkBtn.addEventListener("click", () => {
  workLog.textContent = "";
  workCurrent.textContent = "대기 중입니다.";
});

async function pickNativeTarget(kind) {
  if (requestNativeShellPath(kind)) {
    addWork(kind === "folder" ? "앱 셸에서 폴더 선택 창을 여는 중입니다." : "앱 셸에서 파일 선택 창을 여는 중입니다.");
    return;
  }
  const isFolder = kind === "folder";
  const workItem = addWork(isFolder ? "이미지 폴더 경로를 선택하는 중입니다." : "이미지 파일 경로를 선택하는 중입니다.");
  try {
    const result = await api(isFolder ? "/api/pick-folder" : "/api/pick-file", {});
    if (!result.path) {
      finishWork(workItem, "선택을 취소했습니다.");
      return;
    }
    setTarget(result.path, kind);
    if (isFolder) {
      batchForm.elements.input_dir.value = result.path;
      finishWork(workItem, "폴더 경로를 선택했습니다.");
    } else {
      singleForm.elements.image_path.value = result.path;
      finishWork(workItem, "파일 경로를 선택했습니다.");
    }
  } catch (error) {
    failWork(workItem, error);
  }
}

async function pickNativeDrop() {
  if (requestNativeShellPath("image")) {
    addWork("앱 셸에서 원본 경로 선택 창을 여는 중입니다.");
    return;
  }
  const workItem = addWork("원본 경로를 받을 드롭 창을 여는 중입니다.");
  try {
    const result = await api("/api/drop-path", {});
    if (!result.path) {
      finishWork(workItem, "드래그 선택을 취소했습니다.");
      return;
    }
    setTarget(result.path, result.kind);
    if (result.kind === "folder") {
      batchForm.elements.input_dir.value = result.path;
      finishWork(workItem, "드래그한 폴더의 원본 경로를 선택했습니다.");
    } else {
      singleForm.elements.image_path.value = result.path;
      finishWork(workItem, "드래그한 파일의 원본 경로를 선택했습니다.");
    }
  } catch (error) {
    failWork(workItem, error);
  }
}

openFileBtn.addEventListener("click", () => {
  pickNativeTarget("image");
});

openFolderBtn.addEventListener("click", () => {
  pickNativeTarget("folder");
});

dropZone.addEventListener("click", () => {
  pickNativeDrop();
});

fileInput.addEventListener("change", async () => {
  const workItem = addWork("이미지 파일을 불러오는 중입니다.");
  try {
    const result = await uploadFiles(fileInput.files, "image");
    setTarget(result.path, "image");
    singleForm.elements.image_path.value = result.path;
    finishWork(workItem, "이미지 파일을 불러왔습니다.");
  } catch (error) {
    failWork(workItem, error);
  } finally {
    fileInput.value = "";
  }
});

folderInput.addEventListener("change", async () => {
  const workItem = addWork("이미지 폴더를 불러오는 중입니다.");
  try {
    const result = await uploadFiles(folderInput.files, "folder");
    setTarget(result.path, "folder");
    batchForm.elements.input_dir.value = result.path;
    finishWork(workItem, `이미지 ${result.count}개를 불러왔습니다.`);
  } catch (error) {
    failWork(workItem, error);
  } finally {
    folderInput.value = "";
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}

dropZone.addEventListener("drop", async (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  pickNativeDrop();
  return;
  const files = await collectDroppedFiles(event.dataTransfer);
  const kind = files && files.length > 1 ? "folder" : "image";
  const workItem = addWork(kind === "folder" ? "드롭한 이미지들을 불러오는 중입니다." : "드롭한 이미지를 불러오는 중입니다.");
  try {
    const result = await uploadFiles(files, kind);
    setTarget(result.path, result.kind);
    if (result.kind === "folder") {
      batchForm.elements.input_dir.value = result.path;
      finishWork(workItem, `이미지 ${result.count}개를 불러왔습니다.`);
    } else {
      singleForm.elements.image_path.value = result.path;
      finishWork(workItem, "이미지를 불러왔습니다.");
    }
  } catch (error) {
    failWork(workItem, error);
  }
});

targetPath.addEventListener("change", () => {
  const inferredKind = inferTargetKind(targetPath.value);
  setTarget(targetPath.value, inferredKind);
  if (inferredKind === "folder") {
    batchForm.elements.input_dir.value = targetPath.value;
  } else {
    singleForm.elements.image_path.value = targetPath.value;
  }
});

runTargetBtn.addEventListener("click", () => {
  if (!targetPath.value) {
    renderResult("파일 또는 폴더를 먼저 선택하세요.");
    return;
  }
  const inferredKind = inferTargetKind(targetPath.value);
  setTarget(targetPath.value, inferredKind);
  if (inferredKind === "folder") {
    batchForm.elements.input_dir.value = targetPath.value;
    batchForm.elements.write_sidecars.checked = true;
    batchForm.requestSubmit();
  } else {
    singleForm.elements.image_path.value = targetPath.value;
    singleForm.elements.write_sidecar.checked = true;
    singleForm.requestSubmit();
  }
});

sampleImageBtn.addEventListener("click", () => {
  singleForm.elements.image_path.value = appConfig.sample_image;
  setTarget(appConfig.sample_image, "image");
  setImagePreview(appConfig.sample_image, "image");
  addWork("샘플 이미지 경로를 입력했습니다.", "done");
});

sampleFolderBtn.addEventListener("click", () => {
  batchForm.elements.input_dir.value = appConfig.sample_folder;
  setTarget(appConfig.sample_folder, "folder");
  setImagePreview(appConfig.sample_folder, "folder");
  addWork("샘플 폴더 경로를 입력했습니다.", "done");
});

singleForm.elements.image_path.addEventListener("change", () => {
  setTarget(singleForm.elements.image_path.value, "image");
  setImagePreview(singleForm.elements.image_path.value, "image");
});

batchForm.elements.input_dir.addEventListener("change", () => {
  setTarget(batchForm.elements.input_dir.value, "folder");
  setImagePreview(batchForm.elements.input_dir.value, "folder");
});

for (const control of [
  customPresetName,
  promptBaseType,
  promptLength,
  promptTone,
  tagFormat,
  promptLanguage,
  customPromptText,
  ...promptBuilder.querySelectorAll(".option-grid input"),
]) {
  control.addEventListener("input", updatePromptPreview);
  control.addEventListener("change", updatePromptPreview);
}

customPromptToggle.addEventListener("change", () => {
  if (customPromptToggle.checked) {
    openPromptModal();
  } else {
    closePromptModal({ keepEnabled: false });
  }
});
customPromptToggleBtn.addEventListener("click", () => {
  customPromptToggle.checked = !customPromptToggle.checked;
  customPromptToggle.dispatchEvent(new Event("change", { bubbles: true }));
});
promptBaseTypeBtn.addEventListener("click", togglePromptModeMenu);
savePresetBtn.addEventListener("click", saveCurrentPreset);
loadPresetBtn.addEventListener("click", loadSelectedPreset);
deletePresetBtn.addEventListener("click", deleteSelectedPreset);
closePromptBuilderBtn.addEventListener("click", () => {
  closePromptModal({ keepEnabled: false });
});
applyPromptBuilderBtn.addEventListener("click", () => closePromptModal());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !promptBaseTypeMenu.hidden) {
    closePromptModeMenu();
    return;
  }
  if (event.key === "Escape" && promptModalOpen) {
    closePromptModal();
  }
});
document.addEventListener("click", (event) => {
  if (!promptBaseTypeMenu.hidden && !event.target.closest(".prompt-mode-control")) {
    closePromptModeMenu();
  }
});
sidecarMode.addEventListener("change", updateSidecarModeControls);
combinedIncludeFilenamesBtn.addEventListener("click", () => {
  combinedIncludeFilenames.checked = !combinedIncludeFilenames.checked;
  combinedIncludeFilenames.dispatchEvent(new Event("change", { bubbles: true }));
});
combinedIncludeFilenames.addEventListener("change", () => {
  updateToggleButton(combinedIncludeFilenamesBtn, combinedIncludeFilenames.checked);
});
includeSubfoldersBtn.addEventListener("click", () => {
  includeSubfolders.checked = !includeSubfolders.checked;
  includeSubfolders.dispatchEvent(new Event("change", { bubbles: true }));
});
includeSubfolders.addEventListener("change", () => {
  updateToggleButton(includeSubfoldersBtn, includeSubfolders.checked);
  if (targetKind === "folder" && targetPath.value) {
    renderFolderImages(targetPath.value, "pending");
  }
});

demoBtn.addEventListener("click", async () => {
  const setupWork = addWork("샘플 테스트를 준비하는 중입니다.");
  try {
    singleForm.elements.image_path.value = appConfig.sample_image;
    batchForm.elements.input_dir.value = appConfig.sample_folder;
    setTarget(appConfig.sample_image, "image");
    setImagePreview(appConfig.sample_image, "image");
    await waitForModelLoad();
    finishWork(setupWork, "샘플 입력 준비가 완료되었습니다.");

    const singleMode = selectedMode();
    const batchMode = selectedMode();
    const singleWork = addWork("샘플 단일 이미지 태그를 생성하는 중입니다.");
    const single = await api("/api/generate", {
      image_path: singleForm.elements.image_path.value,
      mode: singleMode,
      preset_id: selectedPresetId(),
      postprocessor_ids: postprocessorsFor(singleMode),
      extra_options: generationPayloadOptions(),
      write_sidecar: true,
      sidecar_mode: sidecarMode.value,
      combined_include_filenames: combinedIncludeFilenames.checked,
    });
    finishWork(singleWork, "샘플 단일 이미지 태그 생성이 완료되었습니다.");

    const batchWork = addWork("샘플 폴더 배치를 실행하는 중입니다.");
    setImagePreview(batchForm.elements.input_dir.value, "folder");
    startPreviewPolling();
    const batch = await api("/api/batch", {
      input_dir: batchForm.elements.input_dir.value,
      mode: batchMode,
      preset_id: selectedPresetId(),
      postprocessor_ids: postprocessorsFor(batchMode),
      extra_options: generationPayloadOptions(),
      write_sidecars: true,
      sidecar_mode: sidecarMode.value,
      combined_include_filenames: combinedIncludeFilenames.checked,
      include_subfolders: includeSubfolders.checked,
    });
    await stopPreviewPolling();
    finishWork(batchWork, "샘플 폴더 배치가 완료되었습니다.");

    renderResult({ "단일 이미지": single, "폴더 배치": batch });
    const health = await api("/api/health");
    updateStatusBadges(health);
    renderDiagnostics(health);
    addWork("샘플 테스트가 완료되었습니다.", "done");
  } catch (error) {
    await stopPreviewPolling();
    renderResult(`오류: ${error.message}`);
    failWork(setupWork, error);
  }
});

singleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(singleForm);
  const mode = selectedMode();
  const imagePath = form.get("image_path");
  setImagePreview(imagePath, "image");
  renderPendingResults([{ path: imagePath, status: "running" }]);
  const workItem = addWork("단일 이미지 태그를 생성하는 중입니다.");
  try {
    const result = await api("/api/generate", {
      image_path: imagePath,
      mode,
      preset_id: selectedPresetId(),
      postprocessor_ids: postprocessorsFor(mode),
      extra_options: generationPayloadOptions(),
      write_sidecar: form.get("write_sidecar") === "on",
      sidecar_mode: sidecarMode.value,
      combined_include_filenames: combinedIncludeFilenames.checked,
    });
    renderResult(result);
    finishWork(workItem, `단일 이미지 태그 생성이 완료되었습니다.${firstSavedPathText([result.sidecar_path])}`);
  } catch (error) {
    renderResult(`오류: ${error.message}`);
    failWork(workItem, error);
  }
});

batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(batchForm);
  const mode = selectedMode();
  const inputDir = form.get("input_dir");
  setImagePreview(inputDir, "folder");
  await renderFolderImages(inputDir, "running");
  const workItem = addWork("폴더 배치를 실행하는 중입니다.");
  try {
    startPreviewPolling();
    const result = await api("/api/batch", {
      input_dir: inputDir,
      mode,
      preset_id: selectedPresetId(),
      postprocessor_ids: postprocessorsFor(mode),
      extra_options: generationPayloadOptions(),
      write_sidecars: form.get("write_sidecars") === "on",
      sidecar_mode: sidecarMode.value,
      combined_include_filenames: combinedIncludeFilenames.checked,
      include_subfolders: includeSubfolders.checked,
    });
    await stopPreviewPolling();
    renderResult(result);
    finishWork(workItem, `폴더 배치가 완료되었습니다.${firstSavedPathText(result.sidecar_paths || [])}`);
  } catch (error) {
    await stopPreviewPolling();
    renderResult(`오류: ${error.message}`);
    failWork(workItem, error);
  }
});

loadConfig()
  .then(() => {
    singleForm.elements.image_path.value = appConfig.sample_image;
    batchForm.elements.input_dir.value = appConfig.sample_folder;
    setTarget(appConfig.sample_image, "image");
    setImagePreview(appConfig.sample_image, "image");
    renderSavedPresetList();
    renderPromptModeMenu();
    updateSidecarModeControls();
    updatePromptPreview();
    prepareAppOnStartup();
  })
  .catch((error) => {
    renderDiagnosticsError(error);
    addWork(`초기화 오류: ${error.message}`, "error");
  });
