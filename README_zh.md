# G1SPEI 快速生产框架：运行指南

作者：Zhenheng Xu；邮箱：xuzh@nercita.org.cn。代码许可证：MIT。

本程序读取指定年月的一对 ERA5-Land 降水、气温栅格，利用预先计算的气候态
和 Gamma 参数，依次生成全球 1 km 降水、温度、PET、SPEI-1 及质量标记。
只计算指定月份，不重复读取 1951–2025 年全部历史数据，也不重新拟合分布。

## 1. 安装与第一次测试

推荐在独立 conda 环境中运行，不要求 ArcGIS。下载代码并进入代码根目录：

```sh
conda env create -f environment.yml
conda activate g1spei
python -m pip install --no-deps --no-build-isolation -e .
python -m pytest -q
python examples/make_demo.py demo
python -m g1spei run --parameters demo/parameters --precipitation demo/precipitation.tif --temperature demo/temperature.tif --precipitation-unit m_month --temperature-unit K --year 2025 --month 7 --output demo/result
```

以上示例完全使用合成数据，不需要下载全球参数。预期降水为 85 mm/月，温度为 16 °C。
输出文件在 `demo/result`。同一路径再次运行会拒绝覆盖，需指定一个新输出目录。

## 2. 支撑数据与文件组织

代码与参数分开发布。GitHub 只上传本代码目录；约 41 GB 参数上传 Zenodo。
参数尚无公开 DOI，发布后在 [PARAMETERS.md](docs/PARAMETERS.md) 填写真实链接。
将所有参数压缩包解压到同一个目录，文件夹结构会自动合并，例如：

```text
workspace/
  G1SPEI/                             # 代码
  G1SPEI-parameters-v1.0.0/
    manifest.json
    ERA5_temperature/
    ERA5_precipitation/
    WorldClim_temperature/
    WorldClim_precipitation/
    SPEI_1km_params/
    PET_1km_params/
  inputs/
  runs/
```

首次使用和搬移数据后执行完整校验；这会读完所有参数，耗时取决于磁盘速度：

```sh
python -m g1spei verify-parameters --parameters ../G1SPEI-parameters-v1.0.0
```

参数包括 96 个月份参数文件及 1 个气候态 Heat Index，共 97 个栅格。
没有将 1990 年测试 Heat Index、纬度栅格、旧测试结果、概览或 notebook 缓存放入参数包。
纬度直接按目标网格像元中心计算。参数使用原始精度的无损压缩，不进行 Int16 量化。

## 3. 实际生产

准备好单波段、带 CRS 和 NoData 的月降水、月平均气温 GeoTIFF。
它们必须与粗分辨率参数的网格严格一致，详见 [输入约定](docs/INPUTS.md)。
程序不猜测输入单位、年月或数据是否为最终版；这些信息由运行者核实。

```sh
python -m g1spei run --parameters ../G1SPEI-parameters-v1.0.0 --precipitation ../inputs/precipitation_2026_01.tif --temperature ../inputs/temperature_2026_01.tif --precipitation-unit m_month --temperature-unit K --year 2026 --month 1 --output ../runs/2026-01
```

降水单位选项：`m_month` 月累计米、`mm_month` 月累计毫米、`m_day` 月平均日累计米、
`mm_day` 月平均日累计毫米。后两种会乘实际月天数。已累计的月降水不能再次乘天数。
气温单位选 `K` 或 `C`。支持路径中包含中文和空格，包含空格时为路径加引号。

小范围检查可增加 `--window 9000 6000 256 256`；表示目标栅格的列偏移、行偏移、宽、高。
全球运行无需此选项。默认 `--tile-size 512`，各月份建议顺序执行以避免磁盘争用。
建议至少留 8 GB 可用内存、20 GB 输出和临时磁盘空间，参数占用另计。

## 4. 结果检查

每次运行输出五个栅格和 `run.json`：降水、气温、PET、SPEI、QA。前四个为 Float32、
无损压缩、NaN 缺测；QA 为 UInt16 位标记，缺测值 65535。不能把 QA 当连续物理量解释。
具体位定义见 [CHANGES_AND_QA.md](docs/CHANGES_AND_QA.md)。

先查看 `run.json` 中有效像元数量、数值范围、低标准差像元、超过 5000 mm 的降水像元、
SPEI 达到上下限的数量；再结合 QA 做空间检查。极大降水标记仅作筛查，不自动裁剪至 5000 mm。
默认低标准差筛查可减少异常值放大，但无法保证排除所有不合理值。

## 5. 两种配置及科学适用范围

- `guarded`（默认）：粗降水标准差低于 0.1 mm/月时屏蔽该处降水及 SPEI；采用真实日历；
  当 0<T≤5 °C 时，最终月 PET 不超过 50 mm。
- `reference`：保留原公式的正标准差计算、原固定非闰年月日长方案、原未校正 PET 上限及
  Heat Index=0 的约定，供数值比较。缺测修复和气候态 Heat Index 仍生效，因而不能称为
  历史产品逐像元严格复现。

`--min-std` 可覆盖阈值，例如 `--min-std 0.01`。0.1 mm 是显式数值保护阈值，尚未由
独立观测优化，不能把它描述成已验证的干旱区科学订正。改变阈值会改变有效覆盖。
如需结果与已发表历史数据严格接续，应评估年度 Heat Index 与气候态 Heat Index 差异，
并对数值保护规则开展历史回算验证。当前包不重新拟合已有 Gamma 参数。

## 6. 中断、错误和发布

完整结果写完后才将 `.partial` 目录改为正式输出目录。失败时保留 `failure.json`，
避免把不完整结果当成成功结果。程序不自动清空用户目录、不覆盖原始文件。
中断后请指定新的输出路径重跑；确认无用后再自行删除旧 `.partial` 目录。

GitHub 上传本代码目录即可，忽略规则已经排除大栅格和运行结果。Zenodo 上传参数压缩包、
`manifest.json`、文件说明及校验文件。公开发布前补充真实 DOI 和参数数据许可；MIT 仅适用于
代码与文档，不能替代 WorldClim 等来源数据的许可。参见 [发布步骤](docs/RELEASE.md)。
