from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.async_api import Frame, Page
from automation.evidence import EvidenceStore
from automation.models import (
    BoundingBox,
    DetectedDialog,
    DetectedMessage,
    FrameInfo,
    InteractiveElement,
    Observation,
    StructuredTable,
)


JS_FRAME_INSPECTOR = r"""
() => {
  const isVisible = (el) => {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const elements = [];
  const candidateSelectors = 'input, button, select, textarea, a[href], [role="button"], [role="link"], [tabindex]:not([tabindex="-1"]), .balance-value';
  const nodes = document.querySelectorAll(candidateSelectors);

  nodes.forEach((node) => {
    const visible = isVisible(node);
    const rect = node.getBoundingClientRect();
    const tag = node.tagName.toLowerCase();
    
    // Determine accessible name or label
    let label = '';
    if (node.id) {
      const lblEl = document.querySelector(`label[for="${node.id}"]`);
      if (lblEl) label = lblEl.innerText.trim();
    }
    if (!label && node.closest('label')) {
      label = node.closest('label').innerText.trim();
    }
    // Also look at adjacent or preceding td in form layouts (e.g. "Member Number:")
    if (!label && node.closest('td')) {
      const prevTd = node.closest('td').previousElementSibling;
      if (prevTd && (prevTd.classList.contains('label-cell') || prevTd.innerText.trim().endsWith(':') || prevTd.tagName.toLowerCase() === 'th')) {
        label = prevTd.innerText.replace(/:$/, '').trim();
      }
    }

    // Contextual labelling for action links/buttons inside data tables (e.g. "View" in accounts table)
    let rowContext = '';
    const row = node.closest('tr');
    if (row && (tag === 'a' || tag === 'button' || (tag === 'input' && node.type === 'button'))) {
      const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim()).filter(Boolean);
      if (cells.length > 1) {
        const otherCells = cells.filter(c => c !== node.innerText.trim());
        if (otherCells.length > 0) {
          rowContext = otherCells.join(' · ');
        }
      }
    }

    const attrs = {};
    for (let i = 0; i < node.attributes.length; i++) {
      const attr = node.attributes[i];
      attrs[attr.name] = attr.value;
    }
    if (rowContext) {
      attrs['row_context'] = rowContext;
    }

    const role = node.getAttribute('role') || (
      tag === 'button' ? 'button' :
      tag === 'a' ? 'link' :
      tag === 'input' && (node.type === 'submit' || node.type === 'button') ? 'button' :
      tag === 'input' && (node.type === 'checkbox') ? 'checkbox' :
      tag === 'input' && (node.type === 'radio') ? 'radio' :
      tag === 'input' || tag === 'textarea' ? 'textbox' :
      tag === 'select' ? 'combobox' : ''
    );

    let name = node.getAttribute('aria-label') ||
               node.getAttribute('placeholder') ||
               (node.type === 'submit' ? node.value : '');

    if (!name && rowContext && node.innerText.trim()) {
      name = `${node.innerText.trim()} (${rowContext})`;
    } else if (!name) {
      name = label || node.name || node.id || node.innerText.trim();
    }

    const value = node.value !== undefined ? String(node.value) : (node.innerText ? node.innerText.trim() : null);

    elements.push({
      tag: tag,
      role: role,
      name: name,
      label: label || name,
      text: node.innerText ? node.innerText.trim() : '',
      value: value,
      attributes: attrs,
      disabled: Boolean(node.disabled || node.getAttribute('aria-disabled') === 'true' || node.classList.contains('disabled-link')),
      visible: visible,
      editable: (tag === 'input' && !['submit', 'button', 'checkbox', 'radio'].includes(node.type)) || tag === 'textarea',
      bounding_box: {
        x: rect.x + window.scrollX,
        y: rect.y + window.scrollY,
        width: rect.width,
        height: rect.height
      }
    });
  });

  // Detect visible message boxes
  const messages = [];
  const msgNodes = document.querySelectorAll('.message-box, .status-line, [role="alert"]');
  msgNodes.forEach((m) => {
    if (!isVisible(m)) return;
    const titleEl = m.querySelector('.message-title');
    const codeEl = m.querySelector('.message-code');
    const title = titleEl ? titleEl.innerText.trim() : '';
    const code = codeEl ? codeEl.innerText.replace(/^Outcome code:\s*|^Failure code:\s*/, '').trim() : '';
    let level = 'info';
    if (m.classList.contains('business')) level = 'business';
    else if (m.classList.contains('failure')) level = 'failure';
    else if (m.classList.contains('warning')) level = 'warning';

    let messageText = m.innerText.trim();
    if (title && messageText.startsWith(title)) {
      messageText = messageText.substring(title.length).trim();
    }
    messages.push({
      title: title,
      message: messageText,
      code: code,
      level: level
    });
  });

  // Detect modal dialogs
  const dialogs = [];
  const dialogNodes = document.querySelectorAll('.legacy-dialog, dialog, [role="dialog"], .dialog-shade');
  dialogNodes.forEach((d) => {
    if (!isVisible(d)) return;
    const titleEl = d.querySelector('.dialog-title');
    const bodyEl = d.querySelector('.dialog-body');
    const buttons = [];
    d.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(btn => {
      if (isVisible(btn)) buttons.push(btn.innerText.trim() || btn.value);
    });

    dialogs.push({
      title: titleEl ? titleEl.innerText.trim() : 'Dialog',
      text: bodyEl ? bodyEl.innerText.trim() : d.innerText.trim(),
      buttons: buttons
    });
  });

  // Extract structured tables
  const tables = [];
  const tableNodes = document.querySelectorAll('table:not(.legacy-root):not(.legacy-dialog):not(.window-title)');
  tableNodes.forEach((t) => {
    if (!isVisible(t)) return;
    const captionEl = t.querySelector('caption') || t.previousElementSibling;
    const caption = (captionEl && captionEl.classList.contains('section-bar')) ? captionEl.innerText.trim() : '';
    
    const headers = [];
    t.querySelectorAll('tr th').forEach(th => headers.push(th.innerText.trim()));

    const rows = [];
    const trNodes = t.querySelectorAll('tr');
    trNodes.forEach(tr => {
      const rowData = [];
      const cells = tr.querySelectorAll('td');
      if (cells.length > 0) {
        cells.forEach(td => rowData.push(td.innerText.trim()));
        rows.push(rowData);
      }
    });

    if (headers.length > 0 || rows.length > 0) {
      tables.push({
        caption: caption,
        headers: headers,
        rows: rows
      });
    }
  });

  return {
    elements: elements,
    messages: messages,
    dialogs: dialogs,
    tables: tables,
    title: document.title,
    url: window.location.href,
    visible_text: document.body ? document.body.innerText : ''
  };
}
"""


class SurfaceObserver:
    """Discovers frames, interactive elements, tables, messages, and takes snapshots."""

    def __init__(self, evidence_store: Optional[EvidenceStore] = None):
        self.evidence_store = evidence_store
        self.obs_count = 0

    def _get_frame_path(self, frame: Frame) -> List[str]:
        """Compute the sequence of frame names from root down to this frame."""
        path: List[str] = []
        curr = frame
        while curr:
            if curr.name:
                path.insert(0, curr.name)
            elif curr.parent_frame:
                # If frame doesn't have a name, identify by index among siblings
                idx = curr.parent_frame.child_frames.index(curr)
                path.insert(0, f"frame_{idx}")
            curr = curr.parent_frame
        return path

    async def observe(self, page: Page, capture_screenshot: bool = True) -> Observation:
        self.obs_count += 1
        obs_id = f"obs_{self.obs_count:03d}"

        frames = page.frames
        frame_hierarchy: List[FrameInfo] = []
        all_elements: List[InteractiveElement] = []
        all_messages: List[DetectedMessage] = []
        all_dialogs: List[DetectedDialog] = []
        all_tables: List[StructuredTable] = []
        visible_text_parts: List[str] = []

        # Index frames
        for f in frames:
            parent_id = None
            depth = 0
            curr = f.parent_frame
            while curr:
                depth += 1
                if parent_id is None:
                    parent_id = curr.name or "root"
                curr = curr.parent_frame

            f_id = f.name or ("root" if depth == 0 else f"frame_{depth}")
            frame_hierarchy.append(FrameInfo(
                frame_id=f_id,
                name=f.name or "",
                url=f.url,
                parent_frame_id=parent_id,
                depth=depth,
            ))

        # Inspect each frame
        element_idx = 0
        for f in frames:
            frame_path = self._get_frame_path(f)
            try:
                data = await f.evaluate(JS_FRAME_INSPECTOR)
            except Exception:
                # Frame may be detached or cross-origin
                continue

            if data.get("visible_text"):
                visible_text_parts.append(f"--- Frame: {' > '.join(frame_path) or 'root'} ---\n{data['visible_text']}")

            for el_data in data.get("elements", []):
                element_idx += 1
                el_id = f"e_{element_idx:02d}"
                bbox = BoundingBox(**el_data["bounding_box"]) if el_data.get("bounding_box") else None
                all_elements.append(InteractiveElement(
                    observation_id=el_id,
                    tag=el_data["tag"],
                    role=el_data.get("role", ""),
                    name=el_data.get("name", ""),
                    label=el_data.get("label", ""),
                    text=el_data.get("text", ""),
                    value=el_data.get("value"),
                    attributes=el_data.get("attributes", {}),
                    disabled=el_data.get("disabled", False),
                    visible=el_data.get("visible", True),
                    editable=el_data.get("editable", False),
                    frame_path=frame_path,
                    bounding_box=bbox,
                ))

            for msg in data.get("messages", []):
                all_messages.append(DetectedMessage(
                    title=msg.get("title", ""),
                    message=msg.get("message", ""),
                    code=msg.get("code", ""),
                    level=msg.get("level", "info"),
                    frame_path=frame_path,
                ))

            for d in data.get("dialogs", []):
                all_dialogs.append(DetectedDialog(
                    title=d.get("title", ""),
                    text=d.get("text", ""),
                    buttons=d.get("buttons", []),
                    frame_path=frame_path,
                ))

            for t in data.get("tables", []):
                all_tables.append(StructuredTable(
                    caption=t.get("caption", ""),
                    headers=t.get("headers", []),
                    rows=t.get("rows", []),
                    frame_path=frame_path,
                ))

        screenshot_ref = None
        if capture_screenshot and self.evidence_store:
            screenshot_id = obs_id
            screenshot_path = self.evidence_store.get_screenshot_path(screenshot_id)
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                screenshot_ref = f"screenshots/{screenshot_id}.png"
            except Exception:
                screenshot_ref = None

        page_title = ""
        try:
            page_title = await page.title()
        except Exception:
            pass

        observation = Observation(
            observation_id=obs_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            page_url=page.url,
            page_title=page_title,
            frame_hierarchy=frame_hierarchy,
            interactive_elements=all_elements,
            visible_text="\n\n".join(visible_text_parts),
            detected_messages=all_messages,
            detected_dialogs=all_dialogs,
            structured_tables=all_tables,
            screenshot_ref=screenshot_ref,
        )

        if self.evidence_store:
            self.evidence_store.save_observation(observation)

        return observation
