# ScrollPack 插件仓库

## 使用
在 ScrollPack 设置 → 插件管理 → 仓库地址填入：
```
https://raw.githubusercontent.com/EOEOY/ScrollPack-plugins/master
```

## 目录结构
```
index.json          ← 插件索引
plugins/            ← 插件 zip 包
```

## 开发插件

1. 复制 ScrollPack 项目中的 `plugins/plugin_template/` 为你的插件目录
2. 修改 `plugin.json`（name、id、class）
3. 实现 `source.py` 中标记的方法
4. 打成 zip：目录结构为 `{plugin_id}/plugin.json`、`{plugin_id}/source.py`、`{plugin_id}/__init__.py`
5. 将 zip 放入 `plugins/` 目录
6. 在 `index.json` 中注册插件信息

### plugin.json 格式
```json
{
  "name": "显示名称",
  "id": "唯一标识",
  "version": "1.0.0",
  "type": "manga 或 novel",
  "module": "source",
  "class": "你的类名"
}
```

### __init__.py
空文件即可，让 Python 识别为包。

## 提交插件
联系仓库维护者提交，或自行搭建插件仓库在软件中配置地址。
