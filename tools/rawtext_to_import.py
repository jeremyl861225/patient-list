#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rawtext_to_import.py — 把原始臨床文字轉成 Patient List 可匯入的 JSON。

    python3 rawtext_to_import.py raw.txt --mrn 12345678 --name 王小明 -o out.import.json
    cat raw.txt | python3 rawtext_to_import.py - --mrn 12345678
    python3 rawtext_to_import.py --validate out.import.json

原始文字用區段標題分段（`#`、`##`、`【】`、`===` 都可以，標題認關鍵字不認格式）：

    # History
    DM type 2
    HTN

    # PI
    fever for 3 days, RLQ abdominal pain for 2 days, progressive
    nausea, vomiting 1 day
    NPO since 2026-08-02
    Signs: McBurney (+), rebounding tenderness RLQ moderate (+), Murphy (-)
    bowel sound hypoactive

    # Med
    Ceftriaxone 1 g IV Q12H
    Acetaminophen 500 mg PO QID
    Normal saline IF 80 mL/hr

    # Vitals
    2026-08-03 08:00  T 38.2  P 104  R 20  BP 118/72  SpO2 97% RA

    # Lab  2026-08-03 06:00
    WBC 15.2 H
    Hb 12.8
    Platelet 233
    CRP 14.2 H

    # Exam  CT 2026-08-03
    CT abdomen with contrast
    Dilated appendix 12 mm with periappendiceal fat stranding.

    # Assessment
    Acute appendicitis with localized peritonitis

    # Plan
    NPO, IV hydration
    Emergent laparoscopic appendectomy

沒有標題時會盡量自動判斷，但**建議加標題**，判斷才穩。
不確定的東西一律不猜：解析不到的行會原封不動收進 note，並在 stderr 列出來。
"""

import argparse
import json
import os
import re
import sys
import unicodedata

# ---------------------------------------------------------------- 常數
# 這三張表必須與 index.html 內的 SYMPTOMS / SIGNS / ROUTES 一致
SYMPTOM_KEYS = {
    "fever": ["fever", "發燒", "febrile"],
    "nausea": ["nausea", "噁心", "nauseated"],
    "vomiting": ["vomiting", "vomitus", "嘔吐", "vomited"],
    "abd_pain": ["abdominal pain", "abd pain", "abdominal painful", "腹痛", "stomachache"],
    "diarrhea": ["diarrhea", "diarrhoea", "腹瀉", "watery stool"],
    "weakness": ["weakness", "malaise", "倦怠", "無力", "fatigue", "general weakness"],
    "drowsy": ["drowsy", "drowsiness", "嗜睡", "somnolent"],
    "bloody_stool": ["bloody stool", "hematochezia", "血便"],
    "tarry_stool": ["tarry stool", "melena", "黑便"],
    "no_defecation": ["no defecation", "no passage of stool", "未解便", "constipation", "obstipation"],
    "distension": ["distension", "distention", "腹脹", "bloating"],
}
COURSES = ["persistent", "intermittent", "progressive", "resolving"]
REGIONS = ["RUQ", "LUQ", "RLQ", "LLQ", "epigastric", "periumbilical",
           "suprapubic", "Rt flank", "Lt flank", "whole abdomen"]
SEVERITY = ["mild", "moderate", "severe"]
SIGN_KEYS = {
    "murphy": ["murphy"],
    "mcburney": ["mcburney", "mc burney"],
    "rovsing": ["rovsing"],
    "obturator": ["obturator"],
    "psoas": ["psoas"],
    "carnett": ["carnett"],
    "cv_knock": ["cv knocking", "cva knocking", "costovertebral", "knocking pain", "cv angle"],
    "brudzinski": ["brudzinski"],
    "kernig": ["kernig"],
    "tender": ["abdominal tenderness", "abd tenderness", "tenderness"],
    "rebound": ["rebounding tenderness", "rebound tenderness", "rebounding", "rebound"],
    "guarding": ["muscle guarding", "guarding"],
    "rigidity": ["rigidity", "board-like"],
}
BOWEL = ["hypoactive", "normoactive", "hyperactive"]
ROUTES = ["PO", "IV", "IF"]
ROUTE_ALIAS = {
    "po": "PO", "p.o.": "PO", "oral": "PO", "口服": "PO",
    "iv": "IV", "i.v.": "IV", "ivd": "IV", "ivp": "IV", "ivf": "IF", "靜脈": "IV",
    "if": "IF", "infusion": "IF", "drip": "IF", "點滴": "IF", "輸液": "IF",
}
FREQ_RE = re.compile(
    r"\b(QD|BID|TID|QID|Q\d{1,2}H|QN|HS|QOD|PRN|STAT|ST|AC|PC|QAM|QPM)\b", re.I)
EXAM_TYPES = ["EKG", "CXR", "Echo", "CT", "EGD", "CFS", "MRI", "PET"]
EXAM_ALIAS = {
    "ecg": "EKG", "ekg": "EKG", "心電圖": "EKG",
    "cxr": "CXR", "chest x-ray": "CXR", "chest xray": "CXR", "胸部x光": "CXR",
    "echo": "Echo", "echocardiography": "Echo", "心臟超音波": "Echo",
    "ct": "CT", "電腦斷層": "CT",
    "egd": "EGD", "panendoscopy": "EGD", "胃鏡": "EGD",
    "cfs": "CFS", "colonoscopy": "CFS", "大腸鏡": "CFS",
    "mri": "MRI", "pet": "PET", "pet-ct": "PET",
}

SECTIONS = [
    ("history", ["history", "past history", "medical history", "pmh", "病史", "過去病史"]),
    ("pi", ["pi", "present illness", "hpi", "現病史", "主訴", "chief complaint", "cc"]),
    ("meds", ["med", "meds", "medication", "medications", "drug", "藥", "用藥", "藥囑", "醫囑"]),
    ("vitals", ["vital", "vitals", "vital sign", "vital signs", "生命徵象", "tpr"]),
    ("labs", ["lab", "labs", "lab data", "laboratory", "檢驗", "抽血", "生化"]),
    ("exams", ["exam", "image", "imaging", "image/exam", "study", "影像", "檢查", "報告"]),
    ("assessment", ["assessment", "impression", "a/p", "評估", "診斷", "diagnosis"]),
    ("plan", ["plan", "計畫", "處置", "treatment plan"]),
    ("note", ["note", "備註", "其他", "misc"]),
]

DATE_RE = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")
TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


# ---------------------------------------------------------------- 工具
def norm(s):
    """全形轉半形、壓掉多餘空白。"""
    s = unicodedata.normalize("NFKC", s)
    return s.replace("　", " ").rstrip()


def iso_date(s):
    m = DATE_RE.search(s)
    if not m:
        return ""
    y, mo, d = m.groups()
    return "%s-%02d-%02d" % (y, int(mo), int(d))


def stamp(s, fallback_date=""):
    """從一段文字抽出 'YYYY-MM-DD HH:MM'（沒時間就只給日期）。"""
    d = iso_date(s) or fallback_date
    t = TIME_RE.search(s)
    if d and t:
        return "%s %02d:%02d" % (d, int(t.group(1)), int(t.group(2)))
    return d


def warn(msg):
    print("  ! " + msg, file=sys.stderr)


# ---------------------------------------------------------------- 分段
HEAD_RE = re.compile(r"^\s*(?:#{1,4}\s*|={2,}\s*|-{2,}\s*|\[|【)?([A-Za-z /&_.-]{2,24}|[一-鿿]{2,8})\s*(?:\]|】|={2,}|:|：)?\s*(.*)$")


def split_sections(text):
    """回傳 [(key, header_rest, [lines])]，未標示的開頭段落 key 為 None。"""
    out = [(None, "", [])]
    for raw in text.splitlines():
        line = norm(raw)
        if not line.strip():
            out[-1][2].append("")
            continue
        key = header_key(line)
        if key:
            out.append((key[0], key[1], []))
        else:
            out[-1][2].append(line)
    return [(k, r, [x for x in ls]) for k, r, ls in out if any(x.strip() for x in ls) or k]


def header_key(line):
    """認得出區段標題就回傳 (key, 標題後面剩下的字)，否則 None。"""
    s = line.strip()
    marked = bool(re.match(r"^\s*(#{1,4}|={2,}|【|\[)", s))
    body = re.sub(r"^\s*(#{1,4}|={2,}|-{2,}|【|\[)\s*", "", s)
    body = re.sub(r"[\]】]", " ", body).strip()
    if not body:
        return None
    tokens = body.split()
    for n in (3, 2, 1):
        if len(tokens) < n:
            continue
        cand = " ".join(tokens[:n]).lower().rstrip(":：").strip()
        rest = " ".join(tokens[n:]).lstrip(":： ").strip()
        for key, words in SECTIONS:
            if cand not in words:
                continue
            # 沒有 # 之類的標記時，要嘛整行就是標題，要嘛標題後面緊接冒號
            if not marked:
                after = body[len(" ".join(tokens[:n])):].lstrip()
                if rest and not after.startswith((":", "：")):
                    return None
            return key, rest
    return None


# ---------------------------------------------------------------- 各段解析
def parse_history(lines):
    return [re.sub(r"^[-*·•\d.)\s]+", "", l).strip() for l in lines if l.strip()]


def parse_lines(lines):
    return [re.sub(r"^[-*·•]\s*|^\d+[.)]\s*", "", l).strip() for l in lines if l.strip()]


def find_days(s):
    m = re.search(r"(?:for\s+)?(\d+)\s*(?:days?|天|日)", s, re.I)
    return m.group(1) if m else ""


def find_region(s):
    low = s.lower()
    for r in REGIONS:
        if r.lower() in low:
            return r
    for pat, r in [(r"\bright lower\b", "RLQ"), (r"\bleft lower\b", "LLQ"),
                   (r"\bright upper\b", "RUQ"), (r"\bleft upper\b", "LUQ"),
                   (r"上腹", "epigastric"), (r"右下腹", "RLQ"), (r"左下腹", "LLQ"),
                   (r"右上腹", "RUQ"), (r"左上腹", "LUQ"), (r"全腹|瀰漫", "whole abdomen"),
                   (r"肚臍|臍周", "periumbilical"), (r"下腹", "suprapubic")]:
        if re.search(pat, low):
            return r
    return ""


def parse_pi(lines):
    pi = {"symptoms": {}, "npo_since": "", "signs": {}, "text": ""}
    leftovers = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        used = False

        # NPO
        m = re.search(r"npo\s*(?:since|from|自|從)?\s*[:：]?\s*(.+)", low)
        if m:
            d = iso_date(m.group(1))
            if d:
                pi["npo_since"] = d
                used = True

        # 理學檢查（整行含 sign 關鍵字才當 sign 處理）
        if re.search(r"\bsigns?\b|理學|pe\s*[:：]", low) or _has_sign(low):
            got = parse_signs(s, pi["signs"])
            used = used or got

        # 症狀：以逗號／分號切開，逐段比對
        for chunk in re.split(r"[,;，；]| and ", s):
            c = chunk.strip()
            if not c:
                continue
            cl = c.lower()
            for key, words in SYMPTOM_KEYS.items():
                if any(w in cl for w in words):
                    ent = pi["symptoms"].setdefault(key, {"on": True, "days": "", "loc": "", "course": ""})
                    ent["on"] = True
                    if re.search(r"\b(no|denied?|without|否認|無)\b", cl):
                        # 明確否認就不當症狀
                        pi["symptoms"].pop(key, None)
                        used = True
                        continue
                    d = find_days(c) or find_days(s)
                    if d:
                        ent["days"] = d
                    if key == "abd_pain":
                        r = find_region(c) or find_region(s)
                        if r:
                            ent["loc"] = r
                        for co in COURSES:
                            if co in cl or co in low:
                                ent["course"] = co
                    used = True

        if not used:
            leftovers.append(s)

    pi["text"] = "\n".join(leftovers).strip()
    return pi


def _has_sign(low):
    return any(any(w in low for w in ws) for ws in SIGN_KEYS.values()) or "bowel sound" in low


def parse_signs(line, signs):
    """一行裡可能有多個 sign，用逗號／分號切開分別判斷正負。"""
    got = False
    for chunk in re.split(r"[,;，；]", line):
        c = chunk.strip()
        if not c:
            continue
        cl = c.lower()
        if "bowel sound" in cl or "腸蠕動" in cl:
            for b in BOWEL:
                if b in cl:
                    signs["bowel_sound"] = {"v": b}
                    got = True
            continue
        for key, words in SIGN_KEYS.items():
            if not any(w in cl for w in words):
                continue
            neg = bool(re.search(r"\(-\)|\(−\)|\bnegative\b|\bno\b|陰性|未見", cl))
            pos = bool(re.search(r"\(\+\)|\bpositive\b|陽性", cl))
            v = "neg" if neg and not pos else "pos"
            ent = {"v": v}
            r = find_region(c)
            if r and key in ("tender", "rebound"):
                ent["loc"] = r
            for sev in SEVERITY:
                if sev in cl:
                    ent["sev"] = sev
            if key == "cv_knock":
                if re.search(r"\brt\b|right|右", cl):
                    ent["side"] = "Rt"
                elif re.search(r"\blt\b|left|左", cl):
                    ent["side"] = "Lt"
                elif "both" in cl or "雙" in cl:
                    ent["side"] = "both"
            signs[key] = ent
            got = True
            break
    return got


def parse_meds(lines):
    meds = []
    for line in lines:
        s = re.sub(r"^[-*·•\d.)\s]+", "", line).strip()
        if not s:
            continue
        route = ""
        for tok, r in sorted(ROUTE_ALIAS.items(), key=lambda kv: -len(kv[0])):
            if re.search(r"(?<![A-Za-z])" + re.escape(tok) + r"(?![A-Za-z])", s, re.I):
                route = r
                s = re.sub(r"(?<![A-Za-z])" + re.escape(tok) + r"(?![A-Za-z])", " ", s, count=1, flags=re.I)
                break
        freq = ""
        mf = FREQ_RE.search(s)
        if mf:
            freq = mf.group(1).upper()
            s = s[:mf.start()] + " " + s[mf.end():]
        rate = ""
        mr = re.search(r"(\d+(?:\.\d+)?)\s*(ml/hr|cc/hr|mL/hr|滴/分)", s, re.I)
        if mr:
            rate = mr.group(0)
            s = s[:mr.start()] + " " + s[mr.end():]
        hold = ""
        mh = re.search(r"hold[^\n]*", s, re.I)
        if mh:
            hold = iso_date(mh.group(0))
            s = s[:mh.start()] + " " + s[mh.end():]
        dose = ""
        md = re.search(r"(\d+(?:\.\d+)?)\s*(mg|g|mcg|µg|ug|IU|U|mL|ml|cc|tab|amp|vial|支|顆|包)\b", s)
        if md:
            dose = md.group(0).strip()
            s = s[:md.start()] + " " + s[md.end():]
        name = re.sub(r"[\s,;:]+", " ", s).strip(" -,;:")
        if not name:
            continue
        meds.append({"name": name, "route": route or "PO", "dose": dose,
                     "freq": freq, "rate": rate, "hold": hold, "note": ""})
    return meds


VITAL_PATS = [
    ("T", r"\bT\s*[:=]?\s*(\d{2}(?:\.\d)?)"),
    ("P", r"\b(?:P|PR|HR|pulse)\s*[:=]?\s*(\d{2,3})"),
    ("R", r"\b(?:R|RR|resp)\s*[:=]?\s*(\d{1,2})"),
    ("BP", r"\b(?:BP|blood pressure)?\s*[:=]?\s*(\d{2,3}\s*/\s*\d{2,3})"),
    ("SpO2", r"\b(?:SpO2|SaO2|O2\s*sat|SPO₂)\s*[:=]?\s*(\d{2,3}\s*%?)"),
]


def parse_vitals(lines, default_date=""):
    out = []
    for line in lines:
        s = norm(line).strip()
        if not s or not re.search(r"\d", s):
            continue
        t = stamp(s, default_date)
        v = {"t": t, "T": "", "P": "", "R": "", "BP": "", "SpO2": "", "O2": ""}
        body = s
        if t:
            body = DATE_RE.sub(" ", body)
            body = TIME_RE.sub(" ", body, count=1)
        for key, pat in VITAL_PATS:
            m = re.search(pat, body, re.I)
            if m:
                val = m.group(1).replace(" ", "")
                if key == "SpO2" and not val.endswith("%"):
                    val += "%"
                v[key] = val
        mo = re.search(r"\b(RA|room air|NC\s*\d+\s*L?|mask\s*\d*\s*L?|N/?C\s*\d+|HFNC[^\s,;]*|"
                       r"ventilator|BiPAP|CPAP|FiO2\s*\d+%?)", body, re.I)
        if mo:
            v["O2"] = mo.group(0).strip()
        if any(v[k] for k in ("T", "P", "R", "BP", "SpO2")):
            out.append(v)
    return out


LAB_LINE = re.compile(r"^(.+?)[\s:：]+(-?\d+(?:\.\d+)?)\s*(.*)$")
LAB_FLAG = re.compile(r"(?:^|\s)(H|L|\*)$")


def parse_labs(lines, header_rest, default_stamp):
    """
    兩種版面：
      (a) 一行一項          WBC 15.2 H
      (b) 表格（tab 或 2+ 空白分欄），第一列是時間
    回傳 {"items":[…], "cols":[…], "vals":{…}}
    """
    labs = {"items": [], "cols": [], "vals": {}}
    rows = [l for l in lines if l.strip()]
    if not rows:
        return labs

    def split_cells(s):
        return [c.strip() for c in re.split(r"\t|\s{2,}", s.strip()) if c.strip()]

    head_cells = split_cells(rows[0])
    is_table = len(head_cells) >= 2 and sum(1 for c in head_cells[1:] if DATE_RE.search(c) or TIME_RE.search(c)) >= 1

    if is_table:
        cols = [stamp(c) or c for c in head_cells[1:]]
        labs["cols"] = cols
        for line in rows[1:]:
            cells = split_cells(line)
            if len(cells) < 2:
                continue
            name, unit = split_unit(cells[0])
            labs["items"].append({"name": name, "unit": unit})
            for i, val in enumerate(cells[1:]):
                if i < len(cols) and val not in ("", "-", "—"):
                    labs["vals"]["%s|%s" % (name, cols[i])] = clean_val(val)
        return labs

    col = stamp(header_rest, "") or default_stamp
    if not col:
        col = "（未註明時間）"
    labs["cols"] = [col]
    for line in rows:
        m = LAB_LINE.match(line.strip())
        if not m:
            warn("Lab 這行看不懂，略過：%s" % line.strip())
            continue
        name, val, tail = m.group(1).strip(" .-:"), m.group(2), (m.group(3) or "").strip()
        flag = ""
        mf = LAB_FLAG.search(tail)
        if mf:
            flag = mf.group(1) if mf.group(1) != "*" else ""
            tail = tail[:mf.start()].strip()
        unit = tail
        if unit and not re.match(r"^[A-Za-zµ%/^\d.·\-]+$", unit):
            warn("Lab「%s」後面的 %r 看不懂，當單位收下" % (name, unit))
        name, u2 = split_unit(name)
        unit = unit or u2
        if not any(it["name"] == name for it in labs["items"]):
            labs["items"].append({"name": name, "unit": unit})
        labs["vals"]["%s|%s" % (name, col)] = (val + (" " + flag if flag else "")).strip()
    return labs


def split_unit(name):
    m = re.match(r"^(.*?)\s*[\(（]\s*([^)）]+)\s*[\)）]\s*$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return name.strip(), ""


def clean_val(v):
    v = v.strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(H|L|\*)?$", v)
    if m:
        flag = m.group(2) or ""
        return (m.group(1) + (" " + flag if flag and flag != "*" else "")).strip()
    return v


def parse_exams(lines, header_rest):
    """每個 exam 段：標題行（型別＋日期）＋其後的 findings。以空白行分隔多筆。"""
    blocks, cur = [], []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)

    head_type, head_date = detect_exam_type(header_rest), iso_date(header_rest)
    out = []
    for b in blocks:
        t = detect_exam_type(b[0]) or head_type or "其他"
        d = iso_date(b[0]) or head_date
        title = b[0].strip() if (detect_exam_type(b[0]) or iso_date(b[0])) else ""
        body = b[1:] if title else b
        if not title:
            title = (header_rest.strip() or t)
        out.append({"type": t, "date": d, "title": re.sub(r"^[-*·•\s]+", "", title),
                    "findings": "\n".join(x.strip() for x in body).strip()})
    return out


def detect_exam_type(s):
    low = " " + s.lower() + " "
    for k in sorted(EXAM_ALIAS, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", low):
            return EXAM_ALIAS[k]
    return ""


# ---------------------------------------------------------------- 主流程
def convert(text, meta):
    p = {
        "mrn": meta.get("mrn", ""), "name": meta.get("name", ""),
        "sex": meta.get("sex", ""), "age": meta.get("age", ""),
        "vs": meta.get("vs", ""), "bed": meta.get("bed", ""),
        "status": meta.get("status", "er"),
    }
    if meta.get("id"):
        p["id"] = meta["id"]
    if meta.get("date"):
        if p["status"] == "ward":
            p["adm_date"] = meta["date"]
        else:
            p["er_date"] = meta["date"]
    if meta.get("er_date"):
        p["er_date"] = meta["er_date"]
    if meta.get("adm_date"):
        p["adm_date"] = meta["adm_date"]

    notes = []
    default_stamp = meta.get("time", "")
    for key, rest, lines in split_sections(text):
        body = [l for l in lines]
        if key is None:
            leftover = [l for l in body if l.strip()]
            if leftover:
                notes.extend(leftover)
            continue
        if key == "history":
            p["history"] = parse_history(body)
        elif key == "pi":
            p["pi"] = parse_pi(body)
        elif key == "meds":
            p["meds"] = parse_meds(body)
        elif key == "vitals":
            p.setdefault("vitals", []).extend(parse_vitals(body, iso_date(rest) or meta.get("date", "")))
        elif key == "labs":
            new = parse_labs(body, rest, default_stamp)
            old = p.setdefault("labs", {"items": [], "cols": [], "vals": {}})
            for it in new["items"]:
                if not any(x["name"] == it["name"] for x in old["items"]):
                    old["items"].append(it)
            for c in new["cols"]:
                if c not in old["cols"]:
                    old["cols"].append(c)
            old["vals"].update(new["vals"])
        elif key == "exams":
            p.setdefault("exams", []).extend(parse_exams(body, rest))
        elif key == "assessment":
            p["assessment"] = parse_lines(body)
        elif key == "plan":
            p["plan"] = parse_lines(body)
        elif key == "note":
            notes.extend(l for l in body if l.strip())

    if notes:
        p["note"] = "\n".join(notes).strip()
        warn("有 %d 行沒有歸到任何欄位，已放進 note。" % len(notes))
    return {k: v for k, v in p.items() if v not in ("", [], {}, None)}


# ---------------------------------------------------------------- 驗證
def validate(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["最外層必須是物件"]
    if doc.get("format") != "patient-list.import":
        errs.append('缺少 "format": "patient-list.import"')
    pts = doc.get("patients")
    if not isinstance(pts, list) or not pts:
        return errs + ["patients 必須是非空陣列"]
    for i, p in enumerate(pts):
        tag = "patients[%d]" % i
        if not p.get("mrn") and not p.get("name") and not p.get("id"):
            errs.append("%s：至少要有 mrn、name 或 id" % tag)
        if p.get("status") not in (None, "er", "ward"):
            errs.append("%s：status 只能是 er 或 ward" % tag)
        for k in ("history", "assessment", "plan", "meds", "vitals", "exams"):
            if k in p and not isinstance(p[k], list):
                errs.append("%s：%s 必須是陣列" % (tag, k))
        for m in p.get("meds", []):
            if m.get("route") and m["route"] not in ROUTES:
                errs.append("%s：藥物「%s」的 route=%s 不在 %s" % (tag, m.get("name"), m["route"], ROUTES))
        for e in p.get("exams", []):
            if e.get("type") and e["type"] not in EXAM_TYPES + ["其他"]:
                errs.append("%s：檢查 type=%s 不在 %s" % (tag, e["type"], EXAM_TYPES))
        pi = p.get("pi") or {}
        for k in (pi.get("symptoms") or {}):
            if k not in SYMPTOM_KEYS:
                errs.append("%s：症狀代碼 %s 不存在（可用：%s）" % (tag, k, ", ".join(SYMPTOM_KEYS)))
        for k, v in (pi.get("signs") or {}).items():
            if k == "bowel_sound":
                if v.get("v") not in BOWEL:
                    errs.append("%s：bowel_sound 只能是 %s" % (tag, BOWEL))
                continue
            if k not in SIGN_KEYS:
                errs.append("%s：理學檢查代碼 %s 不存在（可用：%s）" % (tag, k, ", ".join(SIGN_KEYS)))
            elif v.get("v") not in ("pos", "neg"):
                errs.append("%s：%s 的 v 只能是 pos／neg" % (tag, k))
        labs = p.get("labs") or {}
        if labs:
            names = {it.get("name") for it in labs.get("items", [])}
            cols = set(labs.get("cols", []))
            for key in labs.get("vals", {}):
                if "|" not in key:
                    errs.append("%s：lab vals 的鍵 %r 必須是「項目|時間」" % (tag, key))
                    continue
                n, c = key.rsplit("|", 1)
                if n not in names:
                    errs.append("%s：lab vals 用到未宣告的項目 %s" % (tag, n))
                if c not in cols:
                    errs.append("%s：lab vals 用到未宣告的時間欄 %s" % (tag, c))
    return errs


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="raw data → Patient List 匯入用 JSON")
    ap.add_argument("input", nargs="?", help="原始文字檔（- 表示標準輸入）")
    ap.add_argument("-o", "--out", help="輸出檔；省略就印到標準輸出")
    ap.add_argument("--validate", metavar="FILE", help="只檢查既有的匯入檔")
    ap.add_argument("--mrn"), ap.add_argument("--name"), ap.add_argument("--sex", choices=["M", "F"])
    ap.add_argument("--age"), ap.add_argument("--vs"), ap.add_argument("--bed"), ap.add_argument("--id")
    ap.add_argument("--status", choices=["er", "ward"], default="er")
    ap.add_argument("--date", help="來診／住院日期 YYYY-MM-DD（依 --status 放入對應欄位）")
    ap.add_argument("--er-date"), ap.add_argument("--adm-date")
    ap.add_argument("--time", help="檢驗預設時間欄，例 '2026-08-03 06:00'")
    ap.add_argument("--merge", metavar="FILE", help="併入既有的匯入檔（同 mrn 覆蓋）")
    args = ap.parse_args()

    if args.validate:
        with open(args.validate, encoding="utf-8") as f:
            doc = json.load(f)
        errs = validate(doc)
        if errs:
            print("✗ %d 個問題：" % len(errs))
            for e in errs:
                print("  - " + e)
            sys.exit(1)
        n = len(doc["patients"])
        print("✓ 格式正確，%d 位病人" % n)
        return

    if not args.input:
        ap.error("要嘛給原始文字檔，要嘛用 --validate")
    text = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()

    meta = {"mrn": args.mrn, "name": args.name, "sex": args.sex, "age": args.age,
            "vs": args.vs, "bed": args.bed, "id": args.id, "status": args.status,
            "date": args.date, "er_date": args.er_date, "adm_date": args.adm_date,
            "time": args.time}
    meta = {k: v for k, v in meta.items() if v}
    patient = convert(text, meta)

    doc = {"format": "patient-list.import", "version": 1, "patients": [patient]}
    if args.merge:
        with open(args.merge, encoding="utf-8") as f:
            old = json.load(f)
        keep = [p for p in old.get("patients", [])
                if not (p.get("mrn") and p.get("mrn") == patient.get("mrn"))]
        doc["patients"] = keep + [patient]

    errs = validate(doc)
    for e in errs:
        warn("驗證：" + e)

    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("→ %s（%d 位病人%s）" % (args.out, len(doc["patients"]),
                                    "，%d 個驗證警告" % len(errs) if errs else ""))
        print("   這個檔案是明文病人資料，匯入完就刪掉，不要進版控。")
    else:
        print(out)


if __name__ == "__main__":
    main()
