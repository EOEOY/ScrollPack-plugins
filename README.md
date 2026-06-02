# ScrollPack 插件仓库

## 使用
在 ScrollPack 设置 → 插件管理中填入仓库地址。

## 仓库结构
```
index.json          ← 插件索引
plugins/            ← 插件 zip (加密版不含 .key)
```

## 发布加密插件
```bash
cd ../ScrollPack
python scripts/build_release.py copy_manga
# 输出到 ScrollPack-plugins/plugins/
```
