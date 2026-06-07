# 多媒体隐写工作台

这是一个面向课程展示的多媒体隐写网页项目。当前版本包含图片隐写、图片解码、音频隐写、音频解码、凯撒加密、NASA 今日图片推荐和 Apple Music 榜单试听片段推荐。

面向用户的网页提示和错误提示均已中文化；接口字段名仍保留英文，方便代码调用。

图片隐写：

1. 输入 JPG、BMP 或 PNG 图片
2. 后端统一解码为 RGB 像素
3. 在 RGB 像素字节最低 2 位写入文本
4. 输出 PNG 图片
5. 再上传 PNG 提取隐藏文本

音频隐写：

1. 输入 WAV、MP3 或 M4A 音频
2. WAV 直接读取 PCM 采样数据
3. MP3、M4A 先通过 ffmpeg 解码为 PCM WAV
4. 在 WAV 采样低字节最低 2 位写入文本
5. 输出 WAV 音频
6. 再上传 WAV 提取隐藏文本

## 凯撒加密

图片隐写和音频隐写都支持凯撒偏移量。隐藏时流程是：

```text
输入文本 -> UTF-8 字节级凯撒加密 -> LSB 隐写
```

解码时流程是：

```text
LSB 提取密文字节 -> 使用同一个偏移量解密 -> 输出原文
```

这里不是只移动英文字母，而是对 UTF-8 字节做循环偏移，所以中文、数字、标点和 emoji 都会被加密。偏移量范围是 `0-255`，其中 `0` 表示不加密，也能兼容旧的未加密隐写文件。

## 为什么输出 PNG

JPG 是有损压缩，会破坏最低位信息。PNG 是无损格式，可以保存被改过的像素最低位，所以本迭代统一输出 PNG。

## 为什么 MP3/M4A 输出 WAV

MP3 和 M4A 都是压缩格式，重新编码容易破坏采样最低位。为了让隐写结果稳定，它们只作为输入格式，后端会先把它们解码成 PCM WAV，再进行 WAV LSB 隐写，最终输出 WAV。

## 运行

在本目录运行：

```bash
pip install -r requirements.txt
python run_server.py
```

默认地址：

```text
http://127.0.0.1:8032
```

如果端口被占用：

```bash
python run_server.py --port 8042
```

MP3 和 M4A 输入需要安装 ffmpeg，并确保 `ffmpeg` 命令可用。如果本机通过 winget 安装了 FFmpeg，本项目也会尝试自动寻找 winget 安装路径。

## NASA 今日图片推荐

前端首页会读取：

```text
static/data/nasa_apod.json
```

这个文件由脚本自动生成：

```bash
python scripts/fetch_nasa_apod.py
```

脚本会同时缓存一份推荐图到：

```text
static/data/nasa_apod_image.*
```

仓库里还准备了 GitHub Actions：

```text
.github/workflows/update-nasa-apod.yml
```

它会在 NASA APOD 的美国东部日期进入当天之后自动抓取当天推荐图。APOD 官方每天只有一张推荐图；如果当天内容不是图片，网页会提示暂不作为图片隐写素材，并保留打开 NASA 原页面的入口。

如果当前网络无法访问 `api.nasa.gov` 或 `apod.nasa.gov`，脚本不会一直停在旧图，而是自动启用 Wikimedia Commons 上的 NASA 授权天文图兜底列表，并按日期轮换。这样课堂展示时推荐区仍然会更新，只是来源会显示为 `Wikimedia Commons NASA fallback`。

在本机调试时，如果设置了 `HTTP_PROXY`、`HTTPS_PROXY` 或 `ALL_PROXY`，NASA 官方域名可能会因为代理 TLS 握手失败而不可达。抓取脚本对 NASA 官方请求会自动绕过这些代理，优先直连官方接口。

## 今日音频推荐

前端首页还会读取：

```text
static/data/audio_recommendation.json
```

这个文件由脚本自动生成：

```bash
python scripts/fetch_audio_recommendation.py
```

脚本会读取 Apple Music 国区热门歌曲榜，再通过 iTunes lookup 找到榜单歌曲的公开试听片段。它只缓存约 30 秒的试听音频，不缓存完整歌曲，适合课堂现场播放和上传测试：

```text
static/data/audio_recommendation.m4a
```

仓库里对应的 GitHub Actions 是：

```text
.github/workflows/update-audio-recommendation.yml
```

它每天自动更新一次推荐音频。当前策略不抓完整歌曲，只抓公开试听片段，原因是完整播放链接通常涉及登录、版权和防盗链，不适合作为课堂摊位演示的稳定素材源。

## API

### POST `/api/image/analyze`

识别图片格式和文本容量。

### POST `/api/image/hide`

输入 JPG/BMP/PNG 和文本，输出 PNG。

### POST `/api/image/extract`

输入处理后的 PNG，提取文本。

### POST `/api/audio/analyze`

识别 WAV、MP3 或 M4A，并返回转换后的 WAV 容量。

### POST `/api/audio/hide`

输入 WAV/MP3/M4A 和文本，输出 WAV。

### POST `/api/audio/extract`

输入处理后的 WAV，提取文本。

## 测试

```bash
python -m unittest discover -s tests
```

测试会覆盖 JPG、BMP、PNG 输入，并验证输出 PNG 可以成功提取文本；也会覆盖 WAV 隐写。如果安装了 ffmpeg，还会测试 MP3、M4A 输入转 WAV 输出。

## 测试样例

本目录自带三张测试输入图：

```text
samples/sample-input.jpg
samples/sample-input.bmp
samples/sample-input.png
samples/sample-audio.wav
samples/sample-audio.mp3
```

## 当前技术路线

图片：

```text
JPG/BMP/PNG 输入 -> PNG 输出
先解码成 RGB 裸像素
只修改内存中的 RGB 像素字节
再保存为无损 PNG
```

音频：

```text
WAV 输入 -> WAV LSB 隐写 -> WAV 输出
MP3 输入 -> 解码为 WAV -> WAV LSB 隐写 -> WAV 输出
M4A 输入 -> 解码为 WAV -> WAV LSB 隐写 -> WAV 输出
```
