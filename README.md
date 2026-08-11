# Patient List

急診／住院病人清單的單檔 PWA。手機與電腦同一個帳號登入即可同步，
**病人資料在瀏覽器內加密後才上傳，雲端只存得到密文**。

線上版：<https://jeremyl861225.github.io/patient-list/>

---

## 功能

- **一次來診／住院＝一張卡**：同一位病人再來一次就是新的一張卡（`⋮ → 新增這位病人的下一次來診／住院`，基本資料與病史自動帶過去）；卡片內可看「同一病歷號共 N 次」並互相跳轉。
- **兩個分頁**：急診、住院；同一次來診可雙向挪移（「轉為住院」／「改回急診」），來診、住院、出院三個日期都保留。
- **待開刀註記**：一鍵標記（可附擬行術式／時間），卡片會排到最前面並亮出紅色標籤，工具列另有「待開刀」快速篩選。標記後會附上**同意書／麻醉科／on 急刀**三個小勾選框，在病人頁上點一下就切換並存檔；主畫面的卡片只用亮燈（實心）／熄燈（灰底）呈現，掃一眼就知道還缺哪一項。取消待開刀時勾選會一併清空。
- **出院日期**：登記後住院天數算到出院當天為止，並可順手結束追蹤。
- **結束追蹤**：不再追蹤的病人移到「已結束」分頁，**資料不刪除**，隨時可恢復。
- **搜尋**：病歷號或姓名即時搜尋（三個分頁都有）；來診／住院日期的區間查詢只出現在「已結束」分頁——在追蹤中的病人清單通常不長，用不到日期。
- **病人卡片**：床號、姓名、病歷號、年齡性別（`64M`／`37F`／`8mF` 縮寫）、VS 同一行，底下是 NPO／出院／已結束標記與 Assessment 摘要；來診日期與第幾天在卡片點開後才顯示。年齡純數字視為歲，未滿一歲直接填 `8m`、`20 days` 會原樣顯示。
- **九個欄位**：Medical history／Present illness／Medication／Vital signs／Lab data／Image・Exam／Assessment／Plan／Note。
- **Present illness 結構化輸入**：勾選症狀（發燒、噁心、嘔吐、腹痛〔可填位置與 persistent／intermittent／progressive／resolving〕、腹瀉、倦怠、嗜睡、血便、黑便、未解便、腹脹）並各自填天數，NPO since，以及十三項理學檢查（Murphy／McBurney／Rovsing／Obturator／Psoas／Carnett／CV knocking／Brudzinski／Kernig／腹部壓痛／反彈痛〔皆可填位置與 mild・moderate・severe〕／肌肉緊繃／腹壁僵硬）與 bowel sound。勾選後即時產生英文敘述。
- **Medication**：藥名、途徑（PO／IV／IF）、劑量、頻率、hold 日期，IF 另有流速欄。
- **Vital signs**：T／P／R／BP／SpO₂（含 O₂ demand）／GCS／自由備註，依時間點列表（時間只顯示月／日與時間，年份省略）。
- **Image / Exam**：類型可自行輸入（EKG／CXR／Echo／CT／EGD／CFS／MRI／PET 是建議值，US、MRCP、ERCP… 都能自己打），加日期、標題與 findings。
- **Lab data**：欄＝時間、列＝檢驗項目的表格，過寬時整塊橫向捲動、第一欄固定；可貼上檢驗報告文字自動帶入。表頭的時間只顯示月／日與時間（年份省略），項目名稱的寬度上限抓「plasmacell %」剛好放得下（116px），超過會截斷成 `…`；完整名稱與完整時間都放在 title 裡。
- **檢驗值自動判讀**：兩層。**參考值**決定 `H`／`L`（淡色）、**危險值**決定 `HH`／`LL`（實心底色，
  代表要馬上處理）。只有填了危險值的項目才可能出現 `HH`／`LL`，其餘最多到 `H`／`L`，不會亂猜。
  報告單本來就寫的旗標顏色較深且永遠優先；自動判讀的滑鼠移上去會顯示區間與危險值。
  **單位對不上就整格不判讀**（CRP 用 mg/L、WBC 用 /µL 時數值差一個數量級），值不是純數字也不判讀。
  同一項目兩種單位各自帶一組數字（Ca 用 mg/dL 是 8.6–10.3、用 mmol/L 是 2.15–2.55），不做換算。
- **參考值可以自己改**：「⋮ → 檢驗參考值」列出全部 62 組，每一組的上下限與危險值都能就地編輯，
  改過的標「自訂」並可單獨或全部還原。改動存在本機（`pl.labref`），不上傳。
  標「台大」的是台大檢驗醫學部公布的區間，標「通用」的還沒逐項核對，請照院內報告單校正。
  「⋮ → 檢驗自動判讀」可以整個關掉。
- **匯入／匯出**：JSON 匯入（以 `id`／病歷號比對後合併），可複製整份文字病摘。
- **手機版面**：頁寬等於版面寬、禁止手指縮放；可加到主畫面離線開啟。
- **夜覽模式**：跟著系統配色自動切換（`prefers-color-scheme`），沒有另外的開關。
- **離線可用**：本機留一份密文快取，沒網路照樣開得起來、看得到、改得動；改動排隊等連線後自動補傳。
- **下拉更新**：主畫面往下拉可手動重抓病人資料並檢查程式版本（有新版就自動重新載入）。

## 離線怎麼運作

| 情境 | 行為 |
|---|---|
| 開啟 App | 先用本機密文快取渲染，再去雲端拉最新的蓋上去 |
| 沒網路開啟 | 完全從快取還原（含解鎖用的 vault，所以離線也解得開） |
| 沒網路修改 | 立刻寫進本機快取並排入佇列，右上角顯示「離線 · N 筆待上傳」 |
| 恢復連線 | 自動補傳；也可以下拉更新手動觸發 |
| 下拉更新 | 補傳佇列 → 重抓病人資料 → 比對 `index.html` 裡的 `APPVER` 檢查新版本 |
| 登出 | 清掉這台裝置的金鑰、離線快取與佇列（雲端資料不動）；有未上傳的異動會先警告 |

本機快取存的是**密文**（`localStorage` 的 `pl.cache.<uid>`），沒有資料密碼一樣打不開。
衝突處理是單純的後寫覆蓋——這是自己一個人用的工具，同一位病人不會有兩台裝置同時改。

一台裝置**第一次**使用仍然需要連線（要跟雲端拿 vault，或建立新的）。

## 安全性

| | |
|---|---|
| 登入 | Supabase Email + 密碼 |
| 加密 | AES-GCM 256，金鑰由「資料密碼」經 PBKDF2-SHA256（250,000 次）導出 |
| 伺服器看得到 | 只有密文、`user_id`、更新時間 |
| 搜尋與排序 | 全部在瀏覽器內做（伺服器沒有明文可查） |
| RLS | 每個使用者只讀得到自己的列 |

**忘記資料密碼就解不開既有資料，沒有任何救回的辦法**——這是端對端加密的必然代價。
資料密碼與登入密碼是兩組不同的東西；登入密碼可以用 Email 重設，資料密碼不行。

匯出的 JSON 是**明文**，含可識別資料，請只存在自己控制的裝置。
**任何含真實病人資料的檔案都不要放進這個 repo**（`.gitignore` 已擋掉 `imports/`、`exports/`、`*.import.json`）。

## 安裝

1. 依 [SETUP.md](SETUP.md) 建立 Supabase 專案並跑 `schema.sql`。
2. 把 Project URL 與 publishable key 填進 `index.html` 最上方的 `CONFIG`（或第一次開啟時在畫面上填）。
3. 部署到 GitHub Pages（Settings → Pages → Deploy from a branch → `main` / root）。

## 本機試用

不需要 Supabase，網址加上 `?demo=1`：

```bash
python3 -m http.server 8765
```

然後開 <http://localhost:8765/?demo=1>。資料只存在這台裝置的瀏覽器 localStorage，
但加密流程與正式版完全相同。

> 注意：Web Crypto 需要 https 或 localhost，用 `file://` 直接開會無法啟動。

## 轉檔工具

`tools/rawtext_to_import.py` 把原始資料（檢驗報告、藥囑、生命徵象、病歷段落）
轉成可匯入的 JSON。搭配 `patient-list-import` skill 使用時，Claude 會直接幫你完成整段轉換。

```bash
python3 tools/rawtext_to_import.py raw.txt -o out.import.json --mrn 12345678 --name 王小明
```

## 檔案

```
index.html                  App 本體（單檔）
sw.js                       service worker（只快取自己 scope 的外殼）
schema.sql                  Supabase 資料表與 RLS
SETUP.md                    建立 Supabase 專案的步驟
tools/rawtext_to_import.py  raw data → 匯入用 JSON
tools/README.md             匯入格式規格
.claude/skills/             patient-list-import skill（Claude 轉檔時的作業規則）
vendor/                     supabase-js（放本機，離線與院內網路都開得起來）
```
