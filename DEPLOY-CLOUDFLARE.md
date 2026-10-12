# Mr.Video 官网 · Cloudflare Pages 部署指南

本目录为可直接托管的静态网站：`index.html` + `css/` + `js/` + `images/`。
以下三种方式任选其一，全部免费（Cloudflare Pages Free 额度足够）。

---

## 方式一：控制台「直接上传」拖拽（最快，无需 Git / 无命令行）

1. 打开 https://dash.cloudflare.com → 左侧 **Workers 和 Pages** → **创建** → 选择 **Pages** → **直接上传**。
2. 项目名称填 `mrvideo`（或你喜欢的英文名），点击「创建项目」。
3. 把本项目里的 `mrvideo-cloudflare-pages.zip` 解压后的内容（或直接把 `index.html`、`css`、`js`、`images` 四个拖进去）拖入上传区，点 **部署**。
4. 几秒后获得 `*.pages.dev` 域名；在「自定义域」里绑定你的正式域名（如 `www.mrvideo.com`）。
5. 后续更新：重新打包 zip 上传，或改用方式二/三做持续部署。

---

## 方式二：Git 仓库连接（推荐，支持自动 CI 部署）

> 前提：把本项目推送到 GitHub / GitLab 仓库。

1. 仓库根目录需包含 `index.html`（已满足）。
2. Cloudflare 控制台 → **Workers 和 Pages** → **创建** → **Pages** → 连接 Git 仓库。
3. 构建配置：
   - 框架预设：**无 (None) / 纯静态**
   - 构建命令：**留空**
   - 构建输出目录：**`/`（根目录）**
4. 保存并部署。之后每次 `git push` 自动触发重新部署。

本地已为你初始化好 Git 仓库（`.gitignore` 已排除 `.workbuddy`），你只需：
```bash
git remote add origin <你的仓库地址>
git push -u origin main
```
（若分支名是 master，把 `main` 换成 `master`）

---

## 方式三：Wrangler CLI（开发者，需本地环境）

```bash
npm install -g wrangler
wrangler login            # 浏览器授权
wrangler pages deploy .   # 在项目根目录执行
```
本项目已附 `wrangler.toml`（`pages_build_output_dir = "."`）。

---

## 上线前检查清单

- [ ] 把 `images/logo-horizontal.png`（透明 Logo）放入 `images/`，覆盖占位 JPG
- [ ] 替换所有 `<!-- 待替换 -->` 标注内容：联系方式、价格、案例、新闻
- [ ] 接入表单后端（见 `js/main.js` 内 `TODO: 接入表单接收接口`）
- [ ] 填入 Google Analytics / Meta Pixel ID（见 `index.html` head 注释位）
- [ ] 在 Cloudflare 开启 **始终使用 HTTPS** 与 **自动 HTTPS 重写**
- [ ] 绑定自定义域名并等待证书生效

---

## 备注

- 本沙箱环境无法安装 `wrangler`（npm 被限制）且缺少你的 Cloudflare 凭据，
  故由你按上述任一方式完成最终发布；我已把站点整合成即用成品。
- `mrvideo-cloudflare-pages.zip` 即为「直接上传」所需的完整站点包。
