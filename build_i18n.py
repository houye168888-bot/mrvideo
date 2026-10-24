#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mr.Video 三语站构建脚本（中 / 缅 / 英）
=============================================
架构：
    中文 HTML（唯一内容源）
        └─ 阶段 1：i18n/en.json  ──▶  en/*.html   （英文产物）
        └─ 阶段 2：i18n/my.json  ──▶  my/*.html   （缅语产物，以英文版为基准翻译）

缅语是小语种，按需求「以英文版为基准进行翻译」：
    阶段 2 的输入是阶段 1 生成的英文 HTML，字典 i18n/my.json 的键全部是英文原文。
    因此中文改动 → 英文重生成 → 缅语自动跟随，任何一环缺失都会被构建拦截。

产出：
    index.html / social-media.html          中文站（注入三语切换器 + hreflang）
    en/index.html / en/social-media.html    英文站
    my/index.html / my/social-media.html    缅语站（/my/ 独立真实 URL）

关键特性：
    1. 缺少翻译 → 脚本直接报错退出，三语内容不会脱节
    2. 英文版输出后扫描残留中文，命中即报错；缅语版同样扫描残留中文
    3. 缅语版扫描「未翻译的拉丁文本」，命中即报错
    4. 幂等：可重复执行

用法：
    python build_i18n.py            # 构建
    python build_i18n.py --check    # 只校验，不写文件
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DICT_EN = json.loads((ROOT / "i18n" / "en.json").read_text(encoding="utf-8"))
DICT_MY = json.loads((ROOT / "i18n" / "my.json").read_text(encoding="utf-8"))

TEXT_EN = DICT_EN["text"]
ATTR_EN = DICT_EN["attr"]
PAGES_META_EN = DICT_EN["pages"]
SPECIAL_EN = DICT_EN["special"]
SPECIAL_RE_EN = DICT_EN.get("special_re", [])
DROP_EN = DICT_EN.get("drop", [])
NAV_SHORT_EN = DICT_EN.get("nav_short", {})
UI_EN = DICT_EN["ui"]

TEXT_MY = DICT_MY["text"]
ATTR_MY = DICT_MY["attr"]
PAGES_META_MY = DICT_MY["pages"]
SPECIAL_MY = DICT_MY.get("special", {})
SPECIAL_RE_MY = DICT_MY.get("special_re", [])
KEEP_MY = set(DICT_MY.get("keep", []))
NAV_SHORT_MY = DICT_MY.get("nav_short", {})

# 语言切换器的界面文案（aria-label / title），按当前页面语言取用
UI_BY_LANG = {
    "zh": {
        "aria": UI_EN["lang_menu_aria_zh"],
        "title": UI_EN["lang_menu_title_zh"],
    },
    "en": {
        "aria": UI_EN["lang_menu_aria"],
        "title": UI_EN["lang_menu_title"],
    },
    "my": {
        "aria": DICT_MY["ui"]["lang_menu_aria"],
        "title": DICT_MY["ui"]["lang_menu_title"],
    },
}

# 界面文案（三语切换器等）统一放在 en.json 的 ui 段，三种语言共用
UI = UI_EN

# CJK 汉字 + 中日韩标点 + 全角字符
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
# 缅甸文（Myanmar）区段
MYANMAR = re.compile(r"[\u1000-\u109f\uaa60-\uaa7f\u9aa0-\u9aff]")
# 拉丁字母
LATIN = re.compile(r"[A-Za-z]")

BLOCK_NAMES = ["head-alt", "lang-switch", "lang-switch-drawer", "lang-switch-footer"]

# ---------------------------------------------------------------- 语言定义
LANG_ORDER = ["zh", "en", "my"]
LANG_LABEL = {"zh": "中文", "en": "English", "my": "မြန်မာ"}
LANG_HTML = {"zh": "zh-Hans", "en": "en", "my": "my"}
LANG_HREFLANG = {"zh": "zh-Hans", "en": "en", "my": "my"}
LANG_OG = {"zh": "zh_CN", "en": "en_US", "my": "my_MM"}

# ---------------------------------------------------------------- 社交账号关联
# sameAs 是 schema.org 中把网站主体与各社交官方账号"绑定"的标准字段，
# 搜索引擎据此确认账号归属；Facebook 主页与官网互为官方渠道时可双向验证。
SOCIAL_FACEBOOK = "https://www.facebook.com/profile.php?id=61595448556166"
SOCIAL_TIKTOK = "https://www.tiktok.com/@mrvideo168"
SOCIAL_TELEGRAM = "https://t.me/09973909999"
SOCIAL_SAME_AS = [SOCIAL_FACEBOOK, SOCIAL_TIKTOK, SOCIAL_TELEGRAM]

# 中文主体信息（英文/缅文见 i18n/en.json 与 i18n/my.json 的 jsonld 段）
ORG_NAME_ZH = "Mr.Video 传媒"
ORG_DESC_ZH = (
    "缅甸新媒体一站式服务专家。业务覆盖企业宣传、社交媒体代运营、新媒体人才培训、"
    "短视频电商、全域精准投放与网红孵化，只做有价值的流量。"
)
ORG_ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "77st / 32-33",
    "addressLocality": "Mandalay",
    "addressCountry": "MM",
}
ORG_CONTACT = {
    "email": "xl17607314666@gmai.com",
    "telephone": "09965909999",
}

# 结构化数据（Organization / sameAs）——按语言给出主体名称与描述
PAGES_META_JSONLD = {
    "zh": {"name": ORG_NAME_ZH, "description": ORG_DESC_ZH},
    "en": DICT_EN["jsonld"],
    "my": DICT_MY["jsonld"],
}

# ---------------------------------------------------------------- 页面配置
# 说明：Cloudflare Pages 启用了 clean URLs（/social-media.html → 308 → /social-media），
# 因此 SEO 声明与站内链接统一使用无扩展名形式，避免多一跳重定向。
PAGES = [
    {
        "name": "index",
        "src": "index.html",
        "out_en": "en/index.html",
        "out_my": "my/index.html",
        "urls": {"zh": "/", "en": "/en/", "my": "/my/"},
        "site": "https://mrvideo.vip",
    },
    {
        "name": "social",
        "src": "social-media.html",
        "out_en": "en/social-media.html",
        "out_my": "my/social-media.html",
        "urls": {"zh": "/social-media", "en": "/en/social-media", "my": "/my/social-media"},
        "site": "https://mrvideo.vip",
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


# ---------------------------------------------------------------- 英文阶段
def translate_text_en(text: str, missing: set):
    """翻译一个文本节点，保留原有缩进空白。"""
    m = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S)
    if not m:
        return text
    lead, core, trail = m.group(1), m.group(2), m.group(3)
    key = norm(core)
    if not key or not has_cjk(key):
        return text
    new = TEXT_EN.get(key)
    if new is None:
        missing.add(("text", key))
        return text
    return lead + new + trail


def translate_tag_en(tag: str, missing: set) -> str:
    """翻译标签内的 alt / placeholder / aria-label / title / option[value]。"""

    def repl_attr(m):
        name, val = m.group(1), m.group(2)
        key = norm(val)
        if not key or not has_cjk(key):
            return m.group(0)
        new = ATTR_EN.get(key) or TEXT_EN.get(key)
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
        new = ATTR_EN.get(key) or TEXT_EN.get(key)
        if new is None:
            missing.add(("attr", key))
            return m.group(0)
        return m.group(1) + new + m.group(3)

    tag = re.sub(r"(<option\s+value\s*=\s*\")([^\"]*)(\")", repl_option, tag)
    return tag


# ---------------------------------------------------------------- 缅语阶段
def translate_text_my(text: str, missing: set):
    """把英文文本节点翻译为缅文。

    判定规则：
      - 已是缅文（special 整段替换的产物）→ 跳过
      - 不含拉丁字母（纯数字/符号）→ 跳过
      - 字典命中 → 替换
      - 命中 keep 白名单（品牌名/邮箱/版权）→ 保留原文
      - 其余 → 记入 missing，构建失败（防止漏译）
    """
    m = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S)
    if not m:
        return text
    lead, core, trail = m.group(1), m.group(2), m.group(3)
    key = norm(core)
    if not key:
        return text
    if MYANMAR.search(key):          # 已经是缅文
        return text
    if not LATIN.search(key):        # 纯数字/符号
        return text
    new = TEXT_MY.get(key)
    if new is not None:
        return lead + new + trail
    if key in KEEP_MY:
        return text
    missing.add(("text", key))
    return text


def translate_tag_my(tag: str, missing: set) -> str:
    """翻译缅语版的 alt / placeholder / aria-label / title / option[value]。"""

    def repl_attr(m):
        name, val = m.group(1), m.group(2)
        key = norm(val)
        if not key or MYANMAR.search(key) or not LATIN.search(key):
            return m.group(0)
        new = ATTR_MY.get(key) or TEXT_MY.get(key)
        if new is None:
            if key in KEEP_MY:
                return m.group(0)
            missing.add(("attr", key))
            return m.group(0)
        return f'{name}="{new}"'

    tag = re.sub(
        r"\b(alt|placeholder|aria-label|title)\s*=\s*\"([^\"]*)\"", repl_attr, tag
    )

    def repl_option(m):
        key = norm(m.group(2))
        if not key or MYANMAR.search(key) or not LATIN.search(key):
            return m.group(0)
        new = ATTR_MY.get(key) or TEXT_MY.get(key)
        if new is None:
            if key in KEEP_MY:
                return m.group(0)
            missing.add(("attr", key))
            return m.group(0)
        return m.group(1) + new + m.group(3)

    tag = re.sub(r"(<option\s+value\s*=\s*\")([^\"]*)(\")", repl_option, tag)
    return tag


# ---------------------------------------------------------------- 公共
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


def shorten_nav_labels(src: str, table: dict) -> str:
    """把顶部导航与抽屉菜单的文案替换为短标签（仅当存在映射表时）。"""
    if not table:
        return src

    def replace_in_block(m):
        block = m.group(0)

        def repl(mm):
            open_tag, text, close_tag = mm.group(1), mm.group(2), mm.group(3)
            key = norm(text)
            if key in table:
                return open_tag + table[key] + close_tag
            return mm.group(0)

        return re.sub(r"(<a\b[^>]*>)([^<>]+)(</a>)", repl, block)

    return re.sub(
        r"<nav class=\"(?:main-nav|drawer-nav)\"[^>]*>.*?</nav>",
        replace_in_block,
        src,
        flags=re.S,
    )


def build_english(src: str, meta: dict, missing: set) -> str:
    """中文 → 英文。"""
    out = src

    # 1) 整段正则替换（带内嵌标签的复杂结构）
    for item in SPECIAL_RE_EN:
        out = re.sub(item["pattern"], item["replacement"], out, flags=re.S)

    # 2) 整段字面替换
    for k, v in SPECIAL_EN.items():
        out = out.replace(k, v)

    # 3) 移除中英重复元素
    for pattern in DROP_EN:
        out = re.sub(pattern, "", out, flags=re.S)

    # 4) head 元信息
    out = apply_meta(out, meta)

    # 5) 逐 token 翻译
    parts = []
    for kind, text in tokenize(out):
        if kind == "text":
            parts.append(translate_text_en(text, missing))
        elif kind == "tag":
            parts.append(translate_tag_en(text, missing))
        elif text.startswith("<!-- i18n:"):
            parts.append(text)  # 保留 i18n 占位符注释，供后续注入
        else:
            parts.append("")  # 英文版剥离其余 HTML 注释
    out = "".join(parts)

    # 6) 导航短标签（仅顶部导航与抽屉菜单）
    out = shorten_nav_labels(out, NAV_SHORT_EN)

    # 7) 资源路径回退一级
    out = rewrite_paths_en(out)

    # 8) lang 属性
    out = re.sub(r'<html lang="zh-CN">', '<html lang="en">', out)

    return out


def build_burmese(src: str, meta: dict, missing: set) -> str:
    """英文 → 缅文（阶段 2：输入即英文产物）。"""
    out = src

    # 1) 整段正则替换
    for item in SPECIAL_RE_MY:
        out = re.sub(item["pattern"], item["replacement"], out, flags=re.S)

    # 2) 整段字面替换
    for k, v in SPECIAL_MY.items():
        out = out.replace(k, v)

    # 3) head 元信息
    out = apply_meta(out, meta)

    # 4) 逐 token 翻译
    parts = []
    for kind, text in tokenize(out):
        if kind == "text":
            parts.append(translate_text_my(text, missing))
        elif kind == "tag":
            parts.append(translate_tag_my(text, missing))
        elif text.startswith("<!-- i18n:"):
            parts.append(text)
        else:
            parts.append("")
    out = "".join(parts)

    # 5) 缅文导航短标签（缅文字形较宽，导航用短词避免溢出）
    out = shorten_nav_labels(out, NAV_SHORT_MY)

    # 6) lang 属性（英文产物已改为 lang="en"，此处切到缅文）
    out = re.sub(r'<html lang="en">', '<html lang="my">', out)

    return out


def normalize_links_zh(src: str) -> str:
    """中文站内链接规范化为 Cloudflare clean URLs（无 .html 扩展名）。

    中文站在根目录，故 index.html → / ，social-media.html → /social-media
    幂等：重复构建不会二次改写。
    注意：用零宽断言 (?=") 锚定结尾，避免把 href 的收尾引号吞掉。
    """
    src = re.sub(
        r'href="(?:/)?index\.html(#[^"]*)?(?=")',
        lambda m: 'href="/' + (m.group(1) or ""),
        src,
    )
    src = re.sub(r'href="(?:/)?social-media\.html(?=")', 'href="/social-media', src)
    return src


def normalize_links_en(src: str) -> str:
    """英文版站内链接规范化为 Cloudflare clean URLs（无 .html 扩展名）。

    英文站在 /en/ 子目录，故 index.html → /en/ ，social-media.html → /en/social-media
    幂等：已是 /en/ 前缀的链接不会被二次改写。
    注意：用零宽断言 (?=") 锚定结尾，避免把 href 的收尾引号吞掉。
    """
    src = re.sub(
        r'href="(?:/)?index\.html(#[^"]*)?(?=")',
        lambda m: 'href="/en/' + (m.group(1) or ""),
        src,
    )
    src = re.sub(
        r'href="/(#[^"]*)?(?=")',
        lambda m: 'href="/en/' + (m.group(1) or ""),
        src,
    )
    src = re.sub(r'href="(?:/)?social-media\.html(?=")', 'href="/en/social-media', src)
    src = src.replace('href="/social-media"', 'href="/en/social-media"')
    return src


def normalize_links_my(src: str) -> str:
    """缅语版站内链接：/en/ 前缀整体切到 /my/。

    注意：只在「注入缅语版语言切换器之前」调用，避免把切换器里的
    「English」入口也误改成缅语。
    """
    src = src.replace('href="/en/', 'href="/my/')
    src = src.replace("https://mrvideo.vip/en/", "https://mrvideo.vip/my/")
    return src


# ---------------------------------------------------------------- 三语切换器
def _lang_links(page: dict, cur: str) -> str:
    out = []
    for code in LANG_ORDER:
        url = page["urls"][code]
        current = ' class="is-current" aria-current="true"' if code == cur else ""
        out.append(
            f'<a href="{url}" hreflang="{LANG_HREFLANG[code]}" lang="{LANG_HTML[code]}"{current}>'
            f"{LANG_LABEL[code]}</a>"
        )
    return "".join(out)


def switch_block(page: dict, cur: str, variant: str) -> str:
    """三语切换器。cur = 当前语言（zh / en / my）。

    variant:
      header  → 地球图标 + 当前语言 + 下拉菜单（桌面端）
      drawer  → 三个语言横向排列（移动端抽屉内）
      footer  → 三个语言横向排列（页脚）
    """
    aria = UI_BY_LANG[cur]["aria"]
    title = UI_BY_LANG[cur]["title"]
    current_code = cur

    if variant == "header":
        menu = '<ul class="lang-menu">' + "".join(
            f'<li><a href="{page["urls"][c]}" hreflang="{LANG_HREFLANG[c]}" lang="{LANG_HTML[c]}"'
            + (' class="is-current" aria-current="true"' if c == current_code else "")
            + f">{LANG_LABEL[c]}</a></li>"
            for c in LANG_ORDER
        ) + "</ul>"
        return (
            '<div class="lang-switcher">'
            f'<button type="button" class="lang-switch" aria-haspopup="true" aria-expanded="false" '
            f'aria-label="{aria}" title="{title}">'
            f"{GLOBE_ICON}<span class=\"lang-label\">{LANG_LABEL[current_code]}</span>"
            f'<svg class="lang-caret" viewBox="0 0 24 24" width="12" height="12" fill="none" '
            'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>'
            "</button>"
            f"{menu}</div>"
        )

    cls = "drawer-langs" if variant == "drawer" else "footer-langs"
    return f'<div class="{cls}" role="group" aria-label="{aria}">' + _lang_links(page, current_code) + "</div>"


def jsonld_block(page: dict, lang: str) -> str:
    """生成 Organization 结构化数据，把官网与 Facebook 等社交主页正式关联。

    sameAs 字段是 schema.org 里声明「同一主体的其他官方账号」的标准做法，
    搜索引擎据此把官网与 Facebook 主页视为同一实体的不同呈现，
    也是 Facebook 侧认领官网（官网 ↔ 主页互相验证）的依据。
    """
    meta = PAGES_META_JSONLD[lang]
    canonical = page["site"] + page["urls"][lang]

    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": page["site"] + "/#organization",
        "name": meta["name"],
        "alternateName": "Mr.Video",
        "url": canonical,
        "logo": page["site"] + "/images/logo-wordmark.png",
        "image": page["site"] + "/images/logo-wordmark.png",
        "description": meta["description"],
        "inLanguage": LANG_HTML[lang],
        "address": ORG_ADDRESS,
        "email": ORG_CONTACT["email"],
        "telephone": ORG_CONTACT["telephone"],
        # ↓ 社交主页关联：Facebook / TikTok / Telegram
        "sameAs": SOCIAL_SAME_AS,
    }
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return '  <script type="application/ld+json">\n' + body + "\n  </script>"


def head_block(page: dict, lang: str) -> str:
    """生成 canonical / og:url / og:locale / hreflang（三种语言互指）。"""
    abs_urls = {c: page["site"] + page["urls"][c] for c in LANG_ORDER}
    canonical = abs_urls[lang]
    others = [c for c in LANG_ORDER if c != lang]

    og_alt = "\n".join(
        f'  <meta property="og:locale:alternate" content="{LANG_OG[c]}" />' for c in others
    )
    hreflang = "\n".join(
        f'  <link rel="alternate" hreflang="{LANG_HREFLANG[c]}" href="{abs_urls[c]}" />'
        for c in LANG_ORDER
    )
    return (
        f'  <meta property="og:url" content="{canonical}" />\n'
        f'  <meta property="og:locale" content="{LANG_OG[lang]}" />\n'
        f"{og_alt}\n"
        f'  <link rel="canonical" href="{canonical}" />\n'
        f"{hreflang}\n"
        f'  <link rel="alternate" hreflang="x-default" href="{abs_urls["zh"]}" />\n'
        f"{jsonld_block(page, lang)}"
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
        # 中文站链接先规范化（clean URLs），后续英/缅版本以此为基准加前缀
        src = normalize_links_zh(src)

        # ---------- 阶段 0：中文站 ----------
        zh = src
        zh = inject(zh, "head-alt", head_block(page, "zh"))
        zh = inject(zh, "lang-switch", switch_block(page, "zh", "header"))
        zh = inject(zh, "lang-switch-drawer", switch_block(page, "zh", "drawer"))
        zh = inject(zh, "lang-switch-footer", switch_block(page, "zh", "footer"))

        # ---------- 阶段 1：英文站 ----------
        en = build_english(src, PAGES_META_EN[page["name"]], missing)
        en = normalize_links_en(en)

        # 残留中文检查（在注入语言切换器之前，切换器的语言标识是刻意的）
        residue = sorted(
            {norm(m) for m in re.findall(r"[^<>]*[㐀-䶿一-鿿][^<>]*", en) if norm(m)}
        )

        en = inject(en, "head-alt", head_block(page, "en"))
        en = inject(en, "lang-switch", switch_block(page, "en", "header"))
        en = inject(en, "lang-switch-drawer", switch_block(page, "en", "drawer"))
        en = inject(en, "lang-switch-footer", switch_block(page, "en", "footer"))

        # ---------- 阶段 2：缅语站（以英文产物为基准） ----------
        my = normalize_blocks(en)
        my = build_burmese(my, PAGES_META_MY[page["name"]], missing)
        my = normalize_links_my(my)

        my_residue_cjk = sorted(
            {norm(m) for m in re.findall(r"[^<>]*[㐀-䶿一-鿿][^<>]*", my) if norm(m)}
        )
        # 未翻译的拉丁文本（排除 keep 白名单与纯数字/符号）
        my_untranslated = []
        for kind, text in tokenize(my):
            if kind != "text":
                continue
            key = norm(text)
            if not key or MYANMAR.search(key) or not LATIN.search(key):
                continue
            if key in KEEP_MY or key in TEXT_MY:
                continue
            if any(w in key for w in ("http", "www.", "@", ".com", ".cn")):
                continue
            my_untranslated.append(key)
        my_untranslated = sorted(set(my_untranslated))

        my = inject(my, "head-alt", head_block(page, "my"))
        my = inject(my, "lang-switch", switch_block(page, "my", "header"))
        my = inject(my, "lang-switch-drawer", switch_block(page, "my", "drawer"))
        my = inject(my, "lang-switch-footer", switch_block(page, "my", "footer"))

        # ---------- 报告 ----------
        print(f"[{page['name']}] 中文 ✓  英文 ✓" + (f"（残留中文 {len(residue)} 处）" if residue else "（无残留中文）"))
        for r in residue[:20]:
            print(f"    ! 英文残留：{r[:100]}")

        print(f"[{page['name']}] 缅文 ✓"
              + (f"（残留中文 {len(my_residue_cjk)} 处）" if my_residue_cjk else "（无残留中文）")
              + (f"（未翻译 {len(my_untranslated)} 处）" if my_untranslated else "（无未翻译英文）"))
        for r in my_residue_cjk[:20]:
            print(f"    ! 缅文残留中文：{r[:100]}")
        for r in my_untranslated[:20]:
            print(f"    ! 缅文未翻译：{r[:100]}")

        if residue:
            errors.append(f"{page['name']}: 英文版残留中文 {len(residue)} 处")
        if my_residue_cjk:
            errors.append(f"{page['name']}: 缅语版残留中文 {len(my_residue_cjk)} 处")
        if my_untranslated:
            errors.append(f"{page['name']}: 缅语版未翻译英文 {len(my_untranslated)} 处")

        if not check_only:
            src_path.write_text(zh, encoding="utf-8")
            (ROOT / page["out_en"]).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / page["out_my"]).parent.mkdir(parents=True, exist_ok=True)
            (ROOT / page["out_en"]).write_text(en, encoding="utf-8")
            (ROOT / page["out_my"]).write_text(my, encoding="utf-8")
            print(f"    → 写入 {page['src']} / {page['out_en']} / {page['out_my']}")

    if missing:
        print("\n[错误] 以下文案缺少翻译，请补充到 i18n/en.json 或 i18n/my.json：")
        for kind, key in sorted(missing):
            print(f"    [{kind}] {key}")
        errors.append(f"{len(missing)} 条文案缺翻译")

    if errors:
        print("\n构建失败：\n  - " + "\n  - ".join(errors))
        sys.exit(1)

    print("\n全部通过 ✓" if not check_only else "\n校验通过 ✓")


if __name__ == "__main__":
    main()
