# -*- coding: utf-8 -*-
"""合併所有 .md 檔成單一 HTML 文件。用法: python build_docs.py"""
import markdown
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

MD_ORDER = [
    ('README.md',        '總覽 / 評分 SOP'),
    ('setup.md',         '環境安裝'),
    ('data_sources.md',  '資料來源與歷史回補'),
    ('run_schedule.md',  '執行排程手冊'),
    ('gg_stock_logic.md','程式邏輯'),
    ('todo.md',          '待辦清單'),
]

HTML_TEMPLATE = '''\
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>gg_stock 文件</title>
<style>
  :root {{
    --bg: #1e1e2e; --surface: #27273a; --border: #3b3b52;
    --text: #cdd6f4; --muted: #a6adc8; --accent: #89b4fa;
    --green: #a6e3a1; --red: #f38ba8; --yellow: #f9e2af;
    --code-bg: #181825;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: "Segoe UI", "PingFang TC", sans-serif; font-size: 15px; line-height: 1.7; }}

  /* ── nav ── */
  nav {{ position: fixed; top: 0; left: 0; width: 220px; height: 100vh; background: var(--surface); border-right: 1px solid var(--border); overflow-y: auto; padding: 16px 0; z-index: 100; }}
  nav h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); padding: 0 16px 8px; }}
  nav a {{ display: block; padding: 6px 16px; color: var(--muted); text-decoration: none; font-size: 13px; border-left: 3px solid transparent; }}
  nav a:hover, nav a.active {{ color: var(--accent); border-left-color: var(--accent); background: rgba(137,180,250,.08); }}

  /* ── main ── */
  main {{ margin-left: 220px; padding: 40px 48px; max-width: 960px; }}

  .doc-section {{ margin-bottom: 60px; padding-bottom: 40px; border-bottom: 1px solid var(--border); }}
  .doc-section:last-child {{ border-bottom: none; }}
  .section-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: var(--muted); margin-bottom: 8px; }}

  h1 {{ font-size: 1.8em; color: var(--accent); margin: 0 0 20px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
  h2 {{ font-size: 1.3em; color: var(--accent); margin: 32px 0 12px; }}
  h3 {{ font-size: 1.1em; color: var(--green); margin: 24px 0 8px; }}
  h4 {{ font-size: 1em; color: var(--yellow); margin: 16px 0 6px; }}
  p {{ margin: 0 0 12px; }}
  a {{ color: var(--accent); }}

  /* tables */
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0 20px; font-size: 13.5px; }}
  th {{ background: var(--border); color: var(--text); text-align: left; padding: 7px 12px; }}
  td {{ border-top: 1px solid var(--border); padding: 6px 12px; color: var(--muted); }}
  tr:hover td {{ background: rgba(255,255,255,.03); }}

  /* code */
  code {{ background: var(--code-bg); color: var(--green); padding: 1px 5px; border-radius: 4px; font-size: 0.88em; font-family: "Cascadia Code", "Fira Code", monospace; }}
  pre {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 14px 16px; overflow-x: auto; margin: 12px 0 20px; }}
  pre code {{ background: none; color: #cdd6f4; padding: 0; font-size: 0.87em; }}

  blockquote {{ border-left: 3px solid var(--accent); padding: 4px 16px; margin: 12px 0; color: var(--muted); }}
  ul, ol {{ padding-left: 24px; margin: 8px 0 12px; }}
  li {{ margin-bottom: 4px; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}

  /* checklist */
  li input[type=checkbox] {{ margin-right: 6px; }}
  li.task-list-item {{ list-style: none; margin-left: -20px; }}

  /* scrollbar */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

  @media (max-width: 768px) {{
    nav {{ display: none; }}
    main {{ margin-left: 0; padding: 20px; }}
  }}
</style>
</head>
<body>

<nav>
  <h2>gg_stock 文件</h2>
  {nav_links}
</nav>

<main>
{sections}
</main>

<script>
// 側欄 active highlight
const sections = document.querySelectorAll('.doc-section');
const navLinks  = document.querySelectorAll('nav a');
window.addEventListener('scroll', () => {{
  let cur = '';
  sections.forEach(s => {{ if (window.scrollY >= s.offsetTop - 80) cur = s.id; }});
  navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + cur));
}});
</script>
</body>
</html>
'''

MD_EXT = ['tables', 'fenced_code', 'codehilite', 'toc', 'attr_list', 'nl2br', 'sane_lists']

def slug(filename):
    return filename.replace('.', '-')

def build():
    nav_parts = []
    section_parts = []

    for fname, label in MD_ORDER:
        if not os.path.exists(fname):
            print('skip (not found):', fname)
            continue
        with open(fname, encoding='utf-8') as f:
            text = f.read()

        sid = slug(fname)
        html_body = markdown.markdown(text, extensions=MD_EXT)

        nav_parts.append(f'<a href="#{sid}">{label}</a>')
        section_parts.append(
            f'<section class="doc-section" id="{sid}">'
            f'<div class="section-label">{fname}</div>'
            f'{html_body}'
            f'</section>'
        )

    out = HTML_TEMPLATE.format(
        nav_links='\n  '.join(nav_parts),
        sections='\n'.join(section_parts),
    )
    dst = 'docs.html'
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(out)
    print('wrote', dst, '(%d bytes)' % len(out))

if __name__ == '__main__':
    build()
