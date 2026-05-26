const state = {
  hideFile: null,
  hideImageBase64: "",
  bmp: null,
  outputUrl: "",
  extractFile: null,
  extractImageBase64: "",
};

const els = {
  serverStatus: document.querySelector("#server-status"),
  hideImage: document.querySelector("#hide-image"),
  imageReport: document.querySelector("#image-report"),
  secretText: document.querySelector("#secret-text"),
  textCounter: document.querySelector("#text-counter"),
  hideButton: document.querySelector("#hide-button"),
  outputReport: document.querySelector("#output-report"),
  downloadLink: document.querySelector("#download-link"),
  extractImage: document.querySelector("#extract-image"),
  extractButton: document.querySelector("#extract-button"),
  extractResult: document.querySelector("#extract-result"),
};

const encoder = new TextEncoder();

checkServer();

els.hideImage.addEventListener("change", async (event) => {
  resetOutput();
  const file = event.target.files?.[0];
  state.hideFile = file || null;
  state.bmp = null;
  state.hideImageBase64 = "";

  if (!file) {
    els.imageReport.textContent = "还没有选择图片。";
    updateTextCounter();
    return;
  }

  try {
    state.hideImageBase64 = await fileToBase64(file);
    const result = await postJson("/api/analyze", {
      filename: file.name,
      imageBase64: state.hideImageBase64,
    });
    state.bmp = result.bmp;
    els.imageReport.textContent = formatBmpReport(result.bmp);
  } catch (error) {
    els.imageReport.innerHTML = `<span class="warning">${escapeHtml(error.message)}</span>`;
  }

  updateTextCounter();
});

els.secretText.addEventListener("input", updateTextCounter);

els.hideButton.addEventListener("click", async () => {
  if (!state.hideFile || !state.hideImageBase64) return;
  resetOutput();
  els.hideButton.disabled = true;
  els.outputReport.textContent = "正在处理图片...";

  try {
    const result = await postJson("/api/hide", {
      filename: state.hideFile.name,
      imageBase64: state.hideImageBase64,
      text: els.secretText.value,
    });
    const blob = base64ToBlob(result.imageBase64, "image/bmp");
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
  state.extractImageBase64 = "";
  els.extractResult.textContent = "还没有提取结果。";
  els.extractButton.disabled = true;

  if (!file) return;

  try {
    state.extractImageBase64 = await fileToBase64(file);
    els.extractButton.disabled = false;
  } catch (error) {
    els.extractResult.textContent = error.message;
  }
});

els.extractButton.addEventListener("click", async () => {
  if (!state.extractImageBase64) return;
  els.extractButton.disabled = true;
  els.extractResult.textContent = "正在提取...";

  try {
    const result = await postJson("/api/extract", {
      filename: state.extractFile?.name || "",
      imageBase64: state.extractImageBase64,
    });
    els.extractResult.textContent = result.text || "(隐藏文本为空)";
  } catch (error) {
    els.extractResult.textContent = error.message;
  } finally {
    els.extractButton.disabled = false;
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
  const limit = state.bmp?.max_text_bytes ?? 0;
  const hasImage = Boolean(state.hideFile && state.hideImageBase64 && state.bmp);
  const fits = hasImage && bytes <= limit;

  if (!hasImage) {
    els.textCounter.textContent = `${bytes} 字节；请先选择可用 BMP 图片`;
    els.hideButton.disabled = true;
    return;
  }

  els.textCounter.textContent = `${bytes} / ${limit} 字节`;
  els.textCounter.classList.toggle("warning", !fits);
  els.hideButton.disabled = !fits;
}

function resetOutput() {
  if (state.outputUrl) URL.revokeObjectURL(state.outputUrl);
  state.outputUrl = "";
  els.downloadLink.removeAttribute("href");
  els.downloadLink.classList.add("hidden");
  els.outputReport.textContent = "处理完成后会在这里出现下载按钮。";
}

function formatBmpReport(bmp) {
  return [
    "识别成功：24 位无压缩 BMP",
    `尺寸：${bmp.width} x ${Math.abs(bmp.height)} 像素`,
    `像素区起点：第 ${bmp.pixel_offset} 字节`,
    `可写像素数据：${bmp.pixel_byte_count} 字节`,
    `理论隐写容量：${bmp.capacity_bytes} 字节`,
    `当前文本上限：${bmp.max_text_bytes} 字节`,
  ].join("\n");
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
