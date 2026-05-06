"""
renderer.py — Personalize email templates with contact and reminder data.

Uses simple string-based template substitution (no external dependencies).
Converts Markdown-style formatting to clean HTML for email clients.
"""

import re
import html as html_lib


def _md_to_html(text: str) -> str:
    """
    Convert basic Markdown syntax to HTML.
    Handles: bold, line breaks, horizontal rules, lists.
    """
    # Escape HTML entities first
    text = html_lib.escape(text)

    # Bold: **text** → <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

    # Italic: *text* → <em>text</em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)

    # Horizontal rule
    text = re.sub(r'\n---\n', '\n<hr style="border:none;border-top:1px solid #eee;margin:20px 0;">\n', text)

    # Unordered lists
    def replace_list(m):
        items = m.group(0).strip().split('\n')
        lis = ''.join(f'<li style="margin:4px 0">{item.lstrip("- ").strip()}</li>' for item in items if item.strip())
        return f'<ul style="padding-left:20px;margin:8px 0">{lis}</ul>'
    text = re.sub(r'(^- .+\n?)+', replace_list, text, flags=re.MULTILINE)

    # Line breaks: double newline → paragraph, single → <br>
    paragraphs = text.split('\n\n')
    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para.startswith('<ul') or para.startswith('<hr'):
            html_parts.append(para)
        else:
            para = para.replace('\n', '<br>')
            html_parts.append(f'<p style="margin:0 0 12px 0">{para}</p>')

    return '\n'.join(html_parts)


def _wrap_html(body_html: str) -> str:
    """Wrap email body in a professional HTML email layout."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Email Reminder</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;max-width:600px;width:100%;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                       padding:28px 40px;">
              <p style="margin:0;color:#e0e0ff;font-size:13px;letter-spacing:2px;
                         text-transform:uppercase;opacity:0.7;">Automated Reminder</p>
              <p style="margin:6px 0 0 0;color:#ffffff;font-size:22px;font-weight:700;">
                Email Automation System
              </p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:36px 40px;color:#2d3748;font-size:15px;line-height:1.7;">
              {body_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#f8f9fb;padding:20px 40px;border-top:1px solid #eee;">
              <p style="margin:0;font-size:12px;color:#a0aec0;text-align:center;">
                This is an automated message. Please do not reply directly to this email.<br>
                To unsubscribe, contact your administrator.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_email(subject_template: str, body_md_template: str, context: dict) -> tuple[str, str]:
    """
    Render subject and body with context variables.

    Args:
        subject_template: Subject string with {{variable}} placeholders
        body_md_template: Markdown body with {{variable}} placeholders
        context: Dict of variable values, e.g. {"name": "Arjun", "title": "Math Class"}

    Returns:
        Tuple of (rendered_subject, rendered_html_body)

    Raises:
        KeyError: If a required template variable is missing from context
    """
    # Substitute all {{key}} placeholders
    def substitute(template: str, ctx: dict) -> str:
        def replace_match(m):
            key = m.group(1).strip()
            if key not in ctx:
                raise KeyError(f"Template variable '{{{{ {key} }}}}' not found in context. "
                               f"Available keys: {list(ctx.keys())}")
            return str(ctx[key])
        return re.sub(r'\{\{(\s*\w+\s*)\}\}', replace_match, template)

    rendered_subject = substitute(subject_template, context)
    rendered_body_md = substitute(body_md_template, context)
    rendered_body_html = _wrap_html(_md_to_html(rendered_body_md))

    return rendered_subject, rendered_body_html


if __name__ == "__main__":
    # Quick test
    subj_tmpl = "Reminder: {{name}}, your {{title}} starts soon!"
    body_tmpl = "Hi **{{name}}**,\n\nYour **{{title}}** is on **{{scheduled_time}}**.\n\n---\nBest,\nTeam"
    ctx = {"name": "Arjun Sharma", "title": "Python Class", "scheduled_time": "Jan 20 at 7:00 PM IST"}
    s, h = render_email(subj_tmpl, body_tmpl, ctx)
    print("Subject:", s)
    print("HTML preview (first 200 chars):", h[:200])