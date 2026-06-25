#!/usr/bin/env python3
"""
PDF Resume to Interactive HTML Converter - v4.0
将 PDF 简历转换为带选项卡切换的 IT 科技风格交互式 HTML 文件。

v4.0 重写：
    - 按「数字：标题」编号分节标记拆分全文
    - 教育背景：表格行解析
    - 技术技能：子节（Technical Skills / IT运维管理 / 软技能）+ 要点
    - 证书资质：独立列表，不再混入技能内容
    - 工作经历：按日期块分割，职责用项目符号
    - 项目经验：按「项目名 + 项目时间」分割
"""

import os
import re
import sys

# ── 配置 ──
PDF_PATH = r"D:\AI\PDFResume2HTML\PDF2HTML.pdf"
OUTPUT_HTML_PATH = r"D:\AI\PDFResume2HTML\resume.html"


# ══════════════════════════════════════════════════════════════════════════════
# PDF 提取 — 逐页纯文本
# ══════════════════════════════════════════════════════════════════════════════

def extract_full_text(pdf_path: str) -> str:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            # 移除页眉
            text = re.sub(r'个人简历\s*\nRESUME\s*\n?', '', text)
            pages.append(text.strip())
    return "\n".join(pages)


# ══════════════════════════════════════════════════════════════════════════════
# 按编号分节分割
# ══════════════════════════════════════════════════════════════════════════════

# PDF 提取时编号被剥离，直接用关键词标题拆分
SECTION_KEYWORDS = [
    ("教育背景", "教育背景"),
    ("个人信息", "个人信息"),
    ("技术技能", "技术技能"),
    ("证书和资质", "证书和资质"),
    ("工作经历", "工作经历"),
    ("项目经验", "项目经验"),
]

def split_sections(full_text: str) -> dict:
    """按关键词节标题分割全文，返回 {标题: 内容} 字典"""
    # 找每个关键词的起始位置
    entries = []
    for keyword, label in SECTION_KEYWORDS:
        # 找独立成行的标题（前后有换行或处于文本开头/结尾）
        pattern = re.compile(r'(?:^|\n)\s*' + re.escape(keyword) + r'\s*(?:\n|$)', re.MULTILINE)
        for m in pattern.finditer(full_text):
            entries.append((m.start(), label))
            break  # 每个关键词只取第一次

    if len(entries) <= 1:
        return {"__all__": full_text}

    # 按位置排序
    entries.sort(key=lambda x: x[0])

    sections = {}
    for i, (pos, label) in enumerate(entries):
        # 标题行的结束：m.end() 是标题+换行结束的位置
        m_end = pos + len(label)
        # 向前找到标题行的实际结尾（下一个换行）
        nl = full_text.find('\n', m_end)
        start = (nl + 1) if nl >= 0 else m_end
        # 跳过空行
        while start < len(full_text) and full_text[start] == '\n':
            start += 1
        end = entries[i + 1][0] if i + 1 < len(entries) else len(full_text)
        sections[label] = full_text[start:end].strip()

    return sections


# ══════════════════════════════════════════════════════════════════════════════
# 解析教育背景
# ══════════════════════════════════════════════════════════════════════════════

def parse_education(text: str) -> list:
    """解析表格型教育信息"""
    lines = text.strip().split("\n")
    result = []

    # 跳过表头行（含"起止时间"、"毕业院校"的行）
    data_lines = [l for l in lines if l.strip() and not re.search(r'起止|毕业院校|专业|学历', l)]

    for line in data_lines:
        line = line.strip()
        # 匹配：2002.09–2006.06 湖南理工大学 计算机科学与技术 本科
        m = re.match(r'(\d{4}\.\d{2})[–\-—]+(\d{4}\.\d{2})\s+(.+?)\s+(计算机.+?)(?:\s+(本科|硕士|博士|大专))?$', line)
        if m:
            result.append({
                "period": f"{m.group(1)} — {m.group(2)}",
                "school": m.group(3).strip(),
                "major": m.group(4).strip(),
                "degree": m.group(5) or "本科",
            })
        else:
            # 宽松匹配
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 3:
                result.append({
                    "period": parts[0].strip(),
                    "school": parts[1].strip(),
                    "major": parts[2].strip() if len(parts) > 2 else "",
                    "degree": parts[3].strip() if len(parts) > 3 else "本科",
                })

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 解析个人信息
# ══════════════════════════════════════════════════════════════════════════════

def parse_personal(text: str) -> dict:
    personal = {
        "name": "", "target": "", "phone": "", "email": "",
        "birth": "", "major": "", "gender": "", "ethnicity": "", "exp_years": ""
    }
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 姓名: 姓 名：XXX  或  姓名：XXX
        if m := re.search(r'姓\s*名[：:]\s*(\S{2,4})', line):
            personal["name"] = m.group(1).replace(" ", "")
        elif m := re.search(r'求职意向[：:]\s*(.+)', line):
            personal["target"] = m.group(1).strip()
        elif m := re.search(r'联系电话[：:]\s*([\d\-]{7,15})', line):
            personal["phone"] = m.group(1).strip()
        elif m := re.search(r'([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', line):
            personal["email"] = m.group(1).strip().rstrip(".")
        elif m := re.search(r'出\s*生[：:]\s*(\d{4}\.\d{1,2})', line):
            personal["birth"] = m.group(1)
        elif m := re.search(r'专\s*业[：:]\s*(.+)', line):
            personal["major"] = m.group(1).strip()
        elif m := re.search(r'性\s*别[：:]\s*(.+)', line):
            personal["gender"] = m.group(1).strip()
        elif m := re.search(r'民\s*族[：:]\s*(.+)', line):
            personal["ethnicity"] = m.group(1).strip()
        elif m := re.search(r'工作经验[：:]\s*(.+)', line):
            personal["exp_years"] = m.group(1).strip()

    # 默认值
    if not personal["name"]: personal["name"] = "邓伟"
    if not personal["target"]: personal["target"] = "运维开发/项目管理"
    if not personal["phone"]: personal["phone"] = "15012641201"
    if not personal["email"]: personal["email"] = "daviddeng465@126.com"
    if not personal["exp_years"]: personal["exp_years"] = "18年"

    return personal


# ══════════════════════════════════════════════════════════════════════════════
# 解析技术技能
# ══════════════════════════════════════════════════════════════════════════════

KNOWN_SKILL_SECTIONS = [
    ("Technical Skills", "1.TechnicalSkills"),
    ("IT 运维管理 (ITSM/ITOM)", "2.IT 运维管理"),
    ("软技能", "3.软技能"),
]

def parse_skills(text: str) -> list:
    """解析三级技能：返回 [(节名, [要点列表]), ...]"""
    result = []

    for display_name, start_marker in KNOWN_SKILL_SECTIONS:
        idx = text.find(start_marker)
        if idx < 0:
            continue

        # 找到本节结束位置（下一个已知节的开始）
        end_idx = len(text)
        for _, next_marker in KNOWN_SKILL_SECTIONS:
            ni = text.find(next_marker, idx + len(start_marker))
            if ni > idx and ni < end_idx:
                end_idx = ni

        section_text = text[idx + len(start_marker):end_idx]
        bullets = _extract_bullets(section_text)

        # 清理残留的节标题文字
        clean = []
        for b in bullets:
            b = b.strip()
            # 跳过短碎渣或纯标题残留
            if len(b) < 8:
                continue
            # 跳过明显是子标题的内容
            if re.match(r'^\(?SME\)?$|^IT\s*运维管理|^ITSM$|^ITOM$|^软技能$', b):
                continue
            clean.append(b)

        if clean:
            result.append((display_name, clean))

    # 如果没解析到，尝试用二级标题分割
    if not result:
        parts = re.split(r'\n(?=\d+\.[A-Za-z\u4e00-\u9fff])', text)
        for part in parts:
            part = part.strip()
            if not part or len(part) < 10:
                continue
            # 提取节名
            m = re.match(r'(\d+\.[A-Za-z\u4e00-\u9fff\s]+)', part)
            name = m.group(1).strip() if m else "技能"
            bullets = _extract_bullets(part[m.end():] if m else part)
            bullets = [b for b in bullets if len(b) >= 5]
            if bullets:
                result.append((name, bullets))

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 解析证书资质
# ══════════════════════════════════════════════════════════════════════════════

def parse_certifications(text: str) -> list:
    """从证书和资质节提取证书列表"""
    certs = []
    # 更精确的技能关键词——证书行不应该被过滤
    skills_line = re.compile(
        r'(精通|熟悉|了解|负责|参与|主导|基于|使用|'
        r'自动化操作|脚本开发|运维与开发|'
        r'跨部门|团队协作|流程体系化|运维手册|技术规范|'
        r'推动技术|编排和容器|平台基础设施|监控系统|日志分析|性能监控|'
        r'数据存储与查询|备份与恢复|数据的高可用性|SQL查询性能)'
    )
    # 证书关键词
    cert_line = re.compile(r'(证书|管理员|六级|Azure|DB2|Service\s*NOW|IBM)', re.IGNORECASE)

    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 4:
            continue
        # 跳过分区标题行
        if line in ("证书和资质", "技术技能", "教育背景", "个人信息", "工作经历", "项目经验"):
            continue
        # 跳过以编号开头的技能子标题
        if re.match(r'^\d+\.\s*(Technical|IT|软)', line):
            continue
        # 跳过 `\uf0d8` 开头 (技能要点)
        if re.match(r'[\uf0d8\uf0fc\uf0b7\uf076\uf0a7\uf020\u2022]', line):
            continue
        # 先检查是否是证书，是就保留
        if cert_line.search(line) and len(line) < 50:
            certs.append(line)
            continue
        # 否则通过技能关键词排除
        if skills_line.search(line):
            continue
        # 含"证书"的行也保留
        if '证书' in line and len(line) < 50:
            certs.append(line)

    # 去重
    seen = set()
    out = []
    for c in certs:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 解析工作经历
# ══════════════════════════════════════════════════════════════════════════════

def parse_work_experience(text: str) -> list:
    """按日期/单位/岗位块分割工作经历"""
    result = []

    # 分割模式：匹配日期起头的各类格式
    # 格式1: 在职时间：2026.01–2026.04\n所在单位：XXX
    # 格式2: 2021.09–2024.07\n所在单位：XXX
    # 格式3: 2007.05–2008.05 所在单位：XXX (同行)
    blocks = re.split(r'\n(?=在职时间[：:]|\d{4}\.\d{2}[–\-—])', text)

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue

        period = ""
        company = ""
        position = ""
        duties = []

        # 日期
        if m := re.search(r'在职时间[：:]\s*(\d{4}\.\d{2}[–\-—]+\d{4}\.\d{2})', block):
            period = m.group(1).replace('–', ' — ').replace('-', ' — ')
        elif m := re.search(r'^(\d{4}\.\d{2}[–\-—]+\d{4}[\.\d]*)', block):
            period = m.group(1).replace('–', ' — ').replace('-', ' — ')

        # 单位（支持同行和换行两种格式）
        if m := re.search(r'所在单位[：:]\s*(.+?)(?:\n|$)', block):
            company = m.group(1).strip()
        elif m := re.search(r'(?:^|\n)\s*(所在单位[：:])\s*\n', block):
            next_line = block[m.end():].lstrip()
            company = next_line.split('\n')[0].strip()
            if len(company) < 2:
                company = ""

        # 岗位
        if m := re.search(r'岗位[：:]\s*(.+?)(?:\n|$)', block):
            position = m.group(1).strip()

        # 职责文本（"职责：" 到下一个日期块或结束）
        duties_match = re.search(r'职责[：:]\s*\n?(.*)', block, re.DOTALL)
        if duties_match:
            duties_text = duties_match.group(1)
            duties = _extract_work_duties(duties_text)

        if company and period:
            result.append({
                "period": period,
                "company": company,
                "position": position,
                "duties": duties,
            })

    return result


def _extract_work_duties(text: str) -> list:
    """从工作职责文本中提取要点列表，优先按  子弹符号分割"""
    if not text:
        return []

    # 方法1：按  编号分割（这是PDF中最常见的bullet格式）
    bullets = re.split(r'(?:^|\n)\s*(?:[\uf0d8\uf0fc\uf0b7\uf076\uf0a7\u2022]|\d+[\.\)]\s*)', text)
    items = []
    current = ""
    for chunk in bullets:
        chunk = chunk.strip()
        if not chunk:
            continue
        if current:
            items.append(current)
        current = chunk
    if current:
        items.append(current)

    # 过滤清理
    out = []
    for item in items:
        item = _clean_text(item)
        if item and len(item) > 6:
            out.append(item)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 解析项目经验
# ══════════════════════════════════════════════════════════════════════════════

def parse_projects(text: str) -> list:
    """按行扫描解析项目块"""
    result = []
    lines = text.strip().split("\n")

    # 阶段1：识别项目的起始行（项目名：XXX 或 XXX\n项目时间：...）
    project_starts = []
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls.startswith("项目名：") or ls.startswith("项目名:"):
            project_starts.append(i)
        elif (i + 1 < len(lines)
              and "项目时间" in lines[i + 1]
              and ls
              and not ls.startswith("项目")
              and not ls.startswith("职责")
              and not ls.startswith("\uf0d8")
              and len(ls) > 5):
            project_starts.append(i)

    # 阶段2：按起始行切割块
    project_starts = sorted(set(project_starts))
    blocks_lines = []
    for idx, si in enumerate(project_starts):
        ei = project_starts[idx + 1] if idx + 1 < len(project_starts) else len(lines)
        blocks_lines.append(lines[si:ei])

    # 阶段3：逐块解析
    for block_lines in blocks_lines:
        name = ""
        period = ""
        description_lines = []
        duties_lines = []
        achievements_lines = []

        # 提取项目名
        first = block_lines[0].strip()
        if first.startswith("项目名：") or first.startswith("项目名:"):
            name = first.split("：", 1)[-1].split(":", 1)[-1].strip()
        else:
            name = first

        # 逐行扫描提取各字段
        current_section = "header"  # header, desc, duties, achievements
        for line in block_lines[1:]:
            ls = line.strip()

            # 检测字段切换
            if "项目时间" in ls:
                parts = ls.split("：", 1) if "：" in ls else ls.split(":", 1)
                period = parts[-1].strip() if len(parts) > 1 else ""
                current_section = "desc"
                continue
            elif "项目描述" in ls and (ls.endswith("：") or ls.endswith(":") or ls == "项目描述"):
                current_section = "desc"
                continue
            elif "项目职责" in ls:
                current_section = "duties"
                continue
            elif "项目业绩" in ls:
                current_section = "achievements"
                continue
            elif ls == "职责：" or ls == "职责:":
                current_section = "duties"
                continue
            elif "职责" in ls and ("IBM Mainframe" in ls or "IT specialist" in ls):
                # 特殊处理：IBM Mainframes 的职责行同时包含职位名称
                name_extra = re.sub(r'职责[：:]\s*', '', ls).strip()
                if name_extra:
                    name = f"{name} · {name_extra}"
                continue

            # 按当前字段累积
            if current_section == "desc":
                description_lines.append(ls)
            elif current_section == "duties":
                duties_lines.append(ls)
            elif current_section == "achievements":
                achievements_lines.append(ls)

        # 清理描述：合并行，去掉 bullet 符号
        desc_text = " ".join(description_lines).strip()
        desc_text = re.sub(r'[\uf0d8\uf0fc\uf0b7\uf076\uf0a7\u2022]', '', desc_text)
        desc_text = re.sub(r'\s+', ' ', desc_text)

        # 从行列表中提取 duties 和 achievements
        duties = _extract_bullets_from_lines(duties_lines)
        achievements = _extract_bullets_from_lines(achievements_lines)

        if name and period:
            result.append({
                "name": name,
                "period": period,
                "description": desc_text,
                "duties": duties,
                "achievements": achievements,
            })

    return result


def _extract_bullets_from_lines(lines: list) -> list:
    """从行列表中提取要点，用 \uf0d8 等符号分割"""
    text = "\n".join(lines)
    return _extract_bullets(text)


# ══════════════════════════════════════════════════════════════════════════════
# 通用工具
# ══════════════════════════════════════════════════════════════════════════════

def _extract_bullets(text: str) -> list:
    """从文本中提取要点列表"""
    if not text:
        return []
    lines = text.strip().split("\n")
    result = []
    current = ""
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                result.append(_clean_text(current))
                current = ""
            continue
        # 检测要点起始
        is_bullet = bool(re.match(
            r'^[➤➢►▶•\-\*\uf0d8\uf0fc\uf0b7\uf076\uf0a7\uf020\u2022]|^\s*\d+[\.、\)》]\s*|^[一二三四五六七八九十]+[、]',
            line
        ))
        if is_bullet:
            if current:
                result.append(_clean_text(current))
            current = re.sub(r'^[➤➢►▶•\-\*\uf0d8\uf0fc\uf0b7\uf076\uf0a7\uf020\s\u2022]+|^\s*\d+[\.、\)》]\s*|^[一二三四五六七八九十]+[、]\s*', '', line).strip()
        else:
            current = (current + line) if current else line
    if current:
        result.append(_clean_text(current))

    seen = set()
    out = []
    for b in result:
        b = _clean_text(b)
        if b and len(b) > 3 and b not in seen:
            out.append(b)
            seen.add(b)
    return out


def _clean_text(s: str) -> str:
    s = re.sub(r'\uf0d8|\uf0fc|\uf0b7|\uf076|\uf0a7|\uf020', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[;；]\s*$', '', s)
    return s.strip()


# ══════════════════════════════════════════════════════════════════════════════
# HTML 构建
# ══════════════════════════════════════════════════════════════════════════════

def build_html(personal: dict, data: dict) -> str:
    name = personal.get("name", "")
    target = personal.get("target", "")
    phone = personal.get("phone", "")
    email = personal.get("email", "")
    exp = personal.get("exp_years", "")

    # ── 职业概述 ──
    career = f"""<div class="card">
  <div class="card-header"><h3>👤 职业概述</h3></div>
  <div class="card-body">
    <div class="summary-grid">
      <div class="summary-item"><span class="si-icon">⏱️</span><span class="si-label">工作经验</span><span class="si-val">{exp}</span></div>
      <div class="summary-item"><span class="si-icon">🎯</span><span class="si-label">求职意向</span><span class="si-val">{target}</span></div>
      <div class="summary-item"><span class="si-icon">🎓</span><span class="si-label">最高学历</span><span class="si-val">本科</span></div>
      <div class="summary-item"><span class="si-icon">🌐</span><span class="si-label">英语能力</span><span class="si-val">CET-6</span></div>
    </div>
    <div class="summary-desc">
      <p>资深 IT 运维与 DevOps 工程师，拥有 <strong>{exp}</strong> 行业经验，深耕 ITSM/ITOM 解决方案（IBM Maximo、ServiceNow），精通跨平台系统管理与自动化运维。</p>
      <p>具备丰富的 M365、Azure、AWS 云平台实战经验，擅长 Kubernetes 容器编排与 CI/CD 工具链集成，曾主导多个跨国企业级项目交付。</p>
    </div>
  </div></div>"""

    # ── 教育背景 ──
    edu_parts = []
    for e in data.get("education", []):
        edu_parts.append(f"""    <div class="timeline-card">
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <div class="tl-header"><h3>🎓 {e.get('school', '')}</h3><span class="tl-badge">{e.get('period', '')}</span></div>
        <table class="info-table"><tr><th>专 业</th><td>{e.get('major', '')}</td></tr><tr><th>学 历</th><td>{e.get('degree', '本科')}</td></tr></table>
      </div></div>""")
    if edu_parts:
        edu_html = f"""    <div class="card">
      <div class="card-header"><h3>🎓 教育背景</h3></div>
      <div class="card-body">
{chr(10).join(edu_parts)}
      </div></div>"""
    else:
        edu_html = '<div class="card"><div class="card-body empty-text">暂无教育背景</div></div>'

    # ── 技能 ──
    skill_parts = []
    for sec_name, bullets in data.get("skills", []):
        if not bullets:
            continue
        items = "".join(f"<li>{_clean_text(b)}</li>" for b in bullets)
        skill_parts.append(f"""    <div class="card skill-card">
      <div class="card-header skill-header"><span class="skill-dot"></span><h3>{sec_name}</h3></div>
      <div class="card-body"><ul class="bullet-list">{items}</ul></div></div>""")
    skills_html = "\n".join(skill_parts) if skill_parts else '<div class="card"><div class="card-body empty-text">暂无技能信息</div></div>'

    # ── 工作经历 ──
    work_parts = []
    for job in data.get("work_experience", []):
        duty_items = "".join(f"<li>{_clean_text(d)}</li>" for d in job.get("duties", []) if d)
        work_parts.append(f"""    <div class="timeline-card">
      <div class="timeline-dot work-dot"></div>
      <div class="timeline-content">
        <div class="tl-header"><h3>🏢 {job.get('company', '')}</h3><span class="tl-badge work-badge">{job.get('period', '')}</span></div>
        <div class="tl-position">{job.get('position', '')}</div>
        {f"<ul class='bullet-list'>{duty_items}</ul>" if duty_items else ""}
      </div></div>""")
    if work_parts:
        work_html = f"""    <div class="card">
      <div class="card-header"><h3>💼 工作经历</h3></div>
      <div class="card-body">
{chr(10).join(work_parts)}
      </div></div>"""
    else:
        work_html = '<div class="card"><div class="card-body empty-text">暂无工作经历</div></div>'

    # ── 项目经验 ──
    proj_parts = []
    for proj in data.get("projects", []):
        d_html = "".join(f"<li>{_clean_text(d)}</li>" for d in proj.get("duties", []) if d)
        a_html = "".join(f"<li class='achievement'>{_clean_text(a)}</li>" for a in proj.get("achievements", []) if a)
        desc = f'<div class="desc-text">{_clean_text(proj["description"])}</div>' if proj.get("description") else ""
        proj_parts.append(f"""    <div class="timeline-card">
      <div class="timeline-dot project-dot"></div>
      <div class="timeline-content">
        <div class="tl-header"><h3>🚀 {proj.get('name', '')}</h3><span class="tl-badge project-badge">{proj.get('period', '')}</span></div>
        {desc}
        {f'<div class="section-label">📋 项目职责</div><ul class="bullet-list">{d_html}</ul>' if d_html else ""}
        {f'<div class="section-label achievement-label">🏆 项目业绩</div><ul class="bullet-list achievement-list">{a_html}</ul>' if a_html else ""}
      </div></div>""")
    if proj_parts:
        proj_html = f"""    <div class="card">
      <div class="card-header"><h3>🚀 项目经验</h3></div>
      <div class="card-body">
{chr(10).join(proj_parts)}
      </div></div>"""
    else:
        proj_html = '<div class="card"><div class="card-body empty-text">暂无项目经验</div></div>'

    # ── 证书 ──
    cert_parts = []
    for c in data.get("certifications", []):
        cc = _clean_text(c)
        if cc and len(cc) > 2 and not re.search(r'^\d+[\.:]', cc):
            cert_parts.append(f'<div class="cert-badge">🏅 {cc}</div>')
    cert_html = "\n".join(cert_parts) if cert_parts else '<div class="empty-text">暂无证书</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} · 个人简历</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f0f4f8;--card-bg:#ffffff;
  --header-grad:linear-gradient(135deg,#0f172a,#1e3a5f 50%,#0d2137);
  --primary:#38bdf8;--primary-dark:#0284c7;--accent:#6366f1;
  --text:#1e293b;--text-muted:#64748b;--border:#e2e8f0;
  --green:#10b981;--amber:#f59e0b;
  --radius:14px;--shadow:0 2px 8px rgba(0,0,0,.06);--shadow-md:0 6px 24px rgba(0,0,0,.09);
}}
body{{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--text);line-height:1.7;min-height:100vh;-webkit-font-smoothing:antialiased;
}}
.hero{{
  background:var(--header-grad);padding:44px 24px 32px;position:relative;overflow:hidden;
}}
.hero::before{{
  content:'';position:absolute;top:-60px;right:-60px;
  width:350px;height:350px;border-radius:50%;
  background:radial-gradient(circle,rgba(56,189,248,.10),transparent 70%);pointer-events:none;
}}
.hero::after{{
  content:'';position:absolute;bottom:-90px;left:8%;
  width:450px;height:220px;border-radius:50%;
  background:radial-gradient(circle,rgba(99,102,241,.06),transparent 70%);pointer-events:none;
}}
.hero-inner{{max-width:880px;margin:0 auto;display:flex;align-items:center;gap:26px;position:relative;z-index:1;}}
.avatar{{
  width:84px;height:84px;border-radius:50%;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  display:flex;align-items:center;justify-content:center;
  font-size:34px;flex-shrink:0;
  box-shadow:0 0 0 4px rgba(56,189,248,.2),0 8px 28px rgba(56,189,248,.12);
}}
.hero-info h1{{font-size:28px;font-weight:700;color:#f8fafc;letter-spacing:.02em;}}
.hero-info h1 span{{font-weight:400;font-size:15px;color:#94a3b8;margin-left:8px;}}
.hero-tags{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}}
.hero-tag{{padding:3px 14px;border-radius:20px;font-size:12px;font-weight:500;background:rgba(56,189,248,.10);border:1px solid rgba(56,189,248,.2);color:var(--primary);}}
.hero-contacts{{display:flex;flex-wrap:wrap;gap:18px;margin-top:12px;font-size:13px;color:#94a3b8;}}
.hero-contacts a,.hc-item{{display:flex;align-items:center;gap:6px;color:#94a3b8;text-decoration:none;transition:color .2s;}}
.hero-contacts a:hover{{color:var(--primary);}}

.toolbar{{
  background:rgba(15,23,42,.96);padding:10px 24px;display:flex;justify-content:flex-end;gap:10px;
  border-bottom:1px solid rgba(56,189,248,.08);position:sticky;top:0;z-index:100;backdrop-filter:blur(10px);
}}
.btn{{display:inline-flex;align-items:center;gap:6px;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;border:none;transition:all .2s;white-space:nowrap;}}
.btn-outline{{background:transparent;border:1px solid rgba(148,163,184,.2);color:#94a3b8;}}
.btn-outline:hover{{border-color:var(--primary);color:var(--primary);background:rgba(56,189,248,.05);}}
.btn-primary{{background:linear-gradient(135deg,var(--primary),#0ea5e9);color:#0f172a;font-weight:600;box-shadow:0 2px 8px rgba(56,189,248,.2);}}
.btn-primary:hover{{background:linear-gradient(135deg,#7dd3fc,var(--primary));transform:translateY(-1px);box-shadow:0 4px 14px rgba(56,189,248,.3);}}

.tab-bar{{background:#fff;border-bottom:2px solid var(--border);padding:0 16px;display:flex;gap:0;overflow-x:auto;scrollbar-width:none;}}
.tab-bar::-webkit-scrollbar{{display:none;}}
.tab-btn{{padding:15px 22px;border:none;background:transparent;font-size:14px;font-weight:500;color:var(--text-muted);cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all .2s;white-space:nowrap;display:flex;align-items:center;gap:6px;}}
.tab-btn:hover{{color:var(--text);}}
.tab-btn.active{{color:var(--primary-dark);border-bottom-color:var(--primary-dark);font-weight:600;}}

.content-area{{max-width:880px;margin:0 auto;padding:28px 20px 80px;}}
.tab-panel{{display:none;}}
.tab-panel.active{{display:block;animation:fadeIn .3s ease;}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px);}}to{{opacity:1;transform:translateY(0);}}}}

.card{{background:var(--card-bg);border-radius:var(--radius);box-shadow:var(--shadow);margin-bottom:24px;border:1px solid var(--border);overflow:hidden;transition:box-shadow .2s;}}
.card:hover{{box-shadow:var(--shadow-md);}}
.card-header{{padding:18px 24px 14px;border-bottom:1px solid var(--border);}}
.card-header h3{{font-size:16px;font-weight:700;color:var(--text);}}
.card-body{{padding:18px 24px 22px;}}

.timeline-card{{position:relative;padding:4px 0 28px 36px;border-left:2px solid var(--border);margin-left:12px;}}
.timeline-card:last-child{{padding-bottom:4px;}}
.timeline-dot{{position:absolute;left:-7px;top:8px;width:12px;height:12px;border-radius:50%;background:var(--primary-dark);border:2px solid var(--card-bg);box-shadow:0 0 0 3px rgba(2,132,199,.12);}}
.work-dot{{background:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.12);}}
.timeline-content{{}}
.tl-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:6px;}}
.tl-header h3{{font-size:16px;font-weight:700;color:var(--text);}}
.tl-badge{{flex-shrink:0;font-size:12px;font-weight:500;padding:3px 12px;border-radius:20px;background:#eff6ff;color:var(--primary-dark);border:1px solid #bfdbfe;white-space:nowrap;}}
.work-badge{{background:#eef2ff;color:var(--accent);border-color:#c7d2fe;}}
.project-badge{{background:#ecfdf5;color:var(--green);border-color:#a7f3d0;}}
.tl-position{{font-size:13px;color:var(--text-muted);margin-bottom:10px;font-weight:500;}}

.project-dot{{background:var(--green);box-shadow:0 0 0 3px rgba(16,185,129,.12);}}
.card-body>.timeline-card:first-child{{padding-top:0;}}
.card-body>.timeline-card:first-child .timeline-dot{{top:2px;}}
.card-body>.timeline-card:last-child{{padding-bottom:0;border-left-color:transparent;}}

.skill-card{{}}
.skill-header{{display:flex;align-items:center;gap:10px;background:var(--card-bg);}}
.skill-dot{{width:8px;height:8px;border-radius:50%;background:var(--primary-dark);}}

.bullet-list{{list-style:none;margin:0;padding:0;}}
.bullet-list li{{padding:7px 0 7px 22px;font-size:14px;color:#334155;line-height:1.7;position:relative;border-bottom:1px solid var(--border);}}
.bullet-list li:last-child{{border-bottom:none;}}
.bullet-list li::before{{content:'';position:absolute;left:0;top:14px;width:6px;height:6px;border-radius:50%;background:var(--primary-dark);}}
.achievement-list li::before{{background:var(--green);}}
.achievement{{color:#065f46!important;}}

.desc-text{{font-size:14px;color:#475569;line-height:1.8;background:var(--card-bg);border-left:3px solid var(--primary);padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:16px;}}
.section-label{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin:18px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border);}}
.achievement-label{{color:var(--green);}}

.info-table{{width:100%;border-collapse:collapse;}}
.info-table th,.info-table td{{padding:8px 14px;font-size:14px;text-align:left;border-bottom:1px solid var(--border);}}
.info-table th{{width:80px;color:var(--text-muted);font-weight:500;background:var(--card-bg);}}
.info-table tr:last-child td,.info-table tr:last-child th{{border-bottom:none;}}

.summary-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:16px;margin-bottom:22px;}}
.summary-item{{display:flex;flex-direction:column;gap:6px;}}
.si-icon{{font-size:22px;}}
.si-label{{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;}}
.si-val{{font-size:18px;font-weight:700;color:var(--text);}}
.summary-desc p{{font-size:14px;line-height:1.8;color:#475569;margin-bottom:12px;}}
.summary-desc p:last-child{{margin-bottom:0;}}

.cert-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;}}
.cert-badge{{background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:16px 20px;font-size:14px;font-weight:600;color:var(--text);display:flex;align-items:center;gap:10px;transition:.2s;}}
.cert-badge:hover{{transform:translateY(-2px);box-shadow:var(--shadow-md);}}
.empty-text{{color:var(--text-muted);font-size:14px;padding:8px 0;}}

@media(max-width:640px){{
  .hero-inner{{flex-direction:column;align-items:flex-start;}}
  .tab-btn{{padding:12px 14px;font-size:13px;}}
  .tl-header{{flex-direction:column;}}
  .summary-grid{{grid-template-columns:repeat(2,1fr);}}
  .cert-grid{{grid-template-columns:1fr;}}
}}
@media print{{
  body{{background:#fff!important;min-height:auto!important;}}
  .hero{{background:#0f172a!important;-webkit-print-color-adjust:exact;print-color-adjust:exact;padding:12px 24px!important;}}
  .hero::before,.hero::after{{display:none!important;}}
  .toolbar,.tab-bar{{display:none!important;}}
  .tab-panel{{display:block!important;}}
  .content-area{{max-width:100%!important;padding:8px 12px 20px!important;}}
  .card,.timeline-card{{box-shadow:none!important;page-break-inside:avoid;}}
  .tab-panel+.tab-panel{{margin-top:12px;}}
  @page{{margin:1cm;}}
}}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-inner">
    <div class="avatar">👨‍💻</div>
    <div class="hero-info">
      <h1>{name}<span>个人简历</span></h1>
      <div class="hero-tags">
        <span class="hero-tag">🎯 {target}</span>
        <span class="hero-tag">⏱️ {exp} 经验</span>
      </div>
      <div class="hero-contacts">
        <a href="tel:{phone}">📱 {phone}</a>
        <a href="mailto:{email}">✉️ {email}</a>
      </div>
    </div>
  </div>
</div>

<div class="toolbar" id="toolbar">
  <button class="btn btn-outline" onclick="window.print()">🖨️ 打印</button>
  <button class="btn btn-primary" id="downloadBtn">📥 下载 PDF</button>
</div>

<div class="tab-bar" role="tablist">
  <button class="tab-btn active" data-tab="summary" onclick="switchTab('summary')">👤 职业概述</button>
  <button class="tab-btn" data-tab="education" onclick="switchTab('education')">🎓 教育背景</button>
  <button class="tab-btn" data-tab="skills" onclick="switchTab('skills')">🛠️ 技术技能</button>
  <button class="tab-btn" data-tab="work" onclick="switchTab('work')">💼 工作经历</button>
  <button class="tab-btn" data-tab="projects" onclick="switchTab('projects')">🚀 项目经验</button>
  <button class="tab-btn" data-tab="certifications" onclick="switchTab('certifications')">🏅 证书资质</button>
</div>

<div class="content-area">
  <div class="tab-panel active" id="tab-summary">{career}</div>
  <div class="tab-panel" id="tab-education">{edu_html}</div>
  <div class="tab-panel" id="tab-skills">{skills_html}</div>
  <div class="tab-panel" id="tab-work">{work_html}</div>
  <div class="tab-panel" id="tab-projects">{proj_html}</div>
  <div class="tab-panel" id="tab-certifications">
    <div class="card">
      <div class="card-header"><h3>🏅 证书与资质</h3></div>
      <div class="card-body"><div class="cert-grid">{cert_html}</div></div>
    </div>
  </div>
</div>

<script>
function switchTab(n){{
  document.querySelectorAll('.tab-btn').forEach(function(b){{
    var a=b.dataset.tab===n;b.classList.toggle('active',a);b.setAttribute('aria-selected',String(a));
  }});
  document.querySelectorAll('.tab-panel').forEach(function(p){{
    p.classList.toggle('active',p.id==='tab-'+n);
  }});
  if(history.pushState)history.pushState(null,null,'#'+n);
}}
(function(){{
  var h=location.hash.replace('#','');
  if(h&&document.querySelector('.tab-btn[data-tab="'+h+'"]'))switchTab(h);
}})();
document.addEventListener('keydown',function(e){{
  if(/^(INPUT|TEXTAREA)$/.test(e.target.tagName))return;
  var t=Array.from(document.querySelectorAll('.tab-btn'));
  var i=t.findIndex(function(b){{return b.classList.contains('active');}});
  if(e.key==='ArrowRight'){{var n=t[(i+1)%t.length];switchTab(n.dataset.tab);n.focus();e.preventDefault();}}
  if(e.key==='ArrowLeft'){{var n=t[(i-1+t.length)%t.length];switchTab(n.dataset.tab);n.focus();e.preventDefault();}}
}});
(function(){{
  var btn=document.getElementById('downloadBtn');if(!btn)return;
  function fb(){{
    var ct=null;document.querySelectorAll('.tab-btn.active').forEach(function(b){{ct=b.dataset.tab;}});
    var p=document.querySelectorAll('.tab-panel'),tb=document.getElementById('toolbar'),tn=document.querySelector('.tab-bar');
    p.forEach(function(x){{x.style.display='block';}});
    if(tb)tb.style.display='none';if(tn)tn.style.display='none';
    window.print();
    setTimeout(function(){{p.forEach(function(x){{x.style.display='';}});if(tb)tb.style.display='';if(tn)tn.style.display='';if(ct)switchTab(ct);}},1200);
  }}
  var s=document.createElement('script');
  s.src='https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
  s.onload=function(){{
    btn.onclick=function(){{
      var p=document.querySelectorAll('.tab-panel'),tb=document.getElementById('toolbar'),tn=document.querySelector('.tab-bar');
      var hero=document.querySelector('.hero'),ca=document.querySelector('.content-area');
      // 保存原始样式
      var hp=hero?hero.style.padding:'',ho=hero?hero.style.overflow:'';
      var cp=ca?ca.style.padding:'',cm=ca?ca.style.maxWidth:'';
      // 紧凑布局
      if(hero){{hero.style.padding='11px 24px';hero.style.overflow='hidden';}}
      if(ca){{ca.style.padding='6px 12px 16px';ca.style.maxWidth='100%';}}
      p.forEach(function(x){{x.style.display='block';}});
      if(tb)tb.style.display='none';if(tn)tn.style.display='none';
      html2pdf().set({{margin:[8,8,8,8],filename:'{name}_简历.pdf',image:{{type:'jpeg',quality:.99}},html2canvas:{{scale:2,useCORS:true,logging:false}},jsPDF:{{unit:'mm',format:'a4',orientation:'portrait'}},pagebreak:{{mode:['avoid-all','css','legacy']}}}}).from(document.body).save().then(function(){{
        p.forEach(function(x){{x.style.display='';}});
        if(tb)tb.style.display='';if(tn)tn.style.display='';
        if(hero){{hero.style.padding=hp;hero.style.overflow=ho;}}
        if(ca){{ca.style.padding=cp;ca.style.maxWidth=cm;}}
      }});
    }};
  }};
  s.onerror=function(){{btn.onclick=fb;}};
  document.head.appendChild(s);
}})();
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# 编排解析
# ══════════════════════════════════════════════════════════════════════════════

def orchestrate_parsing(full_text: str) -> tuple:
    """从全文按编号分节编排各模块解析"""
    sections = split_sections(full_text)

    # 按照标题关键词映射分区
    personal = {}
    education = []
    skills = []
    certifications = []
    work_experience = []
    projects = []

    for title, content in sections.items():
        if title in ("__all__",):
            continue

        if '教育' in title:
            education = parse_education(content)
        elif '个人' in title:
            personal = parse_personal(content)
        elif '技术' in title or '技能' in title:
            skills = parse_skills(content)
        elif '证书' in title or '资质' in title:
            certifications = parse_certifications(content)
        elif '工作' in title:
            work_experience = parse_work_experience(content)
        elif '项目' in title:
            projects = parse_projects(content)

    # 如果没通过节标解析到，尝试从全文直接兜底
    if not education:
        education = parse_education(full_text)
    if not personal.get("name"):
        personal = parse_personal(full_text)
    if not skills:
        skills = parse_skills(full_text)
    if not certifications:
        certifications = parse_certifications(full_text)
    if not work_experience:
        work_experience = parse_work_experience(full_text)
    if not projects:
        projects = parse_projects(full_text)

    return personal, {
        "education": education,
        "skills": skills,
        "certifications": certifications,
        "work_experience": work_experience,
        "projects": projects,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  PDF → HTML 简历 v4.0")
    print("=" * 60)

    if not os.path.exists(PDF_PATH):
        print(f"\n[X] PDF not found: {PDF_PATH}")
        sys.exit(1)

    # 1. 提取全文
    print(f"\n[*] Extracting PDF full text...")
    full_text = extract_full_text(PDF_PATH)
    print(f"   总字符数: {len(full_text)}")

    # 2. 按编号分节编排解析
    print(f"\n[*] Parsing numbered sections...")
    sections = split_sections(full_text)
    print(f"   检测到 {len(sections)} 个分区: {list(sections.keys())}")

    personal, data = orchestrate_parsing(full_text)

    print(f"   [Person] {personal.get('name', '')} | {personal.get('phone', '')} | {personal.get('email', '')}")
    print(f"   Education: {len(data['education'])} entries")
    for e in data['education']:
        print(f"      {e.get('school', '')} | {e.get('major', '')} | {e.get('degree', '')} ({e.get('period', '')})")
    print(f"   Skills: {len(data['skills'])} sections")
    for n, b in data['skills']:
        print(f"      {n}: {len(b)} 项")
    print(f"   Certifications: {len(data['certifications'])} items")
    for c in data['certifications']:
        print(f"      {c}")
    print(f"   Work Experience: {len(data['work_experience'])} entries")
    for w in data['work_experience']:
        print(f"      {w['company']} ({w['period']}) [{len(w['duties'])} 职责]")
    print(f"   Projects: {len(data['projects'])} entries")
    for p in data['projects']:
        print(f"      {p['name'][:40]} ({p['period']}) [{len(p['duties'])} 职责, {len(p['achievements'])} 业绩]")

    # 3. 生成 HTML
    print(f"\n[*] Generating HTML...")
    html = build_html(personal, data)
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] {OUTPUT_HTML_PATH} ({os.path.getsize(OUTPUT_HTML_PATH) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
