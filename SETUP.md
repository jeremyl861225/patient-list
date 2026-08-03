# 建立後端（Supabase）

大約十分鐘，只需要做一次。免費方案就夠用。

## 1. 建立專案

1. 到 <https://supabase.com> 註冊／登入 → **New project**。
2. 名稱填 `patient-list`，選一個離台灣近的區域（Northeast Asia (Tokyo) 或 Southeast Asia (Singapore)）。
3. Database Password 自己設一組並記下來（這是資料庫的密碼，App 用不到，但重設專案時會要）。

> 建議**另開一個新專案**，不要跟待辦事項那個專案混用——權限、備份、以及萬一要整個刪掉時比較乾淨。

## 2. 建立資料表

左側 **SQL Editor** → **New query** → 把 `schema.sql` 全部貼上 → **Run**。

跑完會有兩張表：

- `vault`：每個使用者一列，存 PBKDF2 的鹽與驗證用密文（**沒有密碼本身**）。
- `patients`：每位病人一列，內容全部在 `payload` 欄位裡，是密文。

兩張表都開了 Row Level Security，只讀得到 `auth.uid()` 等於自己的列。

## 3. 拿到兩個值

左側 **Project Settings → API**（新版在 **Project Settings → API Keys**）：

- **Project URL**：`https://xxxxxxxx.supabase.co`
- **Publishable key**：`sb_publishable_...`（舊版叫 anon key，`eyJ...` 開頭）

這兩個值本來就設計成可以公開，真正的保護來自 RLS 與本機加密。

> 用新式 `sb_publishable_` 金鑰時，supabase-js **必須是 2.111.0 以上**，
> 這個 repo 的 `vendor/` 已經放好對應版本。

## 4. 填進 App

打開 `index.html`，把最上方的 `CONFIG` 填好：

```js
const CONFIG = {
  SUPABASE_URL: 'https://xxxxxxxx.supabase.co',
  SUPABASE_ANON_KEY: 'sb_publishable_...'
};
```

填了之後每台裝置都不用再各自設定。若留空，App 第一次開啟時會出現設定畫面讓你填（存在該裝置的 localStorage）。

## 5. 關掉確認信（選用）

**Authentication → Sign In / Providers → Email** → 把 **Confirm email** 關掉，
註冊後就能直接登入，不用等信。只有自己用的話建議關掉。

## 6. 部署

推到 GitHub 後，Repo → **Settings → Pages** → Source 選 **Deploy from a branch** → `main` / `/ (root)` → Save。
一兩分鐘後 <https://你的帳號.github.io/patient-list/> 就會活起來，手機用 Safari 開 → 分享 → 加入主畫面。

## 第一次使用

1. 開啟網址 → **註冊**（Email + 登入密碼）。
2. 接著會要你**設定資料密碼**——這組是拿來加密病人資料的，**與登入密碼不同**，
   而且**永遠不會離開你的裝置**。忘記就解不開既有資料，沒有救回的辦法。
3. 之後在別台裝置登入時，會再問一次資料密碼（可勾「在這台裝置記住」）。

## 常見狀況

| 狀況 | 處理 |
|---|---|
| 顯示「無法啟動：沒有 Web Crypto」 | 網址不是 https。用 GitHub Pages 網址或 localhost。 |
| 登入後說「資料密碼不對」 | 這台裝置輸入的資料密碼與當初設定的不同。沒有重設機制，只能想起來。 |
| 有幾筆資料「解不開」 | 那幾筆是用另一組資料密碼加密的（例如中途換過密碼但沒等重新加密跑完）。 |
| 換了資料密碼，其他裝置打不開 | 正常。其他裝置請按「⋮ → 鎖定」再用新密碼解鎖。 |
