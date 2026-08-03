---
name: patient-list-import
description: 把原始病歷文字、螢幕截圖或檢驗報告轉成 Patient List 可匯入的 JSON，並輸出成一行讓使用者直接複製貼進 App。當使用者說「製作病人匯入檔」「轉成匯入檔」「這個病人幫我建卡」「做成 import json」或丟一張病歷截圖過來時使用。
---

# 病人匯入檔製作（Patient List Import）

## 目的

把手上的原始資料（病歷段落截圖、Notepad 文字、檢驗報告、藥囑）轉成
`patient-list.import` 格式的 JSON，讓使用者在 App 裡「⋮ → 匯入資料」貼上就建好一張卡。

格式規格見 `tools/README.md`，轉檔工具是 `tools/rawtext_to_import.py`。

## 輸出規則（最重要）

**預設就是輸出「一行 compact JSON」直接貼在回覆裡讓使用者複製。**
使用者幾乎都是在手機上操作 App，用貼的比下載檔案快得多。

```bash
python3 -c "
import json
d = json.load(open('out.import.json', encoding='utf-8'))
print(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
"
```

- 放進 ```json 圍籬裡，**不要**縮排、不要換行、不要加註解。
- 中文用 `ensure_ascii=False` 保持原樣（App 貼上時會清 BOM 與零寬字元，但別自找麻煩）。
- `pi.text` 裡的換行維持 `\n` 跳脫，一行 JSON 照樣是合法的。
- 檔案另外附一份給使用者存檔（`SendUserFile`）是加分，但**一行 JSON 一定要有**。
- 貼出來之前一定跑過 `json.load()` 與 `--validate`，兩個都過才貼。

## 流程

1. **抄原文**。截圖就先轉正、裁切、放大讀清楚；逐字抄，不要順手改寫。
   Notepad 的自動換行要接回同一行（病史那種長句常被折成 3 行）。
2. **寫成 raw.txt**，用 `# History` / `# PI` / `# Vitals` / `# Lab 日期` /
   `# Exam CT 日期` / `# Assessment` / `# Plan` 分段（區段關鍵字認得中英文）。
3. **跑轉檔工具**：

   ```bash
   python3 tools/rawtext_to_import.py raw.txt \
     --mrn 5516769 --name 林淑貞 --sex F --age 68 --vs 陳柏達 --bed M123 \
     --status er --date 2026-08-03 -o out.import.json
   ```

4. **逐欄回頭對一次原文**（見下面的陷阱），用小段 python 直接改 JSON。
5. **驗證**：`python3 tools/rawtext_to_import.py --validate out.import.json`
6. **輸出一行 JSON**，並列出「我做了哪些判斷」讓使用者覆核。

### 病歷首行怎麼拆

`M123 林淑貞(F,1957/10/30,68y9m) 病:5516769 VS:陳柏達`

| 片段 | 參數 |
|---|---|
| `M123` | `--bed` |
| `林淑貞` | `--name` |
| `F` | `--sex` |
| `68y9m` | `--age 68`（純數字＝歲；未滿一歲才寫 `8m`） |
| `病:5516769` | `--mrn` |
| `VS:陳柏達` | `--vs` |

急診或住院看院內系統網址的 `PatClass`：`E` → `--status er`，`I` → `--status ward`。

## 解析陷阱（每次都要親自看過）

- **「A 有、B 沒有」寫在同一行會整行消失**。`nausea without vomiting` 裡的
  `without` 會被當成否認 nausea，而且那行連 `note` 都不會留 —— 一定要手動把
  `symptoms.nausea` 補回來，原文也留一份在 `pi.text`。
- **症狀關鍵字比對很死**。`abdominal distended sensation` 對不到 `distension`、
  `RUQ pain` 對不到 `abdominal pain`，都要手動補 `symptoms`（`abd_pain` 記得填 `loc`）。
- **理學檢查沒寫正負時預設為陽性**。原文沒有 `(+)` / `(-)` 就自己判斷，不要照收。
- **日期沒有年份會被丟掉**。生命徵象常寫 `08/03 20:20`，要補成 `2026-08-03 20:20`
  才抓得到；年份用病歷其他段落（檢驗日期）推。
- **同一時間點的生命徵象要併成一筆**。原始系統常拆成 T/P/R、BP、SpO₂ 三行。
- **`SpO2:98%(%,L,)` 這種尾巴是系統雜訊**，寫成 `SpO2:98%` 就好。
- **單位用 ASCII**：`K/uL` 而不是 `K/µL`（µ 會觸發「單位看不懂」警告）。
- **檢驗值後面的 `*` 會被丟掉**，只有 `H` / `L` 會保留並在 App 標紅／藍。
  遇到 `PH:7.342 *` 這種要判斷是不是該補 `H` / `L`。
- **藥名含數字＋單位時劑量會抓錯**（`Vitamin B12 1000 mcg`），轉完看一眼。

## 不要做的事

- **不捏造 Assessment / Plan / 診斷**。原文沒寫就留空，讓使用者自己填。
- **不把病史裡的既往用藥拉進 Medication**。`under PLAQUENIL and Methotrexate`
  是病史敘述，`meds` 是這次的藥囑，兩件事。
- **不擅自標「待開刀」**。看到 `PAT: LC+LF after 8/20` 這種語意不明的縮寫，
  照原樣留在 `pi.text`，問過使用者再加 `pending_op` / `op_note`。
- **原文沒有的日期不要自己填死**。真的要補（例如檢查段落只有 findings），
  用該次來診日期，並在回覆裡明講這是推的。

## 病人資料絕對不進版控

產出的 JSON 是**明文病人資料**，這個 repo 是公開的。

- 一律寫在 repo 外（scratchpad），`.gitignore` 已擋 `imports/`、`exports/`、`*.import.json`，
  但不要靠它。
- **不要 commit、不要 push 任何含真實病人資料的檔案**，也不要貼進 commit message、
  PR 標題或內文。
- 一行 JSON 貼在對話裡給使用者複製是可以的（那是給本人看的），檔案用 `SendUserFile` 送。

## 回覆長什麼樣

1. 一行 JSON（```json 圍籬）。
2. 一張表：帶進去了哪些欄位。
3. 一節「要你確認的判斷」：推測的日期、語意不明的縮寫、手動補的症狀、沒寫的欄位。
