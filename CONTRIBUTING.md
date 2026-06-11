# Contributing to ISP Algorithm Handbook

Thank you for your interest in contributing. This handbook covers ISP algorithms, computational photography, and AI-driven image processing. Contributions from practitioners and researchers are welcome.

## Types of Contributions

- **Factual corrections** — wrong numbers, incorrect citations, outdated claims
- **Chapter improvements** — clearer explanations, better examples, missing engineering context
- **Code fixes** — notebook bugs, import errors, deprecated API usage
- **New content** — missing algorithms, recent papers (CVPR/ICCV/ECCV 2023–2025)
- **Translation** — improving `_ch.md` ↔ `_en.md` parity

## How to Submit

1. **For minor fixes** (typos, wrong numbers): open a GitHub Issue using the **[📐 Technical Error template](https://github.com/AIISP/isp_handbook/issues/new?template=01_technical_error.yml)** and include the chapter reference (e.g., `Part 2 Ch05`).
2. **For content changes**: fork → edit → pull request. The repository provides a **[PR template](.github/pull_request_template.md)** — fill it in when opening your PR. Keep PRs focused on one chapter or one topic.
3. **For new chapters**: open an Issue using the **[💡 New Content template](https://github.com/AIISP/isp_handbook/issues/new?template=04_new_content.yml)** first to discuss scope and avoid duplication.
4. **To claim a chapter**: use the **[🙋 Chapter Claim template](https://github.com/AIISP/isp_handbook/issues/new?template=02_chapter_claim.yml)** to announce which chapter you are working on.
5. **For AI-generated content issues**: use the **[🤖 AI Hallucination template](https://github.com/AIISP/isp_handbook/issues/new?template=03_ai_hallucination.yml)**.

### 添加新章节（New Chapter）

1. 在对应 Part 目录下创建新目录，命名格式：`chXX_topic_name/`
2. 同时创建两个文件：`chXX_topic_name_ch.md`（中文）和 `chXX_topic_name_en.md`（英文）
3. 在 `mkdocs.yml` 的 `nav:` 中对应卷的位置添加导航条目
4. 在 `README_ch.md` 和 `README_en.md` 的章节目录表中添加对应行
5. 中文版须包含：§1 原理 → §2 算法 → §3 工程实践 → §4 典型伪影 → §5 代码示例 → §8 术语表 → §9 参考文献
6. 英文版须包含与中文版相同的章节结构，且行数覆盖率 ≥ 65%
7. **图片引用：** EN 版必须包含与 CH 版相同的图片引用（`![](img/...)` 路径一致）

### 提交 EN 翻译（EN Translation）

1. Fork 本仓库，在你的分支中编辑对应的 `_en.md` 文件
2. 覆盖率自检命令：
   ```bash
   wc -l path/to/ch_ch.md path/to/ch_en.md
   # EN/CH 行数比 ≥ 65% 才可提交
   ```
3. 图片引用同步：检查 CH 文件中所有 `![...]` 和 `<img ...>` 标签，确保 EN 文件中均有对应引用
4. 交叉引用格式：统一使用 `Vol. N Ch. M` 格式（如 `Vol. 2 Ch. 05`）
5. 提交 PR 时在描述中注明：覆盖率、新增章节数、图片引用数

## Factual Standards

- Technical claims must be traceable to a paper, datasheet, or platform documentation.
- For SoC performance numbers (TOPS, latency): cite the official Product Brief or a peer-reviewed benchmark. Do not cite third-party estimations without clearly labeling them as estimates.
- Math formulas: use LaTeX notation consistent with the chapter's existing style.
- Cite papers as: `Author et al., "Title", VENUE YEAR.` with DOI or arXiv link where available.

## Code Notebooks

- Notebooks must execute cleanly with `jupyter nbconvert --to notebook --execute`.
- Install dependencies via `pip install -r requirements.txt` (project root) or `conda env create -f environment.yml`. Do not add new dependencies without updating both files.
- No hardcoded absolute paths. Use `os.path.dirname(os.path.abspath('__file__'))` patterns or synthetic data that requires no external files.
- Output cells should be committed with the notebook so readers can preview results without running locally.
- Before committing a notebook, clear any `stderr` outputs that contain local machine paths (`AppData`, `miniforge3`, `/home/username/...`). These leak your environment and look unprofessional in the repo.

## File Naming

Each chapter directory contains:
- `chXX_topic_ch.md` — Chinese version
- `chXX_topic_en.md` — English version
- `chXX_topic_notebook.ipynb` (or `chXX_topic_code.ipynb`) — runnable code (optional; 41 chapters have one)
- `img/` — figures (PNG, max 500 KB per file)

**Bilingual parity target:** `_en.md` line count ≥ 65% of `_ch.md` line count. PRs that expand thin English chapters are especially welcome (see issues labelled `en-expansion`).

**Chapter numbering:** Each Part starts from `ch01` independently. Cross-reference format: `Vol. N Ch. M`. Do not use global chapter numbers.

Do not rename existing files — cross-references in other chapters depend on stable filenames.

## Language and Style

- Chinese (`_ch.md`): technical terms introduced as `术语 (Term)` on first use.
- English (`_en.md`): consistent with IEEE/ACM technical writing style.
- Both versions must cover the same topics; it is acceptable for them to differ in examples or emphasis.

## Review Process

All PRs are reviewed for:
1. Factual accuracy (numbers, citations)
2. Factual consistency with existing chapters (cross-check related chapters before submitting)
3. Code executability (for notebook changes)
4. Language quality

Expect review feedback within 2 weeks. Large PRs may take longer.

## Questions

Open a GitHub Issue with the label `question`. For discussion of broader topics (handbook structure, new volumes), use GitHub Discussions.
