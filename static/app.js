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
  imageShift: document.querySelector("#image-shift"),
  textCounter: document.querySelector("#text-counter"),
  hideButton: document.querySelector("#hide-button"),
  outputReport: document.querySelector("#output-report"),
  downloadLink: document.querySelector("#download-link"),
  extractImage: document.querySelector("#extract-image"),
  imageExtractShift: document.querySelector("#image-extract-shift"),
  extractButton: document.querySelector("#extract-button"),
  extractResult: document.querySelector("#extract-result"),
  audioFile: document.querySelector("#audio-file"),
  audioReport: document.querySelector("#audio-report"),
  audioSecretText: document.querySelector("#audio-secret-text"),
  audioShift: document.querySelector("#audio-shift"),
  audioTextCounter: document.querySelector("#audio-text-counter"),
  audioHideButton: document.querySelector("#audio-hide-button"),
  audioOutputReport: document.querySelector("#audio-output-report"),
  audioDownloadLink: document.querySelector("#audio-download-link"),
  audioExtractFile: document.querySelector("#audio-extract-file"),
  audioExtractShift: document.querySelector("#audio-extract-shift"),
  audioExtractButton: document.querySelector("#audio-extract-button"),
  audioExtractResult: document.querySelector("#audio-extract-result"),
};

const encoder = new TextEncoder();

checkServer();
bindEntryNavigation();
loadNasaApod();
loadAudioRecommendation();

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
      shift: readShift(els.imageShift),
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
  els.extractResult.textContent = "还没有解码结果。";
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
  els.extractResult.textContent = "正在解码...";

  try {
    const result = await postJson("/api/image/extract", {
      filename: state.extractFile?.name || "",
      imageBase64: state.extractBase64,
      shift: readShift(els.imageExtractShift),
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
      shift: readShift(els.audioShift),
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
  els.audioExtractResult.textContent = "还没有解码结果。";
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
  els.audioExtractResult.textContent = "正在解码...";

  try {
    const result = await postJson("/api/audio/extract", {
      filename: state.audioExtractFile?.name || "",
      audioBase64: state.audioExtractBase64,
      shift: readShift(els.audioExtractShift),
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

function bindEntryNavigation() {
  document.querySelectorAll(".entry-card[href^='#']").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.querySelector(link.getAttribute("href"));
      if (!target) return;
      window.setTimeout(() => {
        target.classList.remove("is-jump-target");
        void target.offsetWidth;
        target.classList.add("is-jump-target");
      }, 260);
    });
  });
}

async function loadNasaApod() {
  const title = document.querySelector("#nasa-apod-title");
  const date = document.querySelector("#nasa-date");
  const desc = document.querySelector("#nasa-apod-desc");
  const image = document.querySelector("#nasa-apod-image");
  const credit = document.querySelector("#nasa-credit");
  const sourceLink = document.querySelector("#nasa-source-link");
  const imageLink = document.querySelector("#nasa-image-link");
  if (!title || !date || !desc || !image || !credit || !sourceLink || !imageLink) return;

  try {
    const response = await fetch(`/static/data/nasa_apod.json?ts=${Date.now()}`);
    if (!response.ok) throw new Error("NASA 推荐数据读取失败");
    const apod = await response.json();

    title.textContent = apod.title || "NASA 今日天文图";
    date.textContent = formatNasaDate(apod);
    desc.textContent = formatNasaDescription(apod);
    credit.textContent = apod.copyright ? `来源：${apod.copyright}` : "来源：NASA APOD";
    sourceLink.href = apod.sourceUrl || "https://apod.nasa.gov/apod/astropix.html";

    const imageUrl = apod.cachedImageUrl || apod.imageUrl || apod.thumbnailUrl;
    const imageVersion = apod.fetchedAt || apod.date || Date.now();
    if ((apod.status === "ready" || apod.status === "stale") && imageUrl) {
      image.src = cacheBustedLocalUrl(imageUrl, imageVersion);
      image.onload = () => image.classList.add("is-loaded");
      image.onerror = () => {
        image.removeAttribute("src");
        image.classList.remove("is-loaded");
        desc.textContent = "NASA 图片地址暂时无法加载，可以打开 NASA 页面查看。";
      };
      imageLink.href = cacheBustedLocalUrl(apod.cachedImageUrl || apod.hdImageUrl || imageUrl, imageVersion);
      imageLink.classList.remove("hidden");
    } else {
      image.removeAttribute("src");
      image.classList.remove("is-loaded");
      imageLink.classList.add("hidden");
    }
  } catch (error) {
    title.textContent = "NASA 今日天文图暂不可用";
    date.textContent = "等待 GitHub Actions 下次自动更新";
    desc.textContent = error.message || "推荐数据读取失败。";
    credit.textContent = "NASA APOD";
    image.removeAttribute("src");
    image.classList.remove("is-loaded");
    imageLink.classList.add("hidden");
  }
}

function formatNasaDate(apod) {
  if (!apod?.date) return "NASA APOD";
  const fetched = apod.fetchedAt ? `；自动更新 ${formatDateTime(apod.fetchedAt)}` : "";
  return `NASA APOD ${apod.date}${fetched}`;
}

function formatDateTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-CN", {
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatNasaDescription(apod) {
  if (apod?.status === "not_image") {
    return "今日 APOD 不是图片，暂不作为图片隐写素材。可以打开 NASA 页面查看当天内容。";
  }
  if (apod?.status === "stale") {
    return "本次自动更新失败，当前展示的是上一张可用 NASA 天文图。";
  }
  if (apod?.status === "error") {
    return apod.error ? `抓取失败：${apod.error}` : "NASA 数据暂时不可用，等待下次自动更新。";
  }
  const explanation = apod?.explanation || "每日自动更新，适合作为图片隐写演示素材。";
  return explanation.length > 180 ? `${explanation.slice(0, 180)}...` : explanation;
}

async function loadAudioRecommendation() {
  const date = document.querySelector("#audio-recommend-date");
  const title = document.querySelector("#audio-recommend-name");
  const desc = document.querySelector("#audio-recommend-desc");
  const player = document.querySelector("#audio-recommend-player");
  const meta = document.querySelector("#audio-recommend-meta");
  const sourceLink = document.querySelector("#audio-recommend-source-link");
  const downloadLink = document.querySelector("#audio-recommend-download-link");
  if (!date || !title || !desc || !player || !meta || !sourceLink || !downloadLink) return;

  try {
    const response = await fetch(`/static/data/audio_recommendation.json?ts=${Date.now()}`);
    if (!response.ok) throw new Error("音频推荐数据读取失败");
    const audio = await response.json();

    title.textContent = audio.title || "今日音频推荐";
    date.textContent = formatAudioRecommendationDate(audio);
    desc.textContent = formatAudioRecommendationDescription(audio);
    meta.textContent = formatAudioRecommendationMeta(audio);
    sourceLink.href = audio.sourceUrl || "https://music.apple.com/cn/new";

    const audioUrl = audio.cachedAudioUrl || audio.audioUrl;
    const audioVersion = audio.fetchedAt || audio.date || Date.now();
    if ((audio.status === "ready" || audio.status === "stale") && audioUrl) {
      player.src = cacheBustedLocalUrl(audioUrl, audioVersion);
      downloadLink.href = cacheBustedLocalUrl(audioUrl, audioVersion);
      downloadLink.download = audio.cachedFilename || "audio-recommendation.m4a";
      downloadLink.classList.remove("hidden");
    } else {
      player.removeAttribute("src");
      downloadLink.classList.add("hidden");
    }
  } catch (error) {
    title.textContent = "今日音频推荐暂不可用";
    date.textContent = "等待 GitHub Actions 下次自动更新";
    desc.textContent = error.message || "推荐数据读取失败。";
    meta.textContent = "榜单试听片段";
    player.removeAttribute("src");
    downloadLink.classList.add("hidden");
  }
}

function cacheBustedLocalUrl(url, version) {
  if (!url || !url.startsWith("/")) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${encodeURIComponent(version)}`;
}

function formatAudioRecommendationDate(audio) {
  if (!audio?.date) return "Apple Music 榜单试听";
  const fetched = audio.fetchedAt ? `；自动更新 ${formatDateTime(audio.fetchedAt)}` : "";
  const source = audio.chartName || audio.source || "Apple Music 榜单试听";
  const rank = audio.chartRank ? ` #${audio.chartRank}` : "";
  return `${source}${rank} ｜ ${audio.date}${fetched}`;
}

function formatAudioRecommendationDescription(audio) {
  if (audio?.status === "stale") {
    return "本次自动更新失败，当前展示的是上一段可用音频。";
  }
  if (audio?.status === "error") {
    return audio.error ? `抓取失败：${audio.error}` : "音频推荐暂时不可用，等待下次自动更新。";
  }
  return audio?.description || "每日自动更新，适合作为音频隐写演示素材。";
}

function formatAudioRecommendationMeta(audio) {
  const parts = [];
  if (audio?.artist) parts.push(`歌手：${audio.artist}`);
  if (audio?.album) parts.push(`专辑：${audio.album}`);
  if (audio?.durationSeconds) parts.push(`时长：${formatDuration(audio.durationSeconds)}`);
  return parts.join(" ｜ ") || "榜单试听片段";
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
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
    els.audioTextCounter.textContent = `${bytes} 字节；请先选择 WAV、MP3 或 M4A 音频`;
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
  if (value === "M4A") return "M4A";
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
  if (value === "M4A 已解码为 PCM WAV") return value;
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

function readShift(input) {
  const value = Number.parseInt(input?.value ?? "0", 10);
  if (!Number.isInteger(value) || value < 0 || value > 255) {
    throw new Error("凯撒偏移量必须是 0 到 255 之间的整数");
  }
  return value;
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
  const canvas = document.querySelector("#particle-canvas");
  if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const context = canvas.getContext("2d");
  const pointer = { x: 0, y: 0, active: false };
  let particles = [];
  let width = 0;
  let height = 0;
  let pixelRatio = 1;

  function resize() {
    pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * pixelRatio);
    canvas.height = Math.floor(height * pixelRatio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    createParticles();
  }

  function createParticles() {
    const count = Math.max(120, Math.min(260, Math.floor((width * height) / 7600)));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.34,
      vy: (Math.random() - 0.5) * 0.34,
      radius: Math.random() * 2.3 + 1.2,
      glow: Math.random() * 0.18 + 0.34,
    }));
  }

  function moveParticle(particle) {
    particle.x += particle.vx;
    particle.y += particle.vy;

    if (pointer.active) {
      const dx = particle.x - pointer.x;
      const dy = particle.y - pointer.y;
      const distance = Math.hypot(dx, dy);
      if (distance < 190 && distance > 0) {
        const force = (190 - distance) / 190;
        particle.x += (dx / distance) * force * 0.72;
        particle.y += (dy / distance) * force * 0.72;
      }
    }

    if (particle.x < -20) particle.x = width + 20;
    if (particle.x > width + 20) particle.x = -20;
    if (particle.y < -20) particle.y = height + 20;
    if (particle.y > height + 20) particle.y = -20;
  }

  function draw() {
    context.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i += 1) {
      const current = particles[i];
      moveParticle(current);

      context.beginPath();
      context.arc(current.x, current.y, current.radius, 0, Math.PI * 2);
      context.shadowBlur = 10;
      context.shadowColor = "rgba(0, 122, 255, 0.34)";
      context.fillStyle = `rgba(0, 122, 255, ${current.glow})`;
      context.fill();
      context.shadowBlur = 0;

      for (let j = i + 1; j < particles.length; j += 1) {
        const next = particles[j];
        const distance = Math.hypot(current.x - next.x, current.y - next.y);
        if (distance < 136) {
          context.strokeStyle = `rgba(0, 122, 255, ${0.26 * (1 - distance / 136)})`;
          context.lineWidth = 1.15;
          context.beginPath();
          context.moveTo(current.x, current.y);
          context.lineTo(next.x, next.y);
          context.stroke();
        }
      }
    }

    window.requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", (event) => {
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    pointer.active = true;
  });
  window.addEventListener("pointerleave", () => {
    pointer.active = false;
  });

  resize();
  draw();
})();
