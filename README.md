# BMP 图片隐写网站原型

这是一个图片与音频隐写原型。第一阶段先把课件里的 BMP 图片隐写流程跑通：

1. 输入 BMP 图片
2. 解析并识别像素区
3. 给出可隐藏文本上限
4. 输入要隐藏的文本
5. 修改像素最低 2 位
6. 输出新的 BMP 图片

当前版本只支持 **24 位无压缩 BMP**。代码结构已经为后续迭代预留空间：LSB 核心算法不依赖 BMP，未来可以新增 PNG/JPG 适配层。

项目现在也增加了一个音频隐写原型：

1. 输入 PCM WAV 音频
2. 识别声道数、采样率、位深、时长和容量
3. 输入要隐藏的文本
4. 修改每个采样低字节的最低 2 位
5. 输出新的 WAV 音频
6. 上传新 WAV 验证提取文本

音频第一版支持 **未压缩 PCM WAV**，不支持 MP3/AAC 这类有损压缩格式。

## 项目结构

```text
backend/
  stego_core.py      # 只负责 LSB 写入和提取，不关心图片格式
  bmp_adapter.py     # 只负责 BMP 解析、像素区定位、容量计算
  wav_adapter.py     # 只负责 WAV 解析、音频数据块定位、容量计算
  server.py          # 标准库 HTTP 服务和 API
static/
  index.html         # 最小可用前端页面
  styles.css
  app.js
tests/
  test_bmp_steganography.py
run_server.py
```

## 运行

```bash
python run_server.py
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

如果 8000 端口被占用，可以换端口：

```bash
python run_server.py --port 8010
```

## API

### POST `/api/analyze`

识别 BMP 信息和容量。

请求 JSON：

```json
{
  "filename": "input.bmp",
  "imageBase64": "..."
}
```

### POST `/api/hide`

把文本隐藏到 BMP 图片里。

请求 JSON：

```json
{
  "filename": "input.bmp",
  "imageBase64": "...",
  "text": "要隐藏的文本"
}
```

### POST `/api/extract`

从处理过的 BMP 图片里提取文本。

请求 JSON：

```json
{
  "filename": "input-stego.bmp",
  "imageBase64": "..."
}
```

### POST `/api/audio/analyze`

识别 WAV 信息和容量。

请求 JSON：

```json
{
  "filename": "input.wav",
  "audioBase64": "..."
}
```

### POST `/api/audio/hide`

把文本隐藏到 WAV 音频里。

请求 JSON：

```json
{
  "filename": "input.wav",
  "audioBase64": "...",
  "text": "要隐藏的文本"
}
```

### POST `/api/audio/extract`

从处理过的 WAV 音频里提取文本。

请求 JSON：

```json
{
  "filename": "input-stego.wav",
  "audioBase64": "..."
}
```

## 测试

```bash
python -m unittest discover -s tests
```

项目附带一段原创旋律测试 WAV：

```text
samples/test-melody.wav
```

## 后续迭代建议

下一步如果要支持 PNG/JPG，不需要推倒重写。推荐新增一个 `image_adapter.py`：

```text
PNG/JPG/BMP 输入
-> 用图像库解码成 RGB 像素字节
-> 复用 backend/stego_core.py
-> 输出 PNG
```

这样现有的容量计算、文本写入、文本提取和错误处理逻辑都可以继续保留。
