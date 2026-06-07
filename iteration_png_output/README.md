# 图片隐写迭代版：JPG/BMP/PNG 输入，PNG 输出

这是第二版迭代目录，保留原来的 BMP-only 原型不动。本版本的目标是：

1. 输入 JPG、BMP 或 PNG 图片
2. 后端统一解码为 RGB 像素
3. 在 RGB 像素字节最低 2 位写入文本
4. 输出 PNG 图片
5. 再上传 PNG 提取隐藏文本

## 为什么输出 PNG

JPG 是有损压缩，会破坏最低位信息。PNG 是无损格式，可以保存被改过的像素最低位，所以本迭代统一输出 PNG。

## 运行

在本目录运行：

```bash
pip install -r requirements.txt
python run_server.py
```

默认地址：

```text
http://127.0.0.1:8010
```

如果端口被占用：

```bash
python run_server.py --port 8011
```

## API

### POST `/api/image/analyze`

识别图片格式和文本容量。

### POST `/api/image/hide`

输入 JPG/BMP/PNG 和文本，输出 PNG。

### POST `/api/image/extract`

输入处理后的 PNG，提取文本。

## 测试

```bash
python -m unittest discover -s tests
```

测试会覆盖 JPG、BMP、PNG 输入，并验证输出 PNG 可以成功提取文本。

## 测试样例

本目录自带三张测试输入图：

```text
samples/sample-input.jpg
samples/sample-input.bmp
samples/sample-input.png
```

## 与第一版的差异

第一版：

```text
BMP 输入 -> BMP 输出
直接修改 BMP 像素区字节
```

第二版：

```text
JPG/BMP/PNG 输入 -> PNG 输出
先解码成 RGB 裸像素
只修改内存中的 RGB 像素字节
再保存为无损 PNG
```
