# -*- coding: utf-8 -*-
"""Bundle creation: reward validation, draw-rate discovery, and save safety.

These cover the parts that can write to the live Aztek site, so they run
against fake pages rather than a real browser.
"""
from __future__ import annotations

import asyncio
import inspect

from web import bundle_runner
from web.app import BundleRunRequest, _clean_items, _clean_rewards


# ------------------------------ rewards ------------------------------

def test_clean_rewards_keeps_only_well_formed_entries():
    cleaned = _clean_rewards([
        {'type': 'credit', 'value': 'Alz', 'qty': '100'},   # lowercase kind
        {'type': 'PLAYER_EXP', 'value': 'Rank 5', 'qty': 1},
        {'type': 'BITCOIN', 'value': 'nope', 'qty': '1'},   # unknown kind
        {'type': 'DEBIT', 'value': '', 'qty': '1'},         # no value
        {'type': 'MILEAGE', 'value': 'M', 'qty': '0'},      # not a real amount
        {'type': 'MILEAGE', 'value': 'M', 'qty': 'ten'},    # not a number
    ])
    assert cleaned == [
        {'type': 'CREDIT', 'value': 'Alz', 'qty': '100'},
        {'type': 'PLAYER_EXP', 'value': 'Rank 5', 'qty': '1'},
    ]


def test_creating_is_off_unless_asked():
    """A request that omits do_save must never write to the live site."""
    payload = BundleRunRequest(game='Cabal M')
    assert payload.do_save is False
    assert payload.bundles == []


def test_reward_tabs_use_the_v2_wording():
    """v2 tabs are not the v1 accordion headings — reusing those found nothing.

    The one that actually differs is PLAYER_EXP ("Player Exp." vs "Player
    Experience"), so pin the whole map rather than just the shape.
    """
    assert bundle_runner.REWARD_TABS == {
        'CREDIT': 'Credit', 'DEBIT': 'Debit',
        'MILEAGE': 'Mileage', 'PLAYER_EXP': 'Player Exp.'}
    assert set(bundle_runner.REWARD_TABS) == set(bundle_runner.REWARD_KINDS)


def test_preview_does_not_tour_every_reward_tab():
    """Adding one reward used to also open all four tabs to refill a cache.

    The tour costs four page interactions the operator did not ask for, so it
    belongs to the explicit fetch trip alone.
    """
    assert 'read_reward_options' not in inspect.getsource(
        bundle_runner.BundleBuilder.run)
    assert 'read_reward_options' in inspect.getsource(
        bundle_runner.fetch_reward_options)


# --------------------------- create them all ---------------------------

def test_each_bundle_carries_its_own_type_and_rewards():
    """The queue holds bundles from different events; one setting for the run
    would give them all the same type and the same currency."""
    payload = BundleRunRequest(game='Cabal M', bundles=[
        {'name': 'a', 'bundle_type': 'RANDOM',
         'rewards': [{'type': 'CREDIT', 'value': 'Ark Gem', 'qty': '1'}]},
        {'name': 'b'},
    ])
    assert payload.bundles[0].bundle_type == 'RANDOM'
    assert payload.bundles[0].rewards[0]['value'] == 'Ark Gem'
    assert (payload.bundles[1].bundle_type, payload.bundles[1].rewards) == ('FIXED', [])


def test_items_are_taken_as_typed_in_the_order_given():
    """The page builds bundles from typed or pasted ids, not from a search, so
    an id only has to look like one. Order is the operator's."""
    items = _clean_items([
        {'id': ' 200479 ', 'qty': '3', 'tier': 'Epic'},
        {'id': 'ID 11', 'rate': '12.5'},          # digits dug out of free text
        {'id': '200479', 'qty': '9'},             # already in — Aztek refuses it
        {'id': 'no digits here'},
        {'id': '22', 'qty': 'ten'},               # unreadable count -> 1
    ])
    assert items == [
        {'id': '200479', 'qty': '3', 'tier': 'Epic', 'rate': ''},
        {'id': '11', 'qty': '1', 'tier': 'Common', 'rate': '12.5'},
        {'id': '22', 'qty': '1', 'tier': 'Common', 'rate': ''},
    ]


def test_a_pasted_column_cannot_grow_without_bound():
    items = _clean_items([{'id': str(n)} for n in range(1, 500)])
    assert len(items) == 200


def test_one_failing_bundle_does_not_stop_the_rest():
    """A batch that dies halfway must still report what it did create."""
    builder = _builder()

    async def fake_fill(page, name, *args):
        if name == 'bad':
            raise RuntimeError('เพิ่มไอเทมไม่ได้')
        return 1, 0

    saves = iter([(True, '111'), (True, '333')])
    builder._fill_form = fake_fill
    builder._save = lambda page: _async(next(saves))
    results = asyncio.run(_run_many(builder, ['good', 'bad', 'later']))
    assert [(r['name'], r['saved'], r['bundle_id']) for r in results] == [
        ('good', True, '111'), ('bad', False, None), ('later', True, '333')]
    assert 'เพิ่มไอเทมไม่ได้' in results[1]['error']


async def _async(value):
    return value


async def _run_many(builder, names):
    """Drive run_many with the browser stack stubbed out."""
    bundles = [{'group': n, 'name': n, 'items': [{'id': '1'}], 'rewards': []}
               for n in names]

    class FakeNavPage(FakePage):
        async def goto(self, url, **kwargs):
            return None

    page = FakeNavPage(url='https://x/shop/bundles/create')

    class Ctx:
        pages = [page]

        async def new_page(self):
            return page

        async def close(self):
            return None

    class Browser:
        async def new_context(self, **kwargs):
            return Ctx()

        async def close(self):
            return None

    class Chromium:
        async def launch(self, **kwargs):
            return Browser()

    class Driver:
        chromium = Chromium()

        async def stop(self):
            return None

    async def start():
        return Driver()

    real = bundle_runner.async_playwright
    bundle_runner.async_playwright = lambda: type(
        'P', (), {'start': staticmethod(start)})()
    try:
        return await builder.run_many(game='Cabal M', bundles=bundles,
                                      storage_state={})
    finally:
        bundle_runner.async_playwright = real


# --------------------------- kept-open window ---------------------------

class FakeClosable:
    def __init__(self, name, log):
        self._name = name
        self._log = log

    async def close(self):
        self._log.append(self._name)

    # Playwright's driver handle stops rather than closes.
    async def stop(self):
        self._log.append(self._name)


def test_the_next_run_closes_the_window_the_last_preview_left_open():
    """Browser concurrency is meant to stay at one, so the slot must be reclaimed."""
    closed: list[str] = []
    bundle_runner._KEPT['u1'] = tuple(
        FakeClosable(n, closed) for n in ('pw', 'browser', 'context'))
    asyncio.run(bundle_runner.close_kept('u1'))
    assert closed == ['context', 'browser', 'pw']
    assert 'u1' not in bundle_runner._KEPT


def test_closing_a_window_that_the_operator_already_shut_is_harmless():
    asyncio.run(bundle_runner.close_kept('nobody'))  # must not raise


# --------------------------- fake page bits ---------------------------

class FakeLocator:
    def __init__(self, page, name, index=0):
        self._page = page
        self._name = name
        self._index = index

    @property
    def first(self):
        return self

    def nth(self, index):
        return FakeLocator(self._page, self._name, index)

    async def count(self):
        return self._page.counts.get(self._name, 1)

    async def wait_for(self, **kwargs):
        return None

    async def get_attribute(self, name):
        return self._page.attrs.get(self._name, {}).get(name)

    async def fill(self, value):
        self._page.filled.append((self._name, value))

    async def select_option(self, **kwargs):
        self._page.selected.append((self._name, self._index, kwargs))

    async def click(self, **kwargs):
        self._page.clicked.append(self._name)


class FakePage:
    """Just enough page surface for the header, rate and save paths."""

    def __init__(self, fields=(), url='https://x/shop/bundles/create',
                 response=None, counts=None, attrs=None, blank_tiers=()):
        self._fields = list(fields)
        self._blank_tiers = list(blank_tiers)
        self.url = url
        self.filled: list[tuple[str, str]] = []
        self.clicked: list[str] = []
        self.selected: list[tuple[str, dict]] = []
        self.counts = counts or {}
        self.attrs = attrs or {}
        self._response = response

    async def eval_on_selector_all(self, selector, script):
        return self._fields

    async def evaluate(self, script, arg=None):
        return self._blank_tiers

    def locator(self, selector):
        return FakeLocator(self, selector)

    async def wait_for_timeout(self, ms):
        return None

    def expect_response(self, predicate, timeout=None):
        response = self._response
        page = self

        class Ctx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            @property
            def value(self):
                async def _get():
                    if response is None:
                        raise TimeoutError('no response')
                    return response
                return _get()

        return Ctx()


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.ok = 200 <= status < 300
        self.url = 'https://x/api/bundles'
        self._payload = payload

    async def json(self):
        if self._payload is None:
            raise ValueError('not json')
        return self._payload


def _builder():
    return bundle_runner.BundleBuilder(lambda message, level='INFO': None)


# ------------------------------ header --------------------------------

SWITCH = 'button[role="switch"]'


def test_immediate_send_toggles_the_switch_not_the_hidden_checkbox():
    """The <input type=checkbox> is aria-hidden and covered on v2.

    Clicking it bought a 30s timeout per run and left the toggle on when the
    operator had asked for it off — which delivers a bundle they meant to hold.
    """
    page = FakePage(attrs={SWITCH: {'aria-checked': 'true'}})
    asyncio.run(_builder()._fill_header(page, 'B', 'FIXED', False))
    assert SWITCH in page.clicked
    assert not any('checkbox' in name for name in page.clicked)


def test_immediate_send_is_left_alone_when_it_already_matches():
    page = FakePage(attrs={SWITCH: {'aria-checked': 'true'}})
    asyncio.run(_builder()._fill_header(page, 'B', 'FIXED', True))
    assert page.clicked == []


# --------------------------- quantity / tier ---------------------------

QTY = 'input[name^="items."][name$=".quantity"]'


def test_quantity_stops_at_the_last_item_so_rewards_keep_their_amount():
    """A reward becomes items.1 on the same form; overwriting it with 1 would
    silently turn "Ark Gem x500" into "Ark Gem x1"."""
    page = FakePage(counts={QTY: 2})
    asyncio.run(_builder()._fill_qty_tier(
        page, [{'id': '1', 'qty': '7', 'tier': 'Rare'}]))
    assert page.filled == [(QTY, '7')]


def test_reward_rows_are_given_a_tier_rather_than_asked_for_one():
    """v2 files rewards into the item list, so each one demands a Tier.

    A currency has no rank, and a blank required field blocks the create
    button — so the blanks are filled in for the operator.
    """
    page = FakePage(blank_tiers=[1, 2])
    done = asyncio.run(_builder()._fill_blank_tiers(page))
    assert done == 2
    assert [(name, idx, kw.get('label')) for name, idx, kw in page.selected] == [
        ('select', 1, 'Common'), ('select', 2, 'Common')]


def test_a_tier_the_operator_already_chose_is_left_alone():
    page = FakePage(blank_tiers=[])
    assert asyncio.run(_builder()._fill_blank_tiers(page)) == 0
    assert page.selected == []


def test_blank_tier_search_skips_the_bundle_type_select():
    """It shares the page with the tier pickers and has no Common option.

    Selecting Common there fails outright, so the filter must be on the
    options rather than on position.
    """
    assert "o.textContent.trim() === tier" in bundle_runner._BLANK_TIERS
    assert bundle_runner.TIER_DEFAULT == 'Common'


# ------------------------------ draw rate ------------------------------

def test_rate_targets_the_required_field_not_the_display_rate():
    """A card carries a draw rate and a display rate; only the first is required."""
    page = FakePage(fields=[
        {'name': 'items.0.quantity', 'required': True},
        {'name': 'items.0.randomRate', 'required': True},
        {'name': 'items.0.displayRate', 'required': False},
    ])
    asyncio.run(_builder()._fill_rates(page, [{'id': '1', 'rate': '12.5'}]))
    assert page.filled == [('input[name="items.0.randomRate"]', ''),
                           ('input[name="items.0.randomRate"]', '12.5')]


def test_rate_is_skipped_for_items_without_one():
    page = FakePage(fields=[{'name': 'items.0.rate', 'required': True},
                            {'name': 'items.1.rate', 'required': True}])
    asyncio.run(_builder()._fill_rates(
        page, [{'id': '1', 'rate': ''}, {'id': '2', 'rate': '5'}]))
    assert [name for name, _ in page.filled] == [
        'input[name="items.1.rate"]', 'input[name="items.1.rate"]']


# -------------------------------- save --------------------------------

def test_save_reports_the_new_bundle_id():
    page = FakePage(response=FakeResponse(200, {'data': {'bundleId': 90210}}))
    saved, bundle_id = asyncio.run(_builder()._save(page))
    assert saved is True
    assert bundle_id == '90210'


def test_save_reads_the_id_from_the_redirect_when_the_body_has_none():
    page = FakePage(response=FakeResponse(200, None),
                    url='https://x/shop/bundles/4242')
    saved, bundle_id = asyncio.run(_builder()._save(page))
    assert saved is True
    assert bundle_id == '4242'


def test_save_refuses_to_claim_success_on_an_error_response():
    """An error body can carry unrelated numbers — never report one as an id."""
    page = FakePage(response=FakeResponse(500, {'id': 13}),
                    url='https://x/shop/bundles/999')
    saved, bundle_id = asyncio.run(_builder()._save(page))
    assert saved is False
    assert bundle_id is None


def test_save_uses_the_current_v2_create_bundle_button():
    old = "button:has-text('ยืนยันการสร้างบันเดิล')"
    current = "button:has-text('สร้าง Bundle')"
    page = FakePage(
        response=FakeResponse(200, {'data': {'bundleId': 90210}}),
        counts={old: 0, current: 1},
    )
    saved, bundle_id = asyncio.run(_builder()._save(page))
    assert saved is True
    assert bundle_id == '90210'
    assert page.clicked == [current]


def test_save_stops_when_the_confirm_button_is_missing():
    page = FakePage(counts={
        "button:has-text('สร้าง Bundle')": 0,
        "button:has-text('ยืนยันการสร้างบันเดิล')": 0,
    })
    saved, bundle_id = asyncio.run(_builder()._save(page))
    assert saved is False
    assert bundle_id is None
    assert page.clicked == []
