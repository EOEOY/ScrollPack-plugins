import re
import asyncio
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from plugins.base import LightNovelSource
from utils.http_util import http_get_string, http_get_bytes
from models import Novel, Catalog, Volume, Chapter
from utils.html_util import HTMLUtil
from logger import logger
from scheduler import Scheduler
from config import AppConfig


class ExampleNovelSource(LightNovelSource):
    # ------------------------------------------------------------------
    # 1. URL 匹配 —— 替换为你目标网站的 URL 格式
    #    用正则表达式匹配该网站的小说详情页链接，并捕获小说 ID。
    # ------------------------------------------------------------------
    _URL_PATTERN = re.compile(r"example\.com/novel/(\d+)")

    # ------------------------------------------------------------------
    # 2. 请求频率控制（可选）
    #    Scheduler(每段时间允许的请求数, 时间秒数)
    #    例如：Scheduler(20, 60) 表示每 60 秒最多 20 次请求
    # ------------------------------------------------------------------
    _scheduler = Scheduler(20, 60)

    # 自定义请求头（如网站需要特定 User-Agent 或 Referer）
    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36"
    }

    # ------------------------------------------------------------------
    # 3. 基本属性 —— 必须实现
    # ------------------------------------------------------------------

    @property
    def name(self):
        return "示例小说源"

    @property
    def source_url(self):
        return "https://www.example.com"

    def support_url(self, url: str) -> bool:
        return bool(self._URL_PATTERN.search(url))

    # ------------------------------------------------------------------
    # 4. 辅助方法 —— 从 URL 中提取小说 ID
    # ------------------------------------------------------------------
    def _get_id(self, url: str) -> str:
        m = self._URL_PATTERN.search(url)
        if not m:
            raise ValueError(f"不支持的 URL: {url}")
        return m.group(1)

    async def _http_get(self, url: str, headers=None):
        """带限流的 GET 请求包装，通过 Scheduler 自动控制请求频率"""
        if headers is None:
            headers = self._headers

        async def _task(c):
            return await http_get_string(url, headers=headers)

        return await self._scheduler.run(_task)

    # ==================================================================
    # 5. 核心接口 —— 必须实现以下 4 个方法
    # ==================================================================

    async def get_novel(self, url: str) -> Novel:
        """
        抓取小说基本信息（标题、作者、封面、标签、简介等）
        参数：url - 小说详情页的完整 URL
        返回：Novel 对象
        """
        novel_id = self._get_id(url)

        # 从网站获取小说详情页 HTML
        html = await self._http_get(f"{self.source_url}/novel/{novel_id}")
        doc = BeautifulSoup(html, "html.parser")

        novel = Novel()

        # --- 必填字段 ---
        novel.id = novel_id
        novel.url = url

        # --- 从页面解析信息（以下选择器需要根据目标网站修改）---
        novel.title = (
            doc.select_one("h1.novel-title").text.strip()
            if doc.select_one("h1.novel-title")
            else ""
        )
        novel.author = (
            doc.select_one(".author").text.strip()
            if doc.select_one(".author")
            else ""
        )
        novel.tags = [
            tag.text.strip()
            for tag in doc.select(".tags .tag")
        ]
        novel.description = (
            doc.select_one(".description").text.strip()
            if doc.select_one(".description")
            else ""
        )

        # --- 可选字段 ---
        cover_el = doc.select_one("img.cover")
        if cover_el and cover_el.get("src"):
            novel.cover_url = urljoin(self.source_url, cover_el["src"])

        status_el = doc.select_one(".status")
        if status_el:
            novel.status = status_el.text.strip()

        publisher_el = doc.select_one(".publisher")
        if publisher_el:
            novel.publisher = publisher_el.text.strip()

        novel.alias = ""   # 别名（如原标题是日文时可填写中文译名）

        return novel

    async def get_novel_catalog(self, novel: Novel) -> Catalog:
        """
        抓取小说的目录信息（分卷、章节列表）
        参数：novel - 由 get_novel() 返回的 Novel 对象
        返回：Catalog 对象，包含 Volume 和 Chapter
        """
        novel_id = novel.id

        # 获取目录页 HTML
        html = await self._http_get(f"{self.source_url}/novel/{novel_id}/catalog")
        doc = BeautifulSoup(html, "html.parser")

        catalog = Catalog(novel)

        # 方案 A：有分卷时
        for vol_el in doc.select(".volume"):
            vol_name = (
                vol_el.select_one(".volume-title").text.strip()
                if vol_el.select_one(".volume-title")
                else "默认"
            )
            volume = Volume(vol_name, catalog)

            for ch_el in vol_el.select("a.chapter"):
                ch_name = ch_el.text.strip()
                ch_url = urljoin(self.source_url, ch_el.get("href", ""))
                volume.chapters.append(Chapter(ch_name, ch_url, volume))

            if volume.chapters:
                catalog.volumes.append(volume)

        # 方案 B：无分卷时（所有章节放在一个默认卷下）
        if not catalog.volumes:
            volume = Volume("默认", catalog)
            for ch_el in doc.select("a.chapter"):
                ch_name = ch_el.text.strip()
                ch_url = urljoin(self.source_url, ch_el.get("href", ""))
                volume.chapters.append(Chapter(ch_name, ch_url, volume))
            if volume.chapters:
                catalog.volumes.append(volume)

        return catalog

    async def get_novel_chapter(self, chapter: Chapter) -> str:
        """
        抓取单个章节的正文内容
        参数：chapter - 目录中的一个 Chapter 对象
        返回：包装好的 HTML 字符串
        """
        config = AppConfig()

        # 带重试的章节抓取
        for attempt in range(1, config.max_retries + 1):
            try:
                return await self._do_get_chapter(chapter)
            except Exception as e:
                if attempt < config.max_retries:
                    logger.warning(f"获取章节失败，{attempt}/{config.max_retries} 次重试: {e}")
                    await asyncio.sleep(config.retry_delay_seconds)
                else:
                    raise

    async def _do_get_chapter(self, chapter: Chapter) -> str:
        """实际执行章节内容抓取"""
        url = chapter.chapter_url
        logger.info(f"正在获取: {chapter.volume.volume_name} / {chapter.chapter_name}")

        html = await self._http_get(url)

        # Cloudflare 检测（多数中文网站可能有）
        if "Cloudflare" in html and "Ray ID" in html:
            raise RuntimeError("遇到 Cloudflare 防护页面，请稍后重试")

        doc = BeautifulSoup(html, "html.parser")

        # 提取正文内容区域（选择器需根据目标网站修改）
        content = doc.select_one(".chapter-content")
        if not content:
            logger.error(f"无法获取章节内容: {url}")
            raise RuntimeError("未找到章节正文区域，请检查选择器是否正确")

        # 清理不需要的元素（如广告、导航等）
        HTMLUtil.remove_elements(content.select(".ad"))
        HTMLUtil.remove_elements(content.select(".nav"))

        # 将内容包装为标准 HTML 模板格式
        return self._wrap_document(content)

    def _wrap_document(self, content) -> str:
        """
        将 BeautifulSoup 内容包装为完整的 HTML 文档
        这是框架要求的标准格式，直接用 LightNovelSource.HTML_TEMPLATE
        """
        from bs4 import NavigableString
        from bs4 import BeautifulSoup as BS

        doc = BS(LightNovelSource.HTML_TEMPLATE, "html.parser")

        for node in list(content.children):
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if not text:
                    continue
                p = doc.new_tag("p")
                p.string = text
                doc.body.append(p)
            else:
                parsed = BS(str(node), "html.parser")
                pb = parsed.body or parsed
                for child in list(pb.children):
                    doc.body.append(child)

        # 移除超链接（可选，保留纯文本阅读体验）
        for link in doc.find_all("a"):
            HTMLUtil.unwrap(link)

        return str(doc)

    async def get_image(self, src: str) -> bytes:
        """下载图片，返回图片的二进制数据"""
        return await http_get_bytes(src, headers=self._headers)
