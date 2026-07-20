# AI 規則正本架構：通用實作指南

適用於任何專案，讓 Claude Code、Codex（或未來任何 coding agent）共用同一份規則。
概念出自「Claude Code 搬家到 Codex」影片，本指南加上了 Windows / exFAT 實測後的修正做法。

## 核心概念

- **規則內容只維護一份**（正本），名字中立，不姓 Claude 也不姓 OpenAI。
- 每個 AI 工具只保留一個**入口檔**（它認得的檔名），入口不放內容，只負責把 AI 引導到正本。
- 以後換工具或加新工具，只要「加一道門」，正本永遠不動。

```
project/
├── .ai/
│   └── INSTRUCTIONS.md    ← 唯一正本，規則全部寫這裡
├── CLAUDE.md              ← Claude Code 入口（引用正本）
└── AGENTS.md              ← Codex 入口（指示先讀正本）
```

## 入口的三種實作方式（依環境選一種）

| 方式 | 條件 | 優缺點 |
|------|------|--------|
| A. 引用式入口（**推薦**） | 無條件，任何環境都可用 | 真檔案，git 跨平台零問題；Claude Code 有原生 `@import`，Codex 靠文字指示 |
| B. Symlink（影片原做法） | NTFS/ext4 等，Windows 需開發人員模式或系統管理員 | 兩邊讀到的內容 100% 同步；但 **exFAT 不支援**，git 在 Windows 上對 symlink 支援也不穩 |
| C. Hardlink | 同槽、NTFS | 不建議：編輯器用「寫暫存檔再改名」存檔時會默默斷鏈 |

> **Windows 注意**：先確認槽的檔案系統（`Get-Volume -DriveLetter X`）。exFAT（常見於外接碟、非系統槽）不支援任何連結，只能用方式 A。方式 A 在所有環境都能用，沒有特殊理由就直接用 A。

## 實作步驟（方式 A）

### 1. 建立正本 `.ai/INSTRUCTIONS.md`

把既有的 CLAUDE.md（或 AGENTS.md）內容搬進來。如果是新專案，至少寫這幾節：

```markdown
# <專案名> 專案規則（唯一正本）

> 本檔是這個專案 AI 規則的唯一正本。
> CLAUDE.md 與 AGENTS.md 都只是入口，內容一律改這裡，不要改入口檔。

## 專案簡介
（一段話：這專案做什麼、主要技術棧）

## 環境
（怎麼啟動、怎麼跑測試、必要的環境變數／工作目錄限制）

## 資料與重要檔案（未經同意不要刪除或重建）
（資料庫、快取、成本高的產物）

## 已知地雷
（踩過的 bug、反直覺的行為）

## 工作習慣
（commit 政策、臨時檔放哪、機密不入版控）
```

### 2. 建立 `CLAUDE.md`（Claude Code 入口）

```markdown
# 入口檔（請勿在此加內容）

專案規則正本在 `.ai/INSTRUCTIONS.md`，以下用 import 引入：

@.ai/INSTRUCTIONS.md
```

`@路徑` 是 Claude Code 的原生 import 語法，讀取時會自動展開正本全文，效果等同 symlink。

### 3. 建立 `AGENTS.md`（Codex 入口）

Codex 沒有 import 語法，用明確指示：

```markdown
# 入口檔（請勿在此加內容）

本專案的規則正本在 `.ai/INSTRUCTIONS.md`。

**開始任何工作前，先完整讀取 `.ai/INSTRUCTIONS.md` 並遵守其中所有規則。**
規則需要修改時一律改正本，不要改本檔。
```

### 4. 收尾

- 三個檔案都 commit 進版控（都是真檔案，任何機器 checkout 都能用）。
- 如果原本已有 CLAUDE.md：內容搬進正本後，把原檔**改成入口檔**，不要留兩份內容。
- 驗證：分別在 Claude Code 和 Codex 問「這個專案的規則是什麼？」，兩邊都應答出正本內容。

## 規則分層原則（重要）

**全域規則和專案規則不能混。**

- **專案正本**（`project/.ai/INSTRUCTIONS.md`）：只放這個專案的事——怎麼啟動、資料在哪、哪些檔案不能碰。
- **全域規則**（跨專案的個人偏好、通用工作原則）：放在使用者層級——Claude Code 是 `~/.claude/CLAUDE.md`，Codex 是 `~/.codex/AGENTS.md`。若要全域層也做單一正本，同一套邏輯建 `~/.ai/INSTRUCTIONS.md` + 入口（全域層通常在 C: / NTFS，可用 symlink，但需開發人員模式）。

判斷標準：這條規則換一個專案還成立嗎？成立 → 全域；不成立 → 專案正本。

## Skills 共用（有需要才做）

- 能跨工具共用的 skills → 集中放 `~/.ai/skills/`（或專案 `.ai/skills/`）當正本。
- 依賴平台專屬功能的 skills（例如只有某工具才有的內建能力）→ 留在各自平台目錄，不要硬塞共用區。
- exFAT 上無法用 symlink 連 skills 目錄時，可在各平台的 skill 檔開頭放一行指示引用共用區的正本檔。

## 一鍵搬遷提示詞（貼給 AI 執行）

把下面整段貼給 Claude Code 或 Codex，它會自動幫你完成搬遷：

```
請幫我在這個專案實作「AI 規則單一正本」架構：

1. 先盤點：列出專案根目錄現有的 CLAUDE.md、AGENTS.md、.ai/，以及 .claude/、.codex/
   內的設定；若有既有規則檔，先備份為 <原檔名>.bak。
2. 檢查目前磁碟的檔案系統。無論結果為何，一律採用「引用式入口」（不要用 symlink）：
3. 建立 .ai/INSTRUCTIONS.md 作為唯一正本：合併現有 CLAUDE.md / AGENTS.md 的內容，
   去除重複；若兩檔內容衝突，列出衝突處問我。若專案沒有任何規則檔，依專案實況
   起草（簡介／環境與啟動方式／不可亂動的資料／已知地雷／工作習慣）。
4. 把 CLAUDE.md 改寫成入口檔：只含一行說明 + `@.ai/INSTRUCTIONS.md`。
5. 把 AGENTS.md 改寫成入口檔：只含說明 + 「開始任何工作前，先完整讀取
   .ai/INSTRUCTIONS.md 並遵守其中所有規則」。
6. 驗證：讀取兩個入口檔，確認都能正確導向正本；最後列出你動過的所有檔案。
不要 commit，讓我先檢查。
```

## 常見坑

1. **入口檔又被塞內容**：日後 AI 或人手癢直接改 CLAUDE.md，正本就分裂了。入口檔開頭的「請勿在此加內容」就是防這個；code review 時看到入口檔 diff 要警覺。
2. **exFAT 上建 symlink**：`mklink` 會報 "Incorrect function"，不是權限問題，是檔案系統不支援，換方式 A。
3. **全域規則塞進專案正本**：換專案就失效，還會跟真正的全域規則打架。
4. **無法用正本管理的東西**：hooks、settings.json、MCP 設定、permissions 是各工具私有格式，不能共用，仍要在各工具內各自維護。正本裡可以放一節「設定對照表」記錄兩邊該有哪些等效設定，至少讓人工同步有依據。
