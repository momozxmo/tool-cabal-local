# -*- coding: utf-8 -*-
"""Fill the Aztek v2 "สร้าง Event" form.

An Event is the same shape as an Item Code minus the codes: reward sets that
each hand out one bundle, over two time windows — when the activity runs and
when the prize can be claimed.

The bundle ids are already in the monthly plan, so nothing here searches for
items; the operator brings the numbers with them.
"""
from web import aztek_form
from web.activity_runner import ActivityBuilder

#: label -> spec key, in the order the page shows them
DATE_FIELDS = (
    ('วันเริ่มกิจกรรม', 'start_event'),
    ('วันสิ้นสุดกิจกรรม', 'end_event'),
    ('วันเริ่มรับรางวัล', 'start_claim'),
    ('วันสิ้นสุดการรับรางวัล', 'end_claim'),
)


def _date_trigger(page, label):
    """The date-and-time button belonging to a label."""
    return page.locator('xpath=//label[contains(normalize-space(.),"%s")]'
                        '/following::button[1]' % label).first


class EventBuilder(ActivityBuilder):
    PATH = 'events'
    SAVE_LABEL = 'สร้าง Event'
    KIND = 'Event'
    WRITE_MARK = 'event'

    async def _fill_header(self, page, spec, missing):
        # The page arrives with a generated slug (event-<timestamp>), so this
        # is an overwrite rather than a fill — an empty value would leave that
        # placeholder behind on the live site.
        for field, label in (('slug', 'Slug'), ('name_th', 'ชื่อ Event (ไทย)'),
                             ('name_en', 'ชื่อ Event (อังกฤษ)')):
            text = str(spec.get(field) or '')
            ok = await aztek_form.fill(page, 'input[name="%s"]' % field, text,
                                       self.log, label)
            if not ok or not text:
                missing.append(label)
        await aztek_form.select_by_options(
            page, spec.get('type') or 'WINNER', ('WINNER', 'ALL'), self.log)
        for field, value, label in (
            ('per_player_limit', spec.get('uses_per_user') or '1',
             'จำกัดต่อผู้เล่น'),
            ('quantity', spec.get('quantity') or '0', 'จำนวนรางวัลทั้งหมด'),
            ('remaining', spec.get('remaining') or '0', 'คงเหลือ'),
        ):
            await aztek_form.fill(page, 'input[name="%s"]' % field, value,
                                  self.log, label)
        for label, key in DATE_FIELDS:
            if not await aztek_form.set_datetime(
                    page, _date_trigger(page, label), spec.get(key),
                    self.log, label):
                missing.append(label)

    async def _fill_reward(self, page, index, reward, missing):
        where = 'ชุดรางวัลที่ %d' % (index + 1)
        self.log('  %s: %s (bundle %s)'
                 % (where, reward.get('name_th') or '-',
                    reward.get('bundle_id') or '-'), 'STEP')
        for field, label in (('name_th', 'ชื่อรางวัล (ไทย)'),
                             ('name_en', 'ชื่อรางวัล (อังกฤษ)')):
            text = str(reward.get(field) or '')
            ok = await aztek_form.fill(
                page, 'input[name="rewards.%d.%s"]' % (index, field), text,
                self.log, label)
            if not ok or not text:
                missing.append('%s: %s' % (where, label))
        for field in ('desc_th', 'desc_en'):
            if str(reward.get(field) or ''):
                await aztek_form.fill(
                    page, 'textarea[name="rewards.%d.%s"]' % (index, field),
                    reward.get(field), self.log, field)
        # Only the open reward set is rendered, and it sits above the event's
        # own status switches — so the first "จำกัดจำนวน" is this set's.
        await aztek_form.set_switch(page, 'จำกัดจำนวน',
                                    bool(reward.get('limited')), self.log)
        await aztek_form.fill(
            page, 'input[name="rewards.%d.per_player_limit"]' % index,
            reward.get('uses_per_user') or '1', self.log, 'จำกัดต่อผู้เล่น')
        bundle_id = str(reward.get('bundle_id') or '').strip()
        if not bundle_id:
            missing.append('%s: Bundle' % where)
        elif not await aztek_form.pick_bundle(
                page, aztek_form.reward_card(page, index), bundle_id, self.log):
            missing.append('%s: Bundle %s' % (where, bundle_id))

    async def fill_form(self, page, spec):
        """Fill the whole page and report which required fields are still empty."""
        missing = []
        await self._fill_header(page, spec, missing)
        rewards = spec.get('rewards') or []
        if not rewards:
            missing.append('ชุดรางวัล')
        for index, reward in enumerate(rewards):
            if self._cancel:
                break
            # Unlike Item Code, an Event page loads with no reward set at all.
            if not await self.add_reward_set(page, index):
                missing.append('ชุดรางวัลที่ %d' % (index + 1))
                continue
            await self._fill_reward(page, index, reward, missing)
        return missing
