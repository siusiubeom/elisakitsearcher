# 🧪 ELISA Kit Matcher

A fast, practical Python tool to automatically **discover and match ELISA kits** for multiple analytes  
(e.g. **NOX4 + CXCL10**) from **trusted vendors**, using **DuckDuckGo search + parallel page parsing**.

> Designed for researchers who want **multiple valid kit options**, not just one.

---

## 📌 Table of Contents
- [✨ Features](#-features)
- [🧠 How it works](#-how-it-works)
- [🔧 Installation](#-installation)
- [🚀 Quick Start](#-quick-start)
- [🧪 Common Usage Recipes](#-common-usage-recipes)
- [🌐 Domain Handling](#-domain-handling)
- [⚙️ Performance Tuning](#️-performance-tuning)
- [📤 Output Format](#-output-format)
- [⚠️ Limitations](#️-limitations)
- [🇰🇷 한국어 설명](#-한국어-설명)

---

## ✨ Features
- ✅ Uses a **built-in list of known ELISA vendors** by default (no `--domains` needed)
- ✅ Finds **vendors that have ALL requested analytes**
- ✅ Optional strict filters:
  - **Species** (e.g. mouse)
  - **Sample type** (e.g. serum / plasma)
  - **ELISA keyword** presence
- ✅ **Parallel fetching** for speed (`--workers`)
- ✅ **Hard time budget** to prevent long runs (`--budget-sec`)
- ✅ **Early-stop mode** for fastest first match
- ✅ Outputs **direct product links only** (no scores, no ranking)

---

## 🧠 How it works
1. Uses DuckDuckGo (DDG) search to gather candidate product URLs
2. Runs `site:vendor` searches against trusted ELISA vendors
3. Fetches pages in parallel and extracts text
4. Detects analyte names and aliases
5. Keeps only vendors that have **at least one valid kit per analyte**

---

## 🔧 Installation

### Requirements
- **Python 3.9+**

### Dependencies
```bash
pip install requests beautifulsoup4 ddgs lxml
```

If you see a warning about `duckduckgo_search` being renamed:

```bash
pip install ddgs
```

---

## 🚀 Quick Start (Most Common)

```bash
python elisa_matcher.py
```

**Default behavior:**
- Analytes: `NOX4 CXCL10`
- Species: `mouse`
- Samples: `serum plasma`
- Uses a curated trusted vendor list
- Prints matched vendors + direct product links

---

## 🧪 Common Usage Recipes

### 1️⃣ Specify analytes / species / samples

**PowerShell (Windows)**

```powershell
python elisa_matcher.py `
  --analytes NOX4 CXCL10 `
  --species mouse `
  --sample serum plasma
```

**bash (Mac / Linux)**

```bash
python elisa_matcher.py \
  --analytes NOX4 CXCL10 \
  --species mouse \
  --sample serum plasma
```

> Aliases such as `IP-10 → CXCL10` are supported internally.

### 2️⃣ Get ~5 or more vendor choices (Recommended)

❗ **Do NOT use `--early-stop`**

```powershell
python elisa_matcher.py `
  --site-results 20 `
  --max-fetch 100 `
  --budget-sec 45
```

This will:
- Search more pages per vendor
- Return multiple matched vendors
- Finish in ~30–60 seconds (network dependent)

### 3️⃣ Fastest run (first valid vendor only)

```bash
python elisa_matcher.py --early-stop
```

Stops as soon as one vendor satisfies all analytes.

### 4️⃣ Strict filtering (Optional)

```powershell
python elisa_matcher.py `
  --require-species `
  --require-samples `
  --require-elisa
```

⚠️ Some vendor pages omit details → strict mode may miss valid kits.

---

## 🌐 Domain Handling

### ✅ Default mode (Recommended)
You do **not** need `--domains`.

The script automatically uses a curated list of known ELISA vendors, including:
- FineTest
- Novus / Bio-Techne
- Krishgen
- Abcam
- Thermo Fisher
- CUSABIO
- Cloud-Clone
- and others

This gives **high precision + good speed**.

### 🔧 Override domains manually (Optional)

```powershell
python elisa_matcher.py `
  --domains fn-test.com novusbio.com krishgen.com
```

**Useful when:**
- You already trust specific vendors
- You want maximum speed

### 🌍 Discover domains automatically (Advanced)

```bash
python elisa_matcher.py --discover-domains
```

- Uses web-wide search to discover vendors
- Slower and noisier, but useful for rare targets

---

## ⚙️ Performance Tuning

| Option | Meaning |
|--------|---------|
| `--site-results` | Pages searched per analyte per vendor |
| `--max-fetch` | Max total pages fetched |
| `--workers` | Parallel HTTP workers |
| `--budget-sec` | Hard time limit |
| `--timeout` | Per-page HTTP timeout |

**Aggressive but safe example:**

```powershell
python elisa_matcher.py `
  --site-results 25 `
  --max-fetch 120 `
  --workers 16 `
  --budget-sec 60
```

---

## 📤 Output Format

**Example:**

```
=== MATCHED ===

fn-test.com
  NOX4: https://www.fn-test.com/product/em1238/
  CXCL10: https://www.fn-test.com/product/em0004/

novusbio.com
  NOX4: https://...
  CXCL10: https://...
```

➡️ Each vendor listed has **ALL** requested analytes.

---

## ⚠️ Limitations
- Keyword-based HTML parsing (no JS rendering)
- Some vendors hide info in PDFs → may be missed
- **Always verify datasheets before purchasing**

---

## 🇰🇷 한국어 설명

### 🧪 ELISA Kit Matcher
여러 타겟(예: **NOX4 + CXCL10**)에 대해  
동일한 실험 조건에서 사용 가능한 **ELISA 키트 조합**을 자동으로 찾아주는 Python 도구입니다.

실험자가 직접 구글링하며 비교하는 과정을 **자동화**하는 것이 목적입니다.

### ✨ 주요 기능
- ✅ 기본적으로 **검증된 ELISA vendor 도메인 목록** 사용
- ✅ **모든 타겟을 동시에 만족**하는 vendor만 선택
- ✅ species / sample / ELISA 조건 필터링
- ✅ 병렬 크롤링으로 빠른 실행
- ✅ 점수화 없음, **링크만 출력**

### 🚀 기본 실행

```bash
python elisa_matcher.py
```

**기본값:**
- 타겟: `NOX4`, `CXCL10`
- Species: `mouse`
- Sample: `serum`, `plasma`
- 검증된 vendor 목록 자동 사용

### 🧪 조건 변경

```powershell
python elisa_matcher.py `
  --analytes NOX4 CXCL10 `
  --species mouse `
  --sample serum plasma
```

### 🧠 여러 선택지 얻기 (추천)

```powershell
python elisa_matcher.py `
  --site-results 20 `
  --max-fetch 100 `
  --budget-sec 45
```

👉 `--early-stop` 사용하지 마세요.

### ⚡ 가장 빠른 실행 (1개만 필요할 때)

```bash
python elisa_matcher.py --early-stop
```

### 🌐 도메인 설명
- `--domains` 없이 실행 → 내장 vendor 목록 사용 (추천)
- `--domains` 지정 → 특정 vendor만 검색
- `--discover-domains` → 웹 전체에서 vendor 탐색 (느림)

### 📤 출력 예시

```
=== MATCHED ===

fn-test.com
  NOX4: https://...
  CXCL10: https://...
```

➡️ 각 vendor는 **모든 타겟을 만족**합니다.

---

## 📝 License

This project is provided as-is for research purposes.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📧 Contact

For questions or support, please open an issue on the repository.