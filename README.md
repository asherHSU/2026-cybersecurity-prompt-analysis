# 2026 資安 LLM Prompt Dataset 分析專案

## 研究問題

現有資安相關 LLM prompt datasets 是否提供足夠的脈絡與可操作性資訊，以支援資安雙重用途提示的越獄風險評估？

---

## 專案結構

```
2026詩雅poster/
├── README.md
├── .gitignore
├── data/                         ← 所有資料檔案
│   ├── 人工編碼簿.csv              （300 筆人工編碼完成）
│   ├── coded_remaining.csv        （29,263 筆 AI 自動編碼）
│   ├── 編碼標準.jpg                （CFA / OA 編碼標準圖）
│   ├── sample_50_final.csv        （最終版抽樣 50 筆）
│   ├── sample_250_final.csv       （補抽 250 筆，合計 300 筆）
│   ├── sample_50_proportional.csv （純比例版抽樣 50 筆）
│   ├── sample_50_stratified.csv   （非比例分層版 50 筆）
│   └── sample_50.csv              （純隨機版 50 筆）
├── scripts/                      ← 主要腳本
│   ├── sample_50_final.py         （最終版抽樣：保底 5 + 比例分配）
│   ├── sample_250_final.py        （補抽 250 筆，排除已抽 50 筆）
│   ├── sample_50_proportional.py  （純比例版抽樣）
│   ├── sample_50_stratified.py    （非比例分層版）
│   ├── sample_50.py               （純隨機版）
│   ├── code_remaining.py          （Ollama AI 編碼主腳本）
│   ├── watch_progress.py          （即時進度監控）
│   └── utils/                    ← 工具 / 修復腳本
│       ├── check_quality.py       （資料品質驗證）
│       ├── fix_all_issues.py      （修復編碼異常）
│       ├── apply_manual_codes.py  （套用人工補碼）
│       ├── rerun_err.py           （重跑 ERR 筆數）
│       └── ...
└── datasets/                     ← 原始資料集（六個）
```

---

## 資料集位置

| 資料集 | 路徑 | 筆數 | Prompt 欄位 |
|--------|------|------|-------------|
| CySecBench | `datasets/CySecBench/Dataset/Full dataset/cysecbench.csv` | 12,662 | `Prompt` |
| CyberattackAssistance | `datasets/CyberattackAssistance/mitre_benchmark.json` | 1,000 | `base_prompt` |
| CyberLLMInstruct | `datasets/CyberLLMInstruct/dataset_creation/final_dataset/final_cybersecurity_dataset_20260531_042849.json` | 11,906 | `instruction` |
| MalwareBench | `datasets/MalwareBench/dataset/attack_prompts.xlsx` | 3,520 | `Original Question` |
| RMCBench | `datasets/RMCBench/data/csv/prompt.csv` | 473 | `prompt` |
| llm-attacks | `datasets/llm-attacks/data/advbench/harmful_behaviors.csv` | 520 | `goal` |

**總計：30,081 筆**

> 備註：RMCBench 資料夾內有兩個檔案：`jailbreak-prompt.csv`（78 筆，越獄包裝模板）與 `prompt.csv`（473 筆，實際惡意 prompt）。腳本使用的是 `prompt.csv`。

---

## 抽樣腳本

### 推薦使用：`scripts/sample_50_final.py`

每個資料集保底 5 筆，剩餘 20 筆按比例分配（最大餘數法）。

```bash
python scripts/sample_50_final.py
```

輸出：`data/sample_50_final.csv`（50 筆，含編碼欄位）

**配額：**

| 資料集 | 保底 | 比例追加 | 合計 |
|--------|------|---------|------|
| CySecBench | 5 | +9 | 14 |
| CyberLLMInstruct | 5 | +8 | 13 |
| MalwareBench | 5 | +2 | 7 |
| CyberattackAssistance | 5 | +1 | 6 |
| llm-attacks | 5 | +0 | 5 |
| RMCBench | 5 | +0 | 5 |

### 補抽：`scripts/sample_250_final.py`

保底 30 筆 + 比例分配，排除已抽的 50 筆，輸出 250 筆。

```bash
python scripts/sample_250_final.py
```

輸出：`data/sample_250_final.csv`（250 筆，與 sample_50_final.csv 合計 300 筆不重複）

---

## AI 自動編碼

### `scripts/code_remaining.py`

以 300 筆人工編碼（`data/人工編碼簿.csv`）為 few-shot 範例，用 Ollama mistral:7b 對剩餘 ~29,781 筆自動編碼。

```bash
python scripts/code_remaining.py
```

- 輸出：`data/coded_remaining.csv`
- 支援中斷續跑
- 每 50 筆自動存檔

---

## 執行環境需求

```bash
pip install pandas openpyxl requests
```

Python 3.8 以上，需安裝 [Ollama](https://ollama.com) 並下載 mistral:7b。

---

## 編碼架構

### Contextual Framing Availability (CFA)
prompt 是否提供情境定位（模型行為設定、使用目的、角色、任務背景等）？

| 代碼 | 定義 |
|------|------|
| 0 | 未提供任何情境 |
| 1A | 有提供情境，但首句之外沒有進一步描述 |
| 1B | 有提供情境，且首句之後尚有進一步描述 |
| 999 | 非資安相關 prompt（詐欺、金融犯罪等） |

### Operational Actionability (OA)
prompt 是否要求具體操作細節（步驟、工具、程式碼或可執行攻擊）？

| 代碼 | 定義 |
|------|------|
| 0 | 未要求具體操作細節 |
| 1A | 要求知識層面的純文字內容（步驟指示、教學、策略） |
| 1B | 要求具武器化程度的內容（可執行程式碼、腳本、惡意軟體） |
| 999 | 非資安相關（與 CFA=999 同步） |

---

## CyberLLMInstruct 補充說明

此資料集為**重新生成版本**，非原始論文釋出的 54,928 筆。

- 原因：原始資料集因版權限制僅提供重現腳本（reproduction scripts）
- 生成工具：Ollama（gemma:2b + mistral:7b，本地 GPU 加速）
- 資料來源：NVD CVE、MITRE ATT&CK、CAPEC、arXiv、OpenCVE、Microsoft Security、Ubuntu USN、CTFtime
- 缺少來源：VirusTotal、AlienVault OTX、Shodan 等（API 呼叫失敗）
- 生成時間：2026-05-29 至 2026-05-31

---

## 參考文獻（資料集）

- CySecBench: `cysecbench/dataset` (GitHub)
- CyberattackAssistance: `meta-llama/PurpleLlama` (GitHub)
- CyberLLMInstruct: ElZemity et al. (2026), AISec '25, DOI: 10.1145/3733799.3762968
- MalwareBench: `MAIL-Tele-AI/MalwareBench` (GitHub)
- RMCBench: `qing-yuan233/RMCBench` (GitHub)
- llm-attacks: `llm-attacks/llm-attacks` (GitHub)
