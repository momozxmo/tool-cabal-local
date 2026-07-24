# -*- coding: utf-8 -*-
"""Preview-only bundle filler for the Aztek v2 site.

Phase 1 is preview: it opens the v2 "create bundle" page, fills the header
(name / type / immediate-send) and adds the chosen item ids, then stops WITHOUT
saving — nothing is created on the live site. For local runs it can open a real
(headed) Chrome so the user watches the filled form, mirroring the desktop tool.

The v2 bundle UI is a full page (``/shop/bundles/create``) with stable ids, so
this is a small purpose-built filler rather than the desktop modal engine.
"""
from playwright.async_api import async_playwright

import new_tool
from web.search_runner import to_web_url


def bundle_create_url(game):
    """v2 'create bundle' page URL for a game (desktop targets the v1 host)."""
    return to_web_url(new_tool.game_url(game, 'bundles')) + '/create'


class BundlePreview:
    """Fill one bundle form on Aztek v2 and leave it unsaved."""

    def __init__(self, on_log):
        self._log = on_log
        self._cancel = False

    def log(self, message, level='INFO'):
        self._log(message, level)

    async def _fill_header(self, page, name, btype, deliver):
        # Name — stable id on v2.
        try:
            box = page.locator('#bundle-name, input[name="name"]').first
            await box.wait_for(state='visible', timeout=8000)
            await box.fill(name)
            self.log('ใส่ชื่อ Bundle: %s' % name, 'INFO')
        except Exception as exc:
            self.log('กรอกชื่อ Bundle ไม่สำเร็จ: %s' % exc, 'WARNING')
        # Type — the only <select> in the header.
        try:
            sel = page.locator('select').first
            if await sel.count() > 0:
                for how in ('label', 'value'):
                    try:
                        if how == 'label':
                            await sel.select_option(label=btype)
                        else:
                            await sel.select_option(value=btype)
                        self.log('เลือกประเภท Bundle: %s' % btype, 'INFO')
                        break
                    except Exception:
                        continue
        except Exception as exc:
            self.log('เลือกประเภท Bundle ไม่สำเร็จ: %s' % exc, 'WARNING')
        # Immediate-send toggle.
        try:
            cb = page.locator('input[type="checkbox"]').first
            if await cb.count() > 0:
                checked = await cb.is_checked()
                if checked != deliver:
                    await cb.click()
                self.log('ตั้งส่งทันที: %s' % ('เปิด' if deliver else 'ปิด'), 'INFO')
        except Exception as exc:
            self.log('ตั้งส่งทันทีไม่สำเร็จ: %s' % exc, 'WARNING')

    async def _add_item(self, page, item_id):
        """Search the item id in the 'เพิ่มของเข้า Bundle' panel and click เพิ่ม."""
        try:
            box = page.locator('input[placeholder*="ค้นหาชื่อ Item"], '
                               'input[placeholder*="ค้นหา Item"]').first
            await box.wait_for(state='visible', timeout=8000)
            await box.fill(str(item_id))
            await page.wait_for_timeout(1500)
            # The matching result row exposes an "เพิ่ม" button; pick the row that
            # shows this id.
            row = page.locator(
                'xpath=//*[contains(normalize-space(.),"ID: %s")]'
                '[.//button[contains(normalize-space(.),"เพิ่ม")]]' % item_id).first
            if await row.count() == 0:
                # Fallback: any visible เพิ่ม button after the search.
                add = page.locator('button:has-text("เพิ่ม")').first
            else:
                add = row.locator('button:has-text("เพิ่ม")').first
            if await add.count() > 0 and await add.is_visible():
                await add.click()
                self.log('เพิ่มไอเทม %s' % item_id, 'INFO')
                await page.wait_for_timeout(600)
                return True
            self.log('หาไอเทม %s ไม่เจอในผลค้นหา' % item_id, 'WARNING')
            return False
        except Exception as exc:
            self.log('เพิ่มไอเทม %s ไม่สำเร็จ: %s' % (item_id, exc), 'WARNING')
            return False

    async def _fill_qty_tier(self, page, items):
        """Set quantity and tier on each item card. v2 exposes a stable
        ``items.<n>.quantity`` number input and a hidden <select> for the tier.
        """
        cards = page.locator('input[name^="items."][name$=".quantity"]')
        count = await cards.count()
        for idx in range(count):
            it = items[idx] if idx < len(items) else {}
            qty = str(it.get('qty') or it.get('quantity') or '1')
            tier = it.get('tier') or 'Common'
            try:
                await cards.nth(idx).fill(qty)
            except Exception as exc:
                self.log('ตั้งจำนวนไอเทม #%d ไม่สำเร็จ: %s' % (idx + 1, exc), 'WARNING')
            # The tier control is a radix combobox backed by a native <select>;
            # the nth select on the page maps to the nth item card.
            try:
                selects = page.locator('select')
                if await selects.count() > idx:
                    for how in ('label', 'value'):
                        try:
                            if how == 'label':
                                await selects.nth(idx).select_option(label=tier)
                            else:
                                await selects.nth(idx).select_option(value=tier)
                            break
                        except Exception:
                            continue
            except Exception as exc:
                self.log('ตั้ง Tier ไอเทม #%d ไม่สำเร็จ: %s' % (idx + 1, exc), 'WARNING')
        if count:
            self.log('ตั้งจำนวน/Tier ให้ %d ไอเทม' % count, 'INFO')

    async def run(self, game, name, btype, deliver, items, storage_state,
                  *, headed=False):
        """Open the create page with the user's session and fill it (no save)."""
        url = bundle_create_url(game)
        self.log('เปิดหน้าสร้าง Bundle: %s' % url, 'STEP')
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=not headed)
            context = await browser.new_context(storage_state=storage_state)
            page = await context.new_page()
            shot = None
            final_url = None
            added = 0
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                low = page.url.lower()
                if any(p in low for p in ('/login', '/signin')):
                    raise RuntimeError('session หมดอายุ (โดนเด้งไปหน้า login)')
                await self._fill_header(page, name, btype, deliver)
                for it in items:
                    if self._cancel:
                        break
                    if await self._add_item(page, it.get('id') or it.get('aztek_id')):
                        added += 1
                if added:
                    await page.wait_for_timeout(500)
                    await self._fill_qty_tier(page, items)
                final_url = page.url
                try:
                    shot = await page.screenshot(full_page=True)
                except Exception:
                    shot = None
                self.log('กรอกฟอร์มเสร็จ (ยังไม่กดสร้าง) — เพิ่มไอเทม %d/%d'
                         % (added, len(items)), 'SUCCESS')
                if headed:
                    await page.wait_for_timeout(6000)
            finally:
                await context.close()
                await browser.close()
            return {'url': final_url, 'screenshot': shot, 'added': added,
                    'total': len(items)}
