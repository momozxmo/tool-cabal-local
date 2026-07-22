# -*- coding: utf-8 -*-
"""Static contract for the Item Finder browser UI."""
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.path.join(ROOT, 'web', 'static', 'index.html'), encoding='utf-8').read()


def test_ui_exposes_desktop_item_finder_controls():
    required_ids = [
        'modeEvent', 'modeItemcode', 'modeShop', 'game', 'webAny', 'webYes',
        'webNo', 'templateFile', 'planFile', 'btnImportTemplate', 'btnImportPlan',
        'btnClearWorkspace', 'criteriaTable', 'btnSearch', 'btnStop', 'btnSelectAll',
        'btnClearSelection', 'btnCopySelected', 'btnCopyAll', 'btnExportXlsx',
        'btnExportCsv', 'btnBundles', 'resultsTable', 'notFoundList', 'log',
        'btnClearLog', 'sheetDialog', 'bundleDialog',
    ]
    for element_id in required_ids:
        assert ('id="%s"' % element_id) in HTML, element_id


def test_ui_uses_workspace_api_and_handles_regroup_reset():
    required_fragments = [
        '/api/import-template', '/api/import-plan', '/api/import-plan/apply',
        '/api/workspaces/', '/ws/search', 'workspace_id', 'reset_results',
        'selected_indexes', 'navigator.clipboard',
    ]
    for fragment in required_fragments:
        assert fragment in HTML, fragment
    use_workspace = HTML.split('function useWorkspace(data)', 1)[1].split('async function upload', 1)[0]
    assert 'resetResults()' in use_workspace
    assert 'renderNotFound(data.not_found||[])' in use_workspace


def test_ui_has_all_result_columns_and_shop_description():
    for label in ('Aztek ID', 'ชื่อในเว็บ', 'ชื่อในไฟล์', 'พารามิเตอร์ที่เช็ค',
                  'กลุ่ม / ตาราง', 'คำอธิบายไอเทม'):
        assert label in HTML, label


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
        print('PASS', test.__name__)
    print('ALL PASS (%d)' % len(tests))
