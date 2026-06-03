# ScrollPack 插件仓库

## 使用

在 ScrollPack 设置中填入仓库地址：

```
https://raw.githubusercontent.com/EOEOY/ScrollPack-plugins/master
```

## 开发

1. 参考 `plugin_template` 目录结构
2. 继承 `BrowserSource`（漫画）或 `LightNovelSource`（小说）
3. 实现 `get_novel` / `get_novel_catalog` / `get_image` / `fetch_chapter_images`
4. 打包为 `{plugin_id}.zip`，内部包含 `plugin_id/plugin.json` + `plugin_id/__init__.py` + `plugin_id/source.py`

### plugin.json

```json
{
  "name": "显示名",
  "id": "唯一标?",
  "version": "1.0.0",
  "type": "manga",
  "module": "source",
  "class": "YourClassName"
}
```

## 致谢

哔哩轻小说插件基于 [bili_novel_packer](https://github.com/Montaro2017/bili_novel_packer) 转译，感谢原作者。

## License

CC BY-NC 4.0
