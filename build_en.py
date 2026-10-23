#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mr.Video 双语站构建脚本
=========================
架构：中文 HTML 是唯一内容源 → 本脚本按 i18n/en.json 翻译字典生成纯静态英文站。

产出：
  index.html            (中文首页，注入语言切换器 + hreflang)
  social-media.html     (中文子页，同上)
  en/index.html         (英文首页，纯静态，可被 Google 单独收录)
  en/social-media.html  (英文子页)

关键特性：
  1. 缺少翻译 → 脚本直接报错退出，中英内容不会脱节
  2. 英文版输出后自动扫描残留中文，命中即报错
  3. 幂等：可重复执行

用法：
  python build_en.py            # 构建
  python build_en.py --check    # 只校验，不写文件
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DICT = json.loads((ROOT / "i18n" / "en.json").read_text(encoding="utf-8"))

TEXT = DICT["text"]
ATTR = DICT["attr"]
PAGES_META = DICT["pages"]
SPECIAL = DICT["special"]
SPECIAL_RE = DICT.get("special_re", [])
DROP = DICT.get("drop", [])
UI = DICT["ui"]
NAV_SHORT = DICT.get("nav_short", {})

# CJK 汉字 + 中日韩标点 + 全角字符
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")

BLOCK_NAMES = ["head-alt", "lang-switch", "lang-switch-drawer", "lang-switch-footer"]

# ---------------------------------------------------------------- 页面配置
# 说明：Cloudflare Pages 启用了 clean URLs（/social-media.html → 308 → /social-media），
# 因此 SEO 声明与站内链接统一使用无扩展名形式，避免多一跳重定向。
PAGES = [
    {
        "name": "index",
        "src": "index.html",
        "out": "en/index.html",
        "zh_url": "/",
        "en_url": "/en/",
        "site": "https://mrvideo.vip",
        "switch_label": "EN",
        "switch_aria": UI["aria_zh_to_en"],
        "switch_title": UI["title_zh_to_en"],
    },
    {
        "name": "social",
        "src": "social-media.html",
        "out": "en/social-media.html",
        "zh_url": "/social-media",
        "en_url": "/en/social-media",
        "site": "https://mrvideo.vip",
        "switch_label": "EN",
        "switch_aria": UI["aria_zh_to_en"],
        "switch_title": UI["title_zh_to_en"],
    },
]

GLOBE_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"></circle>'
    '<path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18"></path>'
    "</svg>"
)


# ---------------------------------------------------------------- 工具函数
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def has_cjk(s: str) -> bool:
    return bool(CJK.search(s))


def normalize_blocks(src: str) -> str:
    """把上一次注入的 start/end 区块还原成简单占位符，保证脚本幂等。"""
    for name in BLOCK_NAMES:
        src = re.sub(
            r"<!--\s*i18n:%s:start\s*-->.*?<!--\s*i18n:%s:end\s*-->" % (name, name),
            f"<!-- i18n:{name} -->",
            src,
            flags=re.S,
        )
    return src


def inject(src: str, name: str, content: str) -> str:
    """把占位符替换成带 start/end 标记的内容区块。"""
    block = f"<!-- i18n:{name}:start -->\n{content}\n<!-- i18n:{name}:end -->"
    simple = f"<!-- i18n:{name} -->"
    if simple in src:
        return src.replace(simple, block)
    if f"<!-- i18n:{name}:start -->" in src:
        return re.sub(
            r"<!--\s*i18n:%s:start\s*-->.*?<!--\s*i18n:%s:end\s*-->" % (name, name),
            block,
            src,
            flags=re.S,
        )
    raise SystemExit(f"[错误] 源文件缺少占位符：<!-- i18n:{name} -->")


def tokenize(src: str):
    """把 HTML 拆成 (kind, text)：kind ∈ text / tag / comment。"""
    out, i, n = [], 0, len(src)
    while i < n:
        j = src.find("<", i)
        if j == -1:
            out.append(("text", src[i:]))
            break
        if j > i:
            out.append(("text", src[i:j]))
        if src.startswith("<!--", j):
            k = src.find("-->", j + 4)
            k = n if k == -1 else k + 3
            out.append(("comment", src[j:k]))
            i = k
            continue
        if src.startswith("<!", j):
            k = src.find(">", j)
            k = n if k == -1 else k + 1
            out.append(("tag", src[j:k]))
            i = k
            continue
        if src.startswith("</", j):
            k = src.find(">", j)
            k = n if k == -1 else k + 1
            out.append(("tag", src[j:k]))
            i = k
            continue
        k, quote = j + 1, None
        while k < n:
            ch = src[k]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == ">":
                break
            k += 1
        k = min(k + 1, n)
        out.append(("tag", src[j:k]))
        i = k
    return out


def translate_text(text: str, missing: set):
    """翻译一个文本节点，保留原有缩进空白。"""
    m = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S)
    if not m:
        return text
    lead, core, trail = m.group(1), m.group(2), m.group(3)
    key = norm(core)
    if not key or not has_cjk(key):
        return text
    new = TEXT.get(key)
    if new is None:
        missing.add(("text", key))
        return text
    return lead + new + trail


def translate_tag(tag: str, missing: set) -> str:
    """翻译标签内的 alt / placeholder / aria-label / title / option[value]。"""

    def repl_attr(m):
        name, val = m.group(1), m.group(2)
        key = norm(val)
        if not key or not has_cjk(key):
            return m.group(0)
        new = ATTR.get(key) or TEXT.get(key)
        if new is None:
            missing.add(("attr", key))
            return m.group(0)
        return f'{name}="{new}"'

    tag = re.sub(
        r"\b(alt|placeholder|aria-label|title)\s*=\s*\"([^\"]*)\"", repl_attr, tag
    )

    def repl_option(m):
        key = norm(m.group(2))
        if not has_cjk(key):
            return m.group(0)
        new = ATTR.get(key) or TEXT.get(key)
        if new is None:
            missing.add(("attr", key))
            return m.group(0)
        return m.group(1) + new + m.group(3)

    tag = re.sub(r"(<option\s+value\s*=\s*\")([^\"]*)(\")", repl_option, tag)
    return tag


def apply_meta(src: str, meta: dict) -> str:
    """替换 head 中的 title / meta / og 标签。"""
    src = re.sub(r"<title>.*?</title>", f"<title>{meta['title']}</title>", src, flags=re.S)
    for name, key in (
        ("description", "description"),
        ("keywords", "keywords"),
    ):
        pattern = r'(<meta\s+name="%s"\s+content=")[^"]*(")' % name
        if re.search(pattern, src):
            src = re.sub(
                pattern,
                lambda m: m.group(1) + meta[key] + m.group(2),
                src,
            )
        else:
            # 源文件缺少该 meta 标签 → 主动插入到 description 之后
            src = re.sub(
                r'(<meta\s+name="description"[^>]*>)',
                r'\1\n  <meta name="%s" content="%s" />' % (name, meta[key]),
                src,
                count=1,
            )
    for prop, key in (("og:title", "og:title"), ("og:description", "og:description")):
        src = re.sub(
            r'(<meta\s+property="%s"\s+content=")[^"]*(")' % re.escape(prop),
            lambda m: m.group(1) + meta[key] + m.group(2),
            src,
        )
    # og:url 交由 head-alt 区块统一管理，先移除源文件中的旧值
    src = re.sub(r'<meta\s+property="og:url"[^>]*>', "", src)
    return src


def rewrite_paths_en(src: str) -> str:
    """英文站在 en/ 子目录，资源路径需回退一级。"""
    src = re.sub(r'(src=")(images/)', r"\1../\2", src)
    src = re.sub(r'(src=")(css/)', r"\1../\2", src)
    src = re.sub(r'(src=")(js/)', r"\1../\2", src)
    src = re.sub(r'(href=")(css/)', r"\1../\2", src)
    src = re.sub(r"url\('(images/)", r"url('../\1", src)
    return src


def normalize_links_en(src: str) -> str:
    """英文版站内链接规范化为 Cloudflare clean URLs（无 .html 扩展名）。

    Cloudflare Pages 会对 /en/social-media.html 返回 308 -> /en/social-media，
    因此英文版链接直接使用无扩展名形式，一步到位。

    注意：只作用于英文版产物（不回写中文源文件），且必须在翻译完成后调用，
    否则会破坏 special 字典的整段字面匹配。
    """
    # 首页 -> 社交页
    src = src.replace('href="social-media.html"', 'href="/en/social-media"')
    # 社交页 -> 首页（含锚点）
    src = src.replace('href="index.html', 'href="/en/index.html')
    # 语言切换器指向中文版社交页
    src = src.replace('href="/social-media.html"', 'href="/social-media"')
    # 绝对 URL 同步
    src = src.replace("https://mrvideo.vip/en/social-media.html", "https://mrvideo.vip/en/social-media")
    src = src.replace("https://mrvideo.vip/social-media.html", "https://mrvideo.vip/social-media")
    return src


def shorten_nav_labels(src: str) -> str:
    """把顶部导航与抽屉菜单的文案替换为短标签。

    英文长文案（如 "E-Commerce Products"）会让 1440px 下的导航栏溢出，
    因此仅在 <nav class="main-nav"> 与 <nav class="drawer-nav"> 内使用短标签；
    页脚导航与章节大标题保留完整英文，兼顾 SEO 锚文本。
    """
    if not NAV_SHORT:
        return src

    def replace_in_block(block: str) -> str:
        # <a href="...">TEXT</a> —— 只替换纯文本锚点
        def repl(m):
            open_tag, text, close_tag = m.group(1), m.group(2), m.group(3)
            key = norm(text)
            if key in NAV_SHORT:
                return open_tag + NAV_SHORT[key] + close_tag
            return m.group(0)

        return re.sub(r"(<a\b[^>]*>)([^<>]+)(</a>)", repl, block)

    # 只处理导航类 <nav> 区块
    def repl_nav(m):
        return replace_in_block(m.group(0))

    return re.sub(
        r"<nav class=\"(?:main-nav|drawer-nav)\"[^>]*>.*?</nav>",
        repl_nav,
        src,
        flags=re.S,
    )


def build_english(src: str, meta: dict, missing: set) -> str:
    out = src

    # 1) 整段正则替换（带内嵌标签的复杂结构）
    for item in SPECIAL_RE:
        out = re.sub(item["pattern"], item["replacement"], out, flags=re.S)

    # 2) 整段字面替换
    for k, v in SPECIAL.items():
        out = out.replace(k, v)

    # 3) 移除中英重复元素
    for pattern in DROP:
        out = re.sub(pattern, "", out, flags=re.S)

    # 4) head 元信息
    out = apply_meta(out, meta)

    # 5) 逐 token 翻译
    parts = []
    for kind, text in tokenize(out):
        if kind == "text":
            parts.append(translate_text(text, missing))
        elif kind == "tag":
            parts.append(translate_tag(text, missing))
        elif text.startswith("<!-- i18n:"):
            parts.append(text)  # 保留 i18n 占位符注释，供后续注入
        else:
            parts.append("")  # 英文版剥离其余 HTML 注释
    out = "".join(parts)

    # 6) 导航短标签（仅顶部导航与抽屉菜单）
    out = shorten_nav_labels(out)

    # 7) 资源路径回退一级
    out = rewrite_paths_en(out)

    # 8) lang 属性
    out = re.sub(r'<html lang="zh-CN">', '<html lang="en">', out)

    return out


def head_block(page: dict, lang: str) -> str:
    zh_abs = page["site"] + page["zh_url"]
    en_abs = page["site"] + page["en_url"]
    canonical = en_abs if lang == "en" else zh_abs
    og_url = en_abs if lang == "en" else zh_abs
    og_locale = "en_US" if lang == "en" else "zh_CN"
    og_alt = "zh_CN" if lang == "en" else "en_US"
    return f"""  <meta property="og:url" content="{og_url}" />
  <meta property="og:locale" content="{og_locale}" />
  <meta property="og:locale:alternate" content="{og_alt}" />
  <link rel="canonical" href="{canonical}" />
  <link rel="alternate" hreflang="zh-Hans" href="{zh_abs}" />
  <link rel="alternate" hreflang="en" href="{en_abs}" />
  <link rel="alternate" hreflang="x-default" href="{zh_abs}" />"""


def switch_block(page: dict, lang: str, variant: str) -> str:
    """语言切换器。lang='zh' 表示当前是中文站（跳去英文）。"""
    if lang == "zh":
        href = page["en_url"]
        label = "EN"
        aria = UI["aria_zh_to_en"]
        title = UI["title_zh_to_en"]
    else:
        href = page["zh_url"]
        label = UI["label_en_to_zh"]
        aria = UI["aria_en_to_zh"]
        title = UI["title_en_to_zh"]

    if variant == "header":
        return (
            f'<a href="{href}" class="lang-switch" aria-label="{aria}" title="{title}">'
            f"{GLOBE_ICON}<span>{label}</span></a>"
        )
    if variant == "drawer":
        return (
            f'<a href="{href}" class="drawer-lang" aria-label="{aria}">'
            f"{GLOBE_ICON}<span>{label}</span></a>"
        )
    return (
        f'<a href="{href}" class="lang-switch lang-switch-footer" aria-label="{aria}" '
        f'title="{title}">{GLOBE_ICON}<span>{label}</span></a>'
    )


# ---------------------------------------------------------------- 主流程
def main():
    check_only = "--check" in sys.argv
    missing = set()
    errors = []

    for page in PAGES:
        src_path = ROOT / page["src"]
        raw = src_path.read_text(encoding="utf-8")
        src = normalize_blocks(raw)
        meta = PAGES_META[page["name"]]

        # ---------- 中文站（注入中文版区块） ----------
        zh = src
        zh = inject(zh, "head-alt", head_block(page, "zh"))
        zh = inject(zh, "lang-switch", switch_block(page, "zh", "header"))
        zh = inject(zh, "lang-switch-drawer", switch_block(page, "zh", "drawer"))
        zh = inject(zh, "lang-switch-footer", switch_block(page, "zh", "footer"))
        # 中文站保持原始链接形态（源码即模板，需可被字典匹配）

        # ---------- 英文站 ----------
        en = build_english(src, meta, missing)

        # 残留中文检查（在注入语言切换器之前，切换器的"中文"字样是刻意的语言标识）
        residue = sorted(
            {norm(m) for m in re.findall(r"[^<>]*[㐀-䶿一-鿿][^<>]*", en) if norm(m)}
        )

        en = inject(en, "head-alt", head_block(page, "en"))
        en = inject(en, "lang-switch", switch_block(page, "en", "header"))
        en = inject(en, "lang-switch-drawer", switch_block(page, "en", "drawer"))
        en = inject(en, "lang-switch-footer", switch_block(page, "en", "footer"))
        en = normalize_links_en(en)

        print(f"[{page['name']}] 生成完成" + (f"（残留中文 {len(residue)} 处）" if residue else "（无残留中文）"))
        for r in residue[:20]:
            print(f"    ! 残留：{r[:100]}")

        if residue:
            errors.append(f"{page['name']}: 英文版残留中文 {len(residue)} 处")

        if not check_only:
            src_path.write_text(zh, encoding="utf-8")
            out_path = ROOT / page["out"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(en, encoding="utf-8")
            print(f"    → 写入 {page['src']} / {page['out']}")

    if missing:
        print("\n[错误] 以下中文文案缺少英文翻译，请补充到 i18n/en.json：")
        for kind, key in sorted(missing):
            print(f"    [{kind}] {key}")
        errors.append(f"{len(missing)} 条文案缺翻译")

    if errors:
        print("\n构建失败：\n  - " + "\n  - ".join(errors))
        sys.exit(1)

    print("\n全部通过 ✓" if not check_only else "\n校验通过 ✓")


if __name__ == "__main__":
    main()
