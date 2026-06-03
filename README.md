# ScrollPack 插件仓库

## 使用

在 ScrollPack 设置中填入仓库地址：

```
https://raw.githubusercontent.com/EOEOY/ScrollPack-plugins/master
```

## 开发

详细教程见 [`plugin_template/README.md`](plugin_template/README.md)。

快速步骤：

1. 复制 `plugin_template/novel_template/`（小说）或 `plugin_template/manga_template/`（漫画）
2. 修改 `plugin.json` 和 `source.py`
3. 测试通过后打包为 `{plugin_id}.zip`，内部结构：
   ```
   {plugin_id}/
   ├── plugin.json
   ├── __init__.py      # 空文件
   └── source.py
   ```
4. 放入 `plugins/`，注册到 `index.json`，提 PR

## 致谢

哔哩轻小说插件基于 [bili_novel_packer](https://github.com/Montaro2017/bili_novel_packer) 转译，感谢原作者。

## License

CC BY-NC 4.0
