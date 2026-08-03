# 轉檔工具

把原始臨床文字轉成 Patient List 可以匯入的 JSON。
產出的檔案是**明文病人資料**——放 repo 外、匯入完就刪。

## 用法

```bash
python3 rawtext_to_import.py raw.txt \
  --mrn 12345678 --name 王小明 --sex M --age 58 --vs 李醫師 \
  --status ward --date 2026-08-01 -o out.import.json
```

| 參數 | 說明 |
|---|---|
| `--mrn` `--name` `--sex` `--age` `--vs` `--bed` | 卡片上的基本資料 |
| `--status er\|ward` | 預設 `er` |
| `--date` | 依 `--status` 放進 `er_date` 或 `adm_date` |
| `--er-date` `--adm-date` `--dc-date` | 來診／住院／出院日期，需要各自指定時用 |
| `--pending-op` `--op-note` | 標記待開刀，附擬行術式／時間 |
| `--time` | 檢驗區段沒寫時間時的預設時間欄 |
| `--id` | 指定既有病人的 id（最精準的更新方式） |
| `--merge FILE` | 併進既有的匯入檔（同 `mrn` 覆蓋） |
| `--validate FILE` | 只檢查格式，不轉檔 |

`-o` 省略就印到標準輸出，可以接管線。輸入用 `-` 讀標準輸入。

## 原始文字的寫法

區段標題認關鍵字不認格式，`# History`、`【檢驗】`、`用藥：`、`Plan:` 都可以：

```
# History
DM type 2
HTN

# PI
fever for 3 days, RLQ abdominal pain for 2 days, progressive
nausea, vomiting 1 day
no diarrhea
NPO since 2026-08-02
Signs: McBurney (+), rebounding tenderness RLQ moderate (+), Murphy (-)
bowel sound hypoactive

# Med
Ceftriaxone 1 g IV Q12H
Levofloxacin 500 mg PO QD hold 2026-08-02
Normal saline IF 80 mL/hr

# Vitals
2026-08-03 08:00  T 38.2  P 104  R 20  BP 118/72  SpO2 97% RA  GCS E4M6V5

# Lab  2026-08-03 06:00
WBC 15.2 H
Hb 12.8
CRP (mg/L) 14.2 H

# Exam  CT 2026-08-03
CT abdomen with contrast
Dilated appendix 12 mm with periappendiceal fat stranding.

# Assessment
Acute appendicitis with localized peritonitis

# Plan
NPO, IV hydration
Emergent laparoscopic appendectomy
```

可用的區段關鍵字：`history` / `pi`（含 `hpi`、`現病史`、`主訴`）/ `med` / `vital` /
`lab`（`檢驗`、`抽血`）/ `exam`（`影像`、`檢查`）/ `assessment`（`impression`、`診斷`）/
`plan` / `note`。

### 檢驗的兩種版面

**一行一項**（時間寫在區段標題後面）：

```
# Lab 2026-08-03 06:00
WBC 15.2 H
Cr (mg/dL) 1.4
```

**表格**（tab 或連續兩個以上空白分欄，第一列是時間）：

```
【檢驗】
項目	2026-08-01 06:00	2026-08-02 06:00
WBC (K/uL)	18.3 H	14.1
Cr (mg/dL)	1.8 H	1.4
```

數值後面的 `H`／`L` 會保留，App 顯示時標成紅／藍。

## 解析規則與限制

- **藥囑**：先抓途徑（`PO`/`IV`/`IVD`/`IF`/點滴…）、再抓頻率（`QD`…`Q8H`、`PRN`…）、
  再抓流速與 `hold` 日期、再抓劑量，**剩下的字就當藥名**。所以藥名裡有數字＋單位
  （例如 `Vitamin B12 1000 mcg`）時劑量可能被抓錯，轉完要看一眼。
- **症狀**：以逗號／分號／`and` 切開逐段比對關鍵字，天數認 `for 3 days`／`3 天`。
  同一行出現 `no`／`denied`／`否認` 會把該症狀**移除**（視為明確否認），不會標成陽性。
- **理學檢查**：`(+)`／`positive`／`陽性` 為陽性；`(-)`／`negative`／`no`／`陰性` 為陰性；
  兩者都沒有時**預設為陽性**（因為病歷通常只寫有意義的陽性所見）——這點最容易誤判，
  轉完務必檢查。
- **檢查類型**不再限制在清單內，`US`／`MRCP`／`ERCP` 這類都可以直接寫。
- **GCS**：`E4M6V5` 這種連寫，或 `GCS 14` 都認得；會先抽出來再解析其他數值，
  免得 `E4M6V5` 裡的數字被 T／P／R 的樣式撿走。
- **病史有兩層**：`#.` 開頭是主項，`-` 開頭是上一項的子項（App 會縮排並改用破折號）。
  `#.` 會被吃掉，`-` 會保留成 `- xxx` 當作層級標記。
- **看不懂的行**不會被丟掉，會原封不動收進 `note`，並在 stderr 印出提醒。

## 驗證

```bash
python3 rawtext_to_import.py --validate out.import.json
```

會檢查：`format` 標頭、每位病人至少有 `mrn`／`name`／`id` 其一、`status` 合法、
陣列欄位型別、`route` 只有 PO/IV/IF、exam `type` 在清單內、症狀與理學檢查代碼存在、
`labs.vals` 的鍵都對得到 `items` 與 `cols`。

轉檔時也會自動跑一次，問題會印在 stderr。

## 匯入

在 App 裡「⋮ → 匯入資料」，可以選檔案，也可以把整份內容貼進文字框（貼上時會自動清掉 BOM、零寬字元、被文書軟體換掉的彎引號與程式碼圍籬）。

**一張卡＝一次來診／住院**，所以比對是三段式：

1. 有 `id` → 用 `id`。
2. 有 `mrn` 又有 `er_date`／`adm_date` → 找**同病歷號且日期對得上**的那一次；
   對不上就當成另一次來診，**開新卡**。
3. 有 `mrn` 但沒給日期 → 落在最近一次（還在追蹤的優先）。所以逐日追加檢驗時
   可以不給日期，會自動接到目前那次。
合併的細節見 `patient-list-import` skill 或 App 內的說明。
