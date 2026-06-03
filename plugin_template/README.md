# ScrollPack 插件开发教程

教你制作小说/漫画下载插件。

---

## 目录结构

```
plugin_template/
├── novel_template/          # 小说源模板（继承 LightNovelSource）
│   ├── plugin.json          # 插件元信息
│   ├── __init__.py          # 必须为空文件
│   └── source.py            # 核心抓取逻辑（带详细注释）
├── manga_template/          # 漫画源模板（继承 BrowserSource）
│   ├── plugin.json
│   ├── __init__.py
│   └── source.py            # 核心抓取逻辑（带详细注释）
└── README.md                # 本教程
```

---

## 第一步：选择模板

根据你要抓取的网站类型选择模板：

| 类型 | 目录 | 基类 | 适用场景 |
|---|---|---|---|
| 小说 | `novel_template/` | `LightNovelSource` | 纯 HTML 页面，用 HTTP 请求 + BeautifulSoup 解析 |
| 漫画 | `manga_template/` | `BrowserSource` | 需 JS 渲染的页面，用 Playwright 无头浏览器抓取 |

---

## 第二步：配置 plugin.json

打开 `plugin.json`，修改为你的插件信息：

```json
{
  "name": "显示名称",        // 在 ScrollPack UI 中显示的名字
  "id": "my_plugin",          // 唯一标识，也是 zip 文件名（不含 .zip）
  "version": "1.0.0",         // 语义化版本号
  "type": "novel",            // "novel" 或 "manga"
  "module": "source",         // 固定为 "source"（对应 source.py）
  "class": "MySourceClass"    // 你在 source.py 中定义的类名
}
```

- `id` 必须与目录名、zip 文件名一致
- `type` 决定使用哪个基类：`novel` → `LightNovelSource`，`manga` → `BrowserSource`

---

## 第三步：编写 source.py

模板中的 `source.py` 已经包含了完整的结构注释。你需要做的核心工作是：

### 3.1 修改 URL 匹配正则

```python
_URL_PATTERN = re.compile(r"example\.com/novel/(\d+)")
```
换成你目标网站的小说/漫画详情页 URL 格式，`()` 内捕获的是作品 ID。

### 3.2 必须实现的方法

| 方法 | 作用 | 返回值 |
|---|---|---|
| `get_novel(url)` | 抓取作品基本信息 | `Novel` 对象 |
| `get_novel_catalog(novel)` | 抓取章节目录 | `Catalog` 对象 |
| `get_novel_chapter(chapter)` | 抓取小说章节正文 | `str`（HTML 格式） |
| `fetch_chapter_images(chapter_url)` | 抓取漫画章节图片 URL | `List[str]` |
| `get_image(src)` | 下载单张图片 | `bytes` |

> **注意**：小说源实现 `get_novel_chapter`，漫画源实现 `fetch_chapter_images`。另一个方法保留空实现即可。

### 3.3 框架提供的工具

| 工具 | 位置 | 说明 |
|---|---|---|
| `self._page` | `BrowserSource` | Playwright 页面对象，操作浏览器 DOM |
| `self._safe_goto(url)` | `BrowserSource` | 安全导航到 URL，返回 bool |
| `self._human_delay(a, b)` | `BrowserSource` | 模拟人类延迟 a~b 秒 |
| `self._page.eval_on_selector()` | `BrowserSource` | 在元素上执行 JS |
| `http_get_string()` | `utils.http_util` | HTTP GET，返回字符串 |
| `http_get_bytes()` | `utils.http_util` | HTTP GET，返回字节 |
| `BeautifulSoup` | `bs4` | HTML 解析器 |
| `Scheduler(n, t)` | `scheduler` | 限流器（n 次/t 秒） |
| `AppConfig()` | `config` | 应用配置（可读取 `max_retries` 等） |
| `LightNovelSource.HTML_TEMPLATE` | `plugins.base` | 小说章节课用的 HTML 模板 |

---

## 第四步：测试

将你的插件代码放在 ScrollPack 的插件目录中直接加载测试：

1. 把 `novel_template/`（或 `manga_template/`）目录重命名为你的插件 id
2. 拷贝到 ScrollPack 安装目录下的 `plugins/` 目录
3. 启动 ScrollPack，粘贴目标网站的小说/漫画链接测试
4. 查看日志，确认抓取流程正确

---

## 第五步：打包和发布

测试通过后，打包为 zip：

```
你的插件 ID.zip
└── 你的插件 ID/
    ├── plugin.json
    ├── __init__.py
    └── source.py
```

打包命令（Windows）：

```powershell
Compress-Archive -Path "your_plugin/*" -DestinationPath "your_plugin.zip"
```

然后将 zip 放入本仓库的 `plugins/` 目录，并在 `index.json` 中添加条目：

```json
{
  "id": "你的插件ID",
  "name": "显示名",
  "version": "1.0.0",
  "type": "novel",
  "download": "plugins/你的插件ID.zip",
  "description": "简短描述",
  "author": "你的名字"
}
```

最后提交 PR 到本仓库即可。

---

## 常见问题

### Q: 网站有反爬/Cloudflare 怎么办？
A: 小说源可以检查 Response 中是否包含 Cloudflare 标识并重试。漫画源（Playwright）天然具有较好的反反爬能力。

### Q: 怎么调试？
A: 在源码中添加 `logger.info(...)` 打印日志，ScrollPack 的日志面板会显示。

### Q: 漫画源什么时候用 Playwright 方法，什么时候用 HTTP 请求？
A: HTML 页面解析用 Playwright（`self._page`），图片下载用 HTTP 请求（`http_get_bytes`），效率更高。

### Q: 可以让插件加密吗？
A: 可以在 `plugin.json` 中添加 `"encrypted": true`，然后用加密工具处理。详见现有加密插件示例。

### Q: 图片抓下来全是 loading.gif / 占位图？
A: 很多漫画站用 JS 异步加载图片，会先显示一个 loading 占位图，加载完再替换。不能只检查 `img` 标签是否存在 `src` 属性，必须确认图片真正加载完毕。用 `wait_for_function` 轮询：

```python
await self._page.wait_for_function("""() => {
    const img = document.getElementById('cp_image');
    if (!img) return false;
    const src = img.src || '';
    if (!src || src.startsWith('data:')) return false;
    if (src.includes('loading') || src.includes('placeholder')) return false;
    if (!img.complete) return false;
    if (img.naturalWidth === 0) return false;
    return true;
}""", timeout=60000)
```

关键检查点：`img.complete == true`、`naturalWidth > 0`、`src` 不含 loading/placeholder 字样。

### Q: 漫画章节图片数量不对，只抓到了第一张？
A: 部分漫画站把每张图当一个「分页」。先读取页面中的全局变量（如 `MANGABZ_IMAGE_COUNT`）获取总页数，再逐页导航抓取：

```python
image_count = await self._page.evaluate("MANGABZ_IMAGE_COUNT || 1")
# 逐页导航: /m1234-p2/, /m1234-p3/ ...
for page in range(1, int(image_count) + 1):
    page_url = base_url + "-p" + str(page) + "/"
    await self._safe_goto(page_url)
    # 等待并提取图片...
```

常见的分页 URL 模式：`/m12345/`（第1页）、`/m12345-p2/`（第2页）等。翻页前先搞清楚网站的 URL 规律。
