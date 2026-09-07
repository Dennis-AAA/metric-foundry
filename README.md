# 方向偏好 × 波动率偏好 看板

把「方向偏好 × 波动率偏好」信号矩阵做成可以**日度 / 周度自动更新**的看板：六大类资产（美股 ES、美债 ZN、EUR 6E、JPY 6J、黄金 GC、WTI CL）× 七列信号（短线 DELTA、长线 DELTA、VEGA、SKEW、GAMMA、VOL 体制、综合热度）。全部指标由公开免费数据计算：Yahoo Finance 期货日线与 ETF 期权链、CBOE 波动率指数、CFTC 持仓报告。

- `engine/` — Python 信号引擎 `macrovol`：抓数据 → 打分 → 写 `data/latest.json`
- `data/` — 最新快照、每日历史快照 `history/`、用于历史走势的 `timeline.json`
- `src/` — Next.js 16 + Tailwind + shadcn/ui 看板：矩阵表、单元格解释、逐资产钻取（Gamma 曲线、COT、IV 走势）、方法说明页
- `.github/workflows/update-signals.yml` — 周一至周五收盘后日度更新、周五 COT 发布后周度更新，结果自动提交回仓库

## 本地运行

前置：Node 20+，Python 3.10+（推荐 [uv](https://docs.astral.sh/uv/)）。

```bash
# 1. Python 引擎
uv venv .venv && uv pip install --python .venv/bin/python -e "./engine[dev]"
# 或者：python3 -m venv .venv && .venv/bin/pip install -e "./engine[dev]"

# 2. 生成一次快照（约 20–60 秒，需要访问 Yahoo / CBOE / CFTC）
.venv/bin/python -m macrovol.cli run              # 日度
.venv/bin/python -m macrovol.cli run --mode weekly  # 周度（周五 COT 发布后）

# 3. 看板
npm install
npm run dev -- --port 43117
```

打开 http://127.0.0.1:43117 。页面每次请求都直接读取 `data/latest.json`，重新跑引擎后刷新即可；右上角「日度刷新 / 周度刷新」会调用 `/api/refresh` 在同一台机器上跑引擎（90 秒冷却，防止连点）。`MACROVOL_ALLOW_REFRESH=0` 或 Vercel 无盘环境会自动关掉按钮。若要给公网加口令，设 `MACROVOL_REFRESH_TOKEN`。

常用参数：

```bash
python -m macrovol.cli run --assets ES GC      # 只算部分资产
python -m macrovol.cli run --offline            # 只用 data/cache 里的缓存重算（改阈值时很方便）
python -m macrovol.cli run --skip-options       # 跳过期权链（更快，Skew/Gamma 显示无数据）
python -m macrovol.cli run --intraday           # 保留当天未收盘的行
```

测试：`cd engine && ../.venv/bin/python -m pytest`。

## 每一列怎么算

详细规则见看板内的「方法说明与复现」页（`/methodology`），阈值全部集中在 `engine/macrovol/config.py`，打分逻辑在 `engine/macrovol/signals.py`。概要：

| 列 | 分项 / 输入 | 规则 |
| --- | --- | --- |
| 短线 DELTA (1–4 周) | Flash = 10 日收益 z 值；FM = CFTC 快钱（Leveraged Funds / Managed Money）净仓位 4 周变化 z 值；Gamma = 做市商净 Gamma 为负时放大 Flash | 加权 0.5/0.3/0.2；做市商多 Gamma + 平静体制时 \|原始分\| < 1.25 拉回中性（"高频叠加"） |
| 长线 DELTA (1–3 月) | Confirmed = 价格>MA200、MA50>MA200、63 日收益 三票；RM = CFTC 慢钱（Asset Manager / Swap Dealers）13 周变化 z 值；FV = 对数价格相对 1 年均值偏离 | 加权 0.4/0.3/0.3；趋势未确认而由结构分项主导 → 半档 ±1 并标"结构观察" |
| VEGA | IV（VIX / MOVE×0.065 / GVZ / OVX / FX 期权链 ATM）1 年分位 + (IV−RV20)/RV20 | 水位分 + carry 分 → 强买波 / 买波 / 中性 / 卖波 / 强卖波 |
| SKEW | ETF 期权链 25Δ 风险逆转 / ATM IV（最接近 45 DTE 的流动到期）；美股附加 CBOE SKEW | < −5% 偏空 RR，> +5% 偏多 RR；偏离资产常态标 ⚠ |
| GAMMA | ETF 期权 ≤60 DTE 全部合约的美元 Gamma（call 多 / put 空 假设），±15% 网格重定价求翻转位 | 净 Gamma>0 平静·收theta；<0 风暴·偏多/偏空；接近平衡或翻转位 初起·中性 |
| VOL 体制 | IV 序列 1 年分位、5 日变化、vol-of-vol 分位、RV20/RV60 | 平静 / 混乱 / 高Vol缓和 / 高Vol扩张 / 低Vol转折 |
| 行底 | \|短线\|+\|长线\|+\|Vega\|+\|Skew\|+Gamma 热度+体制热度 (0–12) | 行背景深浅；≠ 表示短线与长线不一致 |

### 复现边界

- 原图的 Flash / FM / Confirmed / RM / FV 是作者内部模型名称，这里给出的是一套自洽、可审计的公开数据实现，口径可在 `signals.py` 里替换。
- 真实做市商 Gamma 需要付费的 OPRA 成交方向数据；免费方案用 ETF 期权 OI 近似，CME 期货期权缺失。SPY / GLD / TLT 代理尚可，USO / FXE / FXY 很弱，单元格带 ⚠。
- FX 没有免费的隐含波动率指数（CBOE EVZ/JYVIX 已停更），EUR / JPY 的 Vega 用期权链 ATM IV + RV 分位代理，Skew 经常"无数据"；看板累计 60 个以上日度快照后会改用自身 IV 历史分位。

## 自动更新

`.github/workflows/update-signals.yml`：

- 周一至周五 22:30 UTC（美东收盘后）跑 `--mode daily`
- 周五 21:00 UTC（CFTC 15:30 ET 发布后）跑 `--mode weekly`
- 也可以在 Actions 页手动触发并选择 mode

每次运行提交 `data/latest.json`、`data/timeline.json` 和 `data/history/<日期>.json`。前端部署（Vercel、静态托管或自托管 `npm run build && npm start`）读到新提交即更新。

## 挂到固定域名（推荐 Fly.io）

日度刷新要跑 Python 并写回 `data/`，所以必须是常驻进程，不能用 Vercel / Cloudflare Pages。Fly 会给你一个**不会变**的地址：`https://gmunu-metric-foundry.fly.dev`，右上角刷新一样能点。

在自己电脑上（先按上面的 Origin CLI 把仓库 clone 下来）：

```bash
# 1. 注册/登录 Fly（浏览器授权，可用 GitHub / Google）
curl -fsSL https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"
fly auth login

# 2. 创建应用、1GB 数据盘并发布
cd metric-foundry
bash scripts/deploy-fly.sh
```

成功后打开 **https://gmunu-metric-foundry.fly.dev** 。以后改代码再跑一遍 `fly deploy` 即可。

### 用自己的域名（例如 board.example.com）

```bash
fly certs add board.example.com -a gmunu-metric-foundry
```

然后在域名 DNS 加一条：

| 类型 | 主机记录 | 目标 |
| --- | --- | --- |
| CNAME | `board` | `gmunu-metric-foundry.fly.dev` |

证书由 Fly 自动签。把 `board.example.com` 换成你已经买好的域名即可。

### 临时分享（地址会变）

当前这次会话上的 Cloudflare 隧道仍可用，但**不是**固定域名，会话结束就没了：

```bash
npm run build && npm run start    # :8080 / :43180
npm run public                    # https://*.trycloudflare.com
```

## 数据源

| 数据 | 来源 |
| --- | --- |
| ES=F ZN=F 6E=F 6J=F GC=F CL=F、^MOVE、^IRX | Yahoo Finance（yfinance） |
| VIX VIX9D VIX3M VVIX SKEW GVZ OVX | CBOE 官方 CSV（cdn.cboe.com） |
| SPY TLT FXE FXY GLD USO 期权链 | Yahoo Finance |
| CFTC TFF（ES/ZN/6E/6J）与 Disaggregated（GC/CL）期货持仓 | publicreporting.cftc.gov Socrata API |

原始数据会缓存到 `data/cache/`（已 gitignore），默认 6 小时内复用；`--cache-hours 0` 强制重新下载。
