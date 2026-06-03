import re
import asyncio
from typing import List
from urllib.parse import urljoin, urlparse

from plugins.base import BrowserSource
from utils.http_util import http_get_bytes
from models import Novel, Catalog, Volume, Chapter
from logger import logger


class ExampleMangaSource(BrowserSource):
    # ------------------------------------------------------------------
    # 1. URL 匹配 —— 替换为你目标网站的 URL 格式
    #    用正则表达式匹配该网站的漫画详情页链接，并捕获漫画 slug/ID。
    # ------------------------------------------------------------------
    _URL_PAT = re.compile(r"example\.com/manga/([a-zA-Z0-9_-]+)")

    # 运行时动态设置的基础域名
    _domain: str = ""

    # ------------------------------------------------------------------
    # 2. 基本属性 —— 必须实现
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "示例漫画源"

    @property
    def source_url(self) -> str:
        return self._domain or "https://www.example.com"

    def support_url(self, url: str) -> bool:
        return bool(self._URL_PAT.search(url))

    # ------------------------------------------------------------------
    # 3. 辅助方法
    # ------------------------------------------------------------------
    def _get_slug(self, url: str) -> str:
        """从 URL 中提取漫画 slug"""
        m = self._URL_PAT.search(url)
        if not m:
            raise ValueError(f"不支持的 URL: {url}")
        return m.group(1)

    def _get_domain(self, url: str) -> str:
        """从完整 URL 中提取协议和域名部分"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    # ==================================================================
    # 4. 核心接口 —— 必须实现以下 4 个方法
    #    BrowserSource 提供 self._page（Playwright 页面对象）、
    #    self._safe_goto()、self._human_delay() 等方法
    # ==================================================================

    async def get_novel(self, url: str) -> Novel:
        """
        抓取漫画基本信息（标题、作者、封面、标签等）
        参数：url - 漫画详情页的完整 URL
        返回：Novel 对象
        """
        # 解析域名和 slug
        self._domain = self._get_domain(url)
        slug = self._get_slug(url)

        # 创建 Novel 对象
        novel = Novel()
        novel.url = url
        novel.id = slug

        # 使用 BrowserSource 提供的安全导航方法
        if not await self._safe_goto(
            f"{self._domain}/manga/{slug}", wait_until="domcontentloaded"
        ):
            raise RuntimeError(f"无法加载漫画页面: {url}")

        # 模拟人类浏览延迟（1~2秒随机）
        await self._human_delay(1, 2)

        # --- 从页面中提取信息（选择器需根据目标网站修改）---

        # 获取标题
        novel.title = await self._page.eval_on_selector(
            "h1", "el => el ? el.textContent.trim() : ''"
        )
        if not novel.title:
            title_from_doc = await self._page.evaluate("document.title || ''")
            novel.title = title_from_doc.strip()

        # 获取作者
        novel.author = await self._page.eval_on_selector(
            "a[href*='/author/']",
            'el => el ? el.textContent.trim() : ""',
        )
        if not novel.author:
            novel.author = "未知"

        # 获取封面
        cover_src = await self._page.eval_on_selector(
            "img.cover",
            'el => el ? (el.src || "") : ""',
        )
        if cover_src:
            novel.cover_url = urljoin(self._domain, cover_src)

        # 获取标签
        novel.tags = await self._page.eval_on_selector_all(
            "a[href*='/tag/']",
            "els => els.map(el => el.textContent.trim().replace('#', '')).filter(t => t)",
        )

        # 获取状态（连载中/已完结）
        status = await self._page.eval_on_selector(
            ".status",
            'el => el ? el.textContent.trim() : ""',
        )
        novel.status = status or ""

        novel.publisher = "示例漫画站"
        novel.description = novel.title

        return novel

    async def get_novel_catalog(self, novel: Novel) -> Catalog:
        """
        抓取漫画的章节列表
        参数：novel - 由 get_novel() 返回的 Novel 对象
        返回：Catalog 对象
        """
        slug = novel.id

        # 确保页面已加载
        await self._ensure_page()

        if not await self._safe_goto(
            f"{self._domain}/manga/{slug}", wait_until="domcontentloaded"
        ):
            logger.warning("无法加载漫画详情页")
            return Catalog(novel)

        # 等待章节列表渲染完成（部分网站用 JS 动态加载）
        try:
            await self._page.wait_for_selector(
                "#chapter-list a[href]", timeout=20000
            )
        except Exception:
            pass

        await asyncio.sleep(2)

        # 提取章节链接及其文本
        raw = await self._page.eval_on_selector_all(
            "#chapter-list a[href*='/chapter/']",
            """els => els.map(el => {
                return {href: el.href, text: el.textContent.trim()};
            })""",
        )

        catalog = Catalog(novel)

        if raw:
            volume = Volume("默认", catalog)
            for link in raw:
                name = link.get("text") or ""
                href = link.get("href", "")
                if name and href:
                    volume.chapters.append(Chapter(name, href, volume))
            if volume.chapters:
                catalog.volumes.append(volume)
                logger.info(f"提取到 {len(volume.chapters)} 个章节")

        return catalog

    async def fetch_chapter_images(self, chapter_url: str) -> List[str]:
        """
        抓取单个章节的所有图片 URL
        参数：chapter_url - 该章节页面的完整 URL
        返回：图片 URL 列表
        """
        logger.info(f"正在加载章节: {chapter_url}")

        if not await self._safe_goto(chapter_url, wait_until="domcontentloaded"):
            return []

        await asyncio.sleep(2)

        # 等待图片加载
        try:
            await self._page.wait_for_function(
                """() => {
                    const imgs = document.querySelectorAll('#chapter-content img[src]');
                    return imgs.length > 0;
                }""",
                timeout=30000,
            )
        except Exception:
            pass

        await asyncio.sleep(1)

        # 如果图片是懒加载的，需要模拟滚动
        prev = 0
        for _ in range(6):
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            cur = await self._page.evaluate(
                "document.querySelectorAll('#chapter-content img[src]').length"
            )
            if cur == prev and cur > 0:
                break
            prev = cur

        # 提取所有图片的 src
        img_urls = await self._page.eval_on_selector_all(
            "#chapter-content img",
            "els => els.map(el => el.src || el.getAttribute('data-src') || '').filter(u => u && !u.startsWith('data:'))",
        )

        if img_urls:
            logger.info(f"  发现 {len(img_urls)} 张图片")

        return img_urls

    async def get_image(self, src: str) -> bytes:
        """
        下载单张图片
        参数：src - 图片 URL
        返回：图片二进制数据
        """
        if not src.startswith("http"):
            src = urljoin(self._domain, src)

        # 带重试的下载
        for _ in range(5):
            try:
                data = await http_get_bytes(
                    src,
                    headers={
                        "Referer": self._domain,
                        "Accept": "image/webp,image/*,*/*;q=0.8",
                    },
                    timeout=20,
                    max_attempts=1,
                )
                if data:
                    return data
            except Exception:
                pass
            await asyncio.sleep(1.5)

        logger.warning(f"图片下载失败: {src[:100]}")
        return b""
