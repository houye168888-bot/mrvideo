# Mr.Video 官网 · Cloudflare Pages 部署指南

本目录为可直接托管的静态网站：`index.html` + `css/` + `js/` + `images/`。
以下三种方式任选其一，全部免费（Cloudflare Pages Free 额度足够）。

---

## 方式一：控制台「直接上传」拖拽（最快，无需 Git / 无命令行）

> **⚠️ 注意：不要点成「Create an app / Workers」。**
> 新版 Cloudflare 控制台点击 **Workers 和 Pages → 创建** 后，默认进入的是 Workers 的「Create an app」界面（显示 Connect GitHub / Start with Hello World / Upload your static files）。
> 静态网站必须用 **Pages**：请点页面底部的 **"Need to use the legacy Pages workflow? Continue to Pages"**，或直接访问 https://dash.cloudflare.com/?to=/:account/pages/create

1. 打开 https://dash.cloudflare.com → 左侧 **Workers 和 Pages** → 点底部 **Continue to Pages** → **创建项目** → 选择 **直接上传**。
2. 项目名称填 `mrvideo`（或你喜欢的英文名），点击「创建项目」。
3. 把本项目里的 `mrvideo-cloudflare-pages.zip` 解压后的内容（或直接把 `index.html`、`css`、`js`、`images` 四个拖进去）拖入上传区，点 **部署**。
4. 几秒后获得 `*.pages.dev` 域名；在「自定义域」里绑定你的正式域名（如 `www.mrvideo.com`）。
5. 后续更新：重新打包 zip 上传，或改用方式二/三做持续部署。

---

## 方式二：Git 仓库连接（推荐，支持自动 CI 部署）

> 前提：把本项目推送到 GitHub / GitLab 仓库。

1. 仓库根目录需包含 `index.html`（已满足）。
2. Cloudflare 控制台 → **Workers 和 Pages** → 点底部 **Continue to Pages** → **创建** → **Pages** → 连接 Git 仓库。
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

---

## 自定义域名解析（绑定你买的域名）

绑定自定义域名能顺带解决缅甸访问 `*.pages.dev` 超时的问题——访问走 Cloudflare 边缘（仰光有节点），比 `pages.dev` 稳定。

### 第 1 步：在 Cloudflare 添加你的域名
1. 控制台 → 左侧 **网站 (Websites)** → **添加站点 (Add a site)** → 输入你的域名（如 `mrvideo.com`）。
2. 套餐选 **Free**。
3. Cloudflare 会显示**两组 NS 服务器地址**（形如 `xxx.ns.cloudflare.com` / `yyy.ns.cloudflare.com`）。**复制下来**，下一步要用。

### 第 2 步：去域名注册商修改 NS（推荐方案 A）
> 若域名只放这个官网，最省事：把整域 DNS 交给 Cloudflare，Pages 绑域时自动建好记录+免费 SSL。

| 注册商 | 后台路径 |
|---|---|
| 阿里云/万网 | 控制台 → **域名** → 域名列表 → 点域名 → **DNS 修改 / 修改 DNS 服务器** → 填 Cloudflare 给的 2 个 NS |
| 腾讯云/DNSPod | 控制台 → **域名注册** → 我的域名 → 管理 → **修改 DNS 服务器** → 填 Cloudflare 的 NS |
| Namecheap | Domain List → 域名 **Manage** → **Nameservers** → 选 Custom DNS → 填 Cloudflare 的 NS |
| GoDaddy | My Products → 域名 → **DNS** → 下方 Nameservers → **Change** → 填 Cloudflare 的 NS |
| Cloudflare 注册 | 域名本身在 CF，跳过此步 |

> 改 NS 后**原注册商的解析记录全部失效**，若域名还挂了邮箱(MX)或其他站点，需回到本步选「方案 B」或把那些记录迁到 Cloudflare。

### 第 3 步：在 Pages 绑定自定义域名
1. 控制台 → **Workers 和 Pages** → `mrvideo` 项目 → **自定义域 (Custom domains)** → **Set up a custom domain**。
2. 输入域名：建议同时绑 `mrvideo.com`（apex）和 `www.mrvideo.com`（子域），两个都填。
3. 按提示**验证所有权**：若第 2 步已改 NS，CF 会自动添加记录并通过；若未改 NS（方案 B），CF 会给出一条 **CNAME** 记录（目标通常为 `mrvideo.pages.dev` 或一串哈希，**以控制台显示为准**），回到注册商 DNS 面板手动添加。
4. 等待 **SSL 证书签发**（通常几分钟，偶尔数小时）。状态变绿即生效。

### 方案 B：不转 NS，只在原注册商加 CNAME（域名另有他用）
1. 在 Pages 自定义域里输入域名，CF 会给一条 CNAME（如 `www` → `mrvideo.pages.dev`）和一条验证记录。
2. 去原注册商 DNS 面板**手动添加**这两条记录，等待生效。
3. 注意：`apex` 域名（不带 www 的 `mrvideo.com`）多数注册商不支持裸 CNAME，需注册商支持 **CNAME Flattening / ALIAS**（Cloudflare、DNSPod 部分支持）；否则只绑 `www` 并做跳转。

### 验证与排错
- 用**无痕窗口**访问 `https://www.mrvideo.com` 与 `https://mrvideo.com`。
- DNS 全球生效需 **5 分钟～48 小时**，可用 https://www.whatsmydns.net 查解析进度。
- 证书未就绪前访问会报 SSL 错误，属正常，等即可。
- 若只放官网，**方案 A（转 NS）** 最稳，且自动获得 CDN、WAF、免费 HTTPS。
