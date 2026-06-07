# 多媒体隐写迭代版

这是第三版迭代目录，保留前面版本不动。本版本包含两条功能线：

面向用户的网页提示和错误提示均已中文化；接口字段名仍保留英文，方便代码调用。

图片隐写：

1. 输入 JPG、BMP 或 PNG 图片
2. 后端统一解码为 RGB 像素
3. 在 RGB 像素字节最低 2 位写入文本
4. 输出 PNG 图片
5. 再上传 PNG 提取隐藏文本

音频隐写：

1. 输入 WAV 或 MP3 音频
2. WAV 直接读取 PCM 采样数据
3. MP3 先通过 ffmpeg 解码为 PCM WAV
4. 在 WAV 采样低字节最低 2 位写入文本
5. 输出 WAV 音频
6. 再上传 WAV 提取隐藏文本

## 为什么输出 PNG

JPG 是有损压缩，会破坏最低位信息。PNG 是无损格式，可以保存被改过的像素最低位，所以本迭代统一输出 PNG。

## 为什么 MP3 输出 WAV

MP3 是有损压缩格式，重新编码会破坏采样最低位。为了让隐写结果稳定，MP3 只作为输入格式，后端会先把它解码成 WAV，再进行 WAV LSB 隐写，最终输出 WAV。

## 运行

在本目录运行：

```bash
pip install -r requirements.txt
python run_server.py
```

默认地址：

```text
http://127.0.0.1:8020
```

如果端口被占用：

```bash
python run_server.py --port 8021
```

MP3 输入需要安装 ffmpeg，并确保 `ffmpeg` 命令可用。如果本机通过 winget 安装了 FFmpeg，本项目也会尝试自动寻找 winget 安装路径。

## API

### POST `/api/image/analyze`

识别图片格式和文本容量。

### POST `/api/image/hide`

输入 JPG/BMP/PNG 和文本，输出 PNG。

### POST `/api/image/extract`

输入处理后的 PNG，提取文本。

### POST `/api/audio/analyze`

识别 WAV 或 MP3，并返回转换后的 WAV 容量。

### POST `/api/audio/hide`

输入 WAV/MP3 和文本，输出 WAV。

### POST `/api/audio/extract`

输入处理后的 WAV，提取文本。

## 测试

```bash
python -m unittest discover -s tests
```

测试会覆盖 JPG、BMP、PNG 输入，并验证输出 PNG 可以成功提取文本；也会覆盖 WAV 隐写。如果安装了 ffmpeg，还会测试 MP3 输入转 WAV 输出。

## 测试样例

本目录自带三张测试输入图：

```text
samples/sample-input.jpg
samples/sample-input.bmp
samples/sample-input.png
samples/sample-audio.wav
samples/sample-audio.mp3
```

## 与前面版本的差异

第一版图片：

```text
BMP 输入 -> BMP 输出
直接修改 BMP 像素区字节
```

第二版图片：

```text
JPG/BMP/PNG 输入 -> PNG 输出
先解码成 RGB 裸像素
只修改内存中的 RGB 像素字节
再保存为无损 PNG
```

第三版音频：

```text
WAV 输入 -> WAV LSB 隐写 -> WAV 输出
MP3 输入 -> 解码为 WAV -> WAV LSB 隐写 -> WAV 输出
```
