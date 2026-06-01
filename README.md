# 2026 資安 LLM Prompt Dataset 分析專案

## 研究問題

現有資安相關 LLM prompt datasets 是否提供足夠的脈絡與可操作性資訊，以支援資安雙重用途提示的越獄風險評估？

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

### `sample_50.py` — 純隨機抽樣

所有資料集合併後去重，不分比例隨機抽取 50 筆。

```bash
python sample_50.py
```

- 輸出：`sample_50.csv`
- 總池：30,081 筆（不去重，保留各資料集完整性）
- 欄位：`id`, `source`, `prompt`
- 注意：大資料集（CySecBench、CyberLLMInstruct）會主導結果，小資料集可能抽不到

---

### `sample_50_stratified.py` — 分層抽樣

依照預設配額從各資料集分別抽樣，確保每個資料集都有代表性。

```bash
python sample_50_stratified.py
```

- 輸出：`sample_50_stratified.csv`
- 欄位：`id`, `source`, `prompt`, `contextual_framing`, `operational_actionability`（後兩欄為人工編碼欄位，預留空白）

**預設配額：**

| 資料集 | 配額 | 選擇理由 |
|--------|------|----------|
| CySecBench | 15 | 最大資料集，代表「未包裝惡意 prompt」 |
| CyberLLMInstruct | 10 | 知識性 instruction，與其他資料集形成對比 |
| CyberattackAssistance | 8 | MITRE ATT&CK 框架，有情境包裝 |
| MalwareBench | 8 | 惡意軟體導向，具體操作請求 |
| llm-attacks | 5 | 極直白有害請求，無任何包裝 |
| RMCBench | 4 | 惡意程式碼請求（Generate code for virus/worm 等） |

如需調整配額，修改腳本中的 `QUOTA` 字典，確保總和等於 50。

---

## 執行環境需求

```bash
pip install pandas openpyxl
```

Python 3.8 以上。

---

## CyberLLMInstruct 補充說明

此資料集為**重新生成版本**，非原始論文釋出的 54,928 筆。

- 原因：原始資料集因版權限制僅提供重現腳本（reproduction scripts）
- 生成工具：Ollama（gemma:2b + mistral:7b，本地 GPU 加速）
- 資料來源：NVD CVE、MITRE ATT&CK、CAPEC、arXiv、OpenCVE、Microsoft Security、Ubuntu USN、CTFtime
- 缺少來源：VirusTotal、AlienVault OTX、Shodan 等（API 呼叫失敗）
- 生成時間：2026-05-29 至 2026-05-31
- 內容性質：知識性問答（「Explain CVE-XXXX」、「How does X attack work?」），非直接攻擊指令

論文中引用此資料集時，應說明為自行重現版本，並與原始論文數字區分。

---

## 編碼架構（人工標註用）

`sample_50_stratified.csv` 預留三個編碼欄位：

### Contextual Framing（情境包裝）
| 代碼 | 定義 |
|------|------|
| 0 | 無情境，直接惡意問題 |
| 1A | 有情境且有進一步說明（角色、目的、背景） |
| 1B | 有情境，但僅一句話，未進一步說明 |

### Operational Actionability（可操作性）
| 代碼 | 定義 |
|------|------|
| 0 | 未要求具體步驟或執行方式 |
| 1A | 低可操作性（概念性說明） |
| 1B | 高可操作性（要求步驟、工具、程式碼或可執行攻擊） |

---

## 參考文獻（資料集）

- CySecBench: `cysecbench/dataset` (GitHub)
- CyberattackAssistance: `meta-llama/PurpleLlama` (GitHub)
- CyberLLMInstruct: ElZemity et al. (2026), AISec '25, DOI: 10.1145/3733799.3762968
- MalwareBench: `MAIL-Tele-AI/MalwareBench` (GitHub)
- RMCBench: `qing-yuan233/RMCBench` (GitHub)
- llm-attacks: `llm-attacks/llm-attacks` (GitHub)
