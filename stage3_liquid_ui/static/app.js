const state = {
  sourceFile: null,
  sourceBase64: "",
  image: null,
  outputUrl: "",
  extractFile: null,
  extractBase64: "",
  audioFile: null,
  audioBase64: "",
  audio: null,
  audioOutputUrl: "",
  audioExtractFile: null,
  audioExtractBase64: "",
};

const els = {
  serverStatus: document.querySelector("#server-status"),
  sourceImage: document.querySelector("#source-image"),
  imageReport: document.querySelector("#image-report"),
  secretText: document.querySelector("#secret-text"),
  textCounter: document.querySelector("#text-counter"),
  hideButton: document.querySelector("#hide-button"),
  outputReport: document.querySelector("#output-report"),
  downloadLink: document.querySelector("#download-link"),
  extractImage: document.querySelector("#extract-image"),
  extractButton: document.querySelector("#extract-button"),
  extractResult: document.querySelector("#extract-result"),
  audioFile: document.querySelector("#audio-file"),
  audioReport: document.querySelector("#audio-report"),
  audioSecretText: document.querySelector("#audio-secret-text"),
  audioTextCounter: document.querySelector("#audio-text-counter"),
  audioHideButton: document.querySelector("#audio-hide-button"),
  audioOutputReport: document.querySelector("#audio-output-report"),
  audioDownloadLink: document.querySelector("#audio-download-link"),
  audioExtractFile: document.querySelector("#audio-extract-file"),
  audioExtractButton: document.querySelector("#audio-extract-button"),
  audioExtractResult: document.querySelector("#audio-extract-result"),
};

const encoder = new TextEncoder();

checkServer();

els.sourceImage.addEventListener("change", async (event) => {
  resetOutput();
  const file = event.target.files?.[0];
  state.sourceFile = file || null;
  state.sourceBase64 = "";
  state.image = null;

  if (!file) {
    els.imageReport.textContent = "还没有选择图片。";
    updateTextCounter();
    return;
  }

  try {
    state.sourceBase64 = await fileToBase64(file);
    const result = await postJson("/api/image/analyze", {
      filename: file.name,
      imageBase64: state.sourceBase64,
    });
    state.image = result.image;
    els.imageReport.textContent = formatImageReport(result.image);
  } catch (error) {
    els.imageReport.innerHTML = `<span class="warning">${escapeHtml(error.message)}</span>`;
  }

  updateTextCounter();
});

els.secretText.addEventListener("input", updateTextCounter);

els.hideButton.addEventListener("click", async () => {
  if (!state.sourceFile || !state.sourceBase64) return;
  resetOutput();
  els.hideButton.disabled = true;
  els.outputReport.textContent = "正在生成 PNG...";

  try {
    const result = await postJson("/api/image/hide", {
      filename: state.sourceFile.name,
      imageBase64: state.sourceBase64,
      text: els.secretText.value,
    });
    const blob = base64ToBlob(result.imageBase64, "image/png");
    state.outputUrl = URL.createObjectURL(blob);
    els.downloadLink.href = state.outputUrl;
    els.downloadLink.download = result.filename;
    els.downloadLink.classList.remove("hidden");
    els.outputReport.textContent = `处理完成。\n写入文本：${result.textBytes} 字节\n输出文件：${result.filename}`;
  } catch (error) {
    els.outputReport.innerHTML = `<span class="warning">${escapeHtml(error.message)}</span>`;
  } finally {
    updateTextCounter();
  }
});

els.extractImage.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  state.extractFile = file || null;
  state.extractBase64 = "";
  els.extractResult.textContent = "还没有提取结果。";
  els.extractButton.disabled = true;

  if (!file) return;

  try {
    state.extractBase64 = await fileToBase64(file);
    els.extractButton.disabled = false;
  } catch (error) {
    els.extractResult.textContent = error.message;
  }
});

els.extractButton.addEventListener("click", async () => {
  if (!state.extractBase64) return;
  els.extractButton.disabled = true;
  els.extractResult.textContent = "正在提取...";

  try {
    const result = await postJson("/api/image/extract", {
      filename: state.extractFile?.name || "",
      imageBase64: state.extractBase64,
    });
    els.extractResult.textContent = result.text || "(隐藏文本为空)";
  } catch (error) {
    els.extractResult.textContent = error.message;
  } finally {
    els.extractButton.disabled = false;
  }
});

els.audioFile.addEventListener("change", async (event) => {
  resetAudioOutput();
  const file = event.target.files?.[0];
  state.audioFile = file || null;
  state.audioBase64 = "";
  state.audio = null;

  if (!file) {
    els.audioReport.textContent = "还没有选择音频。";
    updateAudioTextCounter();
    return;
  }

  try {
    state.audioBase64 = await fileToBase64(file);
    const result = await postJson("/api/audio/analyze", {
      filename: file.name,
      audioBase64: state.audioBase64,
    });
    state.audio = result.audio;
    els.audioReport.textContent = formatAudioReport(result.audio);
  } catch (error) {
    els.audioReport.innerHTML = `<span class="warning">${escapeHtml(error.message)}</span>`;
  }

  updateAudioTextCounter();
});

els.audioSecretText.addEventListener("input", updateAudioTextCounter);

els.audioHideButton.addEventListener("click", async () => {
  if (!state.audioFile || !state.audioBase64) return;
  resetAudioOutput();
  els.audioHideButton.disabled = true;
  els.audioOutputReport.textContent = "正在生成 WAV...";

  try {
    const result = await postJson("/api/audio/hide", {
      filename: state.audioFile.name,
      audioBase64: state.audioBase64,
      text: els.audioSecretText.value,
    });
    const blob = base64ToBlob(result.audioBase64, "audio/wav");
    state.audioOutputUrl = URL.createObjectURL(blob);
    els.audioDownloadLink.href = state.audioOutputUrl;
    els.audioDownloadLink.download = result.filename;
    els.audioDownloadLink.classList.remove("hidden");
    els.audioOutputReport.textContent = `处理完成。\n写入文本：${result.textBytes} 字节\n输出文件：${result.filename}`;
  } catch (error) {
    els.audioOutputReport.innerHTML = `<span class="warning">${escapeHtml(error.message)}</span>`;
  } finally {
    updateAudioTextCounter();
  }
});

els.audioExtractFile.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  state.audioExtractFile = file || null;
  state.audioExtractBase64 = "";
  els.audioExtractResult.textContent = "还没有提取结果。";
  els.audioExtractButton.disabled = true;

  if (!file) return;

  try {
    state.audioExtractBase64 = await fileToBase64(file);
    els.audioExtractButton.disabled = false;
  } catch (error) {
    els.audioExtractResult.textContent = error.message;
  }
});

els.audioExtractButton.addEventListener("click", async () => {
  if (!state.audioExtractBase64) return;
  els.audioExtractButton.disabled = true;
  els.audioExtractResult.textContent = "正在提取...";

  try {
    const result = await postJson("/api/audio/extract", {
      filename: state.audioExtractFile?.name || "",
      audioBase64: state.audioExtractBase64,
    });
    els.audioExtractResult.textContent = result.text || "(隐藏文本为空)";
  } catch (error) {
    els.audioExtractResult.textContent = error.message;
  } finally {
    els.audioExtractButton.disabled = false;
  }
});

async function checkServer() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("服务异常");
    els.serverStatus.textContent = "服务正常";
    els.serverStatus.classList.add("ok");
  } catch {
    els.serverStatus.textContent = "服务不可用";
    els.serverStatus.classList.add("bad");
  }
}

function updateTextCounter() {
  const bytes = encoder.encode(els.secretText.value).length;
  const limit = state.image?.max_text_bytes ?? 0;
  const hasImage = Boolean(state.sourceFile && state.sourceBase64 && state.image);
  const fits = hasImage && bytes <= limit;

  if (!hasImage) {
    els.textCounter.textContent = `${bytes} 字节；请先选择 JPG、BMP 或 PNG 图片`;
    els.hideButton.disabled = true;
    return;
  }

  els.textCounter.textContent = `${bytes} / ${limit} 字节`;
  els.textCounter.classList.toggle("warning", !fits);
  els.hideButton.disabled = !fits;
}

function updateAudioTextCounter() {
  const bytes = encoder.encode(els.audioSecretText.value).length;
  const limit = state.audio?.max_text_bytes ?? 0;
  const hasAudio = Boolean(state.audioFile && state.audioBase64 && state.audio);
  const fits = hasAudio && bytes <= limit;

  if (!hasAudio) {
    els.audioTextCounter.textContent = `${bytes} 字节；请先选择 WAV 或 MP3 音频`;
    els.audioHideButton.disabled = true;
    return;
  }

  els.audioTextCounter.textContent = `${bytes} / ${limit} 字节`;
  els.audioTextCounter.classList.toggle("warning", !fits);
  els.audioHideButton.disabled = !fits;
}

function resetOutput() {
  if (state.outputUrl) URL.revokeObjectURL(state.outputUrl);
  state.outputUrl = "";
  els.downloadLink.removeAttribute("href");
  els.downloadLink.classList.add("hidden");
  els.outputReport.textContent = "处理完成后会在这里出现下载按钮。";
}

function resetAudioOutput() {
  if (state.audioOutputUrl) URL.revokeObjectURL(state.audioOutputUrl);
  state.audioOutputUrl = "";
  els.audioDownloadLink.removeAttribute("href");
  els.audioDownloadLink.classList.add("hidden");
  els.audioOutputReport.textContent = "处理完成后会在这里出现下载按钮。";
}

function formatImageReport(image) {
  return [
    `识别成功：${formatImageFormat(image.input_format)} 输入，PNG 输出`,
    `尺寸：${image.width} x ${image.height} 像素`,
    `原始模式：${formatColorMode(image.source_mode)}`,
    `处理模式：${formatColorMode(image.working_mode)}`,
    `可写像素数据：${image.pixel_byte_count} 字节`,
    `理论隐写容量：${image.capacity_bytes} 字节`,
    `当前文本上限：${image.max_text_bytes} 字节`,
  ].join("\n");
}

function formatAudioReport(audio) {
  return [
    `识别成功：${formatAudioFormat(audio.input_format)} 输入，WAV 输出`,
    `转换方式：${formatConversion(audio.conversion)}`,
    `声道数：${audio.channels}`,
    `采样率：${audio.sample_rate} Hz`,
    `位深：${audio.bits_per_sample} bit`,
    `时长：${audio.duration_seconds} 秒`,
    `音频数据区：${audio.data_byte_count} 字节`,
    `可用采样槽：${audio.sample_slot_count}`,
    `理论隐写容量：${audio.capacity_bytes} 字节`,
    `当前文本上限：${audio.max_text_bytes} 字节`,
  ].join("\n");
}

function formatImageFormat(value) {
  if (value === "JPEG") return "JPG";
  if (value === "PNG") return "PNG";
  if (value === "BMP") return "BMP";
  return "未知格式";
}

function formatAudioFormat(value) {
  if (value === "WAV") return "WAV";
  if (value === "MP3") return "MP3";
  return "未知格式";
}

function formatColorMode(value) {
  const map = {
    RGB: "RGB 真彩色",
    RGBA: "RGBA 带透明通道",
    L: "灰度",
    P: "调色板",
    CMYK: "CMYK 印刷色",
  };
  return map[value] || value || "未知";
}

function formatConversion(value) {
  if (value === "无需转换") return value;
  if (value === "MP3 已解码为 PCM WAV") return value;
  if (value === "none") return "无需转换";
  if (value === "MP3 decoded to PCM WAV") return "MP3 已解码为 PCM WAV";
  return value || "未知";
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function fileToBase64(file) {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function base64ToBlob(base64, type) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

(() => {
  const root = document.documentElement;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  let frame = null;
  let nextX = 50;
  let nextY = 18;

  function updatePointer() {
    root.style.setProperty("--pointer-x", `${nextX}%`);
    root.style.setProperty("--pointer-y", `${nextY}%`);
    frame = null;
  }

  window.addEventListener("pointermove", (event) => {
    nextX = (event.clientX / window.innerWidth) * 100;
    nextY = (event.clientY / window.innerHeight) * 100;
    if (!frame) {
      frame = window.requestAnimationFrame(updatePointer);
    }
  });
})();
